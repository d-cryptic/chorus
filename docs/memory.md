# Chorus — memory (Supermemory) integration

Detailed summary: Memory backbone = Supermemory. Isolation via **container tags** (each = a
vector namespace): `chorus:self` (you — pillars/voice/goals + accept-reject history),
`chorus:target:<handle>` (each tracked person + their posts + voice model), `chorus:research`
(briefs). Metadata (`kind/platform/pillar/content_hash/ts`) filters within a tag.
`opportunity-rank` grounds every score with ONE `client.profile({containerTags:['chorus:self'],
q: tweet})` call — returns static + dynamic profile + relevant memories together. Writes come
from enrich-target / voice-model / research-digest; the feedback loop writes learnings into
`chorus:self`, so accept/reject literally becomes `profile.dynamic` that tunes future ranking.
Access via the Supermemory MCP (memory/recall) on the Hermes box or the SDK; scoped API key
limited to `chorus:*`. Deploy: Cloud free tier → self-host OSS on the Hetzner box for $0/privacy.

## Why Supermemory (vs Hermes-native)
Hermes has built-in memory; Supermemory adds: deterministic **container-tag namespaces**,
a **pre-built user profile** (`static` long-term facts + `dynamic` recent context) in one
call, metadata filtering, token-level **dedup**, and portability across tools. The profile
endpoint is the reason to use it — it collapses "recall my pillars + voice + relevant past"
into a single request per candidate tweet.

## Container-tag scheme (namespaces)
| Tag | Holds | Written by | Read by |
|---|---|---|---|
| `chorus:self` | your pillars, goals, voice model, **accept/reject history** | onboarding, voice-model, feedback loop | opportunity-rank, research-digest |
| `chorus:target:<handle>` | a person's record, their posts/transcripts, their voice model | enrich-target, voice-model | opportunity-rank, enrich-target |
| `chorus:research` | synthesized research briefs | research-digest | opportunity-rank, you |

Keep tags **deterministic** — derive from the handle/id you already have, so any skill can
reconstruct the tag at query time with no lookup.

## Metadata schema (filter within a tag)
`kind` = `person | post | voice_model | brief | edge | feedback` · `platform` = `x | github |
reddit | youtube | hn | web` · `pillar` · `author_tier` · `content_hash` (dedup/idempotency) ·
`ts`. Search with `filters: { AND: [{ key: "kind", value: "post" }] }`.

## Per-skill read/write map
| Skill | Reads | Writes |
|---|---|---|
| `enrich-target` | target tag (dedup check) | `kind:person` record + one `kind:post` per collected item |
| `voice-model` | target/self posts (`kind:post`) | `kind:voice_model` |
| `opportunity-rank` | `profile('chorus:self', q=tweet)` + author's `voice_model` | — (emits to D1 queue, not memory) |
| `research-digest` | `chorus:research` | `kind:brief` |
| feedback loop | — | `kind:feedback` into `chorus:self` (→ becomes `profile.dynamic`) |
| `budget-guard` | — | (memory ingestion tokens count toward the daily ledger) |

## API surface (grounded — v3 stable / v4 profile)
```ts
import Supermemory from "supermemory";
const sm = new Supermemory({ apiKey: process.env.SUPERMEMORY_API_KEY }); // scoped to chorus:*

// enrich-target — store a person's post (idempotent via content_hash + token dedup)
await sm.add({
  content: postText,
  containerTags: [`chorus:target:${handle}`],
  metadata: { kind: "post", platform: "x", content_hash: hash, ts },
});

// voice-model — pull a target's posts to synthesize
const posts = await sm.search.documents({
  q: "recent posts", containerTags: [`chorus:target:${handle}`],
  filters: { AND: [{ key: "kind", value: "post" }] },
});

// opportunity-rank — ONE call grounds the whole score (pillars + voice + relevant past)
const me = await sm.profile({ containerTags: ["chorus:self"], q: candidateTweet });
//   me.static  -> pillars, goals, durable voice   me.dynamic -> recent activity + accept/reject history

// feedback loop — your action becomes part of your dynamic profile
await sm.add({
  content: `POSTED reply to @${handle}: "${finalText}" (angle: ${angle})`,
  containerTags: ["chorus:self"],
  metadata: { kind: "feedback", action: "posted", ts },
});
```
On the Hermes box the same store is reachable via the **MCP** tools `memory` (save/forget)
and `recall` (search + profile) — skills call those; batch jobs/the ranker can use the SDK.

## The feedback → profile.dynamic loop (the payoff)
Every `posted / posted_edited / dismissed` action (already recorded in the D1 `feedback`
table by the dashboard) is ALSO written to `chorus:self` as `kind:feedback`. Supermemory folds
it into `profile.dynamic`, so the next `profile()` call opportunity-rank makes already reflects
what you just accepted or rejected — personalization with no separate training step. The weekly
`rank-tune` pass reads the same signal to adjust weights/denylist.

## Dedup & freshness
`content_hash` metadata + Supermemory's token-level dedup mean unchanged content is never
re-embedded or re-billed. `delta-refresh` still gates writes so we don't even attempt fresh items.

## Deploy modes
1. **Cloud, free tier** — fastest; MCP/SDK with a scoped API key. Start here.
2. **Self-host OSS on the Hetzner box** — `$0`, fully local, best privacy; run alongside Hermes.
   Move here if token cost or data locality matters.
- **Skip Supermemory Pro ($19/mo ≈ $0.63/day)** — it alone breaks the daily budget.

## Security
Use a **scoped API key restricted to `chorus:*` container tags** on the box; secrets via
env/Doppler. Self-hosted = no public exposure (same box, behind the tunnel). Person data is
public-source only, purgeable via `forget`/document delete, TTL'd per `delta-refresh`.

## Cost
`$0.005 / 1k text tokens` ingested (rich media 2×); token-level dedup + delta-refresh keep
steady-state low. Enrichment writes dominate; self-host = `$0`. Fits the ~$0.20–0.65/day envelope.
