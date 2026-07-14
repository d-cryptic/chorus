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
  -- router decision (v0 'the spine'): reply | quote | retweet. A retweet row
  -- carries NO drafts - just a rationale for why it is worth amplifying.
  target         TEXT NOT NULL DEFAULT 'reply',
  gif            TEXT,                          -- Giphy SEARCH phrase (v0: search, never generate)
  thread         TEXT,                          -- JSON array; only when the take needs >280 chars

  status         TEXT NOT NULL DEFAULT 'queued', -- queued|posted|dismissed|snoozed|expired
  created_at     INTEGER NOT NULL,
  expires_at     INTEGER,
  snooze_until   INTEGER,                        -- F8: real snooze
  acted_at       INTEGER,
  final_text     TEXT,                           -- what you actually posted (for voice edit-diff)
  posted_url     TEXT,                           -- URL of the reply you posted (for outcome-track)
  dismiss_reason TEXT,
  draft_index    INTEGER            -- which of the 2-3 drafts you actually picked
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
  quiet_hours TEXT, denylist TEXT,
  -- killed = global kill-switch: absolute, independent of budget, beats `paused`.
  -- `paused` is a soft/resumable stop; `killed` halts every paid call immediately.
  killed INTEGER NOT NULL DEFAULT 0,
  -- L0 suggest-only | L1 draft-and-queue (effective max: Chorus has no write lane).
  -- L2/L3 are refused at the enforcement point - they need outward actions.
  autonomy_level TEXT NOT NULL DEFAULT 'L1'
);
INSERT OR IGNORE INTO settings (id) VALUES (1);

-- G5: one row per cycle → dashboard heartbeat ("last cycle 2h ago · 14 suggested").
CREATE TABLE IF NOT EXISTS run_log (
  -- credits = provider balance at cycle start. This is the meter that ACTUALLY binds:
  -- daily_ceiling_usd counts our own estimate, and 100k credits = $1, so a $0.65 ceiling
  -- is 65k credits/day. Surfacing it is how you see real runway.
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at INTEGER NOT NULL, finished_at INTEGER, suggested INTEGER, error TEXT
);

-- Typed insights (v0 nakama insights spec). Deterministic id = hash(kind|scope|subject)
-- so a re-run SUPERSEDES rather than duplicating. confidence=0 + payload.state=
-- 'insufficient_data' is a first-class, honest result: at low n we refuse to claim.
CREATE TABLE IF NOT EXISTS insight (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  scope TEXT NOT NULL,
  subject_id TEXT,
  term TEXT,
  payload TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0,
  evidence TEXT,
  status TEXT NOT NULL DEFAULT 'active',   -- active|superseded|decayed|archived
  fingerprint TEXT,
  created_at INTEGER NOT NULL,
  superseded_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_insight_live ON insight(status, kind, created_at DESC);

-- L3 synthesis output. Only written when the L1 fingerprint MOVED (change-gating),
-- so a quiet week costs $0 in LLM spend.
CREATE TABLE IF NOT EXISTS playbook (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  phase TEXT NOT NULL,                     -- cold_start|traction|compounding
  doc TEXT NOT NULL,
  fingerprint TEXT,
  created_at INTEGER NOT NULL
);
