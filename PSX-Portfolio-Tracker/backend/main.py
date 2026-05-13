from datetime import date, timedelta, datetime, timezone
import pytz
PKT = pytz.timezone("Asia/Karachi")
from typing import List, Optional, Dict
import os, csv, io
import time
import resend
import uuid
import concurrent.futures
import threading
import logging
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

logger = logging.getLogger(__name__)

from fastapi import FastAPI, Depends, HTTPException, Query, status, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

import crud
import auth as auth_utils
import portfolio as pf
from portfolio import build_portfolio_chart
from database import get_db, create_tables
from deps import get_current_user
from schemas import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshRequest,
    ForgotPasswordRequest, ResetPasswordRequest, UserOut,
    PortfolioCreate, PortfolioOut, PortfolioUpdate,
    TradeCreate, TradeOut, TradeUpdate,
    CashTxCreate, CashTxOut,
    HoldingOut, PortfolioSummary,
    PriceOut, SymbolSearchResult,
    ResendVerificationRequest,
)
from models import CashTransaction, CashTxType, Trade, TradeAction, TradeType, AssetType, User, GlobalSymbol, LivePrice, HistoryPSX
from email_templates import get_email_template
from auth_social import verify_google_token, verify_facebook_token, verify_apple_token
from data_providers import active_provider
from data_providers.composite_provider import CompositeProvider

# Use the same sarmaaya provider instance as the composite provider to share cache
if isinstance(active_provider, CompositeProvider):
    sarmaaya = active_provider._sarmaaya
else:
    from data_providers.sarmaaya_provider import SarmaayaProvider
    sarmaaya = SarmaayaProvider()

app = FastAPI(title="PSX Portfolio Tracker", version="3.0.0")

# Setup Resend
resend.api_key = os.environ.get("RESEND_API_KEY")
if not resend.api_key:
    logger.warning("RESEND_API_KEY is not set. Emails will not be sent.")
else:
    logger.info("Resend API key initialized.")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
logger.info(f"Frontend URL configured as: {FRONTEND_URL}")
if "pakfolio.pk" in FRONTEND_URL.lower() and "localhost" in os.environ.get("ALLOWED_ORIGINS", ""):
    logger.warning("FRONTEND_URL set to production but ALLOWED_ORIGINS contains localhost. Registration links might point to the wrong place for local testing.")

# Parse origins from environment variable

# CORS middle-ware (parsed later)
env_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "")
origins = [origin.strip() for origin in env_origins.split(",") if origin.strip()]

if not origins:
    # Default to local dev if nothing specified
    origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://psx-portfolio-tracker-.*-nasir41s-projects\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/")
def health_check():
    return {"status": "ok", "message": "PSX Portfolio Tracker API is running"}


@app.on_event("startup")
def on_startup():
    import threading
    import time as _time

    # Move ALL startup tasks to background so the server starts INSTANTLY
    def _retry_step(name, fn, retries=5, base_delay=5):
        """Run fn(), retrying up to `retries` times on transient DB errors."""
        for attempt in range(1, retries + 1):
            try:
                fn()
                logger.info(f"Background Startup: '{name}' succeeded (attempt {attempt}).")
                return True
            except Exception as e:
                wait = base_delay * attempt
                logger.warning(
                    f"Background Startup: '{name}' failed (attempt {attempt}/{retries}): {e}. "
                    f"Retrying in {wait}s..."
                )
                _time.sleep(wait)
        logger.error(f"Background Startup: '{name}' permanently failed after {retries} attempts.")
        return False

    def heavy_startup():
        from database import check_connection, create_tables

        logger.info("Background Startup: Initializing...")

        # Step 1 — verify connection (non-fatal if it fails, subsequent steps will also fail/retry)
        _retry_step("check_connection", check_connection)

        # Step 2 — create/verify tables (critical; retry aggressively)
        if not _retry_step("create_tables", create_tables):
            logger.error("Background Startup: Cannot create tables. Skipping dependent steps.")
            return  # No point continuing if the schema doesn't exist

        # Step 3 — register mutual funds (non-critical, don't abort on failure)
        try:
            _register_mutual_funds()
        except Exception as e:
            logger.warning(f"Background Startup: '_register_mutual_funds' failed (non-critical): {e}")

        # Step 4 — seed + sync (non-critical; each independently retried)
        logger.info("Background Startup: Seeding/Syncing started...")
        _retry_step("seed_initial_data", _seed_initial_data, retries=3, base_delay=5)
        _retry_step("sync_symbols", _sync_symbols_if_needed, retries=3, base_delay=5)

        # Step 5 — start scheduler (critical; retry a few times)
        def _start_scheduler():
            from scheduler import start_scheduler
            start_scheduler()

        _retry_step("start_scheduler", _start_scheduler, retries=3, base_delay=5)

        # Step 6 — warm the history cache for popular symbols (non-critical)
        def _warm_history_cache():
            """Pre-fetch 1M history for the most active symbols into the in-memory cache."""
            from database import SessionLocal
            from datetime import date, timedelta
            import time as _t
            # _history_cache / _history_cache_expiry are module-level dicts in main.py

            popular = [
                "OGDC", "PPL", "ENGRO", "LUCK", "HBL", "MCB", "UBL", "BAHL",
                "HUBC", "PSO", "HASCOL", "FFC", "MEBL", "NESTLE", "DGKC",
                "CHCC", "MLCF", "POL", "SEARL", "TRG",
            ]
            today = date.today()
            from_dt = today - timedelta(days=30)
            from_str = from_dt.isoformat()
            to_str = today.isoformat()

            db = SessionLocal()
            try:
                for sym in popular:
                    try:
                        cache_key = f"{sym}_{from_str}_{to_str}"
                        now = _t.time()
                        if cache_key in _history_cache and now < _history_cache_expiry.get(cache_key, 0):
                            continue  # Already cached
                        # Fetch with retry logic via CRUD
                        rows = crud.get_history_points(db, sym, from_dt, today, 35)
                        rows.reverse() # Matches the asc order expected by the loop below
                        if rows:
                            history_list = [
                                {
                                    "date": p.date.isoformat(),
                                    "open": float(p.open) if p.open else None,
                                    "high": float(p.high) if p.high else None,
                                    "low": float(p.low) if p.low else None,
                                    "close": float(p.close) if p.close else None,
                                    "volume": float(p.volume) if p.volume else None,
                                    "sma_50": float(p.sma_50) if p.sma_50 is not None else None,
                                    "sma_200": float(p.sma_200) if p.sma_200 is not None else None,
                                    "sma_20": float(p.sma_20) if p.sma_20 is not None else None,
                                    "bbl_20_2_0": float(p.bbl_20_2_0) if p.bbl_20_2_0 is not None else None,
                                    "bbu_20_2_0": float(p.bbu_20_2_0) if p.bbu_20_2_0 is not None else None,
                                    "rsi_14": float(p.rsi_14) if p.rsi_14 is not None else None,
                                }
                                for p in rows
                            ]
                            _history_cache[cache_key] = history_list
                            _history_cache_expiry[cache_key] = _t.time() + 1800
                            logger.info(f"Warm cache: {sym} ({len(rows)} points)")
                    except Exception as e:
                        logger.warning(f"Warm cache failed for {sym}: {e}")
                        break   # Stop warming if DB is having issues
            finally:
                db.close()

        try:
            _warm_history_cache()
        except Exception as e:
            logger.warning(f"Background Startup: history cache warm failed (non-critical): {e}")

        logger.info("Background Startup: All background tasks initialized.")

    threading.Thread(target=heavy_startup, daemon=True).start()


@app.on_event("shutdown")
def on_shutdown():
    from scheduler import stop_scheduler
    stop_scheduler()


def _register_mutual_funds():
    """Register all known mutual fund symbols with the composite provider."""
    from data_providers.composite_provider import CompositeProvider, MUTUAL_FUND_NAMES
    if isinstance(active_provider, CompositeProvider):
        for symbol, name in MUTUAL_FUND_NAMES.items():
            active_provider.register_mutual_fund(symbol, name)


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/api/auth/register", response_model=Dict, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, data.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    
    user = crud.create_user(db, data.email, data.password)
    
    # Generate verification token
    token = str(uuid.uuid4())
    user.verification_token = token
    user.is_verified = False
    now = datetime.now(timezone.utc)
    user.last_verification_sent_at = now
    user.verification_sent_count = 1
    
    db.commit()
    
    # Send Verification Email via Resend
    if resend.api_key:
        try:
            title = "Verify your account"
            body = f"<p>Welcome to Pakfolio! We're excited to have you on board.</p><p>To get started tracking your investments in the Pakistan Stock Exchange, please verify your email address by clicking the button below:</p>"
            html_content = get_email_template(title, body, "Verify Account", f"{FRONTEND_URL}/verify?token={token}")
            
            params = {
                "from": "Pakfolio Support <help@pakfolio.pk>",
                "to": user.email,
                "subject": "Verify your Pakfolio Account",
                "html": html_content
            }
            verification_link = f"{FRONTEND_URL}/verify?token={token}"
            logger.info("\n" + "="*50)
            logger.info("VERIFICATION LINK GENERATED:")
            logger.info(verification_link)
            logger.info("="*50 + "\n")
            
            logger.info(f"Attempting to send verification email to {user.email}...")
            r = resend.Emails.send(params)
            logger.info(f"Resend response: {r}")
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {e}")
    else:
        verification_link = f"{FRONTEND_URL}/verify?token={token}"
        logger.info("\n" + "="*50)
        logger.info("RESEND API KEY MISSING! VERIFICATION LINK (COPY MANUALLY):")
        logger.info(verification_link)
        logger.info("="*50 + "\n")
        logger.warning(f"Registration successful for {user.username} but email not sent because Resend API key is missing.")
            
    return {"message": "Registration successful. Please check your email (or terminal log) to verify your account."}


