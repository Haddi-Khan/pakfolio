import { Link } from "react-router-dom";
import {
  TrendingUp, BarChart3, PieChart, Calculator, ArrowRight, Sparkles,
  Shield, Zap, Globe, ChevronRight,
} from "lucide-react";

const TOOLS = [
  { label: "SIP Calculator",        href: "/tools/sip",       desc: "Plan systematic investments" },
  { label: "Compounding Calculator", href: "/tools/compounding", desc: "Visualise compound growth" },
  { label: "CAGR Calculator",       href: "/tools/cagr",      desc: "Measure annualized returns" },
  { label: "ROI Calculator",        href: "/tools/roi",       desc: "Calculate return on investment" },
  { label: "Zakat Calculator",      href: "/tools/zakat",     desc: "Islamic wealth obligation" },
  { label: "Brokerage Deduction",   href: "/tools/brokerage", desc: "PSX trade cost breakdown" },
];

const MARKETS = [
  { label: "PSX Stocks",    href: "/markets/stocks",       icon: TrendingUp },
  { label: "Mutual Funds",  href: "/markets/mutual-funds", icon: PieChart },
  { label: "KSE-100 Index", href: "/stocks/KSE100",        icon: BarChart3 },
];

const FEATURES = [
  { icon: TrendingUp, title: "Live PSX Prices",   desc: "Real-time quotes from the Pakistan Stock Exchange, refreshed every minute." },
  { icon: PieChart,   title: "Portfolio Tracking", desc: "Track holdings, P&L, sector allocation, and performance vs KSE-100." },
  { icon: Calculator, title: "Financial Tools",   desc: "SIP, CAGR, ROI, Zakat, and brokerage calculators built for Pakistan investors." },
  { icon: Shield,     title: "Secure & Private",  desc: "Your portfolio data is encrypted and never shared with third parties." },
];

export function Landing() {
  return (
    <div className="min-h-screen bg-bg">
      {/* Hero */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-16">
        <div className="text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 border border-accent/20 text-accent text-xs font-bold uppercase tracking-widest mb-8">
            <Sparkles size={12} />
            Pakistan Stock Exchange Tracker
          </div>
          <h1 className="text-5xl md:text-6xl font-black text-white mb-6 leading-[1.1] tracking-tight">
            Invest smarter in{" "}
            <span className="text-accent">Pakistan</span>
          </h1>
          <p className="text-muted text-lg leading-relaxed mb-10 max-w-xl mx-auto">
            Track your PSX portfolio, explore live market data, and use free financial calculators — all in one place.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link
              to="/login"
              className="flex items-center gap-2 px-6 py-3 rounded-xl bg-accent hover:bg-accent/90 text-white font-bold text-sm shadow-lg shadow-accent/25 transition-all hover:scale-[1.02]"
            >
              Start Tracking Free
              <ArrowRight size={16} />
            </Link>
            <Link
              to="/markets/stocks"
              className="flex items-center gap-2 px-6 py-3 rounded-xl bg-white/5 border border-white/10 text-soft hover:text-white hover:bg-white/10 font-semibold text-sm transition-all"
            >
              Explore Markets
            </Link>
          </div>
        </div>
      </section>

      {/* Markets quick links */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {MARKETS.map((m) => (
            <Link
              key={m.label}
              to={m.href}
              className="flex items-center gap-4 p-5 rounded-2xl bg-surface border border-border hover:border-accent/40 hover:bg-surface/80 transition-all group"
            >
              <div className="w-10 h-10 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                <m.icon size={18} className="text-accent" />
              </div>
              <div className="flex-1">
                <p className="text-white font-bold text-sm">{m.label}</p>
                <p className="text-muted text-xs">Live data</p>
              </div>
              <ChevronRight size={16} className="text-muted group-hover:text-accent transition-colors" />
            </Link>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
        <h2 className="text-2xl font-black text-white mb-8 text-center">Everything you need</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {FEATURES.map((f) => (
            <div key={f.title} className="bg-surface border border-border rounded-2xl p-6 space-y-3">
              <div className="w-9 h-9 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center">
                <f.icon size={16} className="text-accent" />
              </div>
              <h3 className="text-white font-bold text-sm">{f.title}</h3>
              <p className="text-muted text-xs leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Tools grid */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-black text-white">Free Financial Tools</h2>
          <Link to="/tools/sip" className="text-accent text-sm font-semibold hover:underline flex items-center gap-1">
            All tools <ArrowRight size={14} />
          </Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {TOOLS.map((t) => (
            <Link
              key={t.href}
              to={t.href}
              className="flex items-center justify-between p-5 rounded-2xl bg-surface border border-border hover:border-accent/40 hover:bg-surface/80 transition-all group"
            >
              <div>
                <p className="text-white font-bold text-sm">{t.label}</p>
                <p className="text-muted text-xs mt-0.5">{t.desc}</p>
              </div>
              <ChevronRight size={16} className="text-muted group-hover:text-accent transition-colors flex-shrink-0" />
            </Link>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">
        <div className="relative rounded-[2.5rem] bg-surface border border-border overflow-hidden p-12 text-center">
          <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-accent/5 rounded-full blur-[100px] -translate-y-1/2 translate-x-1/2 pointer-events-none" />
          <Zap size={32} className="text-accent mx-auto mb-4" />
          <h2 className="text-3xl font-black text-white mb-3">Ready to track your portfolio?</h2>
          <p className="text-muted text-sm mb-8 max-w-md mx-auto">
            Create a free account and start tracking your PSX investments with real-time data and powerful analytics.
          </p>
          <Link
            to="/login"
            className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-accent hover:bg-accent/90 text-white font-bold text-sm shadow-lg shadow-accent/25 transition-all hover:scale-[1.02]"
          >
            Get Started — It's Free
            <ArrowRight size={16} />
          </Link>
        </div>
      </section>
    </div>
  );
}
