---
name: outcome-track
description: Measure how posted replies performed → reward for rank-tune.
---

# outcome-track

## Purpose
Highest-leverage upgrade (FE1): learn from RESULTS, not mood. How a posted reply actually did
is the ground truth accept/reject only approximates.

## Steps
1. **find** — `status='posted'` suggestions with no `outcome` row, ~24–48h old.
2. **measure** — via `x-read-lane`, fetch likes / replies / profile-clicks for that reply.
3. **write** — `POST /api/box/outcome` `{suggestion_id, likes, replies, profile_clicks}`.

## Schedule
Daily cron, after the main cycle. Feeds `rank-tune`.

## Notes
Reads only — your own posted replies' public metrics. No writes to X.
