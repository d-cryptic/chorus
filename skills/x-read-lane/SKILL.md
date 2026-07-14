---
name: x-read-lane
description: All X reads via X read adapter, gated by budget + delta.
---

# x-read-lane

## Purpose
Single entry point for reading X (timeline, tweets, profiles, followers, replies) so
budget + freshness rules apply in one place. There is NO write lane — the human posts.

## Uses
`X read adapter` MCP port · `budget-guard` · `delta-refresh`.

## Steps
1. **gate** — `budget-guard` (metered source) + `delta-refresh` (skip fresh).
2. **read** — candidate sources are **target-lists + keyword search + your mentions** (NOT a
   home timeline — the private X read adapter has no user-auth for that). Also fetch metrics for posted replies (outcome-track).
3. **emit** — normalized candidates for `opportunity-rank`; profile data for `enrich-target`.

## Output
`candidates[]` and/or profile records.

## ToS / provider risk (accepted, honest)
the private X read adapter is an **unofficial** scraper API — accepted risks: it can block/die (your whole
candidate source → have a fallback: official API free tier for mentions, or a Nitter-class
source), and scraping public data is a ToS grey area. Mitigations: **no user credentials are
used**, reads are public-only, and **your own account cannot be banned for reading** — a core
safety property of the suggest-only design (you post by hand). Writes are absent by design.

## Notes
$0.15/1k, 100k free credits. Never call the port directly — always via this lane (budget +
delta gated).
