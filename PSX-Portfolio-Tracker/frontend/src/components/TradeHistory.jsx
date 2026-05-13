import { Trash2, History, X, Filter, Edit3, Wallet as WalletIcon, Download, Upload } from "lucide-react";
import { fmt } from "../utils/format";
import { api } from "../api/client";
import { useState, useMemo } from "react";
import { usePortfolioCtx } from "../context/PortfolioContext";

export function TradeHistory({ trades, loading, onRefresh, onEdit }) {
  const [deleting, setDeleting] = useState(null);
  const [symbolFilter, setSymbolFilter] = useState("");
  const [actionFilter, setActionFilter] = useState("ALL");
  const [importing, setImporting] = useState(false);
  const { portfolios, activePid, setActivePid } = usePortfolioCtx();

  async function handleDelete(id) {
    if (!confirm("Delete this trade? This cannot be undone.")) return;
    setDeleting(id);
    try {
      await api.trades.remove(id);
      onRefresh?.();
    } catch (e) {
      alert(e.message);
    } finally {
      setDeleting(null);
    }
  }

  async function handleExport() {
    try {
      const blob = await api.trades.export(activePid);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `trades-export-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert("Export failed: " + e.message);
    }
  }

  async function handleImport(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setImporting(true);
    try {
      const res = await api.trades.import(activePid, file);
      if (res.status === "success") {
        alert(`Successfully imported ${res.imported} trades!`);
        onRefresh?.();
      } else {
        alert("Import completed with errors:\n" + res.errors.join("\n"));
      }
    } catch (e) {
      alert("Import failed: " + e.message);
    } finally {
      setImporting(false);
      e.target.value = ""; // Reset file input
    }
  }

  const symbols = useMemo(() => {
    const s = new Set(trades.filter(t => t.type === 'TRADE').map((t) => t.symbol));
    return [...s].sort();
  }, [trades]);

  const filtered = useMemo(() => {
    return trades.filter((t) => {
      if (symbolFilter && t.symbol !== symbolFilter) return false;
      if (actionFilter !== "ALL" && t.action !== actionFilter) return false;
      return true;
    });
  }, [trades, symbolFilter, actionFilter]);

  const hasFilters = symbolFilter || actionFilter !== "ALL";

  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-12 bg-surface-2 animate-pulse rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Portfolio filter */}
        {portfolios.length > 1 && (
          <>
            <div className="flex items-center gap-2">
              <Filter size={12} className="text-muted shrink-0" />
              <span className="text-muted text-xs font-semibold">Portfolio:</span>
              <div className="flex gap-1 flex-wrap">
                {portfolios.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setActivePid(p.id)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${activePid === p.id
                      ? "bg-accent/20 text-accent border border-accent/40"
                      : "bg-surface-2 text-muted border border-border hover:text-soft"
                      }`}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </div>
            <div className="w-px h-4 bg-border" />
          </>
        )}

        {/* Action filter */}
        <div className="flex gap-1">
          {["ALL", "BUY", "SELL", "DEPOSIT", "WITHDRAW"].map((a) => (
            <button
              key={a}
              onClick={() => setActionFilter(a)}
              className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition-all ${actionFilter === a
                ? ["BUY", "DEPOSIT"].includes(a)
                  ? "bg-gain/20 text-gain border border-gain/30"
                  : ["SELL", "WITHDRAW"].includes(a)
                    ? "bg-loss/20 text-loss border border-loss/30"
                    : "bg-surface-3 text-white border border-border-2"
                : "bg-surface-2 text-muted border border-border hover:text-soft"
                }`}
            >
              {a}
            </button>
          ))}
        </div>

        {symbols.length > 1 && (
          <>
            <div className="w-px h-4 bg-border" />
            {/* Symbol chips */}
            <div className="flex flex-wrap gap-1">
              <button
                onClick={() => setSymbolFilter("")}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${!symbolFilter
                  ? "bg-surface-3 text-white border border-border-2"
                  : "bg-surface-2 text-muted border border-border hover:text-soft"
                  }`}
              >
                All
              </button>
              {symbols.map((sym) => (
                <button
                  key={sym}
                  onClick={() => setSymbolFilter(symbolFilter === sym ? "" : sym)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold mono transition-all ${symbolFilter === sym
                    ? "bg-accent/20 text-accent border border-accent/40"
                    : "bg-surface-2 text-muted border border-border hover:text-soft"
                    }`}
                >
                  {sym}
                </button>
              ))}
            </div>
          </>
        )}

        {hasFilters && (
          <button
            onClick={() => { setSymbolFilter(""); setActionFilter("ALL"); }}
            className="flex items-center gap-1 text-xs text-muted hover:text-loss transition-colors ml-auto"
          >
            <X size={12} /> Clear
          </button>
        )}

        {/* Export/Import */}
        <div className="flex items-center gap-2 ml-auto">
          <button
            onClick={handleExport}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest text-muted hover:text-white hover:bg-white/5 transition-all border border-transparent hover:border-white/10"
          >
            <Download size={13} /> Export
          </button>
          <label className="cursor-pointer">
            <input 
              type="file" 
              accept=".csv" 
              onChange={handleImport} 
              className="hidden" 
              disabled={importing}
            />
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all border border-transparent hover:border-white/10 ${
              importing ? "opacity-50 pointer-events-none" : "text-muted hover:text-white hover:bg-white/5"
            }`}>
              <Upload size={13} /> {importing ? "Importing..." : "Import"}
            </div>
          </label>
        </div>
      </div>

      {hasFilters && (
        <div className="text-xs text-muted">
          Showing <span className="text-soft font-semibold">{filtered.length}</span> of {trades.length} trades
        </div>
      )}

      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-muted gap-3">
          <History size={32} className="opacity-20" />
          <p className="text-sm">{trades.length === 0 ? "No activity recorded yet." : "No activities match the filters."}</p>
        </div>
      ) : (
        <div className="overflow-x-auto -mx-1">
          <table className="w-full text-sm min-w-[750px]">
            <thead>
              <tr className="border-b border-border">
                {["Date", "Symbol / Category", "Action", "Price / Type", "Quantity / Info", "Deductions", "Amount / Net Cost", "Notes", ""].map((h) => (
                  <th key={h} className={`py-3 px-3 text-muted text-xs font-semibold uppercase tracking-widest ${h === "Symbol / Category" || h === "Date" || h === "Notes" || h === "" ? "text-left" : "text-right"
                    }`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border/30">
              {filtered.map((t, i) => (
                <tr key={`${t.type}-${t.id}`} className="hover:bg-surface-2/50 transition-colors fade-in" style={{ animationDelay: `${i * 20}ms` }}>
                  <td className="py-3 px-3 text-muted text-xs mono">{fmt.date(t.trade_date)}</td>

                  <td className="py-3 px-3">
                    <div className="flex items-center gap-2">
                      <div className={`w-7 h-7 rounded-lg border flex items-center justify-center ${
                        t.type === 'CASH' ? 'bg-accent/10 border-accent/20' : 'bg-surface-3 border-border'
                      }`}>
                        {t.type === 'CASH' ? (
                          <WalletIcon size={12} className="text-accent" />
                        ) : (
                          <span className="text-accent font-black text-[10px]">{t.symbol.slice(0, 2)}</span>
                        )}
                      </div>
                      <span className="text-white font-bold text-sm">
                        {t.type === 'CASH' ? 'CASH' : t.symbol}
                      </span>
                    </div>
                  </td>

                  <td className="py-3 px-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-bold mono ${
                      ["BUY", "DEPOSIT"].includes(t.action)
                        ? "bg-gain/15 text-gain border border-gain/20"
                        : "bg-loss/15 text-loss border border-loss/20"
                      }`}>
                      {t.action}
                    </span>
                  </td>

                  <td className="py-3 px-3 text-right text-soft mono font-medium">
                    {t.type === 'CASH' ? (
                      <span className="text-muted text-xs uppercase tracking-tighter">Portfolio Cash</span>
                    ) : fmt.num(t.price)}
                  </td>
                  
                  <td className="py-3 px-3 text-right text-soft mono">
                    {t.type === 'CASH' ? (
                      <span className="text-muted text-xs">Adjustment</span>
                    ) : fmt.num(t.quantity, 0)}
                  </td>

                  <td className="py-3 px-3 text-right text-muted mono text-xs">
                    {t.type === 'CASH' ? "—" : fmt.pkr(t.deductions)}
                  </td>

                  <td className="py-3 px-3 text-right text-white font-semibold mono">
                    {fmt.pkr(t.type === 'CASH' ? t.amount : t.net_cost)}
                  </td>

                  <td className="py-3 px-3 text-muted text-xs max-w-[140px] truncate">{t.notes || "—"}</td>
                  <td className="py-3 px-3">
                    <div className="flex items-center justify-end gap-1">
                      {t.type === 'TRADE' && (
                        <button
                          onClick={() => onEdit?.(t)}
                          className="w-7 h-7 rounded-lg flex items-center justify-center text-muted hover:text-accent hover:bg-accent/10 transition-all"
                        >
                          <Edit3 size={13} />
                        </button>
                      )}
                      <button
                        onClick={() => t.type === 'TRADE' ? handleDelete(t.id) : alert('Delete cash from balance tab')}
                        disabled={deleting === t.id}
                        className="w-7 h-7 rounded-lg flex items-center justify-center text-muted hover:text-loss hover:bg-loss/10 transition-all disabled:opacity-30"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
