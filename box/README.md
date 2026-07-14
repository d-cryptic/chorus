# Chorus box — the ranker (product core)

`ranker.py` is the actual product: candidates → **gate** → cheap **heuristic pre-score** →
top-K → **one LLM call each** (angle + drafts) → `POST /api/box/ingest`. Suggest-only — never
posts to X. Two-stage so the LLM only touches survivors (budget-safe). Verified end-to-end
against the local Worker (ranker → queue → run_log heartbeat).

## Run
```bash
export INGEST_URL=https://chorus-app.barundebnath.com INGEST_TOKEN=...  # the Worker + box token
export OPENROUTER_API_KEY=... OPENROUTER_MODEL=deepseek/deepseek-chat
export CHORUS_PILLARS="leverage,writing,priorities" CHORUS_HANDLE=you CHORUS_VOICE="concise, specific"
python3 ranker.py --input candidates.json            # live: posts to /api/box/ingest
python3 ranker.py --input candidates.json --dry-run  # no network; prints what would queue
# flags: --tau 0.6  --cap 25  --topk 50  --denylist nsfw giveaway airdrop
```

## Candidates format
List of `{id, text, author, author_tier (A|B|C), ts (epoch MS — MUST be recent), url,
impressions_per_min, reply_count}`. **`ts` is epoch milliseconds**; stale (>48h) tweets are
gated out — `candidates.example.json` uses `ts:0` only as a shape example.
v1 feeds candidates via `--input`. **TODO:** wire the private X read adapter (target-lists +
keyword search + mentions — NOT the home timeline; X read adapter has no user auth). Do this after
M0.5 (validate Hermes) per docs/review-actions.md.

## Tests
```bash
python3 test_ranker.py   # 10 pure-logic assertions (gate / pre_score / prerank / finalize), no network
```
Caught a real ms→hours unit bug during integration. Live-verified: ranker → /api/box/ingest → queue.

## Config
Copy `.env.example` → `box/.env` (git-ignored), fill in, then `set -a; source box/.env; set +a`.

