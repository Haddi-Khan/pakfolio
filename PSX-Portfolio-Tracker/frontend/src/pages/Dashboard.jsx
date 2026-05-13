import { useState, useEffect } from "react";
import { Plus, Wallet, TrendingUp } from "lucide-react";
import { LayoutDashboard, Clock } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { KPICards } from "../components/KPICards";
import { PortfolioChart } from "../components/PortfolioChart";
import { HoldingsTable } from "../components/HoldingsTable";
import { HoldingsPie } from "../components/HoldingsPie";
import { TradeHistory } from "../components/TradeHistory";
import { LiveTicker } from "../components/Ticker";
import { AddTradeModal } from "../components/AddTradeModal";
import { CashModal } from "../components/CashModal";
import { PortfolioSwitcher } from "../components/PortfolioSwitcher";
import { SectorPie } from "../components/SectorPie";
import { SymbolDetailPanel } from "../components/SymbolDetailPanel";
import { usePortfolioSummary, useHoldings, useTrades, useCash } from "../hooks/usePortfolio";
import { usePortfolioCtx } from "../context/PortfolioContext";
import { useAuth } from "../context/AuthContext";
import { fmt } from "../utils/format";

const TABS = [
  { key: "Holdings", icon: LayoutDashboard },
  { key: "Activity History", icon: Clock },
];

