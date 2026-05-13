import { useState, useRef, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import {
  ChevronDown,
  TrendingUp,
  PieChart,
  BarChart3,
  Calculator,
  Briefcase,
  LogOut,
  User,
  Moon,
  Sun,
  Menu,
  X,
  Building2,
  Layers,
  ArrowUpDown,
  Percent,
  Coins,
  RefreshCcw,
  Scale,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

const MARKETS_MENU = [
  {
    group: "Equities",
    items: [
      { label: "Stocks", href: "/markets/stocks", icon: TrendingUp, desc: "PSX listed companies" },
      { label: "Sectors", href: "/markets/sectors", icon: Building2, desc: "Sector-wise breakdown" },
    ],
  },
  {
    group: "Funds",
    items: [
      { label: "Mutual Funds", href: "/markets/mutual-funds", icon: Layers, desc: "Open & closed-end funds" },
      { label: "ETFs", href: "/markets/etfs", icon: BarChart3, desc: "Exchange traded funds" },
    ],
  },
  {
    group: "Indices",
    items: [
      { label: "KSE-100", href: "/stocks/KSE100", icon: ArrowUpDown, desc: "Pakistan's benchmark index" },
    ],
  },
];

const TOOLS_MENU = [
  {
    group: "Investment",
    items: [
      { label: "SIP Calculator", href: "/tools/sip", icon: RefreshCcw, desc: "Systematic investment plan" },
      { label: "Compounding", href: "/tools/compounding", icon: Percent, desc: "Compound interest growth" },
      { label: "CAGR Calculator", href: "/tools/cagr", icon: TrendingUp, desc: "Annualized growth rate" },
      { label: "ROI Calculator", href: "/tools/roi", icon: BarChart3, desc: "Return on investment" },
    ],
  },
  {
    group: "Pakistan Specific",
    items: [
      { label: "Zakat Calculator", href: "/tools/zakat", icon: Scale, desc: "Annual zakat on assets" },
      { label: "Brokerage Deduction", href: "/tools/brokerage", icon: Coins, desc: "PSX trade cost breakdown" },
    ],
  },
];

function MegaMenu({ groups, onClose }) {
  return (
    <div className="absolute top-full left-0 mt-2 w-[480px] bg-surface border border-border rounded-2xl shadow-2xl shadow-black/40 p-4 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
      <div className="grid grid-cols-2 gap-4">
        {groups.map((group) => (
          <div key={group.group}>
            <p className="text-[10px] font-black uppercase tracking-widest text-muted mb-2 px-1">{group.group}</p>
            <div className="space-y-0.5">
              {group.items.map((item) => (
                <Link
                  key={item.label}
                  to={item.href}
                  onClick={onClose}
                  className="flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-white/5 transition-colors group"
                >
                  <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/5 flex items-center justify-center flex-shrink-0 group-hover:bg-accent/10 group-hover:border-accent/20 transition-colors">
                    <item.icon size={14} className="text-muted group-hover:text-accent transition-colors" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-soft group-hover:text-white transition-colors leading-tight">{item.label}</p>
                    <p className="text-[11px] text-muted leading-tight">{item.desc}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function NavDropdown({ label, groups }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onMouseEnter={() => setOpen(true)}
        onClick={() => setOpen((v) => !v)}
        className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-semibold transition-colors ${
          open ? "text-white bg-white/5" : "text-muted hover:text-white hover:bg-white/5"
        }`}
      >
        {label}
        <ChevronDown size={14} className={`transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
      </button>
      {open && <MegaMenu groups={groups} onClose={() => setOpen(false)} />}
    </div>
  );
}

export function Navbar() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="sticky top-0 z-40 w-full border-b border-border bg-surface/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Logo */}
          <div className="flex items-center gap-6">
            <Link to="/" className="flex items-center gap-2.5 group">
              <div className="w-8 h-8 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center p-1 group-hover:border-accent/30 transition-colors">
                <img src="/logo.png" alt="Pakfolio" className="w-full h-full object-contain" />
              </div>
              <span className="text-white font-black text-sm tracking-tight">Pakfolio</span>
            </Link>

            {/* Desktop Nav */}
            <div className="hidden md:flex items-center gap-1">
              <NavDropdown label="Markets" groups={MARKETS_MENU} />
              <NavDropdown label="Tools" groups={TOOLS_MENU} />

              {user && (
                <Link
                  to="/dashboard"
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-semibold transition-colors ${
                    isActive("/dashboard") ? "text-white bg-white/5" : "text-muted hover:text-white hover:bg-white/5"
                  }`}
                >
                  <Briefcase size={14} />
                  Portfolio
                </Link>
              )}
            </div>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-2">
            <button
              onClick={toggleTheme}
              className="w-8 h-8 rounded-xl flex items-center justify-center text-muted hover:text-white hover:bg-white/5 transition-all"
              title="Toggle theme"
            >
              {theme === "dark" ? <Moon size={14} /> : <Sun size={14} />}
            </button>

            {user ? (
              <div className="hidden md:flex items-center gap-2">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 border border-white/5">
                  <div className="w-5 h-5 rounded-full bg-surface-3 border border-border flex items-center justify-center">
                    <User size={10} className="text-muted" />
                  </div>
                  <span className="text-xs text-soft font-medium max-w-[120px] truncate">
                    {user.username || user.email?.split("@")[0]}
                  </span>
                </div>
                <button
                  onClick={logout}
                  className="w-8 h-8 rounded-xl flex items-center justify-center text-muted hover:text-loss hover:bg-white/5 transition-all"
                  title="Sign out"
                >
                  <LogOut size={14} />
                </button>
              </div>
            ) : (
              <div className="hidden md:flex items-center gap-2">
                <Link
                  to="/login"
                  className="px-4 py-1.5 rounded-xl text-sm font-semibold text-muted hover:text-white hover:bg-white/5 transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  to="/login"
                  className="px-4 py-1.5 rounded-xl text-sm font-bold bg-accent hover:bg-accent/80 text-white transition-colors"
                >
                  Get Started
                </Link>
              </div>
            )}

            {/* Mobile hamburger */}
            <button
              className="md:hidden w-8 h-8 rounded-xl flex items-center justify-center text-muted hover:text-white hover:bg-white/5 transition-all"
              onClick={() => setMobileOpen((v) => !v)}
            >
              {mobileOpen ? <X size={16} /> : <Menu size={16} />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden border-t border-border bg-surface px-4 py-4 space-y-1">
          <p className="text-[10px] font-black uppercase tracking-widest text-muted px-2 mb-2">Markets</p>
          {MARKETS_MENU.flatMap((g) => g.items).map((item) => (
            <Link
              key={item.label}
              to={item.href}
              onClick={() => setMobileOpen(false)}
              className="flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-white/5 text-sm text-soft hover:text-white transition-colors"
            >
              <item.icon size={14} />
              {item.label}
            </Link>
          ))}
          <div className="border-t border-border my-2" />
          <p className="text-[10px] font-black uppercase tracking-widest text-muted px-2 mb-2">Tools</p>
          {TOOLS_MENU.flatMap((g) => g.items).map((item) => (
            <Link
              key={item.label}
              to={item.href}
              onClick={() => setMobileOpen(false)}
              className="flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-white/5 text-sm text-soft hover:text-white transition-colors"
            >
              <item.icon size={14} />
              {item.label}
            </Link>
          ))}
          {user && (
            <>
              <div className="border-t border-border my-2" />
              <Link
                to="/dashboard"
                onClick={() => setMobileOpen(false)}
                className="flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-white/5 text-sm text-soft hover:text-white transition-colors"
              >
                <Briefcase size={14} />
                My Portfolio
              </Link>
              <button
                onClick={() => { logout(); setMobileOpen(false); }}
                className="flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-white/5 text-sm text-loss w-full text-left transition-colors"
              >
                <LogOut size={14} />
                Sign Out
              </button>
            </>
          )}
          {!user && (
            <>
              <div className="border-t border-border my-2" />
              <Link
                to="/login"
                onClick={() => setMobileOpen(false)}
                className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold bg-accent text-white w-full"
              >
                Sign In / Get Started
              </Link>
            </>
          )}
        </div>
      )}
    </nav>
  );
}
