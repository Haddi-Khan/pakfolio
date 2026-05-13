import { TrendingUp, TrendingDown, DollarSign, Wallet, BarChart2, Layers, PiggyBank } from "lucide-react";
import { fmt } from "../utils/format";
import { motion } from "framer-motion";
import CountUp from "react-countup";

export function KPICards({ summary: s }) {
  if (!s) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {[...Array(7)].map((_, i) => (
          <div key={i} className="rounded-2xl h-24 bg-surface border border-border animate-pulse" />
        ))}
      </div>
    );
  }

  const plPos = s.total_gain_loss >= 0;
  const dayPos = s.day_pnl >= 0;

  const cards = [
    {
      label: "TOTAL VALUE",
      hint: "Cash + Equities",
      rawValue: s.total_portfolio_value,
      prefix: "Rs ",
      icon: BarChart2,
      accent: "var(--color-accent)",
      gradient: "from-accent/10 to-transparent",
      glow: "glow-positive",
    },
    {
      label: "TOTAL P&L",
      hint: fmt.pct(s.total_return_pct),
      rawValue: Math.abs(s.total_gain_loss),
      prefix: plPos ? "+Rs " : "-Rs ",
      icon: plPos ? TrendingUp : TrendingDown,
      accent: plPos ? "var(--color-gain)" : "var(--color-loss)",
      gradient: plPos ? "from-gain/10 to-transparent" : "from-loss/10 to-transparent",
      glow: plPos ? "glow-positive" : "glow-negative",
      isPL: true,
      plPos,
    },
    {
      label: "UNREALIZED",
      hint: "Open positions",
      rawValue: Math.abs(s.total_unrealized_pnl),
      prefix: s.total_unrealized_pnl >= 0 ? "+Rs " : "-Rs ",
      icon: Layers,
      accent: "#8B5CF6",
      gradient: "from-purple-500/10 to-transparent",
      glow: "hover:shadow-[0_8px_30px_rgb(139,92,246,0.12)]",
      isPL: true,
      plPos: s.total_unrealized_pnl >= 0,
    },
    {
      label: "REALIZED",
      hint: "Closed positions",
      rawValue: Math.abs(s.total_realized_pnl),
      prefix: s.total_realized_pnl >= 0 ? "+Rs " : "-Rs ",
      icon: Wallet,
      accent: "var(--color-warn)",
      gradient: "from-warn/10 to-transparent",
      glow: "hover:shadow-[0_8px_30px_rgb(245,158,11,0.12)]",
      isPL: true,
      plPos: s.total_realized_pnl >= 0,
    },
    {
      label: "AVAILABLE CASH",
      hint: "Uninvested",
      rawValue: s.cash_balance,
      prefix: "Rs ",
      icon: DollarSign,
      accent: "var(--color-gain)",
      gradient: "from-gain/10 to-transparent",
      glow: "hover:shadow-[0_8px_30px_rgb(16,185,129,0.12)]",
    },
    {
      label: "TOTAL INVESTED",
      hint: "Principal",
      rawValue: s.total_deposited,
      prefix: "Rs ",
      icon: PiggyBank,
      accent: "#10B981",
      gradient: "from-emerald-500/10 to-transparent",
      glow: "hover:shadow-[0_8px_30px_rgb(16,185,129,0.12)]",
    },
    {
      label: "WIN RATIO",
      hint: `${s.win_loss?.wins ?? 0} Wins / ${s.win_loss?.losses ?? 0} Losses`,
      rawValue: s.win_loss?.win_pct ?? 0,
      prefix: "",
      icon: TrendingUp,
      accent: (s.win_loss?.win_pct ?? 0) >= 50 ? "var(--color-gain)" : "var(--color-loss)",
      gradient: (s.win_loss?.win_pct ?? 0) >= 50 ? "from-gain/10 to-transparent" : "from-loss/10 to-transparent",
      glow: (s.win_loss?.win_pct ?? 0) >= 50 ? "glow-positive" : "glow-negative",
      suffix: "%",
    }
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1 }
    }
  };

  return (
    <motion.div 
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3"
    >
      {cards.map((c) => <KPICard key={c.label} {...c} />)}
    </motion.div>
  );
}

function KPICard({ label, hint, rawValue, prefix, icon: Icon, accent, gradient, glow, isPL, plPos }) {
  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
  };

  return (
    <motion.div 
      variants={itemVariants}
      className={`relative rounded-2xl p-4 bg-gradient-to-br ${gradient} bg-surface border border-border overflow-hidden asset-card ${glow}`}
    >
      <div className="absolute top-0 left-0 right-0 h-[1.5px] rounded-t-2xl"
        style={{ background: `linear-gradient(90deg, ${accent}70, transparent)` }} />

      <div className="flex items-center justify-between mb-2">
        <span className="text-[9px] font-black tracking-[0.2em] uppercase opacity-70" style={{ color: accent }}>
          {label}
        </span>
        <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-white/5 border border-white/5">
          <Icon size={12} style={{ color: accent }} />
        </div>
      </div>

      <div className={`text-lg font-bold mono leading-none mb-1 ${
        isPL
          ? plPos ? "text-gain" : "text-loss"
          : "text-white"
      }`}>
        <CountUp
          start={0}
          end={rawValue}
          duration={1.5}
          decimals={label === "WIN RATIO" ? 1 : 0}
          separator=","
          prefix={prefix}
          suffix={label === "WIN RATIO" ? "%" : ""}
          useEasing={true}
        />
      </div>

      <div className={`text-[10px] mono font-bold opacity-60 ${
        isPL ? (plPos ? "text-gain" : "text-loss") : "text-muted"
      }`}>
        {hint}
      </div>
    </motion.div>
  );
}
