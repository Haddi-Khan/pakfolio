import { motion } from "framer-motion";

export function AuthLayout({ children }) {
  return (
    <div className="min-h-screen bg-bg flex">
      {/* Left side: branding/visual */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-surface-2 items-center justify-center border-r border-border">
        <div className="absolute inset-0 bg-mesh opacity-30" />
        <div className="absolute top-1/4 left-1/4 w-[400px] h-[400px] bg-accent/20 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 max-w-md px-8">
          <div className="w-16 h-16 rounded-2xl bg-surface-3/30 border border-border/50 flex items-center justify-center shadow-lg shadow-accent/10 overflow-hidden p-2 mb-8 glass">
            <img src="/logo.png" alt="Pakfolio" className="w-full h-full object-contain drop-shadow-lg" />
          </div>
          <h1 className="text-5xl font-bold text-[var(--color-text-primary)] mb-6 leading-tight">
            Elevate Your<br /><span className="gradient-text-blue">Portfolio</span>
          </h1>
          <p className="text-muted text-lg">
            Experience the next generation of investment tracking with advanced analytics and precise market synchronization.
          </p>
        </div>
      </div>

      {/* Right side: forms */}
      <div className="flex-1 flex items-center justify-center p-4 sm:p-8 relative">
        <div className="absolute top-1/4 right-1/4 w-[300px] h-[300px] bg-accent/5 rounded-full blur-3xl pointer-events-none" />

        <div className="w-full max-w-md relative z-10">
          {/* Logo for mobile */}
          <div className="flex lg:hidden items-center justify-center gap-3 mb-8">
            <div className="w-12 h-12 rounded-2xl bg-surface-3/30 border border-border/50 flex items-center justify-center shadow-lg shadow-accent/10 overflow-hidden p-2 glass">
              <img src="/logo.png" alt="Pakfolio" className="w-full h-full object-contain drop-shadow-lg" />
            </div>
            <div>
              <h1 className="text-[var(--color-text-primary)] font-bold text-2xl leading-none">Pakfolio</h1>
              <p className="text-muted text-xs leading-none mt-1">Premium Stock Tracker</p>
            </div>
          </div>

          {children}
        </div>
      </div>
    </div>
  );
}

export function AuthCard({ title, subtitle, children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -15 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="bg-surface border border-border rounded-2xl p-8 glass-card"
    >
      <div className="mb-6">
        <h2 className="text-[var(--color-text-primary)] font-bold text-2xl">{title}</h2>
        {subtitle && <p className="text-muted text-sm mt-1">{subtitle}</p>}
      </div>
      {children}
    </motion.div>
  );
}

export function AuthError({ children }) {
  if (!children) return null;
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-loss/10 border border-loss/30 rounded-xl px-4 py-3 text-loss text-sm font-medium"
    >
      {children}
    </motion.div>
  );
}
