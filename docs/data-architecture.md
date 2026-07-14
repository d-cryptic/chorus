# Chorus — data architecture: Supermemory × Convex × Cloudflare × Hermes

Detailed summary: Four components, one boundary rule. **Hermes** = agent brain (skills,
browser, messaging, LLM loop) on the Hetzner box. **Supermemory** = semantic/identity memory
(profiles, voice, past posts, learned prefs, RAG grounding via `profile()`). **Convex** =
reactive operational backend (queues, counters, jobs, status, action logs, settings) +
durable workflows (the scheduled enrich/rank/insights pipelines) + the live dashboard data.
**Cloudflare** = edge gating (Access, single email), DNS, tunnel. Rule: if the UI *watches*
it or a job *transacts* it → Convex; if it's semantic recall / "what we know about a person or
you" → Supermemory. Convex durable workflows conduct; they call Supermemory to ground and
scrapers to fetch, then write rows the dashboard reactively renders. This supersedes the D1
dashboard (Convex is strictly better for the reactive queue).

## The boundary rule
| Signal | Owner |
|---|---|
| UI needs live updates on it (queues, counters, status, proposals, render progress) | **Convex** (reactive query) |
| A job transacts/mutates it (jobs, checkpoints, budgets, action log, settings) | **Convex** (mutation) |
| Scheduled / durable multi-step / survives restarts (pipelines, calendar arcs) | **Convex** (scheduler + durable workflow) |
| Semantic recall / embeddings / "who is this / who am I" / RAG grounding | **Supermemory** (containerTags + `profile()`) |
| Learned preferences / voice / accept-reject history that tunes future behavior | **Supermemory** (`chorus:self` dynamic profile) |
| Edge auth / DNS / no public exposure | **Cloudflare** (Access + tunnel) |
| Interactive LLM/browser/messaging execution | **Hermes** (skills) |

**Both have vector search — do not use both for the same job.** Convex vector search = app-scoped
operational retrieval (e.g. "similar open suggestions"). Supermemory = the identity/semantic brain
and the one-call `profile('chorus:self', q)` grounding. Don't duplicate the identity store in Convex.

## Per-feature map (every PRD flow)
| PRD feature / flow | Supermemory (semantic) | Convex (structured / reactive / durable) | Live UI |
|---|---|---|---|
| **01 Onboarding** | growth profile → `chorus:self` static (identity, goals, archetype, topics) | onboarding step/skip/resume state | ✓ step state |
| **02 Role models** | role-model list + derived style patterns; growth roadmap; voice profile | selection/management state | ~ |
| **03 Content creation** | activity signals (captures/projects/learnings), engagement-history embeddings, voice | quota counters (15/mo), draft rows+status, publish jobs | ✓ quota, draft status |
| **04 Community engagement** | your topics+voice for ranking; **accept/reject learning** → `chorus:self` dynamic | **the suggestion queue**, rising-creator list, accept/reject actions | ✓ daily queue |
| **05 Calendar awareness** | profile + people-to-meet context | `calendar_events`, timed prompts, quiet hours, consent flags, **durable multi-day arcs** | ✓ timed push |
| **06 Social integration** | — | OAuth token vault, connection status, action-history log, undo state, scheduled tasks | ✓ connection/action status |
| **07 AI companion** | chat context recall, learned prefs | agent-proposal queue, autonomy config/whitelist, **pause/kill flags**, chat session state | ✓ proposals, instant pause, streaming |
| **08 Context & memory** | **the semantic store**: profiles, embeddings, past posts, voice models | structured state + KV-like hot cache + the **retrieval-API orchestration (FR-8.4)** | ✓ <200ms retrieval |
| **09 Themes / experiments** | theme semantic priors | experiment defs/assignments/holdout, `metric_snapshot` time-series, per-theme rollups, pin/override/retire | ✓ experiment dashboards |
| **10 Insights / playbook** | AKB teardowns+embeddings, `useful_account` correlations, gap_analysis, niche priors, insight *content*, playbook doc, trend-angle library | **pipeline orchestration** (cron→checkpoint), `scrape_jobs` priority queue, edges graph, budget accounting, safety/quarantine/human-review queue, cost meters, kill-switch, run history/replay, insight versioning/status/pin lifecycle | ✓ operator dashboard, kill-switch |
| **11 Generation engine** | RAG namespace `posts:<accountId>` voice priming, few-shot libraries | `media_assets` status (fal_job_id, r2_key), render webhooks, draft-status transitions, moderation/judge verdicts, content-hash caches | ✓ media render status |
| **v0 Stage 3 personas** | versioned personas → `chorus:self` / target tags | persona row/version pointer | — |
| **v0 Stage 4/5/7 candidates** | (author voice via target tags) | `target_candidates` / `interaction_candidates` / `post_ideas` ranked rows | ✓ queues |
| **v0 Stage 8 content_drafts** | voice-filled body (`generateDraft`) | draft row + status + HITL gate | ✓ approval |
| **v0 Stage 9 growth_profile** | profile content | metric feedback loop → Stage 3 | ~ |

