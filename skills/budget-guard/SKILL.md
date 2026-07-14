---
name: budget-guard
description: Gate metered scrapes against a daily spend ceiling.
---

# budget-guard

## Purpose
Keep daily spend inside the **$0.20–0.65/day** envelope (F6). Ported from Nakama's BudgetTracker.

## Ceilings
- **soft_ceiling** default `$0.45` — above this, widen intervals + drop optional enrichment.
- **hard_ceiling** default `$0.65` (from `settings.daily_ceiling_usd`) — deny all metered calls.

Read the ceiling from the `settings` row, not this file, so the dashboard can change it live.

## Steps
1. **read** — today's spend + ceiling: `GET /api/box/spend` and `GET /api/box/settings` (Bearer `INGEST_TOKEN`).
2. **decide** — free MCP ports always allowed. Metered (X read adapter): allow if
   `spend + est ≤ hard_ceiling`; between soft and hard → allow but throttle; else deny and
   signal callers to skip metered sources this run.
3. **record** — after the call, `POST /api/box/spend` (Bearer `INGEST_TOKEN`) with `{source, usd}`.

## Output
`{allow, remaining_usd, throttle, next_interval_hint}`.

## Notes
Ledger lives in the queue store (D1 now / Convex later) via the Worker's token-authed ingest
(F4) — the box has no direct DB access. Free ports log at ~$0 but still count.