## Running the M0 cycle
The daily cycle is just cron running these scripts (`crontab.example`) — no HTTP cycle-runner /
`HERMES_CYCLE_URL` needed for v1 (that's the frozen M1 approach). ranker → digest → mirror on a
schedule.

## Feature scripts (build-complete; test when deployed)
- `telegram_bot.py` — interactive bot: /queue + posted/snooze/dismiss buttons + open-reply URL (daemon; Telegram deferred).
- `enrich.py` — cross-platform enrichment (GitHub/HN/Reddit) -> Supermemory. Live-verified (GitHub+HN).
- `voice_refine.py` — refine chorus:self voice from your ACTUAL posted replies (weekly).
- `outcome_track.py` — measure posted replies' metrics -> /api/box/outcome -> rank-tune (needs posted_url + local adapter lookup).
- `backup.py` — nightly D1 export (14-day retention).
- `embed.py` — optional semantic pillar relevance (EMBED_PILLARS=1; one batched call).
- Mutuals weighting: ranker boosts accounts that follow you back (relationship factor, from targets.json).

## Other box scripts
- `mirror_feedback.py` — reads new feedback (`GET /api/box/feedback`) and mirrors it to Supermemory
  `chorus:self` (M0 personalization loop). `--dry-run` tested; verify `SUPERMEMORY_ADD_URL` vs SDK.
- `digest.py` — daily Telegram digest + heartbeat (`GET /api/box/digest` → Telegram sendMessage).
  `format_digest` unit-tested offline (populated + empty/alert). Needs `TELEGRAM_BOT_TOKEN`/`_CHAT_ID`.

## research (swappable)
`research.py` — swappable search layer for research-digest. `RESEARCH_PROVIDER=linkup` (default,
`LINKUP_API_KEY`) or `firecrawl` (`FIRECRAWL_API_KEY`). Normalized `[{title,url,content}]`; the
response mappers are unit-tested. Add a provider = add one class + a PROVIDERS entry.

## Supermemory / memory (self-hosted)
`mirror_feedback.py`/`onboard.py`/`enrich.py`/`voice_refine.py` write memory to
`SUPERMEMORY_BASE_URL` (default `http://localhost:8000`, key optional). The box runs
**`memory_service.py`** — a tiny Supermemory-API-compatible store (stdlib + SQLite, no
deps, bound to 127.0.0.1) implementing the `/v3/documents` surface Chorus uses
(POST store, GET/`?containerTags=` list, DELETE by tag, POST `/v3/search`). Runs as the
`chorus-memory` systemd unit (`MEMORY_DB=/opt/chorus/memory.db`). Drop-in swap for upstream
`github.com/supermemoryai/supermemory`: just point `SUPERMEMORY_BASE_URL` at it.

## Cloudflare Bot Fight Mode / User-Agent
The Worker sits behind Cloudflare, which **403s the default `Python-urllib` User-Agent**.
Every box→Worker request sets `User-Agent: chorus-box/1.0` so the write path (ingest, spend,
weights, run-log, feedback) is not silently blocked. Keep the header when adding new callers.

## notify (swappable — Telegram / WhatsApp / console)
`notify.py` — `NOTIFY_PROVIDER = telegram | whatsapp | console`. digest.py calls `notify.send()`.
- **telegram**: bot sendMessage (simplest, free) — recommended for v1.
- **whatsapp**: POST to `WHATSAPP_WEBHOOK_URL` — route via a Hermes WhatsApp connector or a bridge
  (WhatsApp Business API needs Meta approval; unofficial bridges carry ban risk).
- **console**: print (default).

## Live-verified adapters
- **the private X read adapter** ✅ — fetched 20 real `@elonmusk` tweets, `map_tweet` mapped all correctly.
- **Linkup** ✅ — real `/v1/search` results normalized. Swap via `RESEARCH_PROVIDER`.

## Telegram digest — DEFERRED (v1)
`digest.py` is built + tested but OFF for v1 (no Telegram creds yet). Enable later with
`TELEGRAM_BOT_TOKEN`/`_CHAT_ID`. Heartbeat still visible in the dashboard header.

## onboard-self
`onboard.py` — fetch your X history (X read adapter `from:you`) → LLM synthesize pillars+voice →
Supermemory `chorus:self`. Dry-run tested. Run once before the first ranker cycle.

## X read adapter
`ranker.py --targets` (from `CHORUS_TARGETS_A/B`) or `--query '<advanced search>'` fetches via
`GET /twitter/tweet/candidate-search` (the adapter key header), maps the real response schema
(`{tweets:[{id,text,author.userName,createdAt,replyCount,viewCount,url}]}`) → candidates.
`map_tweet`/`_parse_ts` unit-tested; live fetch verified at deploy (needs the key).

## Deploy
See [../docs/runbook-deploy.md](../docs/runbook-deploy.md) — the live wiring you run with your creds.

## Design notes
- Weights loaded from `GET /api/box/weights` (rank-tune output); budget/ceiling/pause from
  `GET /api/box/spend` + `/api/box/settings`; run bracketed with `/api/box/run-log`.
- No embeddings in v1 — keyword pillar match + tier + freshness + upside − saturation is enough.
- LLM step has a deterministic fallback when `OPENROUTER_API_KEY` is unset (un-voiced drafts) so
  `--dry-run` and testing work offline.

## Budget guard, kill-switch, autonomy (`budget.py`)

Ports the v0 nakama `BudgetTracker` semantics — see `docs/v0-parity.md`.

- **`would_exceed` before every paid call.** `ranker.py` re-checks the ceiling before
  each LLM draft, so a long cycle cannot blow the budget mid-run (it used to be checked
  once, before the loop). On breach: stop + checkpoint + **alert** — never a silent skip.
- **Spend is recorded as incurred**, not estimated post-hoc, and counted locally so the
  ceiling binds *even if the ledger POST fails*. Flushed every 10 calls + at cycle end.
- **`killed`** = global kill-switch in `settings`. Absolute: beats `paused` and any
  remaining budget. `paused` is the soft, resumable stop.
- **`quiet_hours`** is now actually enforced (the column existed but nothing read it).
- **Fail-closed**: if the ceiling/kill-switch can't be read, the cycle aborts + alerts
  rather than assuming it's safe to spend.
- **`autonomy_level`**: `L0` suggest-only | `L1` draft-and-queue (default). v0's `L2`
  act-with-approval / `L3` autonomous gate *outward actions* — Chorus has no write lane
  by design, so they are **refused** at the enforcement point rather than faked.
- **`CircuitBreaker`** (closed→open→cooldown→half_open) is for *provider reliability*
  and is deliberately separate from the budget ceiling. Wrap any provider call with it.

Rates live in `budget.RATES` (USD/unit). Unknown ops raise — never assume free.
