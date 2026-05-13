import { useState, useEffect } from "react";
import { X, Search, ArrowUpRight, ArrowDownRight, TrendingUp } from "lucide-react";
import { api } from "../api/client";
import { fmt } from "../utils/format";
import { motion, AnimatePresence } from "framer-motion";

const ASSET_TYPES = ["Stock", "Mutual Fund", "ETF", "Forex"];

function useSymbolSearch(query) {
  const [results, setResults] = useState([]);
  useEffect(() => {
    if (!query) { setResults([]); return; }
    const t = setTimeout(() => {
      api.symbols.search(query).then(setResults).catch(() => setResults([]));
    }, 300);
    return () => clearTimeout(t);
  }, [query]);
  return results;
}

// Shared input style — clearly visible on dark modal
const inputCls = "w-full rounded-xl px-3.5 py-2.5 text-sm font-medium bg-surface-2 border border-border text-white placeholder-muted/50 focus:outline-none transition-all";
const inputFocusClass = "focus:ring-1 focus:ring-accent/50 focus:border-accent/60";

export function AddTradeModal({ onClose, onAdded, cashBalance = 0, portfolioId, initialData }) {
  const [assetType, setAssetType] = useState("Stock");
  const [action, setAction] = useState("BUY");
  const [tradeType, setTradeType] = useState("LONG");
  const [symbolQuery, setSymbolQuery] = useState("");
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [showDrop, setShowDrop] = useState(false);
  const [price, setPrice] = useState("");
  const [quantity, setQuantity] = useState("");
  const [deductions, setDeductions] = useState("0");
  const [tradeDate, setTradeDate] = useState(new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const isEdit = !!initialData?.id;

  useEffect(() => {
    if (initialData) {
      if (initialData.action) setAction(initialData.action);
      if (initialData.symbol) {
        const sym = { symbol: initialData.symbol, name: initialData.name, asset_type: initialData.asset_type };
        setSelectedSymbol(sym);
        setSymbolQuery(initialData.symbol);
      }
      if (initialData.asset_type) {
        if (initialData.asset_type === "mutual_fund") setAssetType("Mutual Fund");
        else if (initialData.asset_type === "etf") setAssetType("ETF");
        else setAssetType("Stock");
      }
      if (initialData.price) setPrice(initialData.price.toString());
      if (initialData.quantity) setQuantity(initialData.quantity.toString());
      if (initialData.trade_date) setTradeDate(new Date(initialData.trade_date).toISOString().slice(0, 10));
      if (initialData.notes) setNotes(initialData.notes);
      if (initialData.deductions != null) setDeductions(initialData.deductions.toString());
    }
  }, [initialData]);

  async function handleSelectSymbol(r) {
    setSelectedSymbol(r);
    setSymbolQuery(r.symbol);
    setShowDrop(false);

    // Auto-select asset type if returned from backend
    if (r.asset_type === "mutual_fund") setAssetType("Mutual Fund");
    else if (r.asset_type === "etf") setAssetType("ETF");
    else if (r.asset_type === "stock") setAssetType("Stock");

    // Auto-select asset type if returned from backend
    if (r.asset_type === "mutual_fund") setAssetType("Mutual Fund");
    else if (r.asset_type === "etf") setAssetType("ETF");
    else if (r.asset_type === "stock") setAssetType("Stock");
  }

  // Auto-fill price when symbol or date changes
  useEffect(() => {
    if (!selectedSymbol || !tradeDate) return;

    const isToday = tradeDate === new Date().toISOString().slice(0, 10);
    const fetchPrice = async () => {
      try {
        if (isToday) {
          const q = await api.prices.quote(selectedSymbol.symbol);
          if (q.price) setPrice(q.price.toString());
        } else {
          // Fetch historical price for that date
          // We fetch a 4-day range ending on target date to handle weekends/holidays (taking the last available point)
          const target = new Date(tradeDate);
          const start = new Date(target);
          start.setDate(target.getDate() - 4);
          
          const startStr = start.toISOString().slice(0, 10);
          const points = await api.prices.history(selectedSymbol.symbol, startStr, tradeDate);
          
          if (points && points.length > 0) {
            // Last point is the one closest to (or on) the target date
            const lastPoint = points[points.length - 1];
            setPrice(lastPoint.close.toString());
          }
        }
      } catch (err) {
        console.warn("Failed to auto-fill price:", err);
      }
    };

    fetchPrice();
  }, [selectedSymbol, tradeDate]);

  const searchResults = useSymbolSearch(symbolQuery);
  const gross = price && quantity ? parseFloat(price) * parseFloat(quantity) : null;
  const ded = parseFloat(deductions) || 0;
  const net = gross != null ? (action === "BUY" ? gross + ded : gross - ded) : null;
  const isBuy = action === "BUY";

  async function handleSubmit(e) {
    e.preventDefault();
    if (!selectedSymbol) { setError("Select a symbol"); return; }
    if (!price || !quantity) { setError("Price and quantity are required"); return; }
    setSubmitting(true); setError(null);
    try {
      const data = {
        symbol: selectedSymbol.symbol,
        name: selectedSymbol.name,
        action,
        trade_type: tradeType,
        asset_type: assetType === "Mutual Fund" ? "mutual_fund" : assetType === "ETF" ? "etf" : "stock",
        price: parseFloat(price),
        quantity: parseFloat(quantity),
        deductions: parseFloat(deductions) || 0,
        trade_date: tradeDate,
        notes: notes || null,
      };

      if (isEdit) {
        await api.trades.update(initialData.id, data);
      } else {
        await api.trades.add(data, portfolioId);
      }
      onAdded?.(); onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }} 
        animate={{ opacity: 1 }} 
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg/80 backdrop-blur-md"
      >
        <motion.div 
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
          className="w-full max-w-lg rounded-2xl max-h-[94vh] overflow-y-auto bg-surface border border-border shadow-2xl"
        >

          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 sticky top-0 z-10 bg-surface/90 backdrop-blur border-b border-border">
            <div className="flex items-center gap-3">
              <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm font-black ${isBuy ? "bg-gain/20 text-gain" : "bg-loss/20 text-loss"}`}>
                <TrendingUp size={16} />
              </div>
              <div>
                <h2 className="text-white font-bold text-base leading-none">Open Trade</h2>
                <p className="text-muted text-xs mt-0.5">Cash: <span className="text-soft mono font-semibold">{fmt.pkr(cashBalance)}</span></p>
              </div>
            </div>
            <button onClick={onClose}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-white bg-surface-2 hover:bg-surface-3 transition-colors">
              <X size={14} />
            </button>
          </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">

          {/* BUY / SELL — pill toggle */}
          <div className="grid grid-cols-2 gap-0 rounded-xl p-1 bg-surface-2 border border-border">
            {[["BUY", ArrowUpRight, "bg-gain text-white shadow-gain/40"], ["SELL", ArrowDownRight, "bg-loss text-white shadow-loss/40"]].map(([a, Icon, activeClass]) => (
              <button key={a} type="button" onClick={() => setAction(a)}
                className={`py-2.5 rounded-lg font-black text-sm tracking-widest flex items-center justify-center gap-2 transition-all ${action === a ? `${activeClass} shadow-lg` : "text-muted hover:text-soft border border-transparent"
                  }`}>
                <Icon size={14} />
                {a}
              </button>
            ))}
          </div>

          {/* Asset type pills */}
          <div>
            <label className="text-muted text-xs font-bold uppercase tracking-widest mb-2 block">Asset Type</label>
            <div className="flex flex-wrap gap-2">
              {ASSET_TYPES.map((t) => (
                <button key={t} type="button" onClick={() => setAssetType(t)}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all border ${assetType === t
                    ? "text-accent border-accent/40 bg-accent/10"
                    : "text-muted hover:text-soft border-border/30 bg-surface-2/20"
                    }`}>
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* Symbol + Date */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-muted text-xs font-bold uppercase tracking-widest mb-2 block">Symbol</label>
              <div className="relative">
                <Search size={13} className="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none text-muted" />
                <input
                  type="text" placeholder="Search..."
                  value={symbolQuery}
                  onChange={(e) => { setSymbolQuery(e.target.value); setShowDrop(true); setSelectedSymbol(null); }}
                  onFocus={() => setShowDrop(true)}
                  className={`${inputCls} ${inputFocusClass} pl-9`}
                />
                {showDrop && searchResults.length > 0 && (
                  <div className="absolute top-full left-0 right-0 rounded-xl mt-1 z-20 max-h-44 overflow-y-auto fade-in bg-surface-2 border border-border shadow-2xl">
                    {searchResults.map((r) => (
                      <button key={r.symbol} type="button"
                        onClick={() => handleSelectSymbol(r)}
                        className="w-full text-left px-4 py-2.5 transition-colors flex items-center gap-3 border-b border-border last:border-0 hover:bg-surface-3">
                        <span className="text-accent font-bold text-sm">{r.symbol}</span>
                        <div className="flex-1 min-w-0">
                          <div className="text-white text-xs truncate">{r.name}</div>
                          {r.asset_type && <span className="text-[10px] text-muted uppercase font-bold tracking-tighter">{r.asset_type.replace("_", " ")}</span>}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              {selectedSymbol && (
                <p className="text-xs text-muted mt-1 pl-0.5 truncate fade-in">{selectedSymbol.name}</p>
              )}
            </div>
            <div>
              <label className="text-muted text-xs font-bold uppercase tracking-widest mb-2 block">Date</label>
              <input type="date" value={tradeDate} onChange={(e) => setTradeDate(e.target.value)}
                className={`${inputCls} ${inputFocusClass}`} />
            </div>
          </div>

          {/* Price + Quantity */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-muted text-xs font-bold uppercase tracking-widest mb-2 block">Price (PKR)</label>
              <input type="number" min="0" step="0.01" placeholder="0.00" value={price}
                onChange={(e) => setPrice(e.target.value)}
                className={`${inputCls} ${inputFocusClass} mono`} />
            </div>
            <div>
              <label className="text-muted text-xs font-bold uppercase tracking-widest mb-2 block">Quantity</label>
              <input type="number" min="0" step="0.01" placeholder="0" value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className={`${inputCls} ${inputFocusClass} mono`} />
            </div>
          </div>

          {/* Brokerage */}
          <div>
            <label className="text-muted text-xs font-bold uppercase tracking-widest mb-2 block">Brokerage / Tax (PKR)</label>
            <input type="number" min="0" step="0.01" value={deductions}
              onChange={(e) => setDeductions(e.target.value)}
              className={`${inputCls} ${inputFocusClass} mono`} />
          </div>

          {/* Cost preview */}
          {gross != null && (
            <div className={`rounded-xl p-4 fade-in border ${isBuy ? "bg-gain/10 border-gain/20" : "bg-loss/10 border-loss/20"}`}>
              <div className="grid grid-cols-3 gap-3">
                {[["Gross", fmt.pkr(gross)], ["Fees", fmt.pkr(ded)], ["Net Cost", fmt.pkr(net)]].map(([label, val]) => (
                  <div key={label}>
                    <div className="text-xs mb-1 text-muted">{label}</div>
                    <div className={`font-bold text-sm mono ${label === "Net Cost" ? (isBuy ? "text-gain" : "text-loss") : "text-soft"}`}>{val}</div>
                  </div>
                ))}
              </div>
              {isBuy && cashBalance > 0 && net != null && (
                <div className="mt-3 pt-3 flex justify-between text-xs border-t border-border">
                  <span className="text-muted">Remaining cash</span>
                  <span className={`mono font-semibold ${cashBalance - net < 0 ? "text-loss" : "text-soft"}`}>{fmt.pkr(cashBalance - net)}</span>
                </div>
              )}
            </div>
          )}

          {/* Notes */}
          <div>
            <label className="text-muted text-xs font-bold uppercase tracking-widest mb-2 block">
              Notes <span className="normal-case font-normal text-muted/60">(optional)</span>
            </label>
            <input type="text" placeholder="Add a note..." value={notes} onChange={(e) => setNotes(e.target.value)}
              className={`${inputCls} ${inputFocusClass}`} />
          </div>

          {error && (
            <div className="rounded-xl px-4 py-2.5 text-sm fade-in" style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.25)", color: "#F87171" }}>
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose}
              className="px-5 py-2.5 rounded-xl text-sm font-semibold text-soft hover:text-white transition-all bg-surface-2 border border-border">
              Cancel
            </button>
            <button type="submit" disabled={submitting}
              className={`flex-1 py-2.5 rounded-xl text-sm font-black tracking-wide transition-all disabled:opacity-40 text-white`}
              style={{
                background: isBuy
                  ? "linear-gradient(135deg, #10B981, #059669)"
                  : "linear-gradient(135deg, #EF4444, #DC2626)",
                boxShadow: isBuy ? "0 4px 16px rgba(16,185,129,0.35)" : "0 4px 16px rgba(239,68,68,0.35)",
              }}>
              {submitting ? "Processing..." : `${action} ${selectedSymbol?.symbol || "Trade"}`}
            </button>
          </div>

        </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
