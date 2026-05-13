"""Portfolio P&L calculation — pure functions, no DB or HTTP."""

from datetime import date, timedelta
from typing import Dict, List, Optional
from schemas import HoldingOut, PortfolioSummary
from models import AssetType
from data_providers.base import QuoteData


def build_holdings(holdings_raw: Dict, quotes: Dict[str, QuoteData]) -> List[HoldingOut]:
    result = []
    for symbol, h in holdings_raw.items():
        qty = h["quantity"]
        total_cost = h["total_cost"]
        avg_buy = total_cost / qty if qty else 0

        quote = quotes.get(symbol)
        curr_price = quote.price if quote else None
        curr_value = curr_price * qty if curr_price is not None else None
        gain_loss = (curr_value - total_cost) if curr_value is not None else None
        gain_loss_pct = (gain_loss / total_cost * 100) if gain_loss is not None and total_cost else None

        result.append(HoldingOut(
            symbol=symbol,
            name=h.get("name"),
            quantity=qty,
            avg_buy_price=round(avg_buy, 4),
            total_cost=round(total_cost, 2),
            current_price=round(curr_price, 2) if curr_price is not None else None,
            current_value=round(curr_value, 2) if curr_value is not None else None,
            gain_loss=round(gain_loss, 2) if gain_loss is not None else None,
            gain_loss_pct=round(gain_loss_pct, 2) if gain_loss_pct is not None else None,
            day_change=round(quote.change, 2) if quote and quote.change is not None else None,
            day_change_pct=round(quote.change_pct, 2) if quote and quote.change_pct is not None else None,
            asset_type=h.get("asset_type", AssetType.STOCK),
            sector=h.get("sector")
        ))

    return sorted(result, key=lambda h: -(h.current_value or 0))


def build_summary(
    portfolio_id: int,
    portfolio_name: str,
    holdings: List[HoldingOut],
    cash_balance: float,      # already correct: deposits - withdrawals - buys + sells
    total_deposited: float,   # total cash ever deposited
    realized_pnl: float,      # profit/loss from closed positions
    win_loss_data: Optional[dict] = None, # {"wins": int, "losses": int, "total": int}
) -> PortfolioSummary:
    from schemas import WinLossStats
    win_loss = None
    if win_loss_data:
        win_loss = WinLossStats(
            wins=win_loss_data.get("wins", 0),
            losses=win_loss_data.get("losses", 0),
            total_trades=win_loss_data.get("total", 0),
            win_percentage=win_loss_data.get("win_pct", 0.0)
        )
    total_invested = sum(h.total_cost for h in holdings)
    current_value = sum(h.current_value if h.current_value is not None else h.total_cost for h in holdings)
    
    unrealized_pnl = current_value - total_invested
    total_gain_loss = unrealized_pnl + realized_pnl
    return_pct = (total_gain_loss / total_deposited * 100) if total_deposited else 0.0
    
    # Today's performance: Sum of (day_change * qty)
    day_pnl = sum((h.day_change or 0) * h.quantity for h in holdings)
    prev_day_value = (current_value - day_pnl)
    day_pnl_pct = (day_pnl / prev_day_value * 100) if prev_day_value else 0.0
    
    total_portfolio_value = current_value + cash_balance

    return PortfolioSummary(
        portfolio_id=portfolio_id,
        portfolio_name=portfolio_name,
        total_deposited=round(total_deposited, 2),
        total_invested=round(total_invested, 2),
        current_value=round(current_value, 2),
        total_unrealized_pnl=round(unrealized_pnl, 2),
        total_realized_pnl=round(realized_pnl, 2),
        total_gain_loss=round(total_gain_loss, 2),
        total_return_pct=round(return_pct, 2),
        day_pnl=round(day_pnl, 2),
        day_pnl_pct=round(day_pnl_pct, 2),
        dividend_income=0.0, # Placeholder for now
        cash_balance=round(cash_balance, 2),
        total_portfolio_value=round(total_portfolio_value, 2),
        holdings_count=len(holdings),
        win_loss=win_loss
    )


