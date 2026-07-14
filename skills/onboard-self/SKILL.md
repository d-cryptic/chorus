---
name: onboard-self
description: Bootstrap chorus:self (pillars, goals, voice) on day 0.
---

# onboard-self

## Purpose
Handle cold start (G4): before opportunity-rank can rank or draft, `chorus:self` must exist.

## Steps
1. **interview** — short chat: goals, content pillars, who to reach, tone do/don't.
2. **mine history** — `enrich-target(self)` over your own X (+ optional GitHub/blog) history;
   `voice-model(self)` to synthesize your voice from real posts.
3. **write** — store pillars/goals (static) + voice model to `chorus:self`; cache pillar vectors
   for opportunity-rank's Stage-A pre-score.

## Day-0 mode
Until populated, opportunity-rank surfaces tweets by pillar/author only and labels drafts
"un-voiced (still learning your style)".

## Output
A populated `chorus:self`. Run once; re-run to re-baseline.
