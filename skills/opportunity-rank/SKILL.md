---
name: opportunity-rank
description: Rank tweets worth replying to and draft replies (suggest-only).
---

# opportunity-rank

## Purpose
Decide WHICH candidate tweets are worth commenting on and draft WHAT to say. Never posts —
emits a ranked queue; you post manually.

## Two-stage design (cost-critical — F5)
LLM + memory calls run ONLY on survivors, never on all 500–2,000 candidates.

**Stage A — cheap mechanical pre-score (no LLM, no per-tweet memory):**
1. **gate** — drop: non-target lang · self-authored · duplicate `tweet_id` · stale (past reply
   window) · toxic/off-brand (denylist + a cheap moderation pass).
2. **pre-score** — `pillar_relevance` (embedding sim vs. cached pillar vectors) + `author_value`
   (tier) + `engagement_upside` + `freshness` − `saturation`. Load `weights` via `GET /api/box/weights`
   store at run start (written by `rank-tune`).
3. **take top ~50** by pre-score.

**Stage B — expensive, only on the ~50:**
4. **ground once** — fetch `profile('chorus:self')` ONE time per run (it changes on your
   actions, not per tweet) — pillars, voice, accept/reject history. Per-candidate: a `search`
   on the author's `chorus:target:<handle>` for voice + edges only.
5. **angle + draft** — LLM proposes the best angle in your voice + self-rates originality vs.
   the existing replies; generate 2–3 drafts + rationale. `angle_strength` finalizes the score.
6. **threshold** — keep `score ≥ τ` (0.6); take top N (25/day).
7. **emit** — POST each to `/api/box/ingest` (Bearer `INGEST_TOKEN`); upsert on `tweet_id`.
   Include `tweet_url`, `expires_at`. Bracket the run with `POST /api/box/run-log` (start → finish).
8. **notify** — push top 5 to Telegram; record a `run_log` row (started/finished/suggested).

## Factors & default weights
angle_strength .24 · pillar_relevance .22 · author_value .18 · engagement_upside .16 ·
freshness .12 · relationship .08 · − saturation .15 · − risk .20. Weights live in the
`weights` table; `rank-tune` updates them weekly. See [docs/data-architecture.md](../../docs/data-architecture.md).

## Output
Queue rows (never posts). Human acts from the dashboard/Telegram.

## Notes
Cold start: if `profile('chorus:self')` is empty (day 0), run `onboard-self` first — do not
draft in nobody's voice. Grounding + memory model: [docs/memory.md](../../docs/memory.md).
