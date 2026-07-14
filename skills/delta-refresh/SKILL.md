---
name: delta-refresh
description: Re-scrape only what changed, by content hash + per-source TTL.
---

# delta-refresh

## Purpose
The main cost-saver: decide what actually needs re-fetching so enrichment stays cheap.

## Inputs
A candidate set of sources/targets to potentially refresh.

## Steps
1. **ttl** — per-source freshness windows: tweets daily, followers weekly, bio monthly.
2. **hash** — compare stored content hash to detect real change.
3. **emit** — return only the stale/changed items; skip everything fresh (zero spend).

## Output
`due[]` — the subset worth fetching this run.

## Config
Per-source TTL table.

## Notes
Pair with `budget-guard`. Idempotent: unchanged content is never re-embedded or re-billed.
