import { useState, useMemo } from "react";
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine,
} from "recharts";
import { useChart, useHoldings } from "../hooks/usePortfolio";
import { fmt } from "../utils/format";
import { TrendingUp, TrendingDown, Activity, BarChart3, PieChart as PieChartIcon } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const PERIODS = ["1W", "1M", "3M", "6M", "1Y", "5Y", "10Y", "ALL"];

function CustomTooltip({ active, payload, label, mode }) {
  if (!active || !payload?.length) return null;
  
  const isPerf = mode === "performance";
  const pData = payload.find(p => p.dataKey === (isPerf ? "perf_pct" : "value"));
  const bData = payload.find(p => p.dataKey === (isPerf ? "benchmark_perf_pct" : "benchmark_value"));
  const iData = payload.find(p => p.dataKey === "invested_value");

  return (
    <div className="bg-surface/90 backdrop-blur-xl border border-border rounded-xl px-4 py-3 shadow-2xl space-y-2.5 min-w-[180px]">
      <div className="flex items-center justify-between border-b border-white/5 pb-1.5 mb-1">
        <span className="text-muted text-[9px] font-black uppercase tracking-widest">{fmt.date(label)}</span>
        {!isPerf && pData && iData && (
          <span className={`text-[9px] font-black px-1.5 py-0.5 rounded ${pData.value >= iData.value ? "bg-gain/10 text-gain" : "bg-loss/10 text-loss"}`}>
            {pData.value >= iData.value ? "PROFIT" : "LOSS"}
          </span>
        )}
      </div>

      <div className="space-y-2">
        {/* Portfolio Row */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-accent" />
            <span className="text-[10px] font-bold text-soft uppercase">Portfolio</span>
          </div>
          <span className="text-white font-bold text-sm mono">
            {isPerf ? `${pData?.value > 0 ? "+" : ""}${pData?.value}%` : fmt.pkr(pData?.value)}
          </span>
        </div>

        {/* Benchmark Row */}
        {bData && (
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-amber-400" />
              <span className="text-[10px] font-bold text-soft uppercase">KSE-100</span>
            </div>
            <span className="text-amber-400 font-bold text-sm mono">
              {isPerf ? `${bData.value > 0 ? "+" : ""}${bData.value}%` : fmt.pkr(bData.value)}
            </span>
          </div>
        )}

        {/* Invested Row (Value mode only) */}
        {!isPerf && iData && (
          <div className="flex items-center justify-between gap-4 pt-1 border-t border-white/5">
            <div className="flex items-center gap-2">
              <div className="w-2 h-0.5 bg-muted/40 dashed" />
              <span className="text-[10px] font-bold text-muted uppercase">Invested</span>
            </div>
            <span className="text-muted font-bold text-xs mono">{fmt.pkr(iData.value)}</span>
          </div>
        )}
      </div>
    </div>
  );
}

// Fallback: build a static snapshot chart from holdings current vs cost
function useSnapshotChart(holdings) {
  return useMemo(() => {
    if (!holdings?.length) return [];
    const today = new Date().toISOString().slice(0, 10);
    const cost = holdings.reduce((s, h) => s + h.total_cost, 0);
    const value = holdings.reduce((s, h) => s + (h.current_value ?? h.total_cost), 0);
    return [
      { date: "PREV", value: cost, invested_value: cost, perf_pct: 0 },
      { date: today, value: value, invested_value: cost, perf_pct: cost ? ((value/cost - 1)*100).toFixed(2) : 0 },
    ];
  }, [holdings]);
}

export function PortfolioChart({ pid }) {
  const [period, setPeriod] = useState("1M");
  const [mode, setMode] = useState("value"); // "value" or "performance"
  const [showBenchmark, setShowBenchmark] = useState(true);
  
  const { data: chartData, loading } = useChart(period, pid);
  const { data: holdings } = useHoldings(pid);
  const snapshotData = useSnapshotChart(holdings);

  const data = chartData.length > 0 ? chartData : snapshotData;
  const isSnapshot = chartData.length === 0 && snapshotData.length > 0;

  const lastPoint = data[data.length - 1];
  // Use first non-zero point so change doesn't measure from an empty portfolio start
  const firstNonZeroPoint = data.find(d => d.value > 0) ?? data[0];

  const lastVal = lastPoint?.value;
  const firstVal = firstNonZeroPoint?.value;
  const change = lastVal != null && firstVal != null ? lastVal - firstVal : null;
  const changePct = change != null && firstVal ? (change / firstVal) * 100 : null;
  const isUp = change == null || change >= 0;

  // Colors
  const accentColor = "var(--color-accent)";
  const benchmarkColor = "#fbbf24"; // Amber 400 for high contrast
  const investmentColor = "#5A6B82"; // Muted blue/gray

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl bg-surface border border-border overflow-hidden asset-card relative"
    >
      {/* Background Glow */}
      <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-accent/5 to-transparent pointer-events-none" />
      
      {/* Header / Tabs */}
      <div className="px-6 pt-5 pb-2">
        <div className="flex items-center justify-between mb-6">
          <div className="flex bg-white/5 rounded-xl p-1 border border-white/5">
            <button 
              onClick={() => setMode("value")}
              className={`px-4 py-2 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${
                mode === "value" ? "bg-accent text-white shadow-lg" : "text-muted hover:text-white"
              }`}
            >
              Market Value
            </button>
            <button 
              onClick={() => setMode("performance")}
              className={`px-4 py-2 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${
                mode === "performance" ? "bg-accent text-white shadow-lg" : "text-muted hover:text-white"
              }`}
            >
              Performance
            </button>
          </div>

          <div className="flex bg-white/5 rounded-xl p-1 gap-0.5 border border-white/5">
            {PERIODS.map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-1.5 rounded-lg text-[9px] font-black tracking-widest transition-all ${
                  period === p ? "bg-accent text-white shadow-lg" : "text-muted hover:text-white"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-end justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <span className="text-muted text-[10px] font-black uppercase tracking-[0.2em]">
                {mode === "value" ? "Current Balance" : "Portfolio ROI"}
                {isSnapshot && <span className="text-warn text-[8px] opacity-70 ml-2">(SNAPSHOT)</span>}
              </span>
              
              <button 
                onClick={() => setShowBenchmark(!showBenchmark)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[9px] font-black uppercase tracking-wider transition-all ${
                  showBenchmark 
                    ? "bg-amber-400/10 border-amber-400/20 text-amber-500 shadow-[0_0_15px_rgba(251,191,36,0.1)]" 
                    : "bg-white/5 border-white/10 text-muted hover:text-white hover:bg-white/10"
                }`}
              >
                <Activity size={10} />
                {showBenchmark ? "KSE-100 ON" : "KSE-100 OFF"}
              </button>
            </div>
            
            <div className="flex items-baseline gap-3">
              <span className="text-4xl font-black text-white mono tracking-tighter">
                {mode === "value" 
                  ? (lastVal != null ? fmt.pkr(lastVal) : "—")
                  : (lastPoint?.perf_pct != null ? `${lastPoint.perf_pct > 0 ? "+" : ""}${lastPoint.perf_pct}%` : "—")
                }
              </span>
              {change != null && mode === "value" && (
                <div className={`flex items-center gap-1.5 font-black uppercase tracking-wider text-[11px] px-2 py-0.5 rounded ${isUp ? "bg-gain/10 text-gain" : "bg-loss/10 text-loss"}`}>
                  {isUp ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                  {change >= 0 ? "+" : ""}{fmt.compact(change)}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Chart Container */}
      <div className="px-1 pb-4 relative h-[320px]">
        {loading ? (
          <div className="h-full flex items-center justify-center">
            <div className="w-10 h-10 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        ) : data.length < 2 ? (
          <div className="h-full flex flex-col items-center justify-center text-muted gap-4">
            <BarChart3 size={48} className="opacity-10" />
            <span className="text-[10px] font-black uppercase tracking-widest opacity-40">Insufficient Historical Data</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            {mode === "value" ? (
              <AreaChart data={data} margin={{ top: 20, right: 30, left: 10, bottom: 0 }}>
                <defs>
                  <linearGradient id="valueGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={accentColor} stopOpacity={0.2} />
                    <stop offset="100%" stopColor={accentColor} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: "#5A6B82", fontSize: 10, fontWeight: 800 }}
                  axisLine={false}
                  tickLine={false}
                  dy={10}
                  tickFormatter={d => d === "PREV" ? "" : new Date(d).toLocaleDateString("en-PK", { month: "short", day: "numeric" })}
                />
                <YAxis
                  domain={[
                    0,
                    (max) => {
                      // Include invested_value in the domain so the baseline is always visible
                      const iv = lastPoint?.invested_value || 0;
                      const peak = Math.max(max, iv);
                      return Math.ceil((peak * 1.1) / 50000) * 50000 || 50000;
                    }
                  ]}
                  tick={{ fill: "#5A6B82", fontSize: 10, fontWeight: 800 }}
                  axisLine={false}
                  tickLine={false}
                  dx={-15}
                  width={75}
                  tickFormatter={v => fmt.compact(v)}
                />
                <Tooltip content={<CustomTooltip mode={mode} />} cursor={{ stroke: "rgba(255,255,255,0.05)", strokeWidth: 20 }} />

                {/* Baseline Investment Dotted Line */}
                {lastPoint?.invested_value > 0 && (
                  <ReferenceLine
                    y={lastPoint.invested_value}
                    stroke="#ffffff"
                    strokeOpacity={0.4}
                    strokeWidth={2}
                    strokeDasharray="4 4"
                    label={{
                      position: "insideTopRight",
                      value: "INVESTMENT BASELINE",
                      fill: "#ffffff",
                      fillOpacity: 0.6,
                      fontSize: 10,
                      fontWeight: 900,
                      offset: 15,
                      className: "uppercase tracking-tighter"
                    }}
                  />
                )}

                {showBenchmark && (
                  <Area
                    type="monotone"
                    dataKey="benchmark_value"
                    stroke="#fbbf24" // Amber 400
                    strokeWidth={3}
                    strokeDasharray="6 3"
                    fill="transparent"
                    connectNulls={true}
                    dot={false}
                    isAnimationActive={true}
                  />
                )}
                
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={accentColor}
                  strokeWidth={4}
                  fill="url(#valueGrad)"
                  connectNulls={true}
                  dot={false}
                  activeDot={{ r: 6, fill: accentColor, stroke: "#0B111B", strokeWidth: 3 }}
                  isAnimationActive={true}
                  animationDuration={1500}
                />
              </AreaChart>
            ) : (
              <LineChart key={`chart-perf-${period}-${pid}`} data={data} margin={{ top: 20, right: 30, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: "#5A6B82", fontSize: 10, fontWeight: 800 }}
                  axisLine={false}
                  tickLine={false}
                  dy={10}
                  tickFormatter={d => d === "PREV" ? "" : new Date(d).toLocaleDateString("en-PK", { month: "short", day: "numeric" })}
                />
                <YAxis
                  domain={[
                    (min) => {
                      const padded = Math.ceil(Math.abs(min) * 1.1 / 5) * 5 || 5;
                      return -padded;
                    },
                    (max) => {
                      const padded = Math.ceil(Math.abs(max) * 1.1 / 5) * 5 || 5;
                      return padded;
                    }
                  ]}
                  tick={{ fill: "#5A6B82", fontSize: 10, fontWeight: 800 }}
                  axisLine={false}
                  tickLine={false}
                  dx={-15}
                  width={50}
                  tickFormatter={v => `${v}%`}
                />
                <Tooltip content={<CustomTooltip mode={mode} />} cursor={{ stroke: "rgba(255,255,255,0.05)", strokeWidth: 20 }} />
                
                <ReferenceLine y={0} stroke="#ffffff20" strokeWidth={1} />

                {showBenchmark && (
                  <Line
                    type="monotone"
                    dataKey="benchmark_perf_pct"
                    stroke={benchmarkColor}
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={true}
                  />
                )}
                
                <Line
                  type="monotone"
                  dataKey="perf_pct"
                  stroke={accentColor}
                  strokeWidth={4}
                  dot={false}
                  activeDot={{ r: 6, fill: accentColor, stroke: "#0B111B", strokeWidth: 3 }}
                  isAnimationActive={true}
                  animationDuration={1500}
                />
              </LineChart>
            )}
          </ResponsiveContainer>
        )}
      </div>

      {/* Legend Footer */}
      <div className="px-6 py-4 bg-white/[0.02] border-t border-border flex items-center gap-6">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded bg-accent shadow-[0_0_8px_rgba(59,130,246,0.3)]" />
          <span className="text-[9px] font-black uppercase tracking-widest text-muted">Portfolio</span>
        </div>
        {showBenchmark && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.3)]" />
            <span className="text-[9px] font-black uppercase tracking-widest text-muted">KSE-100 Index</span>
          </div>
        )}
        {mode === "value" && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 bg-muted/40 dashed" />
            <span className="text-[9px] font-black uppercase tracking-widest text-muted italic">Investment Baseline</span>
          </div>
        )}
      </div>
    </motion.div>
  );
}
