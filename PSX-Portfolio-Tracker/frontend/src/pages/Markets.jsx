import { useState, useEffect, useMemo, useCallback } from "react";
import { useParams, Navigate, Link } from "react-router-dom";
import {
  TrendingUp, TrendingDown, Search, BarChart3, PieChart,
  ArrowUpDown, X, GitCompare, ChevronUp, ChevronDown, Minus,
  RefreshCw, AlertCircle, ArrowUpRight, ArrowDownRight,
} from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";
import { api } from "../api/client";
import { fmt } from "../utils/format";

// ─── Shared ───────────────────────────────────────────────────────────────────
const CHART_COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899"];

function ChangeCell({ value }) {
  if (value == null) return <span className="text-muted/40 mono text-sm">—</span>;
  const pos = value >= 0;
  return (
    <span className={`mono text-sm font-bold flex items-center gap-0.5 justify-end ${pos ? "text-gain" : "text-loss"}`}>
      {pos ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      {pos ? "+" : ""}{value.toFixed(2)}%
    </span>
  );
}

function MiniBar({ pct }) {
  const pos = pct >= 0;
  const w = Math.min(Math.abs(pct) * 4, 100);
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-white/5 rounded-full overflow-hidden flex-shrink-0">
        <div
          className={`h-full rounded-full ${pos ? "bg-gain" : "bg-loss"}`}
          style={{ width: `${w}%`, marginLeft: pos ? 0 : "auto" }}
        />
      </div>
    </div>
  );
}

// ─── Market Overview KPIs ─────────────────────────────────────────────────────
function MarketOverview({ summary }) {
  if (!summary) return null;
  const { advances, declines, unchanged, total_volume } = summary;

  const total = advances + declines + unchanged || 1;
  const advPct = (advances / total * 100).toFixed(0);
  const decPct = (declines / total * 100).toFixed(0);

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <div className="bg-surface border border-border rounded-2xl p-4">
        <div className="text-[10px] font-black uppercase tracking-widest text-muted mb-2">Advances</div>
        <div className="text-2xl font-black text-gain mono">{advances}</div>
        <div className="text-[10px] text-muted mt-1">{advPct}% of market</div>
      </div>
      <div className="bg-surface border border-border rounded-2xl p-4">
        <div className="text-[10px] font-black uppercase tracking-widest text-muted mb-2">Declines</div>
        <div className="text-2xl font-black text-loss mono">{declines}</div>
        <div className="text-[10px] text-muted mt-1">{decPct}% of market</div>
      </div>
      <div className="bg-surface border border-border rounded-2xl p-4">
        <div className="text-[10px] font-black uppercase tracking-widest text-muted mb-2">Unchanged</div>
        <div className="text-2xl font-black text-muted mono">{unchanged}</div>
      </div>
      <div className="bg-surface border border-border rounded-2xl p-4">
        <div className="text-[10px] font-black uppercase tracking-widest text-muted mb-2">Total Volume</div>
        <div className="text-2xl font-black text-white mono">{fmt.compact(total_volume)}</div>
        <div className="text-[10px] text-muted mt-1">shares traded</div>
      </div>
    </div>
  );
}

