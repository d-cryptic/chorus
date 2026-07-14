---
name: research-digest
description: Multi-source topic sweep into a cited brief in memory.
---

# research-digest

## Purpose
The cheapest, safest, most extensible feature: sweep many sources on a topic and
synthesize a cited brief you can act on.

## Inputs
`topic` or question.

## Uses
the swappable research layer (`box/research.py`: **linkup** default / firecrawl) · `hn` · `reddit` · `youtube` · `github`.

## Steps
1. **sweep** — parallel reads across the ports (each blind to the others).
2. **dedup** — collapse overlapping sources.
3. **synthesize** — a structured, cited brief.
4. **store** — write to memory; optionally push a morning digest via `messaging`.

## Output
`brief{summary, key_points, sources[]}`.

## Notes
Low-risk and clean (mostly free APIs). Extend by adding MCP ports — the digest widens
automatically.