@app.post("/api/auth/resend-verification")
def resend_verification(data: ResendVerificationRequest, db: Session = Depends(get_db)):
    # 1. Find user by username or email
    user = db.query(User).filter(
        (User.username == data.username_or_email.lower()) | 
        (User.email == data.username_or_email.lower())
    ).first()
    
    if not user:
        # For security, we return success even if user not found to prevent user enumeration
        return {"message": "If the account exists and is not yet verified, a verification email has been sent."}
    
    if user.is_verified:
        return {"message": "Account is already verified."}
        
    now = datetime.now(timezone.utc)
    if user.last_verification_sent_at:
        # Ensure it is timezone-aware if we are comparing with UTC
        last_sent = user.last_verification_sent_at
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)
            
        # Cooldown check: 2 minutes
        if now - last_sent < timedelta(minutes=2):
            diff = timedelta(minutes=2) - (now - last_sent)
            seconds = int(diff.total_seconds())
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS, 
                f"Please wait {seconds} seconds before requesting another email."
            )
            
        # Daily limit check: 5 times
        if now.date() == last_sent.date():
            if user.verification_sent_count >= 5:
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS, 
                    "Daily limit of 5 verification emails reached. Please try again tomorrow."
                )
            user.verification_sent_count += 1
        else:
            # New day, reset count
            user.verification_sent_count = 1
    else:
        # First time resending
        user.verification_sent_count = 1
        
    # Generate new token
    token = str(uuid.uuid4())
    user.verification_token = token
    user.last_verification_sent_at = now
    
    db.commit()
    
    # Send Verification Email
    if resend.api_key:
        try:
            title = "Verify your account"
            body = f"<p>Welcome back! You requested a new verification link for your Pakfolio account.</p><p>Please verify your email address by clicking the button below:</p>"
            html_content = get_email_template(title, body, "Verify Account", f"{FRONTEND_URL}/verify?token={token}")
            
            params = {
                "from": "Pakfolio Support <help@pakfolio.pk>",
                "to": user.email,
                "subject": "Verify your Pakfolio Account",
                "html": html_content
            }
            verification_link = f"{FRONTEND_URL}/verify?token={token}"
            logger.info("\n" + "="*50)
            logger.info("VERIFICATION LINK GENERATED (RESEND):")
            logger.info(verification_link)
            logger.info("="*50 + "\n")
            
            logger.info(f"Resending verification email to {user.email}...")
            r = resend.Emails.send(params)
            logger.info(f"Resend response: {r}")
        except Exception as e:
            logger.error(f"Failed to resend verification email to {user.email}: {e}")
            
    return {"message": "If the account exists and is not yet verified, a verification email has been sent."}


@app.get("/api/auth/verify")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired verification token")
        
    user.is_verified = True
    user.verification_token = None
    db.commit()
    return {"message": "Email verified successfully. You can now log in."}


@app.post("/api/auth/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Please verify your email address before logging in.")
        
    return _make_tokens(user)


class SocialAuthRequest(BaseModel):
    token: str

@app.post("/api/auth/social/{provider}", response_model=TokenResponse)
async def social_login(provider: str, data: SocialAuthRequest, db: Session = Depends(get_db)):
    """
    Unified endpoint for social login/registration.
    """
    user_info = None
    if provider == "google":
        user_info = await verify_google_token(data.token)
    elif provider == "facebook":
        user_info = await verify_facebook_token(data.token)
    elif provider == "apple":
        user_info = await verify_apple_token(data.token)
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsupported provider")

    if not user_info or not user_info.get("email"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid social token or missing email from {provider}")

    email = user_info["email"].lower()
    provider_user_id = user_info["sub"]
    avatar_url = user_info.get("picture")

    # 1. Try finding existing social link
    user = crud.get_user_by_social(db, provider, provider_user_id)
    
    if not user:
        # 2. Try finding user by email
        user = crud.get_user_by_email(db, email)
        if user:
            # Link existing user to this social account
            crud.link_social_account(db, user.id, provider, provider_user_id)
            if not user.avatar_url:
                user.avatar_url = avatar_url
                db.commit()
        else:
            # 3. Create new pre-verified user
            user = crud.create_user_from_social(db, email, avatar_url)
            crud.link_social_account(db, user.id, provider, provider_user_id)

    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User account is disabled")

    return _make_tokens(user)


@app.post("/api/auth/refresh", response_model=TokenResponse)
def refresh_token(data: RefreshRequest, db: Session = Depends(get_db)):
    payload = auth_utils.decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")
    user = crud.get_user(db, int(payload["sub"]))
    if not user or not user.is_active or not user.is_verified:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or unverified")
    return _make_tokens(user)


@app.post("/api/auth/forgot-password", status_code=200)
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, data.email)
    if user:
        # Use the secure token generation in crud.py
        token_raw = crud.create_reset_token(db, user)
        
        if resend.api_key:
            try:
                title = "Reset your password"
                body = f"<p>We received a request to reset the password for your Pakfolio account.</p><p>Click the button below to choose a new password. This link will expire in 1 hour.</p>"
                html_content = get_email_template(title, body, "Reset Password", f"{FRONTEND_URL}/reset-password?token={token_raw}")
                
                resend.Emails.send({
                    "from": "Pakfolio Support <help@pakfolio.pk>",
                    "to": user.email,
                    "subject": "Reset your Pakfolio Password",
                    "html": html_content
                })
            except Exception as e:
                logger.error(f"Failed to send reset email: {e}")

    return {"message": "If that email is registered, a password reset link has been sent."}


@app.post("/api/auth/reset-password", status_code=200)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    # Use the secure token verification in crud.py
    token_obj = crud.get_valid_reset_token(db, data.token)
    
    if not token_obj:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset token")
        
    crud.use_reset_token(db, token_obj, data.new_password)
    
    return {"message": "Password reset successfully"}


@app.get("/api/auth/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


def _register_mf_from_holdings(raw: dict):
    """Register any mutual fund symbols found in holdings with the composite provider."""
    from data_providers.composite_provider import CompositeProvider
    if not isinstance(active_provider, CompositeProvider):
        return
    from models import AssetType
    for sym, data in raw.items():
        if data.get("asset_type") == AssetType.MUTUAL_FUND:
            name = data.get("name") or sym
            active_provider.register_mutual_fund(sym, name)


def _make_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=auth_utils.create_access_token(user.id),
        refresh_token=auth_utils.create_refresh_token(user.id),
    )


# ── Portfolios ────────────────────────────────────────────────────────────────

