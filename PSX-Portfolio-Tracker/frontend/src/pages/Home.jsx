import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Plus,
  Briefcase,
  TrendingUp,
  BarChart3,
  PieChart,
  ArrowRight,
  ChevronRight,
  Sparkles,
  Search,
  LayoutGrid,
} from "lucide-react";
import { usePortfolioCtx } from "../context/PortfolioContext";
import { useAuth } from "../context/AuthContext";
import { motion } from "framer-motion";

export function Home() {
  const { user } = useAuth();
  const { portfolios, createPortfolio, loading } = usePortfolioCtx();
  const [isCreating, setIsCreating] = useState(false);
  const [newPortfolioName, setNewPortfolioName] = useState("");
  const [newPortfolioBalance, setNewPortfolioBalance] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newPortfolioName.trim()) return;
    setIsSubmitting(true);
    try {
      await createPortfolio(newPortfolioName, newPortfolioBalance);
      setNewPortfolioName("");
      setNewPortfolioBalance("");
      setIsCreating(false);
    } catch (err) {
      console.error("Failed to create portfolio", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-bg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12 fade-in w-full">
      {/* Hero Welcome */}
      <header className="relative py-12 px-8 rounded-[2.5rem] bg-surface border border-border overflow-hidden shadow-2xl">
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-accent/5 rounded-full blur-[100px] -translate-y-1/2 translate-x-1/2" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-gain/5 rounded-full blur-[80px] translate-y-1/2 -translate-x-1/2" />
        
        <div className="relative max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 border border-accent/20 text-accent text-xs font-bold uppercase tracking-widest mb-6">
            <Sparkles size={12} />
            Beta Access
          </div>
          <h1 className="text-4xl md:text-5xl font-black text-white mb-4 leading-tight">
            Assalam u Alaikum, <span className="text-accent">{user?.username || user?.email?.split('@')[0]}</span>
          </h1>
          <p className="text-muted text-lg leading-relaxed mb-8">
            Welcome to your Pakfolio command center. Track your investments in the Pakistan Stock Exchange with premium insights and real-time data.
          </p>
          
          <div className="flex flex-wrap gap-4">
            <button 
              onClick={() => setIsCreating(true)}
              className="btn-primary flex items-center gap-2 px-6 py-3"
            >
              <Plus size={18} />
              Create New Portfolio
            </button>
            <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-muted italic text-sm">
              <Search size={14} />
              <input 
                type="text" 
                placeholder="Search stocks..." 
                className="bg-transparent border-none outline-none focus:ring-0 w-32 md:w-48"
              />
            </div>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Portfolios List */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Briefcase size={20} className="text-accent" />
              Your Portfolios
            </h2>
            <span className="text-xs text-muted font-bold px-2 py-0.5 rounded-md bg-white/5">
              {portfolios.length} Total
            </span>
          </div>

          {portfolios.length === 0 ? (
            <div className="bg-surface border border-dashed border-border rounded-3xl p-12 text-center">
               <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto mb-4">
                 <Briefcase size={24} className="text-muted" />
               </div>
               <h3 className="text-white font-bold text-lg mb-2">No portfolios yet</h3>
               <p className="text-muted text-sm mb-6 max-w-xs mx-auto">
                 Start by creating your first portfolio to track your stocks and mutual funds.
               </p>
               <button 
                 onClick={() => setIsCreating(true)}
                 className="text-accent hover:text-soft text-sm font-bold flex items-center gap-2 mx-auto transition-colors"
               >
                 Create your first one <ArrowRight size={14} />
               </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {portfolios.map((p) => (
                <Link 
                  key={p.id} 
                  to={`/portfolio/${p.id}`}
                  className="group bg-surface border border-border hover:border-accent/40 rounded-2xl p-6 transition-all duration-300 hover:shadow-xl hover:shadow-accent/5 relative overflow-hidden"
                >
                  <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-100 transition-opacity">
                    <ChevronRight size={20} className="text-accent" />
                  </div>
                  <div className="w-10 h-10 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                    <LayoutGrid size={20} className="text-accent" />
                  </div>
                  <h3 className="text-white font-bold text-lg mb-1">{p.name}</h3>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-muted">Created {new Date(p.created_at).toLocaleDateString()}</span>
                    {p.is_default && (
                      <span className="text-[10px] uppercase font-black tracking-widest text-accent bg-accent/5 px-2 py-0.5 rounded border border-accent/10">Default</span>
                    )}
                  </div>
                </Link>
              ))}
              
              <button 
                onClick={() => setIsCreating(true)}
                className="border-2 border-dashed border-border rounded-2xl p-6 flex flex-col items-center justify-center text-muted hover:text-accent hover:border-accent/40 transition-all hover:bg-accent/5"
              >
                <Plus size={24} className="mb-2" />
                <span className="font-bold text-sm">Add Portfolio</span>
              </button>
            </div>
          )}
        </div>

        {/* Sidebar Insights */}
        <div className="space-y-6">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <TrendingUp size={20} className="text-gain" />
            Market Insights
          </h2>

          <div className="space-y-4">
            {/* Insights Placeholders */}
            <div className="bg-surface border border-border rounded-2xl p-6 relative overflow-hidden group">
               <div className="absolute top-0 right-0 p-4">
                  <span className="px-2 py-0.5 rounded bg-gain/10 text-gain text-[10px] font-black uppercase tracking-widest border border-gain/20">Coming Soon</span>
               </div>
               <BarChart3 size={24} className="text-muted mb-4" />
               <h3 className="text-white font-bold mb-2">Market Analysis</h3>
               <p className="text-muted text-sm leading-relaxed">
                 Aggregate data on PSX performance, index movers, and sector-wise rotation analysis.
               </p>
            </div>

            <div className="bg-surface border border-border rounded-2xl p-6 relative overflow-hidden group">
               <div className="absolute top-0 right-0 p-4">
                  <span className="px-2 py-0.5 rounded bg-accent/10 text-accent text-[10px] font-black uppercase tracking-widest border border-accent/20">Coming Soon</span>
               </div>
               <PieChart size={24} className="text-muted mb-4" />
               <h3 className="text-white font-bold mb-2">Smart Rebalancing</h3>
               <p className="text-muted text-sm leading-relaxed">
                 AI-powered insights to help you stay within your target asset allocation.
               </p>
            </div>
          </div>
        </div>
      </div>

      {/* Create Modal */}
      {isCreating && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-bg/80 backdrop-blur-md" onClick={() => setIsCreating(false)} />
          <motion.div 
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            className="w-full max-w-md relative bg-surface border border-border rounded-[2rem] p-8 shadow-2xl"
          >
            <h2 className="text-2xl font-bold text-white mb-2">Create Portfolio</h2>
            <p className="text-muted text-sm mb-8">Let's give your new portfolio a name to get started.</p>
            
            <form onSubmit={handleCreate} className="space-y-6">
              <div>
                <label className="text-muted text-xs font-semibold uppercase tracking-widest mb-2 block">Portfolio Name</label>
                <input 
                  autoFocus
                  type="text" 
                  value={newPortfolioName}
                  onChange={(e) => setNewPortfolioName(e.target.value)}
                  placeholder="e.g. Long Term Savings"
                  className="input text-lg"
                  required
                />
              </div>

              <div>
                <label className="text-muted text-xs font-semibold uppercase tracking-widest mb-2 block">Starting Balance (PKR)</label>
                <input 
                  type="number" 
                  step="0.01"
                  value={newPortfolioBalance}
                  onChange={(e) => setNewPortfolioBalance(e.target.value)}
                  placeholder="0.00"
                  className="input text-lg mono"
                />
                <p className="text-[10px] text-muted mt-2 italic px-1">This will be added as an initial deposit to your portfolio.</p>
              </div>

              <div className="flex gap-3">
                <button 
                  type="button" 
                  onClick={() => setIsCreating(false)}
                  className="flex-1 px-6 py-3 rounded-xl bg-white/5 border border-white/10 text-white font-bold hover:bg-white/10 transition-colors"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  disabled={isSubmitting || !newPortfolioName.trim()}
                  className="flex-[2] btn-primary px-6 py-3"
                >
                  {isSubmitting ? "Creating..." : "Create Portfolio"}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
      </div>
    </div>
  );
}
