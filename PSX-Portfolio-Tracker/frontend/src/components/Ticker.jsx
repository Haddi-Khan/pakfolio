import { useEffect, useState } from "react";
import { TrendingUp, TrendingDown, RefreshCw } from "lucide-react";
import { api } from "../api/client";
import { fmt } from "../utils/format";

const FALLBACK_SYMBOLS = [
  "NPL","BIPL","HALEON","NCPL","HUBC","FFC","AVN","MEBL","MZNPETF",
  "LUCK","ENGRO","HBL","MCB","PSO","OGDC","SYS",
];

export function LiveTicker({ holdingSymbols = [] }) {
  const [quotes, setQuotes] = useState({});
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const symbols = holdingSymbols.length > 0 ? holdingSymbols : FALLBACK_SYMBOLS;

  async function fetchQuotes(showSpinner = false) {
    if (showSpinner) setRefreshing(true);
    try {
      const data = await api.prices.bulk(symbols);
      setQuotes(data);
      setLastUpdated(new Date());
    } catch { }
    finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    fetchQuotes();
    const t = setInterval(() => fetchQuotes(), 60_000);
    return () => clearInterval(t);
  }, [symbols.join(",")]);

  const timeStr = lastUpdated
    ? lastUpdated.toLocaleTimeString("en-PK", { hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <div className="rounded-2xl bg-surface border border-border overflow-hidden flex flex-col">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <div>
          <h3 className="text-white text-sm font-bold">Live Prices</h3>
          {timeStr && <p className="text-muted text-xs">Updated {timeStr}</p>}
        </div>
        <button
          onClick={() => fetchQuotes(true)}
          className={"text-muted hover:text-accent transition-colors " + (refreshing ? "animate-spin" : "")}
        >
          <RefreshCw size={13} />
        </button>
      </div>

      <div className="overflow-y-auto flex-1 divide-y divide-border/30">
        {loading
          ? [...Array(8)].map((_, i) => (
              <div key={i} className="px-4 py-3 flex justify-between animate-pulse">
                <div className="h-3.5 w-10 bg-surface-2 rounded" />
                <div className="h-3.5 w-14 bg-surface-2 rounded" />
              </div>
            ))
          : symbols.map((sym) => {
              const q = quotes[sym];
              if (!q?.price) return null;
              const isUp = q.change == null || q.change >= 0;
              return (
                <div key={sym} className="px-4 py-2.5 flex items-center justify-between hover:bg-surface-2/60 transition-colors group">
                  <div>
                    <div className="text-white font-bold text-sm group-hover:text-accent transition-colors">{sym}</div>
                    {q.change_pct != null && (
                      <div className={"flex items-center gap-0.5 text-xs mono font-medium " + (isUp ? "text-gain" : "text-loss")}>
                        {isUp ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                        {fmt.pct(q.change_pct)}
                      </div>
                    )}
                  </div>
                  <div className="text-right">
                    <div className="text-white font-semibold text-sm mono">{fmt.num(q.price)}</div>
                    {q.change != null && (
                      <div className={"text-xs mono " + (isUp ? "text-gain" : "text-loss")}>
                        {isUp ? "+" : ""}{fmt.num(q.change)}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
      </div>
    </div>
  );
}
