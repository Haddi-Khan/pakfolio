"""Migration script: SQLite -> PostgreSQL (Supabase)"""

import os
import sqlite3
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import (
    Base, User, Portfolio, Trade, CashTransaction, 
    HistoricalPrice, LivePrice, PasswordResetToken
)

# Look for .env in current dir, then in backend/
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("backend/.env"):
    load_dotenv("backend/.env")
else:
    # Try parent's sibling if run from backend
    load_dotenv("../.env")

# Source
SQLITE_PATH = "psx_portfolio.db"
# Target
PG_URL = os.getenv("DATABASE_URL")

if not PG_URL:
    print("Error: DATABASE_URL not found in .env")
    exit(1)

if PG_URL.startswith("postgres://"):
    PG_URL = PG_URL.replace("postgres://", "postgresql://", 1)

print(f"Connecting to Supabase...")
pg_engine = create_engine(PG_URL)
SessionPG = sessionmaker(bind=pg_engine)
pg_session = SessionPG()

print("Wiping existing data on Supabase for a clean migration...")
# Recreate tables to ensure clean slate
Base.metadata.drop_all(pg_engine)
Base.metadata.create_all(pg_engine)

# Robust SQLite path discovery
possible_sqlite_paths = [
    "psx_portfolio.db",
    "backend/psx_portfolio.db",
    "../backend/psx_portfolio.db"
]
SQLITE_PATH = None
for p in possible_sqlite_paths:
    if os.path.exists(p):
        SQLITE_PATH = p
        break

if not SQLITE_PATH:
    print("Error: Could not find psx_portfolio.db locally.")
    exit(1)

print(f"Connecting to SQLite ({SQLITE_PATH})...")
sqlite_engine = create_engine(f"sqlite:///{SQLITE_PATH}")
SessionLite = sessionmaker(bind=sqlite_engine)
lite_session = SessionLite()

def migrate_table(model):
    print(f"Migrating {model.__tablename__}...")
    items = lite_session.query(model).all()
    count = 0
    for item in items:
        # Clone the object state (expunge from sqlite, make transient)
        lite_session.expunge(item)
        import sqlalchemy.orm
        sqlalchemy.orm.make_transient(item)
        pg_session.add(item)
        count += 1
    
    try:
        pg_session.commit()
        print(f"Successfully migrated {count} rows to {model.__tablename__}")
    except Exception as e:
        pg_session.rollback()
        print(f"Error migrating {model.__tablename__}: {e}")

# Sequence matters for foreign keys
models_to_migrate = [
    User,
    Portfolio,
    Trade,
    CashTransaction,
    HistoricalPrice,
    LivePrice,
    PasswordResetToken
]

for m in models_to_migrate:
    migrate_table(m)

# Reset sequences in Postgres so next auto-increment IDs are correct
print("\nResetting sequences...")
for model in models_to_migrate:
    if hasattr(model, 'id'):
        table_name = model.__tablename__
        try:
            # Postgres specific SQL to reset sequence
            sql = f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), COALESCE(MAX(id), 1)) FROM {table_name};"
            pg_engine.connect().execute(sqlalchemy.text(sql))
            print(f"Reset sequence for {table_name}")
        except Exception as e:
            # Might fail for tables without a sequence or if already correct
            pass

print("\nMigration Complete!")
print("You can now restart the application.")

lite_session.close()
pg_session.close()
