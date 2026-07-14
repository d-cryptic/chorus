CREATE TABLE IF NOT EXISTS insight (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  scope TEXT NOT NULL,
  subject_id TEXT,
  term TEXT,
  payload TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0,
  evidence TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  fingerprint TEXT,
  created_at INTEGER NOT NULL,
  superseded_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_insight_live ON insight(status, kind, created_at DESC);
CREATE TABLE IF NOT EXISTS playbook (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  phase TEXT NOT NULL,
  doc TEXT NOT NULL,
  fingerprint TEXT,
  created_at INTEGER NOT NULL
);
