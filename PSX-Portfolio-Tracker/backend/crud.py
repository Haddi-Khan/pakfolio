"""Database CRUD — all queries scoped to a portfolio_id (and user_id for auth)."""

import logging
from datetime import datetime, date
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from models import (
    Portfolio, Trade, CashTransaction, TradeAction, AssetType,
    CashTxType, User, PasswordResetToken, HistoricalPrice, LivePrice,
    SocialAccount, GlobalSymbol, HistoryPSX
)
from schemas import PortfolioCreate, TradeCreate, CashTxCreate
import auth as auth_utils
from database import db_retry

logger = logging.getLogger(__name__)


@db_retry(retries=3, delay=1)
def get_global_symbols_count(db: Session) -> int:
    return db.query(GlobalSymbol).count()

@db_retry(retries=3, delay=1)
def get_all_symbols(db: Session) -> List[GlobalSymbol]:
    return db.query(GlobalSymbol).all()

@db_retry(retries=3, delay=1)
def get_market_summary(db: Session) -> Dict:
    """Calculates advances, declines and volume for all stocks."""
    stats = db.query(
        func.count(case((LivePrice.change_pct > 0, 1))),
        func.count(case((LivePrice.change_pct < 0, 1))),
        func.count(case((
            (LivePrice.change_pct == 0) | LivePrice.change_pct.is_(None), 1
        ))),
        func.sum(LivePrice.volume)
    ).join(GlobalSymbol, GlobalSymbol.symbol == LivePrice.symbol)\
     .filter(GlobalSymbol.asset_type == AssetType.STOCK).first()
    
    return {
        "advances": stats[0] or 0,
        "declines": stats[1] or 0,
        "unchanged": stats[2] or 0,
        "total_volume": float(stats[3] or 0)
    }

@db_retry(retries=3, delay=1)
def get_market_movers(db: Session, asset_type: AssetType = AssetType.STOCK, limit: int = 10) -> Dict:
    """Returns top gainers, losers, and most active."""
    # Base query joined with GlobalSymbol to filter by asset_type
    base = db.query(LivePrice).join(GlobalSymbol, GlobalSymbol.symbol == LivePrice.symbol)\
             .filter(GlobalSymbol.asset_type == asset_type, LivePrice.price > 0)
    
    gainers = base.order_by(LivePrice.change_pct.desc()).limit(limit).all()
    losers  = base.order_by(LivePrice.change_pct.asc()).limit(limit).all()
    active  = base.order_by(LivePrice.volume.desc()).limit(limit).all()
    
    return {
        "gainers": gainers,
        "losers": losers,
        "active": active
    }

@db_retry(retries=3, delay=1)
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email.lower()).first()

def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def create_user(db: Session, email: str, plain_password: Optional[str] = None, username: Optional[str] = None) -> User:
    # This part ensures username is NEVER null even if the user didn't provide one
    if not username:
        username = email.split('@')[0] # Uses the part before the @ as a default

    user = User(
        email=email.lower(),
        username=username.lower(),
        hashed_password=auth_utils.hash_password(plain_password) if plain_password else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db: Session, email: str, plain_password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user or not user.hashed_password or not auth_utils.verify_password(plain_password, user.hashed_password):
        return None
    return user


# ── Social Accounts ───────────────────────────────────────────────────────────

def get_user_by_social(db: Session, provider: str, provider_user_id: str) -> Optional[User]:
    acc = db.query(SocialAccount).filter(
        SocialAccount.provider == provider,
        SocialAccount.provider_user_id == provider_user_id
    ).first()
    if acc:
        return get_user(db, acc.user_id)
    return None

def link_social_account(db: Session, user_id: int, provider: str, provider_user_id: str):
    obj = SocialAccount(user_id=user_id, provider=provider, provider_user_id=provider_user_id)
    db.add(obj)
    db.commit()
    return obj

def create_user_from_social(db: Session, email: str, avatar_url: Optional[str] = None) -> User:
    """Creates a pre-verified user from social data."""
    user = User(
        email=email.lower(),
        is_verified=True,
        avatar_url=avatar_url
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ── Password Reset ─────────────────────────────────────────────────────────────

def create_reset_token(db: Session, user: User):
    raw, token_hash, expiry = auth_utils.generate_reset_token()
    # Invalidate any existing unused tokens for this user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False,
    ).update({"used": True})
    token = PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expiry)
    db.add(token)
    db.commit()
    return raw  # Return raw token (sent to user via email)

def get_valid_reset_token(db: Session, raw_token: str) -> Optional[PasswordResetToken]:
    token_hash = auth_utils.hash_reset_token(raw_token)
    return db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > datetime.utcnow(),
    ).first()

def use_reset_token(db: Session, token: PasswordResetToken, new_password: str):
    user = get_user(db, token.user_id)
    user.hashed_password = auth_utils.hash_password(new_password)
    token.used = True
    db.commit()


