import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api/client";

const Ctx = createContext(null);

export function PortfolioProvider({ children }) {
  const { pid } = useParams();
  const navigate = useNavigate();

  const [portfolios, setPortfolios] = useState([]);
  const [activePid, setActivePidState] = useState(pid ? parseInt(pid) : null);
  const [loading, setLoading] = useState(true);

  // Sync state if URL changes
  useEffect(() => {
    if (pid) {
      const numericPid = parseInt(pid);
      if (activePid !== numericPid) {
        setActivePidState(numericPid);
      }
    }
  }, [pid, activePid]);

  const setActivePid = useCallback((newPid) => {
    if (!newPid) return;
    navigate(`/portfolio/${newPid}`);
  }, [navigate]);

  const loadPortfolios = useCallback(async () => {
    try {
      const list = await api.portfolios.list();
      setPortfolios(list);
      // Only auto-select if we specifically don't have a PID in URL
      // but we actually WANT to auto-redirect (e.g. legacy behavior or specific flag)
      // For now, let's keep it simple: Home page handles the empty state.
      if (!pid && list.length > 0) {
        // We can optionally set a default here, but App.jsx will decide to show Home or Redirect
      }
    } catch { }
    finally { setLoading(false); }
  }, [pid]);

  useEffect(() => { loadPortfolios(); }, []);

  const activePortfolio = portfolios.find((p) => p.id === activePid) ?? null;

  async function createPortfolio(name, initialBalance = 0, description = "") {
    const p = await api.portfolios.create({ 
      name, 
      description,
      initial_balance: parseFloat(initialBalance) || 0 
    });
    setPortfolios((prev) => [...prev, p]);
    setActivePid(p.id);
    return p;
  }

  async function deletePortfolio(pid) {
    await api.portfolios.delete(pid);
    const remaining = portfolios.filter((p) => p.id !== pid);
    setPortfolios(remaining);
    if (activePid === pid) {
      setActivePid(remaining[0]?.id ?? null);
    }
  }

  async function setDefault(pid) {
    const p = await api.portfolios.setDefault(pid);
    setPortfolios((prev) => prev.map((x) => ({ ...x, is_default: x.id === pid })));
    setActivePid(pid);
    return p;
  }

  return (
    <Ctx.Provider value={{
      portfolios, activePid, setActivePid,
      activePortfolio, loading,
      createPortfolio, deletePortfolio, setDefault,
      refresh: loadPortfolios,
    }}>
      {children}
    </Ctx.Provider>
  );
}

export function usePortfolioCtx() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("usePortfolioCtx must be inside PortfolioProvider");
  return ctx;
}