@app.get("/api/portfolios", response_model=List[PortfolioOut])
def list_portfolios(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_portfolios(db, current_user.id)


@app.post("/api/portfolios", response_model=PortfolioOut, status_code=201)
def create_portfolio(
    data: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.create_portfolio(db, data, current_user.id)


@app.get("/api/portfolios/{pid}", response_model=PortfolioOut)
def get_portfolio(
    pid: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = crud.get_portfolio(db, pid, current_user.id)
    if not p:
        raise HTTPException(404, "Portfolio not found")
    return p


@app.post("/api/portfolios/{pid}/set-default", response_model=PortfolioOut)
def set_default(
    pid: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = crud.set_default_portfolio(db, pid, current_user.id)
    if not p:
        raise HTTPException(404, "Portfolio not found")
    return p


@app.delete("/api/portfolios/{pid}", status_code=204)
def delete_portfolio(
    pid: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    portfolios = crud.get_portfolios(db, current_user.id)
    if len(portfolios) <= 1:
        raise HTTPException(400, "Cannot delete the only portfolio")
    if not crud.delete_portfolio(db, pid, current_user.id):
        raise HTTPException(404, "Portfolio not found")


def _get_pid(pid: Optional[int], user_id: int, db: Session) -> int:
    if pid:
        p = crud.get_portfolio(db, pid, user_id)
        if not p:
            raise HTTPException(404, "Portfolio not found")
        return pid
    p = crud.get_default_portfolio(db, user_id)
    if not p:
        raise HTTPException(400, "No portfolio found. Create one first.")
    return p.id


# ── Trades ────────────────────────────────────────────────────────────────────

@app.get("/api/trades", response_model=List[TradeOut])
def list_trades(
    portfolio_id: Optional[int] = None,
    symbol: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pid = _get_pid(portfolio_id, current_user.id, db)
    return [_trade_out(t) for t in crud.get_trades(db, pid, symbol=symbol)]


@app.post("/api/trades", response_model=TradeOut, status_code=201)
def add_trade(
    trade: TradeCreate,
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pid = _get_pid(portfolio_id, current_user.id, db)
    return _trade_out(crud.create_trade(db, pid, trade))


@app.delete("/api/trades/{trade_id}", status_code=204)
def remove_trade(
    trade_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trade = crud.get_trade(db, trade_id)
    if not trade:
        raise HTTPException(404, "Trade not found")
    portfolio = crud.get_portfolio(db, trade.portfolio_id, current_user.id)
    if not portfolio:
        raise HTTPException(403, "Not authorized")
    crud.delete_trade(db, trade_id)


@app.put("/api/trades/{trade_id}", response_model=TradeOut)
def update_trade(
    trade_id: int,
    trade_data: TradeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trade = crud.get_trade(db, trade_id)
    if not trade:
        raise HTTPException(404, "Trade not found")
    portfolio = crud.get_portfolio(db, trade.portfolio_id, current_user.id)
    if not portfolio:
        raise HTTPException(403, "Not authorized")
    updated = crud.update_trade(db, trade_id, trade_data)
    return _trade_out(updated)


@app.get("/api/trades/export")
def export_activity(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pid = _get_pid(portfolio_id, current_user.id, db)
    trades = crud.get_trades(db, pid, limit=5000)
    cash_txs = crud.get_cash_transactions(db, pid, limit=5000)
    
    # Combine and normalize
    activity = []
    for t in trades:
        activity.append({
            "date": t.trade_date.isoformat(),
            "type": "TRADE",
            "symbol": t.symbol,
            "action": t.action.value,
            "price_amount": float(t.price),
            "quantity": float(t.quantity),
            "deductions": float(t.deductions),
            "notes": t.notes or ""
        })
    for c in cash_txs:
        activity.append({
            "date": c.tx_date.isoformat(),
            "type": "CASH",
            "symbol": "CASH",
            "action": c.tx_type.value,
            "price_amount": float(c.amount),
            "quantity": 1.0,
            "deductions": 0.0,
            "notes": c.description or ""
        })
    
    # Sort by date
    activity.sort(key=lambda x: x["date"])
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "type", "symbol", "action", "price_amount", "quantity", "deductions", "notes"])
    
    for row in activity:
        writer.writerow([
            row["date"], row["type"], row["symbol"], row["action"],
            row["price_amount"], row["quantity"], row["deductions"], row["notes"]
        ])
    
    output.seek(0)
    filename = f"portfolio-export-{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.post("/api/trades/import")
async def import_activity(
    portfolio_id: Optional[int] = None,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pid = _get_pid(portfolio_id, current_user.id, db)
    
    content = await file.read()
    decoded = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))
    
    imported_count = 0
    errors = []
    
    for row in reader:
        try:
            row_type = row.get("type", "TRADE").upper()
            if row_type == "TRADE":
                trade_data = TradeCreate(
                    symbol=row["symbol"],
                    name=row.get("name"),
                    action=row["action"],
                    trade_type=row.get("trade_type", "LONG"),
                    asset_type=row.get("asset_type", "stock"),
                    price=float(row["price_amount"] if "price_amount" in row else row.get("price", 0)),
                    quantity=float(row["quantity"]),
                    deductions=float(row.get("deductions", 0)),
                    trade_date=date.fromisoformat(row["date"] if "date" in row else row["trade_date"]),
                    notes=row.get("notes")
                )
                crud.create_trade(db, pid, trade_data)
            elif row_type == "CASH":
                cash_data = CashTxCreate(
                    tx_type=row["action"], # DEPOSIT or WITHDRAWAL
                    amount=float(row["price_amount"]),
                    tx_date=date.fromisoformat(row["date"]),
                    description=row.get("notes")
                )
                crud.create_cash_tx(db, pid, cash_data)
            
            imported_count += 1
        except Exception as e:
            errors.append(f"Row {reader.line_num}: {str(e)}")
            
    return {
        "status": "success",
        "imported": imported_count,
        "errors": errors
    }


# ── Cash ──────────────────────────────────────────────────────────────────────

@app.get("/api/cash", response_model=List[CashTxOut])
def list_cash(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pid = _get_pid(portfolio_id, current_user.id, db)
    return crud.get_cash_transactions(db, pid)


@app.post("/api/cash", response_model=CashTxOut, status_code=201)
def add_cash_tx(
    tx: CashTxCreate,
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pid = _get_pid(portfolio_id, current_user.id, db)
    return crud.create_cash_tx(db, pid, tx)


@app.get("/api/cash/balance")
def cash_balance(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pid = _get_pid(portfolio_id, current_user.id, db)
    return {"balance": crud.get_cash_balance(db, pid)}


# ── Holdings ──────────────────────────────────────────────────────────────────

@app.get("/api/holdings", response_model=List[HoldingOut])
def get_holdings(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pid = _get_pid(portfolio_id, current_user.id, db)
    raw, _, _ = crud.get_holdings_raw(db, pid)
    if not raw:
        return []
    _register_mf_from_holdings(raw)
    quotes = _get_quotes_optimized(db, list(raw.keys()))
    return pf.build_holdings(raw, quotes)


# ── Portfolio Summary ─────────────────────────────────────────────────────────

@app.get("/api/portfolio/summary", response_model=PortfolioSummary)
def portfolio_summary(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pid = _get_pid(portfolio_id, current_user.id, db)
    port = crud.get_portfolio(db, pid, current_user.id)
    raw, realized, win_loss = crud.get_holdings_raw(db, pid)
    if raw:
        _register_mf_from_holdings(raw)
    quotes = _get_quotes_optimized(db, list(raw.keys())) if raw else {}
    holdings = pf.build_holdings(raw, quotes)
    cash = crud.get_cash_balance(db, pid)
    deposited = crud.get_total_deposited(db, pid)
    return pf.build_summary(pid, port.name, holdings, cash, deposited, realized, win_loss)


# ── Portfolio Chart ───────────────────────────────────────────────────────────

def _get_historical_with_persistence(db: Session, symbol: str, asset_type: AssetType, from_date: str, to_date: str, background_tasks: Optional[BackgroundTasks] = None) -> List:
    """Gets history from DB, falling back to API and saving results."""
    start_dt = date.fromisoformat(from_date)
    end_dt = date.fromisoformat(to_date)
    
    # 1. Try DB first (both historical_prices and history_psx)
    db_prices = crud.get_historical_prices(db, symbol, start_dt, end_dt)
    
    # Also check history_psx table which has richer data
    from models import HistoryPSX
    from sqlalchemy import func
    
    psx_query = db.query(HistoryPSX).filter(HistoryPSX.symbol == symbol.upper())
    if from_date != "1990-01-01":
        psx_query = psx_query.filter(HistoryPSX.date >= start_dt)
        
    psx_data = psx_query.filter(HistoryPSX.date <= end_dt).order_by(HistoryPSX.date.asc()).all()

    # Merge or prioritize psx_data
    combined_points = []
    if psx_data:
        from data_providers.base import OHLCVPoint
        combined_points = [
            OHLCVPoint(
                date=p.date.isoformat(),
                open=float(p.open or p.close or 0),
                high=float(p.high or p.close or 0),
                low=float(p.low or p.close or 0),
                close=float(p.close or 0),
                volume=float(p.volume or 0)
            )
            for p in psx_data
        ]
    elif db_prices:
        from data_providers.base import OHLCVPoint
        combined_points = [
            OHLCVPoint(
                date=p.date.isoformat(), 
                open=float(p.price), 
                high=float(p.price), 
                low=float(p.price), 
                close=float(p.price), 
                volume=0
            )
            for p in db_prices if p.date
        ]

    # Check freshness
    has_recent = False
    if combined_points:
        last_date_str = combined_points[-1].date
        last_date = date.fromisoformat(last_date_str)
        if last_date >= (date.today() - timedelta(days=3)):
            has_recent = True

    if combined_points and has_recent:
        return combined_points

    # 2. Fallback to API
    api_points = active_provider.get_historical(symbol, from_date, to_date)
    if api_points:
        if background_tasks:
            def bg_save_history():
                from database import SessionLocal
                with SessionLocal() as bg_db:
                    to_save = [{"date": p.date, "price": p.close} for p in api_points]
                    crud.save_historical_prices(bg_db, symbol, to_save, asset_type)
            background_tasks.add_task(bg_save_history)
        return api_points

    # 3. Last fallback
    if db_prices:
        from data_providers.base import OHLCVPoint
        return [
            OHLCVPoint(
                date=p.date.isoformat(), 
                open=float(p.price), 
                high=float(p.price), 
                low=float(p.price), 
                close=float(p.price), 
                volume=0
            )
            for p in db_prices if p.date
        ]
    
    return []


def _get_quotes_optimized(db: Session, symbols: List[str]) -> Dict[str, any]:
    """
    Returns a mix of DB-cached and fresh quotes.
    If DB quotes are > 5 mins old, they are refreshed in background.
    """
    if not symbols: return {}

    # 1. Get whatever we have in DB
    db_prices = crud.get_live_prices(db, symbols)
    
    now = datetime.utcnow()
    to_refresh = []
    result = {}
    
    for sym in symbols:
        p = db_prices.get(sym.upper())
        # If missing or > 5 mins old, mark for refresh
        if not p or (now - p.updated_at) > timedelta(minutes=5):
            to_refresh.append(sym)
        
        if p:
            from data_providers.base import QuoteData
            result[sym.upper()] = QuoteData(
                symbol=p.symbol, price=float(p.price), change=float(p.change or 0),
                change_pct=float(p.change_pct or 0), open=float(p.open or 0), high=float(p.high or 0),
                low=float(p.low or 0), prev_close=float(p.prev_close or 0)
            )

    # 2. If nothing to refresh, return. Otherwise, refresh if any are MISSING in DB.
    # We want to return INSTANTLY if we have old data, and refresh in background.
    # However, for MISSING symbols, we must fetch synchronously.
    missing = [s for s in to_refresh if s.upper() not in result]
    
    if missing:
        fresh_raw = active_provider.get_quotes_bulk(missing)
        # Only save and update with valid prices
        fresh = {s: q for s, q in fresh_raw.items() if q.price is not None}
        crud.save_live_prices(db, fresh)
        result.update(fresh)
        to_refresh = [s for s in to_refresh if s not in missing]

    # 3. Background refresh for stale-but-existing data
    if to_refresh:
        def background_refresh():
            # Create a NEW DB session for the background thread
            from database import SessionLocal
            refresh_db = SessionLocal()
            try:
                logger.info(f"Background refresh starting for {len(to_refresh)} symbols")
                fresh_raw = active_provider.get_quotes_bulk(to_refresh)
                fresh = {s: q for s, q in fresh_raw.items() if q.price is not None}
                crud.save_live_prices(refresh_db, fresh)
                logger.info("Background refresh completed")
            except Exception as e:
                logger.error(f"Background refresh failed: {e}")
            finally:
                refresh_db.close()
        
        threading.Thread(target=background_refresh, daemon=True).start()

    return result


@app.get("/api/portfolio/chart")
def portfolio_chart(
    background_tasks: BackgroundTasks,
    portfolio_id: Optional[int] = None,
    period: str = Query("1M", pattern="^(1W|1M|3M|6M|1Y|5Y|10Y|ALL)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pid = _get_pid(portfolio_id, current_user.id, db)
    raw, _, _ = crud.get_holdings_raw(db, pid)
    # Don't return early anymore, we need to show cash even if no stocks
    # if not raw:
    #     return []

    today = date.today()
    period_map = {
        "1W": timedelta(weeks=1), "1M": timedelta(days=30),
        "3M": timedelta(days=90), "6M": timedelta(days=180),
        "1Y": timedelta(days=365), "5Y": timedelta(days=1825), 
        "10Y": timedelta(days=3650), "ALL": timedelta(days=12775),
    }
    from_date = (today - period_map[period]).isoformat()
    to_date = today.isoformat()

    # Parallelize history fetching
    historical = {}
    from database import SessionLocal
    
    def fetch_with_new_session(sym, h_data):
        # Each thread gets its OWN isolated session
        thread_db = SessionLocal()
        try:
            at = h_data.get("asset_type", AssetType.STOCK)
            return _get_historical_with_persistence(thread_db, sym, at, from_date, to_date, background_tasks)
        finally:
            thread_db.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_sym = {
            executor.submit(fetch_with_new_session, sym, h): sym
            for sym, h in raw.items()
        }
        for future in concurrent.futures.as_completed(future_to_sym):
            sym = future_to_sym[future]
            try:
                historical[sym] = future.result()
            except Exception as e:
                logger.error(f"Failed parallel history fetch for {sym}: {e}")
                historical[sym] = []

    quotes = _get_quotes_optimized(db, list(raw.keys()))
    
    # Inject today's live price to make the chart accurate to the second
    today_str = date.today().isoformat()
    for sym, q in quotes.items():
        if sym in historical and q.price:
            # Add today if not already present in the history
            if not any(p.date == today_str for p in historical[sym]):
                from data_providers.base import OHLCVPoint
                historical[sym].append(OHLCVPoint(
                    date=today_str,
                    open=q.open or q.price,
                    high=q.high or q.price,
                    low=q.low or q.price,
                    close=q.price,
                    volume=q.volume or 0
                ))

    # Correct cash timeline: Needs to include trade costs, not just deposits
    cash_txs = crud.get_cash_transactions(db, pid, limit=2000)
    trades = crud.get_trades(db, pid, limit=2000)
    
    # Combine all events that affect cash vs principle invested
    events = []
    for tx in cash_txs:
        tx_amt = float(tx.amount)
        delta = tx_amt if tx.tx_type == CashTxType.DEPOSIT else -tx_amt
        events.append({"date": tx.tx_date.isoformat(), "delta": delta, "is_principal": True})

    for t in trades:
        t_price = float(t.price)
        t_qty = float(t.quantity)
        t_ded = float(t.deductions)
        # BUY: cash out, SELL: cash in
        delta = -(t_price * t_qty + t_ded) if t.action == TradeAction.BUY else (t_price * t_qty - t_ded)
        events.append({"date": t.trade_date.isoformat(), "delta": delta, "is_principal": False})
        
    events.sort(key=lambda x: x["date"])
    
    cash_timeline = []
    running_cash = 0.0
    running_invested = 0.0
    for ev in events:
        running_cash += ev["delta"]
        if ev["is_principal"]:
            running_invested += ev["delta"]
        
        cash_timeline.append({
            "date": ev["date"], 
            "running_cash": running_cash,
            "invested_value": running_invested
        })

    # 4. Fetch Benchmark (KSE-100)
    # Use a shorter timeout or skip if it's too slow to avoid blocking the whole chart
    try:
        bench_hist = _get_historical_with_persistence(db, "KSE100", AssetType.STOCK, from_date, to_date, background_tasks)
    except Exception as e:
        logger.warning(f"Benchmark fetch failed: {e}")
        bench_hist = []

    return pf.build_portfolio_chart(
        trades, 
        historical, 
        cash_timeline, 
        from_date=from_date,
        benchmark_history=bench_hist
    )


# ── Prices (public — no auth needed) ─────────────────────────────────────────

@app.get("/api/prices/{symbol}", response_model=PriceOut)
def get_price(symbol: str, db: Session = Depends(get_db)):
    symbol = symbol.upper()
    
    try:
        # 1. Try fetching from local DB first (populated by scheduler)
        from models import LivePrice, GlobalSymbol
        db_price = db.query(LivePrice).filter(LivePrice.symbol == symbol).first()
        
        if db_price and db_price.price is not None:
            return PriceOut(
                symbol=db_price.symbol,
                price=float(db_price.price),
                change=float(db_price.change) if db_price.change is not None else None,
                change_pct=float(db_price.change_pct) if db_price.change_pct is not None else None,
                volume=float(db_price.volume) if db_price.volume is not None else None,
                open=float(db_price.open) if db_price.open is not None else None,
                high=float(db_price.high) if db_price.high is not None else None,
                low=float(db_price.low) if db_price.low is not None else None,
                prev_close=float(db_price.prev_close) if db_price.prev_close is not None else None,
            )
    except Exception as e:
        logger.warning(f"get_price DB error for {symbol} (transient?): {e}")

    # 2. Fallback to active provider if DB is empty or errored
    try:
        q = active_provider.get_quote(symbol)
        
        # If change is missing, try to find yesterday's close in DB
        try:
            if (q.change is None or q.prev_close is None) and q.price:
                last_eod = db.query(HistoryPSX).filter(
                    HistoryPSX.symbol == symbol
                ).order_by(HistoryPSX.date.desc()).first()
                
                if last_eod:
                    q.prev_close = float(last_eod.close)
                    q.change = q.price - q.prev_close
                    if q.prev_close > 0:
                        q.change_pct = (q.change / q.prev_close) * 100
        except Exception:
            pass  # prev_close enrichment is optional

        return _price_out(q)
    except Exception as e:
        logger.warning(f"get_price provider error for {symbol}: {e}")
        # Last resort: return a minimal stub so frontend doesn't crash
        from data_providers.base import QuoteData
        return _price_out(QuoteData(symbol=symbol, price=None))




# Cache for history to avoid heavy DB queries
_history_cache = {}
_history_cache_expiry = {}
# Cache for bulk prices (30s TTL — refreshed by scheduler)
_bulk_prices_cache = {}
_bulk_prices_cache_expiry = 0


@app.get("/api/prices/{symbol}/history")
def get_price_history(
    symbol: str,
    background_tasks: BackgroundTasks,
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    db: Session = Depends(get_db)
):
    symbol = symbol.upper()
    cache_key = f"{symbol}_{from_date}_{to_date}"
    now = time.time()
    
    # 1. Check cache (5 minute TTL for history)
    if cache_key in _history_cache and now < _history_cache_expiry.get(cache_key, 0):
        return _history_cache[cache_key]

    try:
        start_dt = date.fromisoformat(from_date)
        end_dt = date.fromisoformat(to_date)
        
        # Calculate point limit based on range
        try:
            days_diff = (end_dt - start_dt).days
            if days_diff <= 8: point_limit = 10
            elif days_diff <= 35: point_limit = 35
            elif days_diff <= 190: point_limit = 200
            elif days_diff <= 370: point_limit = 400
            else: point_limit = 800 # Downsample for 5Y/10Y/ALL
        except:
            point_limit = 800

        # Fetch from DB (with retry)
        psx_points = crud.get_history_points(db, symbol, start_dt, end_dt, point_limit)
        
        psx_points.reverse()

        # Latest valid indicators — use the last point that has them to fill forward
        last_valid_indicators = next(
            (p for p in reversed(psx_points) if p.sma_20 is not None),
            None
        )
        # If none in the current window, do a quick DB look-back (only if needed, with retry)
        if last_valid_indicators is None:
            last_valid_indicators = crud.get_latest_indicators(db, symbol)

        history_list = []
        for p in psx_points:
            point = {
                "date": p.date.isoformat(), 
                "open": float(p.open) if p.open else None, 
                "high": float(p.high) if p.high else None,
                "low": float(p.low) if p.low else None, 
                "close": float(p.close) if p.close else None, 
                "volume": float(p.volume) if p.volume else None,
                "sma_50": float(p.sma_50) if p.sma_50 is not None else None,
                "sma_200": float(p.sma_200) if p.sma_200 is not None else None,
                "sma_20": float(p.sma_20) if p.sma_20 is not None else None,
                "bbl_20_2_0": float(p.bbl_20_2_0) if p.bbl_20_2_0 is not None else None,
                "bbu_20_2_0": float(p.bbu_20_2_0) if p.bbu_20_2_0 is not None else None,
                "rsi_14": float(p.rsi_14) if p.rsi_14 is not None else None,
            }
            # Forward-fill all indicators from last known valid row
            # This ensures BBU/BBL/SMA lines don't drop to null for today's live point
            if point["sma_20"] is None and last_valid_indicators:
                point["sma_20"]     = float(last_valid_indicators.sma_20)     if last_valid_indicators.sma_20     is not None else None
                point["sma_50"]     = float(last_valid_indicators.sma_50)     if last_valid_indicators.sma_50     is not None else None
                point["sma_200"]    = float(last_valid_indicators.sma_200)    if last_valid_indicators.sma_200    is not None else None
                point["bbu_20_2_0"] = float(last_valid_indicators.bbu_20_2_0) if last_valid_indicators.bbu_20_2_0 is not None else None
                point["bbl_20_2_0"] = float(last_valid_indicators.bbl_20_2_0) if last_valid_indicators.bbl_20_2_0 is not None else None
                point["rsi_14"]     = float(last_valid_indicators.rsi_14)     if last_valid_indicators.rsi_14     is not None else None
            
            history_list.append(point)

        # Inject today's live price as the latest point (with retry)
        live_map = crud.get_live_prices(db, [symbol])
        live_quote = live_map.get(symbol)
        if live_quote and live_quote.price and float(live_quote.price) > 0:
            today_str = date.today().isoformat()
            if not history_list or history_list[-1]["date"] < today_str:
                history_list.append({
                    "date": today_str,
                    "open":  float(live_quote.open  or live_quote.price),
                    "high":  float(live_quote.high  or live_quote.price),
                    "low":   float(live_quote.low   or live_quote.price),
                    "close": float(live_quote.price),
                    "volume": int(live_quote.volume or 0),
                    "sma_20":     float(last_valid_indicators.sma_20)     if last_valid_indicators and last_valid_indicators.sma_20     else None,
                    "sma_50":     float(last_valid_indicators.sma_50)     if last_valid_indicators and last_valid_indicators.sma_50     else None,
                    "sma_200":    float(last_valid_indicators.sma_200)    if last_valid_indicators and last_valid_indicators.sma_200    else None,
                    "bbu_20_2_0": float(last_valid_indicators.bbu_20_2_0) if last_valid_indicators and last_valid_indicators.bbu_20_2_0 else None,
                    "bbl_20_2_0": float(last_valid_indicators.bbl_20_2_0) if last_valid_indicators and last_valid_indicators.bbl_20_2_0 else None,
                    "rsi_14":     float(last_valid_indicators.rsi_14)     if last_valid_indicators and last_valid_indicators.rsi_14     else None,
                })

        # Detect data gap: DB ends before yesterday → trigger background gap-fill from Yahoo Finance
        if history_list and len(history_list) >= 2:
            # Use second-to-last (last real DB row, not the injected today point)
            last_db_date = history_list[-2]["date"] if history_list[-1]["date"] == date.today().isoformat() else history_list[-1]["date"]
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            if last_db_date < yesterday:
                gap_from = (date.fromisoformat(last_db_date) + timedelta(days=1)).isoformat()
                logger.info(f"Gap detected for {symbol}: DB ends {last_db_date}, gap starts {gap_from}. Triggering background fill.")

                def _gap_fill(sym, gap_from_date, gap_to_date):
                    try:
                        import yfinance as yf, math
                        import pandas as pd
                        from database import SessionLocal
                        from sqlalchemy import text as _text

                        # Map PSX symbols to Yahoo Finance tickers
                        _YF_SPECIAL = {"KSE100": "^KSE100", "KSE30": "^KSE30"}
                        yf_tick = _YF_SPECIAL.get(sym, f"{sym}.KA")

                        # Fetch 250 extra days so rolling indicators are accurate
                        ind_start = (date.fromisoformat(gap_from_date) - timedelta(days=250)).isoformat()
                        h = yf.Ticker(yf_tick).history(start=ind_start, end=gap_to_date, auto_adjust=True)
                        if h.empty:
                            return
                        c = h["Close"]
                        s20 = c.rolling(20).mean(); s50 = c.rolling(50).mean(); s200 = c.rolling(200).mean()
                        std = c.rolling(20).std(); bbu = s20 + std * 2; bbl = s20 - std * 2
                        dlt = c.diff(); gain = dlt.clip(lower=0).rolling(14).mean(); loss = (-dlt.clip(upper=0)).rolling(14).mean()
                        rsi_s = 100 - (100 / (1 + gain / loss.replace(0, float("nan"))))
                        def _f(v): return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)
                        all_rows = [{"date": idx.strftime("%Y-%m-%d"),
                            "open": _f(row.get("Open")), "high": _f(row.get("High")),
                            "low":  _f(row.get("Low")),  "close": _f(row.get("Close")),
                            "volume": int(row.get("Volume", 0) or 0),
                            "sma_20": _f(s20.get(idx)), "sma_50": _f(s50.get(idx)),
                            "sma_200": _f(s200.get(idx)), "bbu_20_2_0": _f(bbu.get(idx)),
                            "bbl_20_2_0": _f(bbl.get(idx)), "rsi_14": _f(rsi_s.get(idx))}
                            for idx, row in h.iterrows() if row.get("Close")]
                        gap_rows = [r for r in all_rows if r["date"] >= gap_from_date]
                        if not gap_rows:
                            return
                        db2 = SessionLocal()
                        try:
                            CHUNK = 20
                            saved = 0
                            for i in range(0, len(gap_rows), CHUNK):
                                chunk = gap_rows[i:i+CHUNK]
                                params = {}; clauses = []
                                for j, r in enumerate(chunk):
                                    params.update({f"s{j}": sym, f"d{j}": r["date"],
                                        f"o{j}": r["open"], f"h{j}": r["high"], f"l{j}": r["low"],
                                        f"c{j}": r["close"], f"v{j}": r["volume"],
                                        f"s20_{j}": r["sma_20"], f"s50_{j}": r["sma_50"],
                                        f"s200_{j}": r["sma_200"], f"bbu_{j}": r["bbu_20_2_0"],
                                        f"bbl_{j}": r["bbl_20_2_0"], f"rsi_{j}": r["rsi_14"]})
                                    clauses.append(f"(:s{j},:d{j},:o{j},:h{j},:l{j},:c{j},:v{j},:s20_{j},:s50_{j},:s200_{j},:bbu_{j},:bbl_{j},:rsi_{j})")
                                try:
                                    db2.execute(_text(f"""
                                        INSERT INTO history_psx
                                            (symbol,date,open,high,low,close,volume,sma_20,sma_50,sma_200,bbu_20_2_0,bbl_20_2_0,rsi_14)
                                        VALUES {', '.join(clauses)}
                                        ON CONFLICT (symbol,date) DO UPDATE SET
                                            open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                                            close=EXCLUDED.close, volume=EXCLUDED.volume,
                                            sma_20=EXCLUDED.sma_20, sma_50=EXCLUDED.sma_50,
                                            sma_200=EXCLUDED.sma_200, bbu_20_2_0=EXCLUDED.bbu_20_2_0,
                                            bbl_20_2_0=EXCLUDED.bbl_20_2_0, rsi_14=EXCLUDED.rsi_14
                                    """), params)
                                    db2.commit()
                                    saved += len(chunk)
                                except Exception as ce:
                                    db2.rollback()
                                    logger.warning(f"Gap-fill chunk error {sym}: {ce}")
                            logger.info(f"Gap-fill complete: {sym} +{saved} rows ({gap_from_date} to {gap_to_date})")
                            for k in list(_history_cache.keys()):
                                if k.startswith(f"{sym}_"):
                                    del _history_cache[k]; _history_cache_expiry.pop(k, None)
                        finally:
                            db2.close()
                    except Exception as gfe:
                        logger.warning(f"Gap-fill failed for {sym}: {gfe}")

                import threading
                threading.Thread(target=_gap_fill, args=(symbol, gap_from, to_date), daemon=True).start()

        # Only cache non-empty results (prevents poisoning cache with empty [] on transient errors)
        if history_list:
            _history_cache[cache_key] = history_list
            _history_cache_expiry[cache_key] = now + 1800

        # Return DB data if we have at least 2 points; otherwise fall through to Yahoo Finance
        if len(history_list) >= 2:
            return history_list
        # else: fall through to Yahoo Finance fallback

    except Exception as e:
        logger.error(f"Error in get_price_history: {e}")
        # Fall through to Yahoo Finance fallback below
        pass

    # ── Yahoo Finance fallback ────────────────────────────────────────────────
    # Used when: DB has no data OR query failed.
    # PSX stocks on Yahoo Finance use the .KA suffix (e.g. HASCOL.KA)
    try:
        import yfinance as yf
        import pandas as pd
        import math

        # Map PSX symbol to correct Yahoo Finance ticker
        _YF_SPECIAL = {"KSE100": "^KSE100", "KSE30": "^KSE30"}
        yf_symbol = _YF_SPECIAL.get(symbol, f"{symbol}.KA")
        ticker = yf.Ticker(yf_symbol)
        # Fetch a larger window so indicators have enough history to be accurate
        indicator_start = (date.fromisoformat(from_date) - timedelta(days=250)).isoformat()
        hist_full = ticker.history(start=indicator_start, end=to_date, auto_adjust=True)

        if hist_full.empty:
            logger.warning(f"Yahoo Finance: no data for {yf_symbol}")
            return []

        # Compute indicators on full window (so rolling windows are accurate)
        closes = hist_full["Close"]
        sma_20  = closes.rolling(20).mean()
        sma_50  = closes.rolling(50).mean()
        sma_200 = closes.rolling(200).mean()
        std_20  = closes.rolling(20).std()
        bbu     = sma_20 + std_20 * 2
        bbl     = sma_20 - std_20 * 2
        delta   = closes.diff()
        gain    = delta.clip(lower=0).rolling(14).mean()
        loss    = (-delta.clip(upper=0)).rolling(14).mean()
        rs      = gain / loss.replace(0, float("nan"))
        rsi     = 100 - (100 / (1 + rs))

        def _f(v):
            return None if (v is None or (isinstance(v, float) and math.isnan(v))) else float(v)

        # Build full list (needed for DB save)
        all_rows = []
        for idx, row in hist_full.iterrows():
            all_rows.append({
                "date":       idx.strftime("%Y-%m-%d"),
                "open":       _f(row.get("Open")),
                "high":       _f(row.get("High")),
                "low":        _f(row.get("Low")),
                "close":      _f(row.get("Close")),
                "volume":     int(row.get("Volume", 0) or 0),
                "sma_20":     _f(sma_20.get(idx)),
                "sma_50":     _f(sma_50.get(idx)),
                "sma_200":    _f(sma_200.get(idx)),
                "bbu_20_2_0": _f(bbu.get(idx)),
                "bbl_20_2_0": _f(bbl.get(idx)),
                "rsi_14":     _f(rsi.get(idx)),
            })

        # Trim to the originally requested date range for the response
        yf_history = [r for r in all_rows if from_date <= r["date"] <= to_date]

        logger.info(f"Yahoo Finance fallback: {symbol} — {len(yf_history)} points (requested), {len(all_rows)} total")

        # ── Persist to history_psx in the background ─────────────────────────────
        def _save_yf_to_db(sym: str, rows: list):
            """Upsert Yahoo Finance rows into history_psx in small chunks."""
            from database import SessionLocal
            from sqlalchemy import text as _text
            db2 = SessionLocal()
            try:
                CHUNK = 20
                saved = 0
                for i in range(0, len(rows), CHUNK):
                    chunk = rows[i:i + CHUNK]
                    params = {}
                    clauses = []
                    for j, r in enumerate(chunk):
                        params.update({
                            f"s{j}": sym, f"d{j}": r["date"],
                            f"o{j}": r["open"],  f"h{j}": r["high"],
                            f"l{j}": r["low"],   f"c{j}": r["close"],
                            f"v{j}": r["volume"],
                            f"s20_{j}": r["sma_20"],   f"s50_{j}": r["sma_50"],
                            f"s200_{j}": r["sma_200"],
                            f"bbu_{j}": r["bbu_20_2_0"], f"bbl_{j}": r["bbl_20_2_0"],
                            f"rsi_{j}": r["rsi_14"],
                        })
                        clauses.append(
                            f"(:s{j}, :d{j}, :o{j}, :h{j}, :l{j}, :c{j}, :v{j},"
                            f" :s20_{j}, :s50_{j}, :s200_{j}, :bbu_{j}, :bbl_{j}, :rsi_{j})"
                        )
                    try:
                        db2.execute(_text(f"""
                            INSERT INTO history_psx
                                (symbol, date, open, high, low, close, volume,
                                 sma_20, sma_50, sma_200, bbu_20_2_0, bbl_20_2_0, rsi_14)
                            VALUES {', '.join(clauses)}
                            ON CONFLICT (symbol, date) DO UPDATE SET
                                open       = EXCLUDED.open,
                                high       = EXCLUDED.high,
                                low        = EXCLUDED.low,
                                close      = EXCLUDED.close,
                                volume     = EXCLUDED.volume,
                                sma_20     = EXCLUDED.sma_20,
                                sma_50     = EXCLUDED.sma_50,
                                sma_200    = EXCLUDED.sma_200,
                                bbu_20_2_0 = EXCLUDED.bbu_20_2_0,
                                bbl_20_2_0 = EXCLUDED.bbl_20_2_0,
                                rsi_14     = EXCLUDED.rsi_14
                        """), params)
                        db2.commit()
                        saved += len(chunk)
                    except Exception as chunk_err:
                        logger.warning(f"YF DB save chunk error for {sym}: {chunk_err}")
                        db2.rollback()
                logger.info(f"YF → DB: saved {saved}/{len(rows)} rows for {sym}")
                # Invalidate cache so next request uses fresh DB data
                for k in list(_history_cache.keys()):
                    if k.startswith(f"{sym}_"):
                        del _history_cache[k]
                        _history_cache_expiry.pop(k, None)
            except Exception as e:
                logger.error(f"YF DB save failed for {sym}: {e}")
            finally:
                db2.close()

        # Run DB save in background thread so the HTTP response is not delayed
        import threading
        threading.Thread(target=_save_yf_to_db, args=(symbol, all_rows), daemon=True).start()

        if yf_history:
            _history_cache[cache_key] = yf_history
            _history_cache_expiry[cache_key] = now + 1800
        return yf_history

    except Exception as yf_err:
        logger.warning(f"Yahoo Finance fallback failed for {symbol}: {yf_err}")
        return []





# ── Fast Bulk Prices (DB-only, no external fetch) ─────────────────────────────

@app.post("/api/prices/bulk")
def bulk_prices(symbols: List[str], db: Session = Depends(get_db)):
    """
    Returns live prices for a list of symbols straight from the DB.
    Never hits an external provider — designed to be called by the frontend
    to populate the Markets table instantly.
    """
    global _bulk_prices_cache, _bulk_prices_cache_expiry
    now = time.time()

    if not symbols:
        return {}

    upper = [s.upper() for s in symbols]

    try:
        live_map = crud.get_live_prices(db, upper)
        rows = list(live_map.values())
    except Exception as e:
        db.rollback()
        logger.warning(f"bulk_prices DB error: {e}")
        return {}

    result = {}
    for r in rows:
        result[r.symbol] = {
            "symbol": r.symbol,
            "price": float(r.price) if r.price is not None else None,
            "change": float(r.change) if r.change is not None else None,
            "change_pct": float(r.change_pct) if r.change_pct is not None else None,
            "open": float(r.open) if r.open is not None else None,
            "high": float(r.high) if r.high is not None else None,
            "low": float(r.low) if r.low is not None else None,
            "volume": int(r.volume) if r.volume is not None else None,
            "prev_close": float(r.prev_close) if r.prev_close is not None else None,
        }
    return result


# Cache for fundamentals to avoid redundant HTTP calls
_fundamental_cache = {}
_fundamental_cache_expiry = {}

@app.get("/api/stocks/{symbol}/fundamentals")
def get_stock_fundamentals(symbol: str):
    symbol = symbol.upper()
    now = time.time()
    
    # 1. Check local cache (1 hour)
    if symbol in _fundamental_cache and now < _fundamental_cache_expiry.get(symbol, 0):
        return _fundamental_cache[symbol]
        
    # 2. Get ISIN from provider (cached in provider level)
    quote = sarmaaya.get_quote(symbol)
    isin = getattr(quote, 'isin', None)
    
    # 3. Fetch fundamentals
    data = sarmaaya.get_fundamentals(isin or symbol)
    
    # 4. Store in cache
    _fundamental_cache[symbol] = data
    _fundamental_cache_expiry[symbol] = now + 3600
    
    return data


@app.get("/api/markets/summary")
def get_market_summary(db: Session = Depends(get_db)):
    try:
        return crud.get_market_summary(db)
    except Exception as e:
        logger.warning(f"get_market_summary failed (transient DB error?): {e}")
        return {"advances": 0, "declines": 0, "unchanged": 0, "total_volume": 0}


@app.get("/api/scheduler/status")
def scheduler_status():
    """Return current scheduler job states and next run times."""
    from scheduler import _scheduler, _is_market_open
    if not _scheduler or not _scheduler.running:
        return {"running": False, "jobs": []}
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        })
    return {"running": True, "market_open": _is_market_open(), "jobs": jobs}


@app.post("/api/scheduler/run-now/{job_id}")
def scheduler_run_now(job_id: str):
    """Manually trigger a scheduler job immediately (admin use)."""
    from scheduler import _scheduler
    if not _scheduler:
        raise HTTPException(503, "Scheduler not running")
    job = _scheduler.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job '{job_id}' not found")
    _scheduler.modify_job(job_id, next_run_time=datetime.now(PKT))
    return {"triggered": job_id}


# Cache for symbol names to avoid repeated full-table scans
_symbol_name_cache = {}
_symbol_cache_expiry = 0

def _get_symbol_names(db: Session, asset_type: AssetType):
    global _symbol_name_cache, _symbol_cache_expiry
    now = time.time()
    
    # Refresh cache every 1 hour
    if not _symbol_name_cache or now > _symbol_cache_expiry:
        logger.info("Refreshing symbol name cache...")
        results = crud.get_symbol_names(db)
        _symbol_name_cache = {r.symbol: r.name for r in results}
        _symbol_cache_expiry = now + 3600
        
    return _symbol_name_cache

@app.get("/api/markets/movers")
def get_market_movers(type: str = "stocks", db: Session = Depends(get_db)):
    at = AssetType.STOCK if type == "stocks" else AssetType.MUTUAL_FUND
    try:
        data = crud.get_market_movers(db, asset_type=at)
        name_map = _get_symbol_names(db, at)
    except Exception as e:
        logger.warning(f"get_market_movers failed (transient DB error?): {e}")
        return {"gainers": [], "losers": [], "active": []}

    def _to_mover(p):
        return {
            "symbol": p.symbol,
            "name": name_map.get(p.symbol) or p.symbol,
            "price": float(p.price) if p.price is not None else None,
            "change": float(p.change) if p.change is not None else None,
            "change_pct": float(p.change_pct) if p.change_pct is not None else None,
            "volume": int(p.volume) if p.volume is not None else None,
            "asset_type": type,
        }

    return {
        "gainers": [_to_mover(p) for p in data["gainers"]],
        "losers":  [_to_mover(p) for p in data["losers"]],
        "active":  [_to_mover(p) for p in data["active"]]
    }


# Cache for peers
_peer_cache = {}
_peer_cache_expiry = {}

@app.get("/api/stocks/{symbol}/peers")
def get_stock_peers(symbol: str, db: Session = Depends(get_db)):
    symbol = symbol.upper()
    now = time.time()
    
    # 1. Check local cache (1 hour)
    if symbol in _peer_cache and now < _peer_cache_expiry.get(symbol, 0):
        return _peer_cache[symbol]
    
    try:
        # Use retryable CRUD to get sector and peers
        sym_row, sector_peers = crud.get_stock_peers_data(db, symbol)
        if not sym_row or not sym_row.sector:
            return []

        # Also try by asset_type match if same sector is empty (sector data sparse)
        if not sector_peers:
            sector_peers = db.query(GlobalSymbol).filter(
                GlobalSymbol.asset_type == AssetType.STOCK,
                GlobalSymbol.symbol != symbol,
            ).limit(6).all()

        # Bulk-fetch live prices for peer symbols (with retry)
        peer_symbols = [p.symbol for p in sector_peers]
        live_map = crud.get_live_prices(db, peer_symbols)

        result = []
        for gs in sector_peers:
            lp = live_map.get(gs.symbol)
            result.append({
                "symbol": gs.symbol,
                "name": gs.name,
                "sector": gs.sector,
                "price": float(lp.price) if lp and lp.price else None,
                "change": float(lp.change) if lp and lp.change else None,
                "change_pct": float(lp.change_pct) if lp and lp.change_pct else None,
            })
            
        # Store in cache
        _peer_cache[symbol] = result
        _peer_cache_expiry[symbol] = now + 3600
        return result

    except Exception as e:
        logger.warning(f"get_stock_peers DB error (transient?): {e}")
        # Return stale cache if available
        return _peer_cache.get(symbol, [])



# ── Symbols (public) ──────────────────────────────────────────────────────────

@app.get("/api/symbols/search", response_model=List[SymbolSearchResult])
def search_symbols(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    try:
        results = crud.search_global_symbols(db, q)
        if not results:
            # Fallback to provider if DB is empty or no match
            results = active_provider.search_symbols(q)
        return [SymbolSearchResult(symbol=r.symbol, name=r.name, asset_type=r.asset_type)
                for r in results]
    except Exception as e:
        logger.warning(f"search_symbols DB error (transient?): {e}")
        return []



# Cache for the full symbols list (1 hour)
_all_symbols_cache = None
_all_symbols_expiry = 0

@app.get("/api/symbols", response_model=List[SymbolSearchResult])
def all_symbols(db: Session = Depends(get_db)):
    global _all_symbols_cache, _all_symbols_expiry
    now = time.time()
    
    # Return cache if still fresh (2 hour TTL — symbol list is fully static)
    if _all_symbols_cache and now < _all_symbols_expiry:
        return _all_symbols_cache

    try:
        results = crud.get_all_symbols(db)
        if not results:
            results = active_provider.get_all_symbols()
        
        _all_symbols_cache = [SymbolSearchResult(symbol=r.symbol, name=r.name, asset_type=r.asset_type)
                for r in results]
        _all_symbols_expiry = now + 7200  # 2-hour cache
        return _all_symbols_cache

    except Exception as e:
        logger.warning(f"all_symbols DB error (transient?): {e}")
        # Return stale cache if we have it, otherwise empty list
        if _all_symbols_cache:
            logger.info("all_symbols: returning stale cache due to DB error")
            return _all_symbols_cache
        return []



# ── Helpers ───────────────────────────────────────────────────────────────────

def _trade_out(t) -> TradeOut:
    return TradeOut(
        id=t.id, portfolio_id=t.portfolio_id, symbol=t.symbol, name=t.name,
        action=t.action, trade_type=t.trade_type, asset_type=t.asset_type,
        price=t.price, quantity=t.quantity, deductions=t.deductions,
        trade_date=t.trade_date, notes=t.notes, gross_value=t.gross_value,
        net_cost=t.net_cost, created_at=t.created_at,
    )


def _price_out(q) -> PriceOut:
    change = q.change
    change_pct = q.change_pct
    
    # Calculate if missing but we have price/prev_close
    if change is None and q.price and q.prev_close:
        change = q.price - q.prev_close
    if change_pct is None and q.price and q.prev_close and q.prev_close != 0:
        change_pct = (change / q.prev_close) * 100

    return PriceOut(
        symbol=q.symbol, price=q.price, change=change,
        change_pct=change_pct, volume=q.volume, open=q.open,
        high=q.high, low=q.low, prev_close=q.prev_close,
        asset_type=q.asset_type,
        aum=q.aum, risk_profile=q.risk_profile,
        is_shariah=q.is_shariah, category=q.category,
    )


def _sync_symbols_if_needed():
    """Background task to sync symbols on startup if DB is empty."""
    def run_sync():
        from database import SessionLocal
        import crud
        db = SessionLocal()
        try:
            # Check if symbols already exist
            count = crud.get_global_symbols_count(db)
            if count == 0:
                logger.info("Local symbol cache is empty. Synchronizing from provider...")
                all_syms = active_provider.get_all_symbols()
                if all_syms:
                    data = [{"symbol": s.symbol, "name": s.name, "asset_type": s.asset_type} for s in all_syms]
                    crud.sync_global_symbols(db, data)
                    logger.info(f"Synchronized {len(data)} symbols successfully.")
        except Exception as e:
            logger.error(f"Failed to sync symbols on startup: {e}")
        finally:
            db.close()
    
    # Run in background to not block startup
    threading.Thread(target=run_sync, daemon=True).start()


def _seed_initial_data():
    from database import SessionLocal
    from datetime import date as d

    db = SessionLocal()
    try:
        if crud.get_user_by_email(db, "demo@example.com"):
            return  # already seeded

        # Create demo user
        user = crud.create_user(db, email="demo@example.com", plain_password="password123", username="demo")
        user.is_verified = True  # Auto-verify demo user

        # ── PSX Main portfolio (stocks only, exact CSV data) ──────────────────
        psxmain = crud.create_portfolio(db, PortfolioCreate(
            name="PSX Main",
            description="Primary PSX equity portfolio",
        ), user.id)
        psxmain.is_default = True
        db.commit()

        psxmain_trades = [
            ("NPL",     "Nishat Power Limited",             500,    93.85,   75.00, "STOCK"),
            ("BIPL",    "BankIslami Pakistan Limited",      270,    38.05,   33.00, "STOCK"),
            ("HALEON",  "Haleon Pakistan Limited",           40,   954.88,   35.00, "STOCK"),
            ("NCPL",    "Nishat Chunian Power Limited",    1000,    68.55,  150.00, "STOCK"),
            ("HUBC",    "The Hub Power Company Limited",    280,   238.20,  121.00, "STOCK"),
            ("FFC",     "Fauji Fertilizer Company Limited",  80,   539.35,   79.00, "STOCK"),
            ("AVN",     "Avanceon Limited",                9730,    45.44, 1168.00, "STOCK"),
            ("MEBL",    "Meezan Bank Limited",               50,   170.45,   16.00, "STOCK"),
            ("MZNPETF", "Meezan Pakistan ETF",             2500,    20.24,  200.00, "ETF"),
        ]
        total_cost_main = sum(price * qty + ded for _, _, qty, price, ded, _ in psxmain_trades)

        from models import CashTransaction as CT
        db.add(CT(
            portfolio_id=psxmain.id, tx_type=CashTxType.DEPOSIT,
            amount=round(total_cost_main, 2), tx_date=d(2026, 3, 5),
            description="Initial deposit — PSX Main",
        ))
        for sym, name, qty, price, ded, atype in psxmain_trades:
            db.add(Trade(
                portfolio_id=psxmain.id, symbol=sym, name=name,
                action=TradeAction.BUY, trade_type=TradeType.LONG,
                asset_type=AssetType(atype),
                price=price, quantity=qty, deductions=ded,
                trade_date=d(2026, 3, 5),
            ))

        # ── Sarmaya portfolio (all 15 trades from CSV, 1M deposit) ───────────
        sarmaya = crud.create_portfolio(db, PortfolioCreate(
            name="Sarmaya",
            description="Full Sarmaya.pk import — stocks + mutual funds",
        ), user.id)
        db.commit()

        sarmaya_trades = [
            # sym, name, qty, price, ded, asset_type
            ("NPL",     "Nishat Power Limited",                       500,      93.85,    75.00, "STOCK"),
            ("BIPL",    "BankIslami Pakistan Limited",                270,      38.05,    33.00, "STOCK"),
            ("AMMF",    "Al Meezan Mutual Fund",                   496.49,      50.35,   424.00, "MUTUAL_FUND"),
            ("ALHAA",   "Alhamra Islamic Asset Allocation Fund",  234.6905,    207.62,     0.00, "MUTUAL_FUND"),
            ("ALHIIF",  "Alhamra Islamic Income Fund",            515.7162,    107.60,     0.00, "MUTUAL_FUND"),
            ("HALEON",  "Haleon Pakistan Limited",                     40,     954.88,    35.00, "STOCK"),
            ("MAAF",    "Meezan Asset Allocation Fund",            164.41,     121.64,   339.00, "MUTUAL_FUND"),
            ("MBF",     "Meezan Balanced Fund",                   179.2466,     28.39,    85.00, "MUTUAL_FUND"),
            ("MIF",     "Meezan Islamic Fund",                    291.8201,    171.34,   848.00, "MUTUAL_FUND"),
            ("NCPL",    "Nishat Chunian Power Limited",              1000,      68.55,   150.00, "STOCK"),
            ("HUBC",    "The Hub Power Company Limited",              280,     238.20,   121.00, "STOCK"),
            ("FFC",     "Fauji Fertilizer Company Limited",            80,     539.35,    79.00, "STOCK"),
            ("AVN",     "Avanceon Limited",                          9730,      45.44,  1168.00, "STOCK"),
            ("MEBL",    "Meezan Bank Limited",                         50,     170.45,    16.00, "STOCK"),
            ("MZNPETF", "Meezan Pakistan ETF",                       2500,      20.24,   200.00, "ETF"),
        ]

        db.add(CT(
            portfolio_id=sarmaya.id, tx_type=CashTxType.DEPOSIT,
            amount=1_000_000.00, tx_date=d(2026, 3, 5),
            description="Initial 1M deposit — Sarmaya portfolio",
        ))
        for sym, name, qty, price, ded, atype in sarmaya_trades:
            db.add(Trade(
                portfolio_id=sarmaya.id, symbol=sym, name=name,
                action=TradeAction.BUY, trade_type=TradeType.LONG,
                asset_type=AssetType(atype),
                price=price, quantity=qty, deductions=ded,
                trade_date=d(2026, 3, 5),
            ))

        db.commit()

        # ── CSV Import portfolio (trades-export-2026-03-05.csv, 1M deposit) ──
        csv_portfolio = crud.create_portfolio(db, PortfolioCreate(
            name="CSV Import 2026-03-05",
            description="Imported from trades-export-2026-03-05.csv — 15 trades, 1M starting investment",
        ), user.id)
        db.commit()

        csv_trades = [
            # (symbol, name, quantity, price, deductions, asset_type)  ← exact CSV values
            ("NPL",     "Nishat Power Limited",                   500,       93.85,    75.00, "STOCK"),
            ("BIPL",    "BankIslami Pakistan Limited",            270,       38.05,    33.00, "STOCK"),
            ("AMMF",    "Al Meezan Mutual Fund",                  496.49,    50.35,   424.00, "MUTUAL_FUND"),
            ("ALHAA",   "Alhamra Islamic Asset Allocation Fund",  234.6905, 207.62,     0.00, "MUTUAL_FUND"),
            ("ALHIIF",  "Alhamra Islamic Income Fund",            515.7162, 107.60,     0.00, "MUTUAL_FUND"),
            ("HALEON",  "HALEON Pakistan Limited",                 40,      954.88,    35.00, "STOCK"),
            ("MAAF",    "Meezan Asset Allocation Fund",           164.41,   121.64,   339.00, "MUTUAL_FUND"),
            ("MBF",     "Meezan Balanced Fund",                   179.2466,  28.39,    85.00, "MUTUAL_FUND"),
            ("MIF",     "Meezan Islamic Fund",                    291.8201, 171.34,   848.00, "MUTUAL_FUND"),
            ("NCPL",    "Nishat Chunian Power Limited",          1000,       68.55,   150.00, "STOCK"),
            ("HUBC",    "The Hub Power Company Limited",           280,     238.20,   121.00, "STOCK"),
            ("FFC",     "Fauji Fertilizer Company Limited",        80,      539.35,    79.00, "STOCK"),
            ("AVN",     "Avanceon Limited",                      9730,       45.44,  1168.00, "STOCK"),
            ("MEBL",    "Meezan Bank Limited",                     50,      170.45,    16.00, "STOCK"),
            ("MZNPETF", "Meezan Pakistan ETF",                   2500,       20.24,   200.00, "ETF"),
        ]

        db.add(CT(
            portfolio_id=csv_portfolio.id, tx_type=CashTxType.DEPOSIT,
            amount=1_000_000.00, tx_date=d(2026, 3, 5),
            description="Initial 1M investment — CSV Import 2026-03-05",
        ))
        for sym, name, qty, price, ded, atype in csv_trades:
            db.add(Trade(
                portfolio_id=csv_portfolio.id, symbol=sym, name=name,
                action=TradeAction.BUY, trade_type=TradeType.LONG,
                asset_type=AssetType(atype),
                price=price, quantity=qty, deductions=ded,
                trade_date=d(2026, 3, 5),
            ))

        db.commit()
    finally:
        db.close()

