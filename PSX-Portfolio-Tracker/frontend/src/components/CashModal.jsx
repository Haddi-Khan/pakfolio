import { useState } from "react";
import { X, ArrowDownLeft, ArrowUpRight, Wallet } from "lucide-react";
import { api } from "../api/client";
import { fmt } from "../utils/format";
import { motion, AnimatePresence } from "framer-motion";

const inputCls = "w-full rounded-xl px-3.5 py-2.5 text-sm font-medium bg-surface-2 border border-border text-white placeholder-muted/50 focus:outline-none transition-all focus:ring-1 focus:ring-accent/50 focus:border-accent/60";

export function CashModal({ onClose, onAdded, portfolioId }) {
  const [txType, setTxType] = useState("DEPOSIT");
  const [amount, setAmount] = useState("");
  const [txDate, setTxDate] = useState(new Date().toISOString().slice(0, 10));
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!amount || parseFloat(amount) <= 0) { setError("Enter a valid amount"); return; }
    setSubmitting(true); setError(null);
    try {
      await api.cash.add({ tx_type: txType, amount: parseFloat(amount), tx_date: txDate, description: description || null }, portfolioId);
      onAdded?.(); onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  const isDeposit = txType === "DEPOSIT";

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
          className="w-full max-w-md rounded-2xl bg-surface border border-border shadow-2xl"
        >

          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface/90 rounded-t-2xl">
            <div className="flex items-center gap-3">
              <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${isDeposit ? "bg-gain/20 text-gain" : "bg-loss/20 text-loss"}`}>
                <Wallet size={16} />
              </div>
              <div>
                <h2 className="text-white font-bold text-base leading-none">Cash Transaction</h2>
                <p className="text-muted text-xs mt-0.5">Deposit or withdraw</p>
              </div>
            </div>
            <button onClick={onClose}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-white bg-surface-2 hover:bg-surface-3 transition-colors">
              <X size={14} />
            </button>
          </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">

          {/* Deposit / Withdraw toggle */}
          <div className="grid grid-cols-2 gap-0 rounded-xl p-1 bg-surface-2 border border-border">
            {[["DEPOSIT", "Add Cash", ArrowDownLeft, "bg-gain text-white shadow-gain/40"],
            ["WITHDRAWAL", "Withdraw Cash", ArrowUpRight, "bg-loss text-white shadow-loss/40"]].map(([val, label, Icon, activeClass]) => (
              <button key={val} type="button" onClick={() => setTxType(val)}
                className={`py-2.5 rounded-lg font-bold text-sm flex items-center justify-center gap-2 transition-all ${txType === val ? `${activeClass} shadow-lg` : "text-muted hover:text-soft border border-transparent"
                  }`}>
                <Icon size={14} />
                {label}
              </button>
            ))}
          </div>

          {/* Amount */}
          <div>
            <label className="text-muted text-xs font-bold uppercase tracking-widest mb-2 block">Amount (PKR)</label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm font-bold select-none text-muted">PKR</span>
              <input
                type="number" min="0" step="0.01" placeholder="0.00"
                value={amount} onChange={(e) => setAmount(e.target.value)} autoFocus
                className={`${inputCls} mono pl-14 text-lg font-bold border ${isDeposit ? "bg-gain/10 border-gain/20" : "bg-loss/10 border-loss/20"}`}
              />
            </div>
            {amount && parseFloat(amount) > 0 && (
              <p className="text-xs mt-1.5 pl-0.5 mono fade-in">
                <span className={`font-semibold ${isDeposit ? "text-gain" : "text-loss"}`}>
                  {isDeposit ? "+" : "−"}{fmt.pkr(parseFloat(amount))}
                </span>
              </p>
            )}
          </div>

          {/* Date */}
          <div>
            <label className="text-muted text-xs font-bold uppercase tracking-widest mb-2 block">Date</label>
            <input type="date" value={txDate} onChange={(e) => setTxDate(e.target.value)}
              className={inputCls} />
          </div>

          {/* Description */}
          <div>
            <label className="text-muted text-xs font-bold uppercase tracking-widest mb-2 block">
              Description <span className="normal-case font-normal text-muted/60">(optional)</span>
            </label>
            <textarea
              placeholder="e.g. Monthly top-up..."
              value={description} onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className={`${inputCls} resize-none`} />
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
                background: isDeposit
                  ? "linear-gradient(135deg, #10B981, #059669)"
                  : "linear-gradient(135deg, #EF4444, #DC2626)",
                boxShadow: isDeposit ? "0 4px 16px rgba(16,185,129,0.35)" : "0 4px 16px rgba(239,68,68,0.35)",
              }}>
              {submitting ? "Processing..." : isDeposit ? "Add Cash" : "Withdraw Cash"}
            </button>
          </div>
        </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
