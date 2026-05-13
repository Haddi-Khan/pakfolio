import { TrendingUp, TrendingDown, Minus, ChevronRight, DollarSign } from "lucide-react";
import { Link } from "react-router-dom";
import { fmt } from "../utils/format";
import { motion, AnimatePresence } from "framer-motion";

function PLBadge({ value, pct }) {
  if (value == null) return <span className="text-muted">—</span>;
  const pos = value >= 0;
  return (
    <div className={`inline-flex flex-col items-end px-2.5 py-1 rounded-lg mono ${pos ? "bg-gain/10 text-gain" : "bg-loss/10 text-loss"
      }`}>
      <span className="font-bold text-sm leading-tight">{pos ? "+" : ""}{fmt.num(value)}</span>
      <span className="text-xs opacity-80">{fmt.pct(pct)}</span>
    </div>
  );
}

function DayChange({ pct }) {
  if (pct == null) return <span className="text-muted">—</span>;
  const pos = pct >= 0;
  const Icon = pos ? TrendingUp : TrendingDown;
  return (
    <div className={`flex items-center justify-end gap-1 mono text-sm font-semibold ${pos ? "text-gain" : "text-loss"}`}>
      <Icon size={12} />
      {fmt.pct(pct)}
    </div>
  );
}

function WeightBar({ pct, color }) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-surface-2 rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${Math.min(pct, 100)}%`, background: color || "#3B82F6" }} />
      </div>
      <span className="text-muted text-xs mono">{pct?.toFixed(1)}%</span>
    </div>
  );
}

export function HoldingsTable({ holdings, loading, onSymbolClick, onCloseClick, cashBalance = 0 }) {
  if (loading) {
    return (
      <div className="space-y-2 p-1">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-14 bg-surface-2 animate-pulse rounded-xl" />
        ))}
      </div>
    );
  }

  if (!holdings?.length && cashBalance <= 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted gap-3">
        <Minus size={32} className="opacity-20" />
        <p className="text-sm">No holdings yet. Add your first trade.</p>
      </div>
    );
  }

  // Total includes cash so weights are relative to full portfolio
  const equitiesValue = holdings.reduce((s, h) => s + (h.current_value ?? h.total_cost), 0);
  const totalValue = equitiesValue + cashBalance;

  return (
    <div className="overflow-x-auto -mx-1">
      <table className="w-full text-sm min-w-[700px]">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left py-3 px-4 text-muted text-xs font-semibold uppercase tracking-widest">Symbol</th>
            <th className="text-right py-3 px-3 text-muted text-xs font-semibold uppercase tracking-widest">Qty</th>
            <th className="text-right py-3 px-3 text-muted text-xs font-semibold uppercase tracking-widest">Avg Buy</th>
            <th className="text-right py-3 px-3 text-muted text-xs font-semibold uppercase tracking-widest">Cur. Price</th>
            <th className="text-right py-3 px-3 text-muted text-xs font-semibold uppercase tracking-widest">Mkt Value</th>
            <th className="text-right py-3 px-3 text-muted text-xs font-semibold uppercase tracking-widest">P&L</th>
            <th className="text-right py-3 px-3 text-muted text-xs font-semibold uppercase tracking-widest">Day</th>
            <th className="py-3 px-3"></th>
          </tr>
        </thead>
        <motion.tbody 
          initial="hidden"
          animate="show"
          variants={{
            hidden: { opacity: 0 },
            show: { opacity: 1, transition: { staggerChildren: 0.05 } }
          }}
          className="divide-y divide-border/40"
        >
          {holdings.map((h, i) => {
            const weight = totalValue ? ((h.current_value ?? h.total_cost) / totalValue) * 100 : 0;
            const priceUp = h.current_price != null && h.current_price >= h.avg_buy_price;
            return (
              <motion.tr 
                variants={{
                  hidden: { opacity: 0, x: -10 },
                  show: { opacity: 1, x: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
                }}
                key={h.symbol}
                onClick={() => onSymbolClick?.(h)}
                className={`hover:bg-surface-2/60 transition-colors group ${onSymbolClick ? "cursor-pointer" : ""}`}
              >
                <td className="py-3.5 px-4">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-surface-3 border border-border flex items-center justify-center shrink-0">
                      <span className="text-accent font-black text-xs">{h.symbol.slice(0, 2)}</span>
                    </div>
                    <div>
                      <Link 
                        to={h.asset_type === "mutual_fund" ? `/mutual-funds/${h.symbol}` : `/stocks/${h.symbol}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="flex items-center gap-1 font-bold text-white text-sm hover:text-accent hover:underline decoration-accent/40 decoration-2 underline-offset-4 transition-all"
                      >
                        {h.symbol}
                        <ChevronRight size={12} className="opacity-0 group-hover:opacity-100 transition-opacity text-accent" />
                      </Link>
                      <div className="text-muted text-xs truncate max-w-[130px]">{h.name}</div>
                    </div>
                  </div>
                </td>
                <td className="py-3.5 px-3 text-right">
                  <span className="text-soft mono font-medium">{fmt.num(h.quantity, 0)}</span>
                </td>
                <td className="py-3.5 px-3 text-right">
                  <span className="text-soft mono">{fmt.num(h.avg_buy_price)}</span>
                </td>
                <td className="py-3.5 px-3 text-right">
                  {h.current_price != null ? (
                    <span className={`mono font-semibold ${priceUp ? "text-gain" : "text-loss"}`}>
                      {fmt.num(h.current_price)}
                    </span>
                  ) : <span className="text-muted">—</span>}
                </td>
                <td className="py-3.5 px-3 text-right">
                  <span className="text-white font-semibold mono">
                    {h.current_value != null ? fmt.pkr(h.current_value) : "—"}
                  </span>
                </td>
                <td className="py-3.5 px-3 text-right">
                  <PLBadge value={h.gain_loss} pct={h.gain_loss_pct} />
                </td>
                <td className="py-3.5 px-3 text-right">
                  <DayChange pct={h.day_change_pct} />
                </td>
                <td className="py-3.5 px-3">
                  <WeightBar pct={weight} />
                </td>
                <td className="py-3.5 px-3 text-right">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onCloseClick?.(h);
                    }}
                    className="opacity-0 group-hover:opacity-100 px-3 py-1.5 rounded-lg bg-loss/10 text-loss border border-loss/20 hover:bg-loss hover:text-white text-[10px] font-black uppercase tracking-widest transition-all shadow-sm shadow-loss/20"
                  >
                    Close
                  </button>
                </td>
              </motion.tr>
            );
          })}

          {/* Cash row — always PKR 1 = 1 PKR, no P&L */}
          {cashBalance > 0 && (
            <motion.tr 
              variants={{ hidden: { opacity: 0, x: -10 }, show: { opacity: 1, x: 0 } }}
              className="opacity-70 hover:opacity-100 hover:bg-surface-2/60 transition-all"
            >
              <td className="py-3.5 px-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-surface-3 border border-border flex items-center justify-center shrink-0">
                    <DollarSign size={14} className="text-gain" />
                  </div>
                  <div>
                    <div className="font-bold text-soft text-sm">PKR Cash</div>
                    <div className="text-muted text-xs">Available cash</div>
                  </div>
                </div>
              </td>
              <td className="py-3.5 px-3 text-right">
                <span className="text-soft mono font-medium">{fmt.num(cashBalance, 2)}</span>
              </td>
              <td className="py-3.5 px-3 text-right">
                <span className="text-muted mono">1.00</span>
              </td>
              <td className="py-3.5 px-3 text-right">
                <span className="text-gain mono font-semibold">1.00</span>
              </td>
              <td className="py-3.5 px-3 text-right">
                <span className="text-white font-semibold mono">{fmt.pkr(cashBalance)}</span>
              </td>
              <td className="py-3.5 px-3 text-right">
                <span className="text-muted text-xs mono">—</span>
              </td>
              <td className="py-3.5 px-3 text-right">
                <span className="text-muted text-xs mono">—</span>
              </td>
              <td className="py-3.5 px-3">
                <WeightBar pct={totalValue ? (cashBalance / totalValue) * 100 : 0} color="var(--color-gain, #10B981)" />
              </td>
            </motion.tr>
          )}
        </motion.tbody>
      </table>
    </div>
  );
}
