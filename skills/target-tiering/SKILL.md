---
name: target-tiering
description: Classify targets deep/medium/shallow to set sources + cadence.
---

# target-tiering

## Purpose
Decide how much attention each tracked person deserves, bounding enrichment cost.

## Steps
1. **classify** — deep (~10–20 key people) / medium / shallow (long tail).
2. **map** — deep = all MCP sources, daily; medium = X + 1–2 free ports, few-daily;
   shallow = X-only, weekly.
3. **emit** — tier + source-set + cadence per target.

## Output
`tiered_targets[]` consumed by `enrich-target` and `delta-refresh`.

## Notes
A bounded ~150-target set on delta refresh keeps enrichment ~$0.05–0.30/day. Unbounded
daily deep-profiling of hundreds of targets across every platform blows past $2/day.
