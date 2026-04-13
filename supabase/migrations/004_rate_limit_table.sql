-- 004_rate_limit_table.sql
-- H-03: Persistent rate limiting table.
--
-- Replaces the in-memory RateLimitState singleton which reset on every deploy
-- and was incompatible with horizontal scaling. This table persists counters
-- across restarts and works correctly with multiple backend instances.
--
-- Uses a sliding window strategy: each row tracks the count and window_start
-- for a given key (ip:path). Rows older than the window are considered expired.
--
-- Cleanup is handled lazily on each request (no background job required).

CREATE TABLE IF NOT EXISTS rate_limit_counters (
  key          TEXT         NOT NULL,
  count        INTEGER      NOT NULL DEFAULT 1,
  window_start TIMESTAMPTZ  NOT NULL DEFAULT now(),
  PRIMARY KEY (key)
);

-- Index for fast TTL lookups during cleanup
CREATE INDEX IF NOT EXISTS idx_rate_limit_window ON rate_limit_counters (window_start);

-- RLS: this table is only accessible via service role (backend jobs only)
ALTER TABLE rate_limit_counters ENABLE ROW LEVEL SECURITY;

-- No user-facing policies: only service_role can read/write
-- (service_role bypasses RLS by design — correct for internal use)

COMMENT ON TABLE rate_limit_counters IS
  'H-03: Persistent sliding-window rate limit counters. '
  'Keyed by ip:path. Replaces volatile in-memory state.';