// ─── Top Movers ───────────────────────────────────────────────────────────────
function TopMovers({ movers, onCompare, compareSet }) {
  const [tab, setTab] = useState("gainers");
  const list = movers ? (movers[tab] || []) : [];

  return (
    <div className="bg-surface border border-border rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-border">
        <h2 className="text-sm font-black uppercase tracking-widest text-white flex items-center gap-2">
          <TrendingUp size={14} className="text-accent" />
          Market Movers
        </h2>
        <div className="flex bg-bg rounded-lg p-1">
          {[
            { id: "gainers", label: "Gainers", icon: ArrowUpRight },
            { id: "losers", label: "Losers", icon: ArrowDownRight },
            { id: "active", label: "Most Active", icon: BarChart3 },
          ].map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[10px] font-bold transition-all ${
                tab === t.id ? "bg-accent text-white shadow-lg" : "text-muted hover:text-white"
              }`}
            >
              <t.icon size={12} />
              <span className="hidden sm:inline">{t.label}</span>
            </button>
          ))}
        </div>
      </div>
      <div className="divide-y divide-border">
        {list.map((s, i) => {
          const inCompare = compareSet.has(s.symbol);
          return (
            <div key={s.symbol} className="flex items-center gap-3 px-4 py-3 hover:bg-white/[0.02] transition-colors">
              <span className="text-[10px] text-muted/40 mono w-4 flex-shrink-0">{i + 1}</span>
              <Link to={`${(s.asset_type || "").toLowerCase() === "mutual_fund" ? "/mutual-funds" : "/stocks"}/${s.symbol}`} className="flex-1 min-w-0">
                <div className="text-sm font-bold text-white hover:text-accent transition-colors">{s.symbol}</div>
                <div className="text-[11px] text-muted truncate">{s.name}</div>
              </Link>
              <div className="text-right">
                <div className="text-sm font-bold mono text-white">{fmt.num(s.price)}</div>
                <ChangeCell value={s.change_pct} />
              </div>
              {tab === "active" && (
                <div className="text-[11px] text-muted mono w-16 text-right">{fmt.compact(s.volume)}</div>
              )}
              <button
                onClick={() => onCompare(s.symbol)}
                title={inCompare ? "Remove from compare" : "Add to compare"}
                className={`w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 transition-all ${
                  inCompare ? "bg-accent/20 text-accent" : "text-muted/30 hover:text-muted hover:bg-white/5"
                }`}
              >
                <GitCompare size={12} />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Compare Panel ────────────────────────────────────────────────────────────
function ComparePanel({ symbols: allSymbols, prices, compareSet, onToggle, onClear }) {
  const [histories, setHistories] = useState({});
  const [period, setPeriod] = useState("1M");
  const [loading, setLoading] = useState(false);

  const compareList = Array.from(compareSet);

  const periodDays = { "1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365 };

  useEffect(() => {
    if (compareList.length === 0) return;
    setLoading(true);
    const days = periodDays[period];
    const to = new Date().toISOString().split("T")[0];
    const from = new Date(Date.now() - days * 86400000).toISOString().split("T")[0];

    Promise.all(
      compareList.map(sym =>
        api.prices.history(sym, from, to)
          .then(data => ({ sym, data: data || [] }))
          .catch(() => ({ sym, data: [] }))
      )
    ).then(results => {
      const map = {};
      results.forEach(({ sym, data }) => { map[sym] = data; });
      setHistories(map);
      setLoading(false);
    });
  }, [compareSet, period]);

  // Merge all dates into one chart-ready array, normalized to % from first value
  const chartData = useMemo(() => {
    if (compareList.length === 0) return [];
    const allDates = new Set();
    compareList.forEach(sym => {
      (histories[sym] || []).forEach(p => allDates.add(p.date));
    });
    const sorted = Array.from(allDates).sort();
    const baselines = {};
    compareList.forEach(sym => {
      const h = histories[sym] || [];
      baselines[sym] = h[0]?.price || null;
    });

    return sorted.map(date => {
      const row = { date };
      compareList.forEach(sym => {
        const pt = (histories[sym] || []).find(p => p.date === date);
        if (pt && baselines[sym]) {
          row[sym] = parseFloat(((pt.price / baselines[sym] - 1) * 100).toFixed(2));
        }
      });
      return row;
    });
  }, [histories, compareList]);

  if (compareList.length === 0) return null;

  return (
    <div className="bg-surface border border-accent/30 rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-border">
        <div className="flex items-center gap-2">
          <GitCompare size={15} className="text-accent" />
          <span className="text-sm font-black text-white uppercase tracking-widest">Compare</span>
          <div className="flex gap-2 ml-2">
            {compareList.map((sym, i) => (
              <div key={sym} className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold border"
                style={{ borderColor: CHART_COLORS[i] + "60", backgroundColor: CHART_COLORS[i] + "15", color: CHART_COLORS[i] }}>
                {sym}
                <button onClick={() => onToggle(sym)} className="hover:opacity-70">
                  <X size={10} />
                </button>
              </div>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            {Object.keys(periodDays).map(p => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-2 py-1 rounded-lg text-[10px] font-black transition-colors ${
                  period === p ? "bg-accent text-white" : "text-muted hover:text-white hover:bg-white/5"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
          <button onClick={onClear} className="text-muted hover:text-white transition-colors ml-2">
            <X size={14} />
          </button>
        </div>
      </div>

      <div className="p-5">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        ) : chartData.length === 0 ? (
          <div className="flex items-center justify-center h-48 text-muted text-sm">No data available</div>
        ) : (
          <>
            <p className="text-[10px] text-muted/60 mb-3">Normalized performance (% from start of period)</p>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#5A6B82" }} tickLine={false}
                  tickFormatter={d => d?.slice(5)} interval="preserveStartEnd" />
                <YAxis tick={{ fontSize: 10, fill: "#5A6B82" }} tickLine={false} axisLine={false}
                  tickFormatter={v => `${v > 0 ? "+" : ""}${v.toFixed(1)}%`} width={52} />
                <Tooltip
                  contentStyle={{ background: "#0B1221", border: "1px solid #1E2D40", borderRadius: 12 }}
                  labelStyle={{ color: "#5A6B82", fontSize: 11 }}
                  formatter={(v, name) => [`${v > 0 ? "+" : ""}${v?.toFixed(2)}%`, name]}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                {compareList.map((sym, i) => (
                  <Line key={sym} type="monotone" dataKey={sym}
                    stroke={CHART_COLORS[i]} strokeWidth={2} dot={false}
                    connectNulls activeDot={{ r: 4 }} />
                ))}
              </LineChart>
            </ResponsiveContainer>

            {/* Stats table */}
            <div className="mt-4 grid gap-2" style={{ gridTemplateColumns: `repeat(${compareList.length}, 1fr)` }}>
              {compareList.map((sym, i) => {
                const q = prices[sym];
                const symInfo = allSymbols.find(s => s.symbol === sym);
                return (
                  <div key={sym} className="rounded-xl border p-3 space-y-2"
                    style={{ borderColor: CHART_COLORS[i] + "40", backgroundColor: CHART_COLORS[i] + "08" }}>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: CHART_COLORS[i] }} />
                      <Link to={`/stocks/${sym}`} className="text-sm font-black text-white hover:text-accent">{sym}</Link>
                    </div>
                    {symInfo?.name && <p className="text-[10px] text-muted truncate">{symInfo.name}</p>}
                    <div className="space-y-1">
                      <div className="flex justify-between text-[11px]">
                        <span className="text-muted">Price</span>
                        <span className="font-bold mono text-white">{q?.price != null ? fmt.num(q.price) : "—"}</span>
                      </div>
                      <div className="flex justify-between text-[11px]">
                        <span className="text-muted">Day Change</span>
                        <span className={`font-bold mono ${(q?.change_pct || 0) >= 0 ? "text-gain" : "text-loss"}`}>
                          {q?.change_pct != null ? `${q.change_pct >= 0 ? "+" : ""}${q.change_pct.toFixed(2)}%` : "—"}
                        </span>
                      </div>
                      <div className="flex justify-between text-[11px]">
                        <span className="text-muted">Volume</span>
                        <span className="font-bold mono text-white">{q?.volume != null ? fmt.compact(q.volume) : "—"}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Main Stocks Table ────────────────────────────────────────────────────────
function StocksTable({ symbols, prices, onCompare, compareSet }) {
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState("change_pct");
  const [sortDir, setSortDir] = useState("desc");

  const toggleSort = useCallback((key) => {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
  }, [sortKey]);

  const filtered = useMemo(() => {
    let list = symbols.map(s => ({ ...s, q: prices[s.symbol] }));
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(s => s.symbol.toLowerCase().includes(q) || (s.name || "").toLowerCase().includes(q));
    }
    list.sort((a, b) => {
      let av = a.q?.[sortKey] ?? (sortKey === "symbol" ? a.symbol : -Infinity);
      let bv = b.q?.[sortKey] ?? (sortKey === "symbol" ? b.symbol : -Infinity);
      if (sortKey === "symbol") { av = a.symbol; bv = b.symbol; }
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
    return list;
  }, [symbols, prices, search, sortKey, sortDir]);

  function SortIcon({ col }) {
    if (sortKey !== col) return <ArrowUpDown size={11} className="text-muted/30" />;
    return sortDir === "asc" ? <ChevronUp size={11} className="text-accent" /> : <ChevronDown size={11} className="text-accent" />;
  }

  const cols = [
    { key: "symbol",     label: "Symbol / Name", cls: "text-left",  flex: "flex-[2]" },
    { key: "price",      label: "Price",         cls: "text-right", flex: "flex-1"   },
    { key: "change",     label: "Change",        cls: "text-right", flex: "flex-1"   },
    { key: "change_pct", label: "Change %",      cls: "text-right", flex: "flex-1"   },
    { key: "volume",     label: "Volume",        cls: "text-right", flex: "flex-1"   },
  ];

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/5 border border-border flex-1 max-w-sm">
          <Search size={14} className="text-muted flex-shrink-0" />
          <input
            type="text"
            placeholder="Search symbol or company name..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="bg-transparent border-none outline-none text-sm text-white placeholder-muted w-full"
          />
          {search && (
            <button onClick={() => setSearch("")} className="text-muted hover:text-white">
              <X size={12} />
            </button>
          )}
        </div>
        <span className="text-xs text-muted">{filtered.length.toLocaleString()} results</span>
        {compareSet.size > 0 && (
          <span className="text-xs text-accent font-bold">{compareSet.size} selected to compare</span>
        )}
      </div>

      <div className="bg-surface border border-border rounded-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-2 px-5 py-3 border-b border-border">
          {cols.map(c => (
            <button
              key={c.key}
              onClick={() => toggleSort(c.key)}
              className={`${c.flex} flex items-center gap-1 text-[10px] font-black uppercase tracking-widest text-muted hover:text-white transition-colors ${c.cls}`}
            >
              {c.cls === "text-right" && <SortIcon col={c.key} />}
              {c.label}
              {c.cls === "text-left" && <SortIcon col={c.key} />}
            </button>
          ))}
          <div className="w-6 flex-shrink-0" />
        </div>

        <div className="divide-y divide-border max-h-[560px] overflow-y-auto">
          {(search ? filtered : filtered.slice(0, 20)).map(s => {
            const q = prices[s.symbol];
            const pos = (q?.change_pct || 0) >= 0;
            const inCompare = compareSet.has(s.symbol);
            return (
              <div key={s.symbol}
                className={`flex items-center gap-2 px-5 py-3 hover:bg-white/[0.02] transition-colors ${inCompare ? "bg-accent/5" : ""}`}
              >
                <div className="flex-[2] min-w-0">
                  <Link to={`/stocks/${s.symbol}`} className="text-sm font-bold text-white hover:text-accent transition-colors">
                    {s.symbol}
                  </Link>
                  {s.name && <p className="text-[11px] text-muted truncate">{s.name}</p>}
                </div>
                <div className="flex-1 text-right mono text-sm font-bold text-white">
                  {q?.price != null ? fmt.num(q.price) : <span className="text-muted/30">—</span>}
                </div>
                <div className={`flex-1 text-right mono text-sm font-bold ${q?.change != null ? (pos ? "text-gain" : "text-loss") : "text-muted/30"}`}>
                  {q?.change != null ? `${pos ? "+" : "-"}${fmt.num(Math.abs(q.change))}` : "—"}
                </div>
                <div className="flex-1 flex items-center justify-end gap-2">
                  <MiniBar pct={q?.change_pct || 0} />
                  <ChangeCell value={q?.change_pct} />
                </div>
                <div className="flex-1 text-right mono text-[11px] text-muted">
                  {q?.volume != null ? fmt.compact(q.volume) : "—"}
                </div>
                <button
                  onClick={() => onCompare(s.symbol)}
                  title={inCompare ? "Remove from compare" : "Add to compare (max 4)"}
                  className={`w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 transition-all ${
                    inCompare ? "bg-accent/20 text-accent" : "text-muted/20 hover:text-muted hover:bg-white/5"
                  }`}
                >
                  <GitCompare size={12} />
                </button>
              </div>
            );
          })}
          {filtered.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 gap-2">
              <AlertCircle size={24} className="text-muted/40" />
              <p className="text-muted text-sm">No symbols match "{search}"</p>
              <button onClick={() => setSearch("")} className="text-accent text-xs hover:underline">Clear search</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Mutual Funds Table ────────────────────────────────────────────────────────
function MutualFundsTable({ symbols, prices, onCompare, compareSet }) {
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState("change_pct");
  const [sortDir, setSortDir] = useState("desc");

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
  };

  const filtered = useMemo(() => {
    let list = symbols.map(s => ({ ...s, q: prices[s.symbol] }));
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(s => s.symbol.toLowerCase().includes(q) || (s.name || "").toLowerCase().includes(q));
    }
    list.sort((a, b) => {
      const av = a.q?.[sortKey] ?? -Infinity;
      const bv = b.q?.[sortKey] ?? -Infinity;
      return sortDir === "asc" ? av - bv : bv - av;
    });
    return list;
  }, [symbols, prices, search, sortKey, sortDir]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/5 border border-border flex-1 max-w-sm">
          <Search size={14} className="text-muted flex-shrink-0" />
          <input
            type="text"
            placeholder="Search fund..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="bg-transparent border-none outline-none text-sm text-white placeholder-muted w-full"
          />
          {search && <button onClick={() => setSearch("")} className="text-muted hover:text-white"><X size={12} /></button>}
        </div>
        <span className="text-xs text-muted">{filtered.length.toLocaleString()} funds</span>
      </div>
      <div className="bg-surface border border-border rounded-2xl overflow-hidden">
        <div className="grid grid-cols-[2fr_1fr_1fr_1fr_1fr_28px] text-[10px] font-black uppercase tracking-widest text-muted px-5 py-3 border-b border-border gap-2">
          <button onClick={() => toggleSort("symbol")} className="text-left flex items-center gap-1 hover:text-white">Symbol / Name <ArrowUpDown size={10} /></button>
          <button onClick={() => toggleSort("price")} className="text-right flex items-center gap-1 justify-end hover:text-white">NAV <ArrowUpDown size={10} /></button>
          <button onClick={() => toggleSort("change")} className="text-right flex items-center gap-1 justify-end hover:text-white">Change <ArrowUpDown size={10} /></button>
          <button onClick={() => toggleSort("change_pct")} className="text-right flex items-center gap-1 justify-end hover:text-white">Change % <ArrowUpDown size={10} /></button>
          <span className="text-right">AUM</span>
          <span />
        </div>
        <div className="divide-y divide-border max-h-[560px] overflow-y-auto">
          {(search ? filtered : filtered.slice(0, 20)).map(s => {
            const q = prices[s.symbol];
            const pos = (q?.change_pct || 0) >= 0;
            const inCompare = compareSet.has(s.symbol);
            return (
              <div key={s.symbol} className={`grid grid-cols-[2fr_1fr_1fr_1fr_1fr_28px] items-center gap-2 px-5 py-3 hover:bg-white/[0.02] ${inCompare ? "bg-accent/5" : ""}`}>
                <div className="min-w-0">
                  <Link to={`/mutual-funds/${s.symbol}`} className="text-sm font-bold text-white hover:text-accent truncate block">{s.symbol}</Link>
                  {s.name && <p className="text-[11px] text-muted truncate">{s.name}</p>}
                </div>
                <div className="text-right mono text-sm font-bold text-white">
                  {q?.price != null ? fmt.num(q.price) : <span className="text-muted/30">—</span>}
                </div>
                <div className={`text-right mono text-sm font-bold ${q?.change != null ? (q.change >= 0 ? "text-gain" : "text-loss") : "text-muted/30"}`}>
                  {q?.change != null ? `${q.change >= 0 ? "+" : ""}${fmt.num(q.change)}` : "—"}
                </div>
                <div className={`text-right mono text-sm font-bold ${q?.change_pct != null ? (pos ? "text-gain" : "text-loss") : "text-muted/30"}`}>
                  {q?.change_pct != null ? `${pos ? "+" : ""}${q.change_pct.toFixed(2)}%` : "—"}
                </div>
                <div className="text-right mono text-[11px] text-muted">
                  {q?.aum != null ? fmt.compact(q.aum) : "—"}
                </div>
                <button
                  onClick={() => onCompare(s.symbol)}
                  className={`w-6 h-6 rounded-lg flex items-center justify-center transition-all ${inCompare ? "bg-accent/20 text-accent" : "text-muted/20 hover:text-muted hover:bg-white/5"}`}
                >
                  <GitCompare size={12} />
                </button>
              </div>
            );
          })}
          {filtered.length === 0 && (
            <div className="text-center py-12 text-muted text-sm">No funds match "{search}"</div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Sectors view ─────────────────────────────────────────────────────────────
function SectorsView({ symbols, prices }) {
  const sectors = useMemo(() => {
    const map = {};
    symbols.forEach(s => {
      const sec = s.sector || "Other";
      if (!map[sec]) map[sec] = { name: sec, stocks: [], advances: 0, declines: 0, totalChange: 0, count: 0 };
      map[sec].stocks.push(s);
      const q = prices[s.symbol];
      if (q?.change_pct != null) {
        map[sec].totalChange += q.change_pct;
        map[sec].count++;
        if (q.change_pct > 0) map[sec].advances++;
        else if (q.change_pct < 0) map[sec].declines++;
      }
    });
    return Object.values(map)
      .map(s => ({ ...s, avgChange: s.count > 0 ? s.totalChange / s.count : 0 }))
      .sort((a, b) => b.stocks.length - a.stocks.length);
  }, [symbols, prices]);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {sectors.map(sec => {
        const pos = sec.avgChange >= 0;
        return (
          <div key={sec.name} className="bg-surface border border-border rounded-2xl p-5 space-y-3 hover:border-border-2 transition-colors">
            <div className="flex items-center justify-between">
              <h3 className="text-white font-bold text-sm leading-tight flex-1">{sec.name}</h3>
              <div className={`text-sm font-black mono ml-2 flex-shrink-0 ${pos ? "text-gain" : "text-loss"}`}>
                {pos ? "+" : ""}{sec.avgChange.toFixed(2)}%
              </div>
            </div>
            <div className="flex items-center gap-3 text-[10px]">
              <span className="text-gain font-bold">{sec.advances}↑</span>
              <span className="text-loss font-bold">{sec.declines}↓</span>
              <span className="text-muted">{sec.stocks.length} stocks</span>
            </div>
            {/* Progress bar: green = advances, red = declines */}
            {sec.count > 0 && (
              <div className="h-1.5 bg-white/5 rounded-full overflow-hidden flex">
                <div className="bg-gain h-full" style={{ width: `${sec.advances / sec.count * 100}%` }} />
                <div className="bg-loss h-full" style={{ width: `${sec.declines / sec.count * 100}%` }} />
              </div>
            )}
            <div className="flex flex-wrap gap-1.5 mt-1">
              {sec.stocks.slice(0, 7).map(s => {
                const q = prices[s.symbol];
                const pos = (q?.change_pct || 0) >= 0;
                return (
                  <Link
                    key={s.symbol}
                    to={`/stocks/${s.symbol}`}
                    className={`text-[11px] font-bold px-2 py-0.5 rounded-lg border transition-all hover:scale-105 ${
                      q?.price != null
                        ? pos
                          ? "text-gain bg-gain/10 border-gain/20"
                          : "text-loss bg-loss/10 border-loss/20"
                        : "text-muted bg-white/[0.03] border-border"
                    }`}
                  >
                    {s.symbol}
                  </Link>
                );
              })}
              {sec.stocks.length > 7 && (
                <span className="text-[11px] text-muted/50 self-center">+{sec.stocks.length - 7}</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Main Markets page ────────────────────────────────────────────────────────
const MARKET_TYPES = ["stocks", "mutual-funds", "sectors", "etfs"];

export function Markets() {
  const { type } = useParams();
  const [allSymbols, setAllSymbols] = useState([]);
  const [prices, setPrices] = useState({});
  const [summary, setSummary] = useState(null);
  const [movers, setMovers] = useState(null);
  const [loading, setLoading] = useState(true);
  const [compareSet, setCompareSet] = useState(new Set());
  const [lastUpdated, setLastUpdated] = useState(null);

  // Derived — must be before useEffect (hooks order)
  const isStocks = type === "stocks";
  const isMF = type === "mutual-funds";
  const isSectors = type === "sectors";

  useEffect(() => {
    if (!type || !MARKET_TYPES.includes(type)) return;
    setLoading(true);
    setPrices({});
    setAllSymbols([]);
    setCompareSet(new Set());

    const apiType = isMF ? "mutual-funds" : "stocks";

    // 1. Fetch Market Summary and Movers (Fast!)
    Promise.all([
      api.markets.summary(),
      api.markets.movers(apiType),
      api.symbols.all()
    ]).then(([sum, mov, syms]) => {
      setSummary(sum);
      setMovers(mov);
      setAllSymbols(syms);

      // 2. Filter symbols for this type
      const currentSyms = syms.filter(s => {
        const at = (s.asset_type || "").toLowerCase();
        if (isMF) return at === "mutual_fund";
        return at === "stock" || at === "etf";
      });

      // 3. Seed prices from movers immediately
      const initialPrices = {};
      [...mov.gainers, ...mov.losers, ...mov.active].forEach(m => {
        initialPrices[m.symbol] = m;
      });
      setPrices(initialPrices);
      setLastUpdated(new Date());

      // 4. Page is ready — stop the spinner now
      setLoading(false);

      // 5. Load ALL prices IN PARALLEL chunks (much faster than serial)
      const allKeys = currentSyms.map(s => s.symbol);
      const chunkSize = 100;
      const chunks = [];
      for (let i = 0; i < allKeys.length; i += chunkSize) {
        chunks.push(allKeys.slice(i, i + chunkSize));
      }
      // Fire all chunks at once — single DB query per chunk, all in parallel
      Promise.all(
        chunks.map(chunk =>
          api.prices.bulk(chunk).catch(() => ({}))
        )
      ).then(results => {
        const merged = Object.assign({}, ...results);
        setPrices(prev => ({ ...prev, ...merged }));
        setLastUpdated(new Date());
      }).catch(console.error);
    })
    .catch(err => { console.error(err); setLoading(false); });
  }, [type]);


  const stockSymbols = useMemo(() => allSymbols.filter(s => {
    const at = (s.asset_type || "").toLowerCase();
    return at === "stock" || at === "etf";
  }), [allSymbols]);
  const mfSymbols = useMemo(() => allSymbols.filter(s => (s.asset_type || "").toLowerCase() === "mutual_fund"), [allSymbols]);

  const toggleCompare = useCallback((sym) => {
    setCompareSet(prev => {
      const next = new Set(prev);
      if (next.has(sym)) next.delete(sym);
      else if (next.size < 4) next.add(sym);
      return next;
    });
  }, []);

  const displaySymbols = isStocks || isSectors ? stockSymbols : mfSymbols;

  // Early redirect — after all hooks
  if (!type || !MARKET_TYPES.includes(type)) return <Navigate to="/markets/stocks" replace />;

  return (
    <div className="min-h-screen bg-bg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Page header + tabs */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-4">
            <div>
              <h1 className="text-2xl font-black text-white">
                {isStocks ? "PSX Stocks" : isMF ? "Mutual Funds" : isSectors ? "Sectors" : "ETFs"}
              </h1>
              {lastUpdated && (
                <p className="text-[10px] text-muted mt-0.5 flex items-center gap-1">
                  <RefreshCw size={9} />
                  Updated {lastUpdated.toLocaleTimeString()}
                </p>
              )}
            </div>
            <nav className="flex gap-1 bg-surface border border-border rounded-xl p-1">
              {[
                { key: "stocks", label: "Stocks" },
                { key: "mutual-funds", label: "Mutual Funds" },
                { key: "sectors", label: "Sectors" },
                { key: "etfs", label: "ETFs" },
              ].map(t => (
                <Link
                  key={t.key}
                  to={`/markets/${t.key}`}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                    type === t.key ? "bg-accent text-white" : "text-muted hover:text-white"
                  }`}
                >
                  {t.label}
                </Link>
              ))}
            </nav>
          </div>
          {compareSet.size === 0 && (
            <p className="text-[11px] text-muted/60 hidden sm:block">
              Click <GitCompare size={10} className="inline" /> on any row to compare
            </p>
          )}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-32">
            <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <>
            {/* Market KPIs */}
            {(isStocks || isMF) && <MarketOverview summary={summary} />}

            {/* Compare panel */}
            {compareSet.size > 0 && (
              <ComparePanel
                symbols={allSymbols}
                prices={prices}
                compareSet={compareSet}
                onToggle={toggleCompare}
                onClear={() => setCompareSet(new Set())}
              />
            )}

            {/* Top movers */}
            {(isStocks || isMF) && (
              <TopMovers
                movers={movers}
                onCompare={toggleCompare}
                compareSet={compareSet}
              />
            )}

            {/* Main table / view */}
            {isStocks && (
              <StocksTable
                symbols={stockSymbols}
                prices={prices}
                onCompare={toggleCompare}
                compareSet={compareSet}
              />
            )}
            {isMF && (
              <MutualFundsTable
                symbols={mfSymbols}
                prices={prices}
                onCompare={toggleCompare}
                compareSet={compareSet}
              />
            )}
            {isSectors && <SectorsView symbols={stockSymbols} prices={prices} />}
            {type === "etfs" && (
              <div className="bg-surface border border-dashed border-border rounded-2xl p-16 text-center">
                <BarChart3 size={32} className="text-muted mx-auto mb-4" />
                <h3 className="text-white font-bold mb-2">ETFs Coming Soon</h3>
                <p className="text-muted text-sm max-w-xs mx-auto">PSX ETF data will be available here soon.</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
