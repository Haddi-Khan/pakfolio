import { useState, useRef, useEffect } from "react";
import { ChevronDown, Plus, Check, Trash2, Briefcase } from "lucide-react";
import { usePortfolioCtx } from "../context/PortfolioContext";

export function PortfolioSwitcher() {
  const { portfolios, activePid, setDefault, activePortfolio, createPortfolio, deletePortfolio } = usePortfolioCtx();
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const ref = useRef(null);

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    if (!newName.trim()) return;
    await createPortfolio(newName.trim());
    setNewName("");
    setCreating(false);
    setOpen(false);
  }

  async function handleDelete(e, pid) {
    e.stopPropagation();
    if (portfolios.length <= 1) return;
    if (!confirm("Delete this portfolio and all its trades?")) return;
    await deletePortfolio(pid);
    setOpen(false);
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 px-3 py-2 rounded-xl border border-border-2 bg-surface-2 hover:bg-surface-3 transition-all text-sm"
      >
        <Briefcase size={13} className="text-accent" />
        <span className="text-white font-semibold max-w-[120px] truncate">
          {activePortfolio?.name ?? "Select Portfolio"}
        </span>
        <ChevronDown size={12} className={`text-muted transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute left-0 top-full mt-2 w-64 bg-surface-3 border border-border-2 rounded-2xl shadow-2xl z-50 overflow-hidden fade-in">
          <div className="px-3 py-2 border-b border-border">
            <p className="text-muted text-xs font-semibold uppercase tracking-widest">Portfolios</p>
          </div>

          <div className="max-h-60 overflow-y-auto">
            {portfolios.map((p) => (
              <div
                key={p.id}
                onClick={() => { setDefault(p.id); setOpen(false); }}
                className="flex items-center justify-between px-3 py-2.5 hover:bg-surface-2 cursor-pointer group transition-colors"
              >
                <div className="flex items-center gap-2 min-w-0">
                  {p.id === activePid
                    ? <Check size={13} className="text-accent shrink-0" />
                    : <div className="w-3.5 h-3.5 shrink-0" />
                  }
                  <div className="min-w-0">
                    <div className={`text-sm font-semibold truncate ${p.id === activePid ? "text-accent" : "text-white"}`}>{p.name}</div>
                    {p.description && <div className="text-xs text-muted truncate">{p.description}</div>}
                  </div>
                </div>
                {portfolios.length > 1 && (
                  <button
                    onClick={(e) => handleDelete(e, p.id)}
                    className="opacity-0 group-hover:opacity-100 text-muted hover:text-loss transition-all ml-2 shrink-0"
                  >
                    <Trash2 size={12} />
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className="border-t border-border p-2">
            {creating ? (
              <form onSubmit={handleCreate} className="flex gap-2">
                <input
                  autoFocus
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Portfolio name"
                  className="flex-1 bg-surface border border-border-2 rounded-lg px-3 py-1.5 text-white text-sm placeholder-muted outline-none focus:border-accent"
                />
                <button
                  type="submit"
                  className="px-3 py-1.5 bg-accent rounded-lg text-white text-sm font-semibold hover:opacity-90"
                >
                  Add
                </button>
              </form>
            ) : (
              <button
                onClick={() => setCreating(true)}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-soft hover:text-white hover:bg-surface-2 transition-all text-sm"
              >
                <Plus size={13} />
                New Portfolio
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
