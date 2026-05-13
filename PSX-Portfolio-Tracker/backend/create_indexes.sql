-- Run this in Supabase Dashboard → SQL Editor
-- CONCURRENTLY means no table lock — safe to run on live data

-- Primary fix: composite index on history_psx (symbol + date)
-- Without this, every chart query does a full table scan → timeout
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_history_psx_symbol_date
    ON public.history_psx (symbol, date DESC);

-- Bonus: index on just symbol for fast peer lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_history_psx_symbol_only
    ON public.history_psx (symbol);

-- Verify indexes were created:
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'history_psx';