## The BOTH straddlers — how to split each seam
- **Insight & playbook records** → *content* (evidence, angle, embedding) in Supermemory; *lifecycle* (version, TTL, status, supersede, pin precedence) as Convex rows that reference the Supermemory doc id.
- **content_drafts / generateDraft** → row + status + HITL gate in Convex; the voice-filled body grounded from Supermemory, stored as a Convex field (+ optional Supermemory doc for future RAG).
- **growth_profile feedback loop** → profile in Supermemory (`chorus:self`); metric feedback + the loop trigger in Convex.
- **Engagement metric snapshots** → raw counters/time-series in Convex; derived/embedded signals in Supermemory.
- **Trend candidate** → velocity/ranking/diffusion-stage in Convex; embeddings/angle in Supermemory.
- **Context Retrieval API (FR-8.4)** → a Convex `action` that calls `sm.profile()` + reads Convex tables, merges, returns <200ms. **This is the one seam where they meet in a single call.**
- **GDPR deletion cascade** → a Convex mutation/action that deletes Convex rows **and** calls Supermemory `forget` / document-delete for the user's containerTags. Neither owns it alone.

## Durable workflows → Convex (a real upgrade over the PRD's DO+Queue machinery)
The PRD hand-rolls per-user Durable Objects + Queues + KV cadence clocks + DLQ for: the insights
pipeline (cron→checkpoint {completedSteps,status,paused,day}), the priority scrape queue, and the
multi-day calendar arcs. **Convex's scheduler + durable agent/workflow component replaces all of
that**: cron triggers, async tool loops with no time limit, automatic state recovery on restart,
built-in retries, and workpool parallelism — while staying reactive so the operator dashboard and
kill-switch are live. Map: insights pipeline → one Convex workflow; scrape queue → Convex table +
scheduled functions gated by `budget-guard`; calendar arcs → durable workflow with multi-day sleeps.

## How the four compose (one enrich→rank cycle)
```
Convex cron ──fires──> Convex durable workflow "daily-cycle"
   │ 1. target-tiering + delta-refresh  (Convex tables: scrape_jobs, hashes)
   │ 2. budget-guard check              (Convex: spend_ledger)
   │ 3. call Hermes / scrapers          (Convex action → Hermes MCP / X read adapter)
   │ 4. write person records + posts    (Supermemory: chorus:target:<h>)
   │ 5. opportunity-rank per candidate  (Hermes skill; grounds via sm.profile('chorus:self', q))
   │ 6. INSERT suggestion rows          (Convex: suggestions table)  ──reactive──> dashboard live
   └ 7. you act (posted/dismissed)      (Convex mutation + Supermemory add kind:feedback → profile.dynamic)
```

## Revised stack & hosting
- **Hermes** on Hetzner (`cax11`) — skills, browser, messaging, LLM loop.
- **Convex** — managed cloud (free tier) OR self-hosted (`get-convex/convex-backend` is OSS) on the
  same box for $0/locality. Holds all structured/reactive state + durable workflows + dashboard data.
- **Supermemory** — cloud free tier or self-hosted OSS on the box. Semantic/identity memory.
- **Cloudflare** — Access (single email) + DNS + tunnel front `app.` (dashboard) and `hermes.`.
- Dashboard frontend stays on Cloudflare Pages (or Convex-hosted), reactive to Convex.

## Migration: D1 dashboard → Convex
The Worker+D1 dashboard we shipped is the v0 fallback. Migrate `suggestion` / `feedback` /
`spend_ledger` into Convex tables (same shape as `dashboard/schema.sql`); replace the polling
`fetch` in `public/index.html` with a Convex reactive subscription (queue updates live, no refresh);
move `rank-tune` + the daily cycle onto Convex cron. Keep D1 as a documented fallback.

## Backend phasing (G2) — v1 runs on M0 (D1)
**M0 = D1 (shipped, tested, THE v1 path)** — the Worker+D1 dashboard + `/api/box/*` is the live
queue store; skills read/write via the Worker's token-authed box API.
**M1 = Convex — BUILT but FROZEN for v1** (per the design review). The `convex/` code typechecks,
but its user-visible gain over D1 (live updates without refresh) doesn't justify self-hosting a
Convex backend + new tunnel ingress for a single user on a morning digest. Revisit post-v1. Do NOT
build against Convex for v1; target the M0 box API.

## Auth for Convex (G3 — decide before migrating)
Convex cloud (`*.convex.cloud`) is NOT reachable through the Cloudflare zone, so Access cannot
gate it. **Decision: self-host Convex on the Hetzner box behind the tunnel**, preserving the
"everything behind Access, single email" invariant. (Convex-cloud alternative = add Convex Auth,
a second identity system — documented exception, not chosen.)

## Out of scope for Chorus v1 (cut)
The **PRD-09 (experiments/themes)** and **PRD-11 (media-render)** rows above are imported nakama
ambitions — NOT built in Chorus v1 (suggest-only, single-user). Listed for lineage only.

## Cost
Convex: free tier covers a solo build (function calls + a little storage/search); usage-based after.
Supermemory: `$0.005/1k` tokens, dedup. Both self-hostable on the Hetzner box for $0. Still fits
~$0.20–0.65/day; the only always-on cost is the box (~$0.14/day).