# ── Portfolios ────────────────────────────────────────────────────────────────

def create_portfolio(db: Session, data: PortfolioCreate, user_id: int) -> Portfolio:
    obj = Portfolio(user_id=user_id, name=data.name, description=data.description)
    db.add(obj)
    db.commit()
    db.refresh(obj)

    # Handle initial balance as a deposit
    if data.initial_balance > 0:
        deposit = CashTransaction(
            portfolio_id=obj.id,
            tx_type=CashTxType.DEPOSIT,
            amount=data.initial_balance,
            tx_date=date.today(),
            description="Initial Balance"
        )
        db.add(deposit)
        db.commit()

    return obj

def get_portfolios(db: Session, user_id: int) -> List[Portfolio]:
    return db.query(Portfolio).filter(Portfolio.user_id == user_id).order_by(Portfolio.created_at).all()

def get_portfolio(db: Session, pid: int, user_id: Optional[int] = None) -> Optional[Portfolio]:
    q = db.query(Portfolio).filter(Portfolio.id == pid)
    if user_id is not None:
        q = q.filter(Portfolio.user_id == user_id)
    return q.first()

def get_default_portfolio(db: Session, user_id: int) -> Optional[Portfolio]:
    p = db.query(Portfolio).filter(Portfolio.user_id == user_id, Portfolio.is_default == True).first()
    if not p:
        p = db.query(Portfolio).filter(Portfolio.user_id == user_id).order_by(Portfolio.id).first()
    return p

def set_default_portfolio(db: Session, pid: int, user_id: int) -> Optional[Portfolio]:
    db.query(Portfolio).filter(Portfolio.user_id == user_id).update({Portfolio.is_default: False})
    p = get_portfolio(db, pid, user_id)
    if p:
        p.is_default = True
        db.commit()
        db.refresh(p)
    return p

def delete_portfolio(db: Session, pid: int, user_id: int) -> bool:
    p = get_portfolio(db, pid, user_id)
    if not p:
        return False
    db.delete(p)
    db.commit()
    return True


# ── Trades ────────────────────────────────────────────────────────────────────

