import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { fmt } from "../utils/format";
import { motion } from "framer-motion";

const COLORS = [
  "#3B82F6", "#10B981", "#6366F1", "#F59E0B", "#8B5CF6",
  "#EC4899", "#14B8A6", "#F97316", "#06B6D4", "#84CC16",
];

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div className="bg-surface-3 border border-border-2 rounded-xl px-4 py-3 shadow-2xl fade-in">
      <div className="flex items-center gap-2 mb-1">
        <div className="w-2.5 h-2.5 rounded-full" style={{ background: d.payload.color }} />
        <span className="text-white font-bold text-sm">{d.name}</span>
      </div>
      <p className="text-soft mono text-sm">{fmt.pkr(d.value)}</p>
      <p className="text-xs mono mt-0.5" style={{ color: d.payload.color }}>{d.payload.pct}% of portfolio</p>
    </div>
  );
}

export function HoldingsPie({ holdings, cashBalance = 0 }) {
  if (!holdings?.length && cashBalance <= 0) return null;

  const equitiesValue = (holdings ?? []).reduce((s, h) => s + (h.current_value || h.total_cost), 0);
  const total = equitiesValue + cashBalance;
  const data = (holdings ?? []).map((h, i) => ({
    name: h.symbol,
    value: h.current_value || h.total_cost,
    pct: (((h.current_value || h.total_cost) / total) * 100).toFixed(1),
    color: COLORS[i % COLORS.length],
  }));

  if (cashBalance > 0) {
    data.push({
      name: "PKR Cash",
      value: cashBalance,
      pct: ((cashBalance / total) * 100).toFixed(1),
      color: "var(--color-gain, #10B981)",
    });
  }

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className="h-full"
    >
      <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-muted mb-6">Portfolio Distribution</h3>

      {/* Pie */}
      <div className="relative mb-6 flex justify-center">
        <ResponsiveContainer width="100%" height={180}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={80}
              paddingAngle={4}
              dataKey="value"
              strokeWidth={0}
              isAnimationActive={true}
              animationDuration={1500}
            >
              {data.map((d, i) => (
                <Cell key={i} fill={d.color} opacity={0.85} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
        
        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-[10px] font-black uppercase tracking-wider text-muted opacity-60">Assets</span>
          <span className="text-sm font-bold text-white">{data.length}</span>
        </div>
      </div>

      {/* Legend list */}
      <div className="space-y-3.5 px-1">
        {data.sort((a,b) => b.value - a.value).map((d) => (
          <div key={d.name} className="flex items-center justify-between group cursor-default">
            <div className="flex items-center gap-2.5">
              <div className="w-2 h-2 rounded-full ring-4 ring-black/20" style={{ background: d.color }} />
              <span className="text-white font-bold text-[11px] group-hover:text-accent transition-colors">{d.name}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-muted text-[10px] font-bold mono opacity-60 group-hover:opacity-100">{fmt.compact(d.value)}</span>
              <span className="text-[10px] font-black mono w-8 text-right" style={{ color: d.color }}>{d.pct}%</span>
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
