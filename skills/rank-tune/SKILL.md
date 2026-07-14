---
name: rank-tune
description: Weekly pass that personalizes ranking weights from feedback.
---

# rank-tune

## Purpose
Close the learning loop (G1): turn posted/edited/dismissed actions — and real outcomes when
available — into updated ranking weights, denylist, and pillar vectors.

## Inputs
`feedback` rows (action + reason + edited text), `outcome` rows (FE1, when present), current `weights`.

## Steps
1. **aggregate** — acceptance rate by pillar / author-tier / factor; cluster dismiss reasons.
2. **adjust** — nudge `weights` toward accepted factor profiles, away from dismissed; grow
   `settings.denylist` from "off-brand"/"toxic" reasons.
3. **voice** — feed `posted_edited` diffs (draft → actual) into `voice-model` for `chorus:self`.
4. **write** — `POST /api/box/weights` per factor + update `settings.denylist`; opportunity-rank reads these at run start.

## Schedule
Weekly cron.

## Notes
Outcome-weighted (FE1) beats accept/reject: a draft you liked that flopped should lose weight.
Prefer `outcome` signal when present.
