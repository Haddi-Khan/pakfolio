/**
 * API client — all HTTP calls in one place.
 * BASE_URL can be swapped via env var for production.
 */

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function getToken() {
  return localStorage.getItem("pakfolio_access_token");
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  if (res.status === 204) return null;
  return res.json();
}

function withPid(path, pid) {
  const sep = path.includes("?") ? "&" : "?";
  return pid ? `${path}${sep}portfolio_id=${pid}` : path;
}

export const api = {
  // ── Auth (no token needed for login/register) ───────────────────────────
  auth: {
    register: (email, password) =>
      request("/api/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
    login: (email, password) =>
      request("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
    loginSocial: (provider, token) =>
      request(`/api/auth/social/${provider}`, { method: "POST", body: JSON.stringify({ token }) }),
    refresh: (refresh_token) =>
      request("/api/auth/refresh", { method: "POST", body: JSON.stringify({ refresh_token }) }),
    me: () => request("/api/auth/me"),
    verify: (token) => request(`/api/auth/verify?token=${token}`),
    forgotPassword: (email) =>
      request("/api/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) }),
    resetPassword: (token, new_password) =>
      request("/api/auth/reset-password", { method: "POST", body: JSON.stringify({ token, new_password }) }),
    resendVerification: (email) =>
      request("/api/auth/resend-verification", { method: "POST", body: JSON.stringify({ username_or_email: email }) }),
  },

  // ── Portfolios ──────────────────────────────────────────────────────────
  portfolios: {
    list: () => request("/api/portfolios"),
    create: (data) => request("/api/portfolios", { method: "POST", body: JSON.stringify(data) }),
    get: (pid) => request(`/api/portfolios/${pid}`),
    setDefault: (pid) => request(`/api/portfolios/${pid}/set-default`, { method: "POST" }),
    delete: (pid) => request(`/api/portfolios/${pid}`, { method: "DELETE" }),
  },

  portfolio: {
    summary: (pid) => request(withPid("/api/portfolio/summary", pid)),
    chart: (period = "1M", pid) => request(withPid(`/api/portfolio/chart?period=${period}`, pid)),
  },

  holdings: {
    list: (pid) => request(withPid("/api/holdings", pid)),
  },

  trades: {
    list: (symbol, pid) => request(withPid(`/api/trades${symbol ? `?symbol=${symbol}` : ""}`, pid)),
    add: (trade, pid) => request(withPid("/api/trades", pid), { method: "POST", body: JSON.stringify(trade) }),
    remove: (id) => request(`/api/trades/${id}`, { method: "DELETE" }),
    export: async (pid) => {
      const token = getToken();
      const res = await fetch(`${BASE_URL}${withPid("/api/trades/export", pid)}`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Export failed");
      return res.blob();
    },
    import: (pid, file) => {
      const formData = new FormData();
      formData.append("file", file);
      const token = getToken();
      // We don't use 'request' here because it forces JSON content-type
      return fetch(`${BASE_URL}${withPid("/api/trades/import", pid)}`, {
        method: "POST",
        body: formData,
        headers: { "Authorization": `Bearer ${token}` }
      }).then(res => res.json());
    },
  },

  cash: {
    balance: (pid) => request(withPid("/api/cash/balance", pid)),
    list: (pid) => request(withPid("/api/cash", pid)),
    add: (tx, pid) => request(withPid("/api/cash", pid), { method: "POST", body: JSON.stringify(tx) }),
  },

  prices: {
    quote: (symbol) => request(`/api/prices/${symbol}`),
    bulk: (symbols) => request("/api/prices/bulk", { method: "POST", body: JSON.stringify(symbols) }),
    history: (symbol, from, to) => request(`/api/prices/${symbol}/history?from=${from}&to=${to}`),
  },

  symbols: {
    search: (q) => request(`/api/symbols/search?q=${encodeURIComponent(q)}`),
    all: () => request("/api/symbols"),
    fundamentals: (symbol) => request(`/api/stocks/${symbol}/fundamentals`),
    peers: (symbol) => request(`/api/stocks/${symbol}/peers`),
  },
  markets: {
    summary: () => request("/api/markets/summary"),
    movers: (type) => request(`/api/markets/movers?type=${type}`),
  },
};