def create_trade(db: Session, pid: int, trade: TradeCreate) -> Trade:
    obj = Trade(portfolio_id=pid, **trade.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def get_trades(db: Session, pid: int, symbol: Optional[str] = None,
               skip: int = 0, limit: int = 500) -> List[Trade]:
    q = db.query(Trade).filter(Trade.portfolio_id == pid)
    if symbol:
        q = q.filter(Trade.symbol == symbol.upper())
    return q.order_by(Trade.trade_date.desc(), Trade.created_at.desc()).offset(skip).limit(limit).all()

def get_trade(db: Session, trade_id: int) -> Optional[Trade]:
    return db.query(Trade).filter(Trade.id == trade_id).first()

def delete_trade(db: Session, trade_id: int) -> bool:
    obj = get_trade(db, trade_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True

def update_trade(db: Session, trade_id: int, data: TradeCreate) -> Optional[Trade]:
    obj = get_trade(db, trade_id)
    if not obj:
        return None
    for key, value in data.model_dump().items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


# ── Cash ──────────────────────────────────────────────────────────────────────

def create_cash_tx(db: Session, pid: int, tx: CashTxCreate) -> CashTransaction:
    obj = CashTransaction(portfolio_id=pid, **tx.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def get_cash_transactions(db: Session, pid: int, skip: int = 0, limit: int = 200) -> List[CashTransaction]:
    return (
        db.query(CashTransaction)
        .filter(CashTransaction.portfolio_id == pid)
        .order_by(CashTransaction.tx_date.desc(), CashTransaction.created_at.desc())
        .offset(skip).limit(limit).all()
    )

def get_cash_balance(db: Session, pid: int) -> float:
    """
    True cash balance:
      deposits - withdrawals - BUY net costs + SELL proceeds
    """
    # Cash transactions (deposits / withdrawals)
    tx_balance = db.query(
        func.coalesce(
            func.sum(
                case(
                    (CashTransaction.tx_type == CashTxType.DEPOSIT, CashTransaction.amount),
                    else_=-CashTransaction.amount,
                )
            ),
            0.0,
        )
    ).filter(CashTransaction.portfolio_id == pid).scalar()

    # Trade cash impact: BUY subtracts (price*qty + deductions), SELL adds (price*qty - deductions)
    trade_impact = db.query(
        func.coalesce(
            func.sum(
                case(
                    (Trade.action == TradeAction.BUY,
                     -(Trade.price * Trade.quantity + Trade.deductions)),
                    else_=(Trade.price * Trade.quantity - Trade.deductions),
                )
            ),
            0.0,
        )
    ).filter(Trade.portfolio_id == pid).scalar()

    return round(float(tx_balance) + float(trade_impact), 2)


def get_total_deposited(db: Session, pid: int) -> float:
    """Sum of all DEPOSIT cash transactions (what you put in)."""
    result = db.query(
        func.coalesce(func.sum(CashTransaction.amount), 0.0)
    ).filter(
        CashTransaction.portfolio_id == pid,
        CashTransaction.tx_type == CashTxType.DEPOSIT,
    ).scalar()
    return float(result)


# ── Holdings (computed from trades) ──────────────────────────────────────────

def get_holdings_raw(db: Session, pid: int) -> tuple[dict, float, dict]:
    """
    Returns (holdings_dict, total_realized_pnl, win_loss_stats)
    holdings_dict[symbol] = {quantity, total_cost, name, asset_type, sector}
    win_loss_stats = {"wins": int, "losses": int, "total": int, "win_pct": float}
    Uses weighted average cost method.
    """
    trades = (
        db.query(Trade)
        .filter(Trade.portfolio_id == pid)
        .order_by(Trade.trade_date, Trade.created_at)
        .all()
    )
    holdings: dict = {}
    realized_pnl = 0.0
    
    # Track wins/losses
    wins = 0
    losses = 0
    sell_count = 0

    # Fetch symbol sectors for lookup
    symbols_data = {s.symbol: s.sector for s in db.query(GlobalSymbol.symbol, GlobalSymbol.sector).all()}

    for t in trades:
        sym = t.symbol
        # Cast Decimal to float for calculations
        t_price = float(t.price)
        t_quantity = float(t.quantity)
        t_deductions = float(t.deductions)

        if sym not in holdings:
            holdings[sym] = {
                "quantity": 0.0, "total_cost": 0.0, "name": t.name,
                "asset_type": t.asset_type or AssetType.STOCK,
                "sector": symbols_data.get(sym)
            }

        h = holdings[sym]
        if t.action == TradeAction.BUY:
            h["total_cost"] += t_price * t_quantity + t_deductions
            h["quantity"] += t_quantity
        else:  # SELL
            if h["quantity"] > 0:
                # Part 1: Pro-rata cost of the shares sold
                avg_cost_per_share = h["total_cost"] / h["quantity"]
                cost_of_shares_sold = avg_cost_per_share * t_quantity
                
                # Part 2: Net proceeds from the sale
                net_proceeds = t_price * t_quantity - t_deductions
                
                # Part 3: Realized Gain/Loss on this specific trade
                trade_realized = net_proceeds - cost_of_shares_sold
                realized_pnl += trade_realized
                
                # Update holding state
                h["total_cost"] -= cost_of_shares_sold
                h["quantity"] -= t_quantity
                h["quantity"] = max(0.0, h["quantity"])
                h["total_cost"] = max(0.0, h["total_cost"])
                
                # Update Win/Loss stats
                sell_count += 1
                if trade_realized > 0:
                    wins += 1
                elif trade_realized < 0:
                    losses += 1

    active_holdings = {k: v for k, v in holdings.items() if v["quantity"] > 0.001}
    
    win_loss_stats = {
        "wins": wins,
        "losses": losses,
        "total": sell_count,
        "win_pct": (wins / sell_count * 100) if sell_count > 0 else 0.0
    }
    
    return active_holdings, round(realized_pnl, 2), win_loss_stats


# ── Historical Prices ─────────────────────────────────────────────────────────

def get_historical_prices(db: Session, symbol: str, start_date: date, end_date: date) -> List[HistoricalPrice]:
    return (
        db.query(HistoricalPrice)
        .filter(
            HistoricalPrice.symbol == symbol.upper(),
            HistoricalPrice.date >= start_date,
            HistoricalPrice.date <= end_date
        )
        .order_by(HistoricalPrice.date.asc())
        .all()
    )


def save_historical_prices(db: Session, symbol: str, prices: List[dict], asset_type: AssetType):
    """
    prices: List of {"date": date|str, "price": float}
    Uses a simple UPSERT-like logic: delete existing and re-insert.
    """
    symbol = symbol.upper()
    dates = []
    for p in prices:
        d = p["date"]
        if isinstance(d, str):
            d = datetime.strptime(d, "%Y-%m-%d").date()
        dates.append(d)

    if not dates:
        return

    # Delete existing to simulate UPSERT
    db.query(HistoricalPrice).filter(
        HistoricalPrice.symbol == symbol,
        HistoricalPrice.date.in_(dates)
    ).delete(synchronize_session=False)

    # Bulk insert
    objects = [
        HistoricalPrice(
            symbol=symbol,
            date=d,
            price=p["price"],
            asset_type=asset_type
        )
        for p, d in zip(prices, dates)
    ]
    db.bulk_save_objects(objects)
    db.commit()


# ── Live Prices ───────────────────────────────────────────────────────────────

@db_retry(retries=3, delay=1)
def get_live_prices(db: Session, symbols: List[str]) -> Dict[str, LivePrice]:
    upper = [s.upper() for s in symbols]
    prices = db.query(LivePrice).filter(LivePrice.symbol.in_(upper)).all()
    return {p.symbol: p for p in prices}

@db_retry(retries=3, delay=1)
def get_stock_peers_data(db: Session, symbol: str):
    """Fetches sector info and peers for a symbol."""
    sym_row = db.query(GlobalSymbol).filter(GlobalSymbol.symbol == symbol).first()
    if not sym_row or not sym_row.sector:
        return sym_row, []
    
    peers = db.query(GlobalSymbol).filter(
        GlobalSymbol.sector == sym_row.sector,
        GlobalSymbol.symbol != symbol,
        GlobalSymbol.asset_type == AssetType.STOCK,
    ).limit(6).all()
    return sym_row, peers

@db_retry(retries=3, delay=1)
def get_history_points(db: Session, symbol: str, start_dt: date, end_dt: date, limit: int):
    """Fetches historical price points with indicators."""
    return db.query(HistoryPSX).filter(
        HistoryPSX.symbol == symbol,
        HistoryPSX.date <= end_dt,
        HistoryPSX.date >= start_dt
    ).order_by(HistoryPSX.date.desc()).limit(limit).all()

@db_retry(retries=3, delay=1)
def get_latest_indicators(db: Session, symbol: str):
    """Fetches the most recent row with indicators for forward-filling."""
    return db.query(HistoryPSX).filter(
        HistoryPSX.symbol == symbol,
        HistoryPSX.sma_20.isnot(None)
    ).order_by(HistoryPSX.date.desc()).first()

@db_retry(retries=3, delay=1)
def get_symbol_names(db: Session):
    """Fetches all symbol-to-name mappings."""
    return db.query(GlobalSymbol.symbol, GlobalSymbol.name).all()


def save_live_prices(db: Session, quotes: Dict[str, any]):
    """
    quotes: Dict of symbol -> QuoteData-like object
    Uses PostgreSQL-specific bulk UPSERT for maximum performance.
    """
    if not quotes:
        return

    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from models import LivePrice
    
    values = []
    now = datetime.utcnow()
    
    for sym, q in quotes.items():
        if q.price is None:
            continue
        
        values.append({
            "symbol": sym.upper(),
            "price": q.price,
            "change": q.change,
            "change_pct": q.change_pct,
            "open": q.open,
            "high": q.high,
            "low": q.low,
            "prev_close": q.prev_close,
            "volume": getattr(q, 'volume', 0),
            "updated_at": now
        })

    if not values:
        return

    # Use Postgres-native ON CONFLICT UPDATE
    stmt = pg_insert(LivePrice).values(values)
    update_stmt = stmt.on_conflict_do_update(
        index_elements=['symbol'],
        set_={
            "price": stmt.excluded.price,
            "change": stmt.excluded.change,
            "change_pct": stmt.excluded.change_pct,
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "volume": stmt.excluded.volume,
            "prev_close": stmt.excluded.prev_close,
            "updated_at": stmt.excluded.updated_at
        }
    )

    try:
        db.execute(update_stmt)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Bulk live_price save failed: {e}")


def save_global_symbols(db: Session, symbols: List[any]):
    """
    symbols: List of SymbolInfo or similar objects with .symbol, .name, .asset_type
    """
    for s in symbols:
        sym = s.symbol.upper()
        db_sym = db.query(GlobalSymbol).filter(GlobalSymbol.symbol == sym).first()
        if not db_sym:
            db_sym = GlobalSymbol(symbol=sym)
            db.add(db_sym)
        
        db_sym.name = s.name
        db_sym.asset_type = s.asset_type if hasattr(s, 'asset_type') else AssetType.STOCK
        if hasattr(s, 'sector') and s.sector:
            db_sym.sector = s.sector

    db.commit()


def sync_global_symbols(db: Session, data: List[Dict]):
    # Optimized bulk insert/update
    existing = {s.symbol for s in db.query(GlobalSymbol.symbol).all()}
    to_add = []
    for item in data:
        if item["symbol"] not in existing:
            to_add.append(GlobalSymbol(
                symbol=item["symbol"],
                name=item["name"],
                asset_type=item.get("asset_type", AssetType.STOCK)
            ))
    if to_add:
        db.bulk_save_objects(to_add)
        db.commit()


def search_global_symbols(db: Session, query: str, limit: int = 20) -> List[GlobalSymbol]:
    """Search symbols by ticker or name with optimization."""
    q = query.upper()
    return db.query(GlobalSymbol).filter(
        (GlobalSymbol.symbol.ilike(f"{q}%")) | 
        (GlobalSymbol.name.ilike(f"%{q}%"))
    ).limit(limit).all()