export function Dashboard() {
  const [tab, setTab] = useState("Holdings");
  const [showTradeModal, setShowTradeModal] = useState(false);
  const [showCashModal, setShowCashModal] = useState(false);
  const [selectedHolding, setSelectedHolding] = useState(null); // { symbol, ...holding }
  const [tradeModalInitialData, setTradeModalInitialData] = useState(null);

  const { activePid } = usePortfolioCtx();
  const { user } = useAuth();

  const { data: summary, refresh: refreshSummary } = usePortfolioSummary(activePid);
  const { data: holdings, loading: holdingsLoading, refresh: refreshHoldings } = useHoldings(activePid);
  const { data: trades, loading: tradesLoading, refresh: refreshTrades } = useTrades(undefined, activePid);
  const { data: cash, loading: cashLoading, refresh: refreshCash } = useCash(activePid);

  useEffect(() => {
    if (summary?.portfolio_name) {
      document.title = `${summary.portfolio_name} | Pakfolio`;
    } else {
      document.title = "Dashboard | Pakfolio";
    }
  }, [summary?.portfolio_name]);

  function handleAdded() {
    refreshSummary();
    refreshHoldings();
    refreshTrades();
    refreshCash();
  }

  function handleCloseHolding(h) {
    setTradeModalInitialData({
      action: "SELL",
      symbol: h.symbol,
      name: h.name,
      asset_type: h.asset_type,
      price: h.current_price || h.avg_buy_price,
      quantity: h.quantity
    });
    setShowTradeModal(true);
  }

  const holdingSymbols = holdings.map((h) => h.symbol);
  const plPos = summary?.total_gain_loss == null || summary.total_gain_loss >= 0;

  // Unified activity history
  const activities = [
    ...trades.map(t => ({ ...t, type: 'TRADE' })),
    ...cash.map(c => ({
      ...c,
      type: 'CASH',
      trade_date: c.tx_date, // Normalized for sorting
      action: c.tx_type,
      notes: c.description
    }))
  ].sort((a, b) => new Date(b.trade_date) - new Date(a.trade_date));

  return (
    <div className="min-h-screen bg-bg flex flex-col relative">
      {/* Ambient background glow */}
      <div className="fixed top-0 inset-x-0 h-[500px] bg-accent/5 rounded-full blur-[120px] pointer-events-none -translate-y-1/2" />

      {/* Portfolio action bar */}
      <div className="border-b border-border bg-surface/60 backdrop-blur-sm">
        <div className="flex items-center justify-between px-6 py-2.5 max-w-7xl mx-auto">
          <div className="flex items-center gap-3">
            <PortfolioSwitcher />
            {summary && (
              <div className={"hidden md:flex items-center gap-2 px-3 py-1 rounded-full border mono text-xs font-bold " + (
                plPos ? "border-gain/30 bg-gain/10 text-gain" : "border-loss/30 bg-loss/10 text-loss"
              )}>
                <TrendingUp size={12} />
                {fmt.pct(summary.total_return_pct)} overall
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowCashModal(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-border-2 text-soft text-sm font-medium hover:bg-surface-2 hover:text-white transition-all"
            >
              <Wallet size={13} />
              <span className="hidden sm:inline">Cash</span>
            </button>
            <button
              onClick={() => setShowTradeModal(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-gradient-to-r from-accent to-accent-2 text-white text-sm font-bold shadow-lg shadow-accent/25 hover:shadow-accent/40 hover:scale-[1.02] transition-all"
            >
              <Plus size={13} />
              Add Trade
            </button>
          </div>
        </div>
      </div>

      {/* Body */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4 }}
        className="flex-1 min-h-0 bg-bg"
      >
        <div className="max-w-[1600px] mx-auto p-4 lg:p-6 grid grid-cols-1 lg:grid-cols-4 gap-6 relative z-10">
          
          {/* Main Content */}
          <div className="lg:col-span-3 space-y-6">
            <KPICards summary={summary} />
            <PortfolioChart pid={activePid} />

            <div className="rounded-2xl bg-surface border border-border shadow-2xl overflow-hidden min-h-[500px]">
              <div className="flex items-center justify-between border-b border-border px-6 pt-2">
                <div className="flex gap-8">
                  {TABS.map(({ key, icon: Icon }) => (
                    <button
                      key={key}
                      onClick={() => setTab(key)}
                      className={"flex items-center gap-2 py-4 text-[11px] font-black uppercase tracking-[0.2em] border-b-2 -mb-px transition-all " + (
                        tab === key ? "border-accent text-accent" : "border-transparent text-muted hover:text-white"
                      )}
                    >
                      <Icon size={14} />
                      {key}
                      {key === "Holdings" && holdings.length > 0 && (
                        <span className="ml-1 px-1.5 py-0.5 rounded-md bg-white/5 text-[9px] font-bold">{holdings.length}</span>
                      )}
                    </button>
                  ))}
                </div>
              </div>

              <div className="p-0">
                {tab === "Holdings" ? (
                  <HoldingsTable
                    holdings={holdings}
                    loading={holdingsLoading}
                    onSymbolClick={setSelectedHolding}
                    onCloseClick={handleCloseHolding}
                    cashBalance={summary?.cash_balance ?? 0}
                  />
                ) : (
                  <div className="p-6">
                    <TradeHistory 
                      trades={activities} 
                      loading={tradesLoading || cashLoading} 
                      onRefresh={handleAdded} 
                      onEdit={handleCloseHolding} 
                    />
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Sidebar */}
          <aside className="lg:col-span-1 space-y-6">
            <div className="rounded-2xl bg-surface border border-border shadow-xl p-5 sticky top-[80px] space-y-10">
              <HoldingsPie holdings={holdings} cashBalance={summary?.cash_balance ?? 0} />
              
              <div className="pt-6 border-t border-border">
                <SectorPie holdings={holdings} />
              </div>

              <div className="pt-6 border-t border-border">
                <LiveTicker holdingSymbols={holdingSymbols} />
              </div>
            </div>
          </aside>
        </div>
      </motion.div>

      {showTradeModal && (
        <AddTradeModal
          cashBalance={summary?.cash_balance ?? 0}
          portfolioId={activePid}
          initialData={tradeModalInitialData}
          onClose={() => { setShowTradeModal(false); setTradeModalInitialData(null); }}
          onAdded={handleAdded}
        />
      )}
      {showCashModal && (
        <CashModal
          portfolioId={activePid}
          onClose={() => setShowCashModal(false)}
          onAdded={handleAdded}
        />
      )}
      {selectedHolding && (
        <SymbolDetailPanel
          symbol={selectedHolding.symbol}
          holding={selectedHolding}
          pid={activePid}
          onClose={() => setSelectedHolding(null)}
        />
      )}
    </div>
  );
}
