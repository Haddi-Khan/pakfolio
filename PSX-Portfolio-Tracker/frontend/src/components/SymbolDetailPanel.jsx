import { useState, useEffect, useMemo } from "react";
import { X, TrendingUp, TrendingDown, RefreshCw, ArrowUpRight, ArrowDownRight } from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { api } from "../api/client";
import { fmt } from "../utils/format";
import { motion, AnimatePresence } from "framer-motion";

const PERIODS = ["1W", "1M", "3M", "6M", "1Y"];

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-surface-3 border border-border rounded-xl px-3 py-2 shadow-2xl">
      <p className="text-muted text-xs mb-0.5">{fmt.date(label)}</p>
      <p className="text-white font-bold mono">{fmt.num(payload[0].value)}</p>
    </div>
  );
}

export function SymbolDetailPanel({ symbol, holding, pid, onClose }) {
  const [quote, setQuote] = useState(null);
  const [history, setHistory] = useState([]);
  const [trades, setTrades] = useState([]);
  const [period, setPeriod] = useState("1M");
  const [loadingQuote, setLoadingQuote] = useState(true);
  const [loadingChart, setLoadingChart] = useState(true);
  const [loadingTrades, setLoadingTrades] = useState(true);

  // Fetch live quote
  useEffect(() => {
    setLoadingQuote(true);
    api.prices.quote(symbol)
      .then(setQuote)
      .catch(() => setQuote(null))
      .finally(() => setLoadingQuote(false));
  }, [symbol]);

  // Fetch price history
  useEffect(() => {
    setLoadingChart(true);
    const today = new Date().toISOString().slice(0, 10);
    const periodDays = { "1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365 };
    const from = new Date(Date.now() - periodDays[period] * 86400000).toISOString().slice(0, 10);
    api.prices.history(symbol, from, today)
      .then(setHistory)
      .catch(() => setHistory([]))
      .finally(() => setLoadingChart(false));
  }, [symbol, period]);

  // Fetch trades for this symbol in this portfolio
  useEffect(() => {
    setLoadingTrades(true);
    api.trades.list(symbol, pid)
      .then(setTrades)
      .catch(() => setTrades([]))
      .finally(() => setLoadingTrades(false));
  }, [symbol, pid]);

  const chartData = history.map((p) => ({ date: p.date, value: p.close }));
  const firstVal = chartData[0]?.value;
  const lastVal = chartData[chartData.length - 1]?.value;
  const change = firstVal && lastVal ? lastVal - firstVal : null;
  const changePct = change != null && firstVal ? (change / firstVal) * 100 : null;
  const isUp = change == null || change >= 0;
  const strokeColor = isUp ? "#10B981" : "#EF4444";

  const isQuoteUp = quote?.change == null || (quote?.change ?? 0) >= 0;

  // Close on Escape
  useEffect(() => {
    function onKey(e) { if (e.key === "Escape") onClose(); }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }} 
        animate={{ opacity: 1 }} 
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-start justify-end p-4 bg-bg/80 backdrop-blur-md"
      >
        <div className="absolute inset-0 -z-10" onClick={onClose} />

        <motion.div
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
          className="w-full max-w-xl rounded-2xl flex flex-col max-h-[calc(100vh-2rem)] overflow-hidden bg-surface border border-border shadow-2xl"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 shrink-0 border-b border-border bg-surface/90">
            <div className="flex items-center gap-3">
              <div className={`w-11 h-11 rounded-xl border flex items-center justify-center shrink-0 font-black text-sm ${
              isQuoteUp ? "bg-gain/10 border-gain/20 text-gain" : "bg-loss/10 border-loss/20 text-loss"
            }`}>
              {symbol.slice(0, 2)}
            </div>
            <div>
              <div className="text-white font-bold text-lg leading-none">{symbol}</div>
              {holding?.name && <div className="text-muted text-xs mt-0.5 truncate max-w-[240px]">{holding.name}</div>}
            </div>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-xl flex items-center justify-center text-muted hover:text-white hover:bg-surface-2 transition-all">
            <X size={15} />
          </button>
        </div>

        <div className="overflow-y-auto flex-1 p-5 space-y-4">

          {/* Live Price + Position */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl p-4 bg-surface-2/50 border border-border">
              <div className="text-xs font-bold uppercase tracking-widest mb-2 text-muted">Live Price</div>
              {loadingQuote ? (
                <div className="h-8 w-24 bg-surface-2 animate-pulse rounded-lg" />
              ) : quote?.price ? (
                <>
                  <div className="text-white font-bold text-2xl mono leading-none">{fmt.num(quote.price)}</div>
                  {quote.change != null && (
                    <div className={`flex items-center gap-1.5 mt-1.5 text-sm mono font-semibold ${isQuoteUp ? "text-gain" : "text-loss"}`}>
                      {isQuoteUp ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                      {isQuoteUp ? "+" : ""}{fmt.num(quote.change)}
                      <span className="text-xs opacity-80">({fmt.pct(quote.change_pct)})</span>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-muted text-sm">Price unavailable</div>
              )}
            </div>

            {holding && (
              <div className="rounded-xl p-4 bg-surface-2/50 border border-border">
                <div className="text-xs font-bold uppercase tracking-widest mb-2 text-muted">Your Position</div>
                <div className="text-white font-bold text-xl mono leading-none">{fmt.pkr(holding.current_value ?? holding.total_cost)}</div>
                <div className="flex items-center gap-2 mt-1.5 text-xs">
                  <span className="text-muted mono">{fmt.num(holding.quantity, 2)} units</span>
                  {holding.gain_loss != null && (
                    <span className={`mono font-bold ${holding.gain_loss >= 0 ? "text-gain" : "text-loss"}`}>
                      {holding.gain_loss >= 0 ? "+" : ""}{fmt.pkr(holding.gain_loss)}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Stats row */}
          {quote && (quote.open || quote.high || quote.low || quote.prev_close) && (
            <div className="grid grid-cols-4 gap-2">
              {[
                ["Open", fmt.num(quote.open)],
                ["High", fmt.num(quote.high)],
                ["Low", fmt.num(quote.low)],
                ["Prev", fmt.num(quote.prev_close)],
              ].map(([label, val]) => (
                <div key={label} className="rounded-xl p-2.5 text-center bg-surface-2/50 border border-border">
                  <div className="text-muted text-xs mb-1">{label}</div>
                  <div className="text-soft text-sm font-semibold mono">{val ?? "—"}</div>
                </div>
              ))}
            </div>
          )}

          {/* Price Chart */}
          <div className="rounded-xl p-4 bg-surface-2/50 border border-border">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-white font-semibold text-sm">Price History</div>
                {change != null && !loadingChart && (
                  <div className={`text-xs mono font-medium mt-0.5 ${isUp ? "text-gain" : "text-loss"}`}>
                    {isUp ? "+" : ""}{fmt.num(change)} ({fmt.pct(changePct)}) this period
                  </div>
                )}
              </div>
              <div className="flex bg-surface-2 border border-border rounded-xl p-0.5 gap-0.5">
                {PERIODS.map((p) => (
                  <button key={p} onClick={() => setPeriod(p)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all ${
                      period === p ? "bg-accent text-white shadow-sm" : "text-muted hover:text-soft"
                    }`}>
                    {p}
                  </button>
                ))}
              </div>
            </div>

            {loadingChart ? (
              <div className="h-36 bg-surface-2 animate-pulse rounded-xl" />
            ) : chartData.length < 2 ? (
              <div className="h-36 flex items-center justify-center text-muted text-sm">No price history available</div>
            ) : (
              <ResponsiveContainer width="100%" height={148}>
                <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id={`grad-${symbol}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={strokeColor} stopOpacity={0.25} />
                      <stop offset="100%" stopColor={strokeColor} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="2 4" stroke="var(--color-border)" vertical={false} />
                  <XAxis dataKey="date" tick={{ fill: "var(--color-muted)", fontSize: 9 }} axisLine={false} tickLine={false}
                    tickFormatter={(d) => new Date(d).toLocaleDateString("en-PK", { month: "short", day: "numeric" })} />
                  <YAxis tick={{ fill: "var(--color-muted)", fontSize: 9 }} axisLine={false} tickLine={false} width={52}
                    tickFormatter={(v) => fmt.compact(v)} domain={["auto", "auto"]} />
                  <Tooltip content={<ChartTooltip />} cursor={{ stroke: "var(--color-border)", strokeWidth: 1 }} />
                  <Area type="monotone" dataKey="value" stroke={strokeColor} strokeWidth={2}
                    fill={`url(#grad-${symbol})`} dot={false}
                    activeDot={{ r: 4, fill: strokeColor, stroke: "var(--color-surface)", strokeWidth: 2 }} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Your Trades */}
          <div>
            <div className="text-muted text-xs font-semibold uppercase tracking-widest mb-3">Your Trades</div>
            {loadingTrades ? (
              <div className="space-y-2">
                {[...Array(3)].map((_, i) => <div key={i} className="h-11 bg-surface-2 animate-pulse rounded-xl" />)}
              </div>
            ) : trades.length === 0 ? (
              <div className="text-muted text-sm text-center py-6 border border-border rounded-xl bg-surface-2/30">
                No trades recorded for {symbol}
              </div>
            ) : (
              <div className="space-y-1.5">
                {trades.map((t) => (
                  <div key={t.id} className="flex items-center justify-between rounded-xl px-4 py-3 transition-colors bg-surface-2/30 border border-border">
                    <div className="flex items-center gap-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-bold ${
                        t.action === "BUY" ? "bg-gain/15 text-gain" : "bg-loss/15 text-loss"
                      }`}>
                        {t.action === "BUY" ? <ArrowUpRight size={10} /> : <ArrowDownRight size={10} />}
                        {t.action}
                      </span>
                      <span className="text-muted text-xs mono">{fmt.date(t.trade_date)}</span>
                    </div>
                    <div className="text-right">
                      <div className="text-white text-sm font-bold mono">{fmt.pkr(t.net_cost)}</div>
                      <div className="text-muted text-xs mono">{fmt.num(t.quantity, 2)} × {fmt.num(t.price)}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
