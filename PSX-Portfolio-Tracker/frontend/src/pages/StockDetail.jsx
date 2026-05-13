import { useState, useEffect, useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { TrendingUp, TrendingDown, LayoutGrid, BarChart3, Users, Landmark, Activity, ExternalLink } from "lucide-react";
import {
  ComposedChart, Area, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { api } from "../api/client";
import { fmt } from "../utils/format";
import { motion } from "framer-motion";

const PERIODS = ["1W", "1M", "3M", "6M", "1Y", "5Y", "10Y", "ALL"];

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-surface border border-border rounded-xl px-3 py-2 shadow-2xl min-w-[140px]">
      <p className="text-muted text-xs mb-2 border-b border-white/10 pb-1">{fmt.date(label)}</p>
      <div className="space-y-1">
        {payload.map((entry, index) => (
          <div key={index} className="flex justify-between items-center gap-4">
            <span className="text-[10px] font-bold uppercase" style={{ color: entry.color }}>{entry.name}</span>
            <span className="text-white font-bold mono text-sm">{fmt.num(entry.value)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function StockDetail() {
  const { symbol } = useParams();
  const [quote, setQuote] = useState(null);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [fundamentals, setFundamentals] = useState(null);
  const [peers, setPeers] = useState([]);
  const [period, setPeriod] = useState("1M");
  const [loading, setLoading] = useState(true);


  // Fetch quote + initial history (1M) IN PARALLEL on mount
  useEffect(() => {
    async function fetchMainData() {
      setLoading(true);
      setHistoryLoading(true);
      const today = new Date().toISOString().slice(0, 10);
      const from1M = new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10);
      try {
        // Fire quote + default history + secondary data all at once
        const [q] = await Promise.all([
          api.prices.quote(symbol),
          // Kick off 1M history immediately in parallel
          api.prices.history(symbol, from1M, today)
            .then(h => { setHistory(h); setHistoryLoading(false); })
            .catch(() => { setHistory([]); setHistoryLoading(false); }),
          // Secondary data also in parallel
          api.symbols.fundamentals(symbol).then(setFundamentals).catch(() => setFundamentals({})),
          api.symbols.peers(symbol).then(setPeers).catch(() => setPeers([])),
        ]);
        setQuote(q);
        setLoading(false);
      } catch (err) {
        console.error("Failed to fetch stock detail:", err);
        setLoading(false);
        setHistoryLoading(false);
      }
    }
    fetchMainData();
  }, [symbol]);

  useEffect(() => {
    if (symbol) {
      document.title = `${symbol} | Pakfolio`;
    }
    return () => { document.title = "Pakfolio"; };
  }, [symbol]);

  // Period change (NOT initial load — that's handled above)
  const isFirstRender = useState(true);
  useEffect(() => {
    // Skip first render — initial 1M is already loaded above
    if (period === "1M" && isFirstRender[0]) {
      isFirstRender[0] = false;
      return;
    }
    isFirstRender[0] = false;
    setHistoryLoading(true);
    const today = new Date().toISOString().slice(0, 10);
    const periodDays = { "1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365, "5Y": 1825, "10Y": 3650 };
    const from = period === "ALL"
      ? "1990-01-01"
      : new Date(Date.now() - periodDays[period] * 86400000).toISOString().slice(0, 10);
    api.prices.history(symbol, from, today)
      .then(h => { setHistory(h); setHistoryLoading(false); })
      .catch(() => { setHistory([]); setHistoryLoading(false); });
  }, [period]);


  const chartData = useMemo(() => history.map((p) => ({ 
      date: p.date, 
      Price: p.close,
      SMA50: p.sma_50,
      SMA200: p.sma_200,
      BBU: p.bbu_20_2_0,
      BBL: p.bbl_20_2_0,
      RSI: p.rsi_14
  })), [history]);
  const isUp = (quote?.change ?? 0) >= 0;
  const strokeColor = isUp ? "var(--color-gain, #10B981)" : "var(--color-loss, #EF4444)";

  if (loading) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg text-white pb-20 bg-mesh selection:bg-accent/30 font-inter">
      <div className="max-w-6xl mx-auto px-4 pt-8 space-y-16">
        
        {/* Hero Section */}
        <motion.section 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="relative"
        >
          {/* Background Symbol Label */}
          <div className="absolute -top-20 -left-12 text-[14rem] font-black text-white/[0.02] select-none pointer-events-none uppercase tracking-tighter italic">
            {symbol.slice(0, 3)}
          </div>

          <div className="relative grid grid-cols-1 lg:grid-cols-3 gap-12 items-end">
            <div className="lg:col-span-2 space-y-10">
              <div className="space-y-4">
                <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-accent/10 border border-accent/20 text-accent text-[10px] font-bold uppercase tracking-[0.2em] shadow-lg">
                  <div className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
                  Live Market Analysis
                </div>
                <h1 className="text-7xl lg:text-[10rem] font-black tracking-tighter leading-[0.85] gradient-text-blue">{quote?.symbol}</h1>
                <p className="text-2xl text-soft/60 font-medium max-w-xl leading-relaxed">
                  {quote?.name}
                  {quote?.asset_type === 'mutual_fund' && (
                    <span className="ml-4 px-3 py-1 rounded-lg bg-accent/10 border border-accent/20 text-accent text-[12px] font-black uppercase tracking-widest">
                      Mutual Fund
                    </span>
                  )}
                </p>
              </div>
              
              <div className="flex flex-wrap items-center gap-10">
                <div className="space-y-2">
                  <div className="text-muted text-[10px] font-black uppercase tracking-[0.2em] opacity-80">Current Valuation</div>
                  <div className="text-7xl font-black mono tracking-tighter flex items-center gap-4">
                    {quote?.asset_type === 'mutual_fund' ? fmt.num(quote?.price) : fmt.num(quote?.price)}
                    <span className="text-xl text-muted font-bold self-end mb-3 tracking-widest">{quote?.asset_type === 'mutual_fund' ? 'NAV' : 'PKR'}</span>
                  </div>
                </div>
                
                <div className="h-16 w-px bg-white/10 hidden sm:block" />

                <div className="space-y-2">
                  <div className="text-muted text-[10px] font-black uppercase tracking-[0.2em] opacity-80">Net Performance</div>
                  <div className={`text-4xl font-black mono tracking-tighter ${isUp ? "gradient-text-green glow-text-green" : "gradient-text-red glow-text-red"}`}>
                    {isUp ? "+" : ""}{fmt.num(quote?.change)}
                  </div>
                </div>
              </div>
            </div>

            <motion.div 
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
              className="grid grid-cols-2 gap-4 lg:pb-3"
            >
               {[
                 { label: "Open", val: quote?.open, icon: LayoutGrid, accent: "#8B5CF6", glow: "rgba(139, 92, 246, 0.2)" },
                 { label: "Day High", val: quote?.high, icon: TrendingUp, accent: "#10B981", glow: "rgba(16, 185, 129, 0.2)" },
                 { label: "Day Low", val: quote?.low, icon: TrendingDown, accent: "#EF4444", glow: "rgba(239, 68, 68, 0.2)" },
                 { 
                   label: quote?.asset_type === 'mutual_fund' ? "AUM" : "Volume", 
                   val: quote?.asset_type === 'mutual_fund' ? fmt.compact(quote?.aum) : fmt.compact(quote?.volume), 
                   icon: BarChart3, 
                   accent: "#3B82F6", 
                   glow: "rgba(59, 130, 246, 0.2)" 
                 },
               ].map((s) => (
                 <div key={s.label} className="glass-card glow-border p-6 rounded-[2rem] group hover:scale-[1.02] transition-transform shadow-2xl">
                   <div className="text-muted text-[10px] font-black uppercase tracking-[0.2em] mb-4 flex items-center gap-3">
                     <div className="w-6 h-6 rounded-xl flex items-center justify-center shadow-lg" style={{ background: s.accent + "15", border: `1px solid ${s.accent}30` }}>
                       <s.icon size={11} style={{ color: s.accent }} />
                     </div>
                     {s.label}
                   </div>
                   <div className="text-white font-black text-2xl mono group-hover:text-accent transition-colors tracking-tight">{s.val ?? "—"}</div>
                   <div className="absolute inset-0 bg-gradient-to-br transition-opacity opacity-0 group-hover:opacity-10 pointer-events-none" 
                     style={{ background: `radial-gradient(circle at top right, ${s.glow}, transparent)` }} />
                 </div>
               ))}
            </motion.div>
          </div>
        </motion.section>

        {/* Chart Section */}
        <motion.section 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="glass-card rounded-[3rem] p-5 lg:p-10 shadow-2xl relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-96 h-96 bg-accent/5 blur-[120px] rounded-full -translate-y-1/2 translate-x-1/2" />
          
          <div className="relative flex flex-col lg:flex-row items-center justify-between gap-8 mb-16">
            <div className="flex items-center gap-6">
              <div className="w-16 h-16 rounded-[1.5rem] bg-accent/10 flex items-center justify-center text-accent border border-accent/20 shadow-2xl">
                <BarChart3 size={32} />
              </div>
              <div>
                <h2 className="text-3xl font-black tracking-tighter mb-1">Price Trajectory</h2>
                <div className="flex items-center gap-2 text-[10px] text-muted font-black uppercase tracking-[0.2em]">
                  <span className="w-1.5 h-1.5 rounded-full bg-gain animate-pulse" />
                  Real-time Data Stream
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-5">
              <div className="flex bg-white/[0.03] backdrop-blur-3xl rounded-[1.25rem] p-1.5 border border-white/5 shadow-2xl">
                {PERIODS.map((p) => (
                  <button key={p} onClick={() => setPeriod(p)}
                    className={`px-5 py-2.5 rounded-xl text-xs font-bold transition-all duration-200 ${
                      period === p ? "bg-white/10 text-white shadow-inner" : "text-muted hover:text-white"
                    }`}>
                    {p}
                  </button>
                ))}
              </div>

              {quote?.asset_type !== 'mutual_fund' && (
                <a 
                  href={`https://www.tradingview.com/symbols/PSX-${symbol.toUpperCase()}/`} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="px-6 py-2.5 flex items-center gap-2 rounded-xl text-xs font-black uppercase tracking-[0.1em] transition-all duration-300 bg-white/[0.03] border border-white/5 text-muted hover:text-white hover:bg-white/10 shadow-xl"
                >
                  TradingView <ExternalLink size={14} />
                </a>
              )}
            </div>
          </div>

          <div className="h-[520px] relative">
            {historyLoading ? (
              <div className="h-full flex flex-col items-end justify-end gap-1 pb-4 px-2 overflow-hidden">
                {/* Animated skeleton bar chart */}
                {Array.from({ length: 32 }).map((_, i) => {
                  const h = 20 + Math.sin(i * 0.7) * 30 + Math.random() * 25;
                  return (
                    <div
                      key={i}
                      className="w-full rounded-sm bg-white/[0.04] animate-pulse"
                      style={{
                        height: `${h}%`,
                        animationDelay: `${i * 30}ms`,
                        background: `linear-gradient(90deg, rgba(255,255,255,0.03), rgba(255,255,255,0.07), rgba(255,255,255,0.03))`,
                        backgroundSize: "200% 100%",
                        animation: `pulse 1.5s ease-in-out ${i * 30}ms infinite`,
                        display: "none"
                      }}
                    />
                  );
                })}
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
                  <svg viewBox="0 0 200 60" className="w-full h-24 opacity-10">
                    <polyline
                      points="0,50 20,35 40,45 60,20 80,30 100,10 120,25 140,15 160,30 180,20 200,35"
                      fill="none" stroke="currentColor" strokeWidth="2"
                      className="text-accent"
                    />
                  </svg>
                  <div className="h-1 w-40 bg-white/5 rounded-full overflow-hidden">
                    <div className="h-full bg-accent/40 rounded-full animate-[loading-bar_1.5s_ease-in-out_infinite]" style={{width:"40%", animation: "pulse 1s ease-in-out infinite"}} />
                  </div>
                  <span className="text-[10px] font-black uppercase tracking-[0.3em] text-muted/40">Loading Chart</span>
                </div>
              </div>
            ) : chartData.length < 2 ? (
              <div className="h-full flex flex-col items-center justify-center text-muted gap-5">
                <div className="w-16 h-16 rounded-full border-2 border-white/5 flex items-center justify-center animate-pulse">
                   <Activity size={32} className="opacity-20" />
                </div>
                <span className="text-xs font-black uppercase tracking-[0.3em] opacity-40">No Chart Data Available</span>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={strokeColor} stopOpacity={0.4} />
                      <stop offset="100%" stopColor={strokeColor} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="8 12" stroke="var(--color-border)" vertical={false} />
                  <XAxis dataKey="date" tick={{ fill: "var(--color-muted)", fontSize: 10, fontWeight: 900 }} 
                    axisLine={false} tickLine={false} dy={25}
                    tickFormatter={(d) => new Date(d).toLocaleDateString("en-PK", { month: "short", day: "numeric" })} />
                  <YAxis tick={{ fill: "var(--color-muted)", fontSize: 10, fontWeight: 900 }} 
                    axisLine={false} tickLine={false} width={80} dx={-25}
                    tickFormatter={(v) => fmt.compact(v)} domain={["auto", "auto"]} />
                  <Tooltip content={<ChartTooltip />} cursor={{ stroke: `${strokeColor}20`, strokeWidth: 2 }} />
                  
                  {/* Indicators */}
                  <Line type="monotone" dataKey="BBU" stroke="#3B82F6" strokeWidth={1} dot={false} strokeOpacity={0.4} />
                  <Line type="monotone" dataKey="BBL" stroke="#3B82F6" strokeWidth={1} dot={false} strokeOpacity={0.4} />
                  <Line type="monotone" dataKey="SMA200" stroke="#8B5CF6" strokeWidth={2} dot={false} strokeDasharray="5 5" />
                  <Line type="monotone" dataKey="SMA50" stroke="#F59E0B" strokeWidth={2} dot={false} strokeDasharray="3 3" />
                  
                  <Area type="monotone" dataKey="Price" stroke={strokeColor} strokeWidth={5}
                    fill="url(#chartGradient)" dot={false} 
                    activeDot={{ r: 10, fill: strokeColor, stroke: "var(--color-surface)", strokeWidth: 4 }} />
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </div>

        </motion.section>        {/* Fundamentals & Peers / Fund Details */}
        <motion.div 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="grid grid-cols-1 lg:grid-cols-12 gap-12"
        >
          {quote?.asset_type === 'mutual_fund' ? (
            <section className="lg:col-span-12 space-y-12">
               <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
                  {[
                    { label: "Risk Profile", val: quote?.risk_profile, icon: Activity, color: "text-warn bg-warn/10" },
                    { label: "Fund Category", val: quote?.category, icon: LayoutGrid, color: "text-accent bg-accent/10" },
                    { label: "Shariah Status", val: quote?.is_shariah ? "Shariah Compliant" : "Conventional", icon: Landmark, color: "text-gain bg-gain/10" },
                    { label: "Asset Management", val: fmt.compact(quote?.aum), icon: BarChart3, color: "text-blue-400 bg-blue-400/10" }
                  ].map((info) => (
                    <div key={info.label} className="glass-card p-8 rounded-[2.5rem] border border-white/5 shadow-2xl relative group overflow-hidden">
                      <div className={`w-14 h-14 rounded-2xl ${info.color} flex items-center justify-center mb-6 shadow-xl`}>
                        <info.icon size={24} />
                      </div>
                      <div className="text-muted text-[10px] font-black uppercase tracking-[0.3em] mb-2">{info.label}</div>
                      <div className="text-2xl font-black text-white group-hover:text-accent transition-colors">{info.val || "—"}</div>
                      <div className="absolute -bottom-4 -right-4 w-24 h-24 bg-current opacity-0 group-hover:opacity-[0.03] blur-2xl transition-opacity" />
                    </div>
                  ))}
               </div>
            </section>
          ) : (
            <>
              {/* Fundamentals – Glass Table */}
              <section className="lg:col-span-8 glass-card rounded-[3rem] p-10 overflow-hidden relative">
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-12">
                    <div className="flex items-center gap-6">
                      <div className="w-16 h-16 rounded-[1.5rem] bg-warn/10 flex items-center justify-center text-warn border border-warn/20 shadow-xl">
                        <Landmark size={32} />
                      </div>
                      <div>
                        <h2 className="text-3xl font-black tracking-tighter mb-1">Financial Integrity</h2>
                        <div className="text-[10px] text-muted font-black uppercase tracking-[0.3em]">Yearly Auditor Balance Sheet</div>
                      </div>
                    </div>
                    <div className="hidden sm:block px-6 py-2.5 rounded-2xl bg-white/[0.03] border border-white/5 text-[10px] font-black uppercase tracking-[0.2em] text-muted shadow-2xl">
                      Latest 5 Periods
                    </div>
                  </div>

                  <div className="overflow-x-auto -mx-10 px-10">
                    <table className="w-full text-sm border-separate border-spacing-y-2">
                      <thead>
                        <tr className="text-muted/60">
                          <th className="text-left pb-8 font-black uppercase tracking-[0.3em] text-[10px] pl-4">Key Performance Indicator</th>
                          {fundamentals && Object.keys(fundamentals).length > 0 && Object.keys(fundamentals).slice(0, 5).map(year => (
                            <th key={year} className="text-right pb-8 font-black mono text-sm pr-4">{year}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="">
                        {fundamentals && Object.keys(fundamentals).length > 0 && Object.keys(Object.values(fundamentals)[0] || {}).map(ratioKey => (
                          <tr key={ratioKey} className="group hover:bg-white/[0.03] transition-all duration-300">
                            <td className="py-6 font-bold text-soft/80 capitalize tracking-tight flex items-center gap-4 pl-4 rounded-l-2xl border-l-[3px] border-transparent group-hover:border-accent">
                              <span className="w-1.5 h-1.5 rounded-full bg-accent/20 group-hover:bg-accent transition-colors" />
                              {ratioKey.replace(/_/g, ' ')}
                            </td>
                            {Object.keys(fundamentals).slice(0, 5).map(year => (
                              <td key={year} className="text-right py-6 mono text-white font-black text-base pr-4 group-hover:text-accent transition-colors">
                                {fmt.num(fundamentals[year][ratioKey])}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {(!fundamentals || Object.keys(fundamentals).length === 0) && (
                      <div className="py-24 text-center flex flex-col items-center gap-6">
                        <div className="w-20 h-20 rounded-full border border-white/5 flex items-center justify-center animate-pulse">
                          <Activity size={40} className="text-muted/20" />
                        </div>
                        <p className="text-muted text-[10px] font-black uppercase tracking-[0.4em] opacity-30">Financial data not available</p>
                      </div>
                    )}
                  </div>
                </div>
                {/* Decorative backgrounds */}
                <div className="absolute bottom-0 right-0 w-64 h-64 bg-accent/2 blur-[100px] rounded-full translate-y-1/2 translate-x-1/2 pointer-events-none" />
              </section>

              {/* Market Comparison – Premium Cards */}
              <section className="lg:col-span-4 space-y-10 stagger-4 animate-slide-up">
                <div className="flex items-center gap-6 px-4">
                  <div className="w-16 h-16 rounded-[1.5rem] bg-accent-2/10 flex items-center justify-center text-accent-2 border border-accent-2/20 shadow-xl">
                    <Users size={32} />
                  </div>
                  <div>
                    <h2 className="text-3xl font-black tracking-tighter mb-1">Market Peers</h2>
                    <div className="text-[10px] text-muted font-black uppercase tracking-[0.3em]">Sector Correlation</div>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-5">
                  {peers?.length > 0 ? peers.map(peer => (
                    <Link key={peer.symbol} to={`/stocks/${peer.symbol}`} className="group relative">
                      <div className="absolute inset-0 bg-accent/30 blur-3xl opacity-0 group-hover:opacity-40 transition-opacity rounded-[2.5rem] -z-10" />
                      <div className="relative glass-card glow-border p-6 rounded-[2.5rem] group-hover:-translate-y-1.5 transition-all duration-500 shadow-2xl">
                        <div className="flex items-center justify-between gap-6">
                          <div className="flex items-center gap-5">
                            <div className="w-14 h-14 rounded-2xl bg-white/[0.03] border border-white/10 flex items-center justify-center font-black text-sm text-soft group-hover:text-white group-hover:border-accent/40 shadow-inner overflow-hidden relative transition-all">
                              <div className="absolute inset-0 bg-accent/2 opacity-0 group-hover:opacity-100 transition-opacity" />
                              <span className="relative z-10">{peer.symbol.slice(0, 2)}</span>
                            </div>
                            <div>
                              <div className="text-lg font-black group-hover:text-accent transition-colors tracking-tighter mb-0.5">{peer.symbol}</div>
                              <div className="text-[11px] font-black text-muted/60 uppercase tracking-widest truncate max-w-[120px]">{peer.name}</div>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-xl font-black mono text-white group-hover:text-accent transition-colors mb-1">{fmt.num(peer.price)}</div>
                            <div className={`text-[10px] font-black mono px-2 py-0.5 rounded-lg border shadow-sm ${
                              peer.change >= 0 
                                ? "bg-gain/10 border-gain/20 text-gain" 
                                : "bg-loss/10 border-loss/20 text-loss"
                            }`}>
                              {peer.change >= 0 ? "+" : ""}{fmt.pct(peer.change_pct)}
                            </div>
                          </div>
                        </div>
                      </div>
                    </Link>
                  )) : (
                    <div className="glass-card p-16 rounded-[3rem] text-center flex flex-col items-center gap-6 shadow-2xl opacity-50">
                      <Users size={40} className="text-muted/30" />
                      <span className="text-[10px] font-black uppercase tracking-[0.4em] text-muted">Comparison Nodes Not Found</span>
                    </div>
                  )}
                </div>
                
                {/* Call to action or helper */}
                <div className="glass p-6 rounded-[2rem] border-dashed text-center">
                  <p className="text-[10px] text-muted font-black uppercase tracking-[0.3em]">Select a ticker to analyze sector correlation</p>
                </div>
              </section>
            </>
          )}
        </motion.div>
      </div>
    </div>
  );
}
