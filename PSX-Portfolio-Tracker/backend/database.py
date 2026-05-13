import os
import logging
import time
from functools import wraps
from urllib.parse import urlparse
from dotenv import load_dotenv
from sqlalchemy import create_engine, exc, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from models import Base

# Setup Logging
logger = logging.getLogger(__name__)

load_dotenv()
if not os.getenv("DATABASE_URL"):
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./psx_portfolio.db"

# SQLAlchemy 2.0 requires postgresql:// instead of postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ── Connection Strategy ───────────────────────────────────────────────────────
#
# Port 6543 = Supabase transaction pooler (PgBouncer). Supabase explicitly
# recommends NullPool for this port because PgBouncer already handles pooling
# server-side. Running our own QueuePool on top creates double-pooling and
# causes unpredictable SSL drops.
#
# We use NullPool (one fresh connection per request) with a custom `creator`
# function that retries the SSL handshake up to 3 times before failing.
# This handles transient "SSL connection has been closed unexpectedly" errors
# at the TCP layer without complex pool management.

def _make_pg_connection():
    """
    Open a psycopg2 connection to Supabase, retrying up to 3 times on
    transient SSL / OperationalError failures.
    """
    import psycopg2

    parsed = urlparse(DATABASE_URL)
    host    = parsed.hostname
    port    = parsed.port or 5432
    dbname  = parsed.path.lstrip("/")
    user    = parsed.username
    password = parsed.password

    connect_kwargs = dict(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        connect_timeout=15,
        sslmode="require",
        application_name="pakfolio",
        # TCP Keepalives to prevent "SSL connection closed unexpectedly"
        # especially when using Supabase/PgBouncer which may drop idle sockets.
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    )

    last_exc = None
    for attempt in range(1, 6):   # 5 attempts
        try:
            conn = psycopg2.connect(**connect_kwargs)
            return conn
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            last_exc = e
            if attempt < 5:
                wait = 0.1 * attempt    # 0.1s, 0.2s, 0.3s, 0.4s
                logger.warning(f"DB connect attempt {attempt}/5 failed ({e}). Retrying in {wait:.2f}s…")
                time.sleep(wait)

    logger.error(f"DB connect failed after 5 attempts: {last_exc}")
    raise last_exc


# NullPool + retry creator:
#   - NullPool: each request gets its own fresh connection (no double-pooling
#     on top of PgBouncer which already pools server-side on port 6543).
#   - creator=_make_pg_connection: retries the SSL handshake on failure so
#     transient drops are healed before the request handler even sees them.
engine = create_engine(
    DATABASE_URL,
    creator=_make_pg_connection,
    poolclass=NullPool,
    # Disable SQLAlchemy's compiled-statement cache (incompatible with
    # PgBouncer transaction pooler; prepared statements are not supported)
    execution_options={"compiled_cache": None},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def db_retry(retries=3, delay=1):
    """Decorator to retry a function on transient DB errors."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for i in range(retries):
                try:
                    return func(*args, **kwargs)
                except (exc.OperationalError, exc.InterfaceError, exc.InternalError) as e:
                    last_exception = e
                    logger.warning(
                        f"Database operation error (attempt {i+1}/{retries}): {e}"
                    )
                    
                    # Search for a session in args or kwargs and rollback to clear the poisoned state
                    # before the next retry attempt.
                    for arg in list(args) + list(kwargs.values()):
                        if hasattr(arg, "rollback") and hasattr(arg, "close"):
                            try:
                                arg.rollback()
                                logger.info("Session rolled back after retryable error.")
                            except Exception as rb_err:
                                logger.error(f"Failed to rollback session during retry: {rb_err}")
                                
                    time.sleep(delay * (i + 1))
            raise last_exception
        return wrapper
    return decorator


def check_connection():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True
    except Exception:
        return False


@db_retry(retries=5, delay=2)
def create_tables():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tables created/verified.")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        raise
    finally:
        # Always attempt to rollback any uncommitted/poisoned transaction 
        # before closing the session. This is critical when using PgBouncer 
        # in transaction mode on port 6543.
        try:
            db.rollback()
        except Exception:
            pass
        db.close()