def build_portfolio_chart(
    trades: List,                  # List of Trade models
    historical: Dict[str, list],  # symbol -> [OHLCVPoint]
    cash_timeline: list,           # [{"date": str, "running_cash": float}]
    from_date: Optional[str] = None,
    benchmark_history: List = None, # List[OHLCVPoint]
) -> list:
    """
    Build a high-fidelity daily portfolio value series by:
      1. Creating a continuous date range.
      2. Deriving holdings for every single day from trade records.
      3. Summing equity (point-in-time holdings * prices) + cash.
    """
    all_dates: set = set()
    price_series: Dict[str, Dict[str, float]] = {}

    for sym, points in historical.items():
        price_series[sym] = {}
        for p in points:
            price_series[sym][p.date] = p.close
            all_dates.add(p.date)

    # Also include dates from cash events so the chart starts when the first deposit happened
    for entry in cash_timeline:
        all_dates.add(entry["date"])

    if not all_dates:
        # Final fallback: if there is NOTHING, not even cash, then return empty
        return []

    # Generate full date range
    sorted_data_dates = sorted(all_dates)
    if not sorted_data_dates:
        return []

    data_start_dt = date.fromisoformat(sorted_data_dates[0])

    # The portfolio's first activity date — never show the chart before this.
    first_activity_dt = date.fromisoformat(cash_timeline[0]["date"]) if cash_timeline else data_start_dt

    if from_date:
        requested_start_dt = date.fromisoformat(from_date)
        # Clamp to the first activity date so long-period charts (5Y/10Y) don't
        # show years of flat-zero before the portfolio even existed.
        start_dt = max(requested_start_dt, first_activity_dt)
    else:
        start_dt = first_activity_dt

    end_dt = date.fromisoformat(sorted_data_dates[-1])
    
    # If the end date is before the start date (e.g. looking at a week where no data exists yet)
    # we still want to show the range requested.
    if end_dt < start_dt:
        end_dt = start_dt
    
    continuous_dates = []
    curr = start_dt
    while curr <= end_dt:
        continuous_dates.append(curr.isoformat())
        curr += timedelta(days=1)

    # Map trades to dates and pre-calculate initial holdings for trades BEFORE start_dt
    trades_by_date: Dict[str, List] = {}
    curr_holdings: Dict[str, float] = {}
    from models import TradeAction

    for t in trades:
        dt_str = t.trade_date.isoformat()
        if dt_str < start_dt.isoformat():
            # Initial state: trade happened before chart range
            sym = t.symbol.upper()
            qty = float(t.quantity)
            if sym not in curr_holdings:
                curr_holdings[sym] = 0.0
            if t.action == TradeAction.BUY:
                curr_holdings[sym] += qty
            else:
                curr_holdings[sym] -= qty
        else:
            # Within chart range
            if dt_str not in trades_by_date:
                trades_by_date[dt_str] = []
            trades_by_date[dt_str].append(t)

    # Pre-calculate initial cash/principle for events BEFORE start_dt
    _last_cash = 0.0
    _last_principle = 0.0
    start_dt_str = start_dt.isoformat()
    for entry in cash_timeline:
        if entry["date"] < start_dt_str:
            _last_cash = entry["running_cash"]
            _last_principle = entry.get("invested_value", 0.0)
        else:
            break

    # Build maps for events WITHIN chart range
    cash_map: Dict[str, float] = {}
    principle_map: Dict[str, float] = {}
    for entry in cash_timeline:
        if entry["date"] >= start_dt_str:
            cash_map[entry["date"]] = entry["running_cash"]
            principle_map[entry["date"]] = entry.get("invested_value", 0.0)

    # Main iteration: calculate value per day
    result = []
    # Pre-fill prices for symbols to avoid KeyError, using earliest available price as backfill
    _last_prices = {}
    for sym, points in historical.items():
        if points:
            # points are sorted chronologically, so points[0] is the earliest
            _last_prices[sym] = points[0].close
        else:
            _last_prices[sym] = 0.0

    for d in continuous_dates:
        # Update current holdings state based on trades today
        if d in trades_by_date:
            for t in trades_by_date[d]:
                sym = t.symbol.upper()
                qty = float(t.quantity)
                if sym not in curr_holdings:
                    curr_holdings[sym] = 0.0
                
                if t.action == TradeAction.BUY:
                    curr_holdings[sym] += qty
                else: # SELL
                    curr_holdings[sym] -= qty
                    curr_holdings[sym] = max(0.0, curr_holdings[sym])

        # Update last prices
        for sym in historical:
            if sym in price_series and d in price_series[sym]:
                _last_prices[sym] = price_series[sym][d]

        # Update cash
        if d in cash_map:
            _last_cash = cash_map[d]

        # Calculate Equity
        equity_value = 0.0
        for sym, qty in curr_holdings.items():
            if qty > 0:
                price = _last_prices.get(sym, 0.0)
                equity_value += qty * price

        if d in principle_map:
            _last_principle = principle_map[d]
        
        today_val = round(equity_value + _last_cash, 2)
        result.append({
            "date": d, 
            "value": today_val, 
            "invested_value": round(_last_principle, 2)
        })

    # -- Benchmark & Performance Normalization --
    if result:
        bench_series = {}
        if benchmark_history:
            bench_series = {p.date: p.close for p in benchmark_history}

        # Use the first day the portfolio has actual value as the 0% baseline.
        # This avoids dividing by zero for the empty pre-trade period.
        p_start_idx = next((i for i, r in enumerate(result) if r["value"] > 0), None)
        p_start_val = result[p_start_idx]["value"] if p_start_idx is not None else 0

        # Find the benchmark baseline: first bench date AT OR AFTER the portfolio start.
        # This ensures the benchmark 0% reference aligns with when the portfolio began.
        b_start_val = None
        b_start_date = None
        if p_start_idx is not None and bench_series:
            p_start_date = result[p_start_idx]["date"]
            for d in sorted(bench_series):
                if d >= p_start_date:
                    b_start_val = bench_series[d]
                    b_start_date = d
                    break

        last_b_perf = None  # None until we have actual benchmark data
        b_started = False
        for i in range(len(result)):
            d = result[i]["date"]
            # 1. Portfolio performance % — only meaningful once portfolio has value
            if p_start_val > 0 and p_start_idx is not None and i >= p_start_idx:
                result[i]["perf_pct"] = round(((result[i]["value"] / p_start_val) - 1) * 100, 2)
            else:
                result[i]["perf_pct"] = None  # None = gap in Recharts, not drawn

            # 2. Benchmark — only emit values after benchmark data actually starts
            if b_start_val and b_start_date:
                if d in bench_series and d >= b_start_date:
                    b_started = True
                    result[i]["benchmark_perf_pct"] = round(((bench_series[d] / b_start_val) - 1) * 100, 2)
                    last_b_perf = result[i]["benchmark_perf_pct"]
                    result[i]["benchmark_value"] = round((bench_series[d] / b_start_val) * p_start_val, 2)
                elif b_started and d > b_start_date:
                    # Weekend/holiday gap-fill with last known value (only after data has started)
                    result[i]["benchmark_perf_pct"] = last_b_perf
                    if last_b_perf is not None:
                        result[i]["benchmark_value"] = round((1 + last_b_perf / 100) * p_start_val, 2)
                # else: before benchmark data range — leave as None (no key set)

    return result
