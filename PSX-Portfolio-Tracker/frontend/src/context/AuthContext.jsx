import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

const AuthCtx = createContext(null);

const ACCESS_KEY = "pakfolio_access_token";
const REFRESH_KEY = "pakfolio_refresh_token";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // On mount: try to restore session from stored tokens
  useEffect(() => {
    const token = localStorage.getItem(ACCESS_KEY);
    if (!token) {
      setLoading(false);
      return;
    }
    api.auth.me()
      .then(setUser)
      .catch(() => {
        // Access token expired — try refresh
        const rt = localStorage.getItem(REFRESH_KEY);
        if (!rt) { setLoading(false); return; }
        return api.auth.refresh(rt)
          .then((tokens) => {
            _saveTokens(tokens);
            return api.auth.me();
          })
          .then(setUser)
          .catch(() => _clearTokens());
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const tokens = await api.auth.login(email, password);
    _saveTokens(tokens);
    const me = await api.auth.me();
    setUser(me);
    return me;
  }, []);

  const register = useCallback(async (email, password) => {
    // With email verification, register no longer returns tokens
    const res = await api.auth.register(email, password);
    return res;
  }, []);

  const loginSocial = useCallback(async (provider, token) => {
    const tokens = await api.auth.loginSocial(provider, token);
    _saveTokens(tokens);
    const me = await api.auth.me();
    setUser(me);
    return me;
  }, []);

  const logout = useCallback(() => {
    _clearTokens();
    setUser(null);
  }, []);

  const forgotPassword = useCallback((email) => api.auth.forgotPassword(email), []);
  const resetPassword = useCallback((token, newPassword) => api.auth.resetPassword(token, newPassword), []);

  return (
    <AuthCtx.Provider value={{ user, loading, login, loginSocial, register, logout, forgotPassword, resetPassword }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}

export function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY);
}

function _saveTokens(tokens) {
  localStorage.setItem(ACCESS_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

function _clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}
