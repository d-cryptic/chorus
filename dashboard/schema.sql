-- Chorus queue store (Cloudflare D1). M0 backend (M1 = Convex, see docs/data-architecture.md).
-- opportunity-rank writes via the Worker's token-authed ingest; the dashboard reads.

CREATE TABLE IF NOT EXISTS suggestion (
  id             TEXT PRIMARY KEY,
  tweet_id       TEXT NOT NULL,
  tweet_url      TEXT,                          -- FE2: link + intent-url target
  tweet_text     TEXT NOT NULL,
  author_handle  TEXT NOT NULL,
  author_tier    TEXT,
  score          REAL NOT NULL,
  factors        TEXT,
  pillar         TEXT,
  angle          TEXT,
  drafts         TEXT,
  rationale      TEXT,
  status         TEXT NOT NULL DEFAULT 'queued', -- queued|posted|dismissed|snoozed|expired
  created_at     INTEGER NOT NULL,
  expires_at     INTEGER,
  snooze_until   INTEGER,                        -- F8: real snooze
  acted_at       INTEGER,
  final_text     TEXT,                           -- what you actually posted (for voice edit-diff)
  posted_url     TEXT,                           -- URL of the reply you posted (for outcome-track)
  dismiss_reason TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_suggestion_tweet ON suggestion(tweet_id); -- F8: no dupes
CREATE INDEX IF NOT EXISTS idx_suggestion_status_score ON suggestion(status, score DESC);

CREATE TABLE IF NOT EXISTS feedback (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  suggestion_id TEXT NOT NULL,
  action        TEXT NOT NULL,                   -- posted|posted_edited|dismissed|snoozed
  final_text    TEXT,                            -- F9: was misnamed edit_diff
  reason        TEXT,
  ts            INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS spend_ledger (
  id     INTEGER PRIMARY KEY AUTOINCREMENT,
  day    TEXT NOT NULL, source TEXT NOT NULL, usd REAL NOT NULL, ts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_spend_day ON spend_ledger(day);

-- FE1: how a posted reply actually performed → real reward for rank-tune.
CREATE TABLE IF NOT EXISTS outcome (
  suggestion_id TEXT PRIMARY KEY,
  likes INTEGER, replies INTEGER, profile_clicks INTEGER, measured_at INTEGER
);

-- G1: where rank-tune writes learned weights and opportunity-rank reads them at run start.
CREATE TABLE IF NOT EXISTS weights (
  key TEXT PRIMARY KEY, value REAL NOT NULL, updated_at INTEGER
);

-- FE4: single-row operational settings the daily cycle reads before doing anything.
CREATE TABLE IF NOT EXISTS settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  paused INTEGER NOT NULL DEFAULT 0,
  daily_ceiling_usd REAL NOT NULL DEFAULT 0.65,
  quiet_hours TEXT, denylist TEXT
);
INSERT OR IGNORE INTO settings (id) VALUES (1);

-- G5: one row per cycle → dashboard heartbeat ("last cycle 2h ago · 14 suggested").
CREATE TABLE IF NOT EXISTS run_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at INTEGER NOT NULL, finished_at INTEGER, suggested INTEGER, error TEXT
);
