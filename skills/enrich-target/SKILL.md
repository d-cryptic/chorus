---
name: enrich-target
description: Gather cross-platform context on a person and store it in memory.
---

# enrich-target

## Purpose
Build/refresh a person record (yours or a target's) by fanning out across the wired
MCP data ports, respecting tier + budget, and writing the result to memory.

## Inputs
`handle` or person id, `tier` (from `target-tiering`).

## Uses
MCP ports: `firecrawl` · `github` · `reddit` · `youtube` · `hn` · `X read adapter` (via
`x-read-lane`). Plus `budget-guard`, `supermemory.memory`.

## Steps
1. **plan** — from `tier`, pick which sources apply (deep = all; shallow = X-only).
2. **gate** — call `budget-guard` before any metered port (X read adapter/apify). If near the
   ceiling, drop metered sources this run; keep the free MCP ports.
3. **fetch** — parallel reads across the chosen ports (only stale items per `delta-refresh`).
4. **normalize** — collapse into one person record: bio, pillars, recent posts, links,
   followers/following summary, interaction edges.
5. **store** — write to `chorus:target:<handle>` (Supermemory): one `kind:person` record +
   one `kind:post` per item, `content_hash` metadata for dedup; trigger `voice-model` if drifted.
   See [docs/memory.md](../../docs/memory.md).

## Output
A normalized person record persisted to memory (id = content hash for idempotent dedup).

## Notes
Others' likes are private (2024) — do not attempt. Free-API ports (hn/github/reddit/
youtube/rss) are ~$0 and clean; enrich liberally. LinkedIn/IG/TikTok (apify) are the
expensive, brittle, ban-prone tail — occasional + cache hard.
