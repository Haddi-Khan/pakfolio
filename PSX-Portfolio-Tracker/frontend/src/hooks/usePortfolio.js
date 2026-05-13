import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

export function usePortfolioSummary(pid) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    if (!pid) return;
    setLoading(true);
    try {
      const summary = await api.portfolio.summary(pid);
      setData(summary);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [pid]);

  useEffect(() => {
    setData(null);
    setLoading(true);
    fetch();
  }, [pid, fetch]);
  return { data, loading, error, refresh: fetch };
}

export function useHoldings(pid) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    if (!pid) return;
    setLoading(true);
    try {
      setData(await api.holdings.list(pid));
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [pid]);

  useEffect(() => {
    setData([]);
    setLoading(true);
    fetch();
  }, [pid, fetch]);
  return { data, loading, error, refresh: fetch };
}

export function useTrades(symbol, pid) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    if (!pid) return;
    setLoading(true);
    try {
      setData(await api.trades.list(symbol, pid));
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [symbol, pid]);

  useEffect(() => {
    setData([]);
    setLoading(true);
    fetch();
  }, [pid, fetch]);
  return { data, loading, error, refresh: fetch };
}

export function useChart(period, pid) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!pid) return;
    setData([]);
    setLoading(true);
    api.portfolio.chart(period, pid)
      .then(setData)
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [period, pid]);

  return { data, loading };
}

export function useCash(pid) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    if (!pid) return;
    setLoading(true);
    try {
      setData(await api.cash.list(pid));
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [pid]);

  useEffect(() => {
    setData([]);
    setLoading(true);
    fetch();
  }, [pid, fetch]);
  return { data, loading, error, refresh: fetch };
}
