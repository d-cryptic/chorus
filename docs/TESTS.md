# Chorus — test catalog & verification

Detailed summary: What's been verified offline and how. M0 dashboard (Worker + D1) was run
live via `wrangler dev --local` and exercised with 18 functional + 6 auth assertions — ALL PASS;
one real bug found & fixed (stale seed timestamps hidden by the expiry filter). Dashboard JS (3
pages) syntax-valid. Convex functions typecheck clean (0 real errors). Terraform `tofu validate`
passes. Not offline-testable (needs accounts): actual deploy, Hermes runtime, MCP ports,
Supermemory/Convex live calls, `tofu apply` — tracked as deploy-gated.

## Results (2026-07-13)
| Suite | Method | Result |
|---|---|---|
| M0 API flows (18) | live `wrangler dev --local` + curl | ✅ all pass |
| M0 auth / gate (6) | fresh worker, no DEV_OPEN | ✅ all pass (fail-closed proven) |
| Dashboard JS (3 pages) | `node --check` | ✅ parse clean |
| Convex functions (9 files) | `tsc` w/ stubbed `_generated` | ✅ 0 real errors |
| Terraform (whole module) | `tofu validate` | ✅ valid |

### M0 API flows verified
list-queued (200, seeded, score-desc) · ingest **401 without token / 200 with** / **401 wrong
token** · dedup **UNIQUE(tweet_id) upsert** (score refreshed, no dup row) · CSRF **400 without
X-Chorus** · dismiss (200, leaves queue) + feedback row · **unknown id → 404** · spend record +
read (IST day) · **expired hidden** · **snooze hidden** · review aggregates (dismiss reason
recorded) · static pages served.

### Gate (fail-closed) verified
No JWT + DEV_OPEN off → human GET/POST **403**; box ingest bypasses identity via Bearer token
(200 correct / 401 wrong); static `/` stays public. Matches "only barundebnath91@gmail.com;
nothing else exposed."

### Bug found & fixed
`seed.sql` used 2025 epochs → the (correct) expiry filter hid every demo row in 2026. Fixed to
`expires_at NULL` + recent `created_at`. Also `/review.html` → `/review` (Assets 307 redirect).

## How to run (M0)
```bash
cd dashboard && npm install
printf 'DEV_OPEN=1\nINGEST_TOKEN=testtok\nALLOWED_EMAIL=you@x.com\nACCESS_TEAM_DOMAIN=t\nACCESS_AUD=t\n' > .dev.vars
npx wrangler d1 execute chorus --local --file=./schema.sql
npx wrangler d1 execute chorus --local --file=./seed.sql
npx wrangler dev --local --port 8787            # then curl the /api/* endpoints
```
Convex typecheck: `cd convex && npm i && npx tsc --noEmit` (needs `_generated` from `npx convex dev`).

## Requirements traceability
| Requirement | Verified by | Status |
|---|---|---|
| Suggest-only — no automated X writes | Worker has only read/ingest/action; no post endpoint | ✅ code + live |
| Single-email Access gate | fail-closed 403 test + explicit per-host Access apps (tofu) | ✅ tested + validated |
| Budget ≤$0.65/day | `settings.dailyCeilingUsd=0.65`; budget-guard; spend ledger tested | ✅ |
| Everything gated, landing public | static public / `/api` 403; infra apps | ✅ tested |
| Free TLS (no ACM) | one-level `chorus-*` hosts | ✅ (flatten) |
| Dedup / expiry / snooze | live tests | ✅ |
| Feedback loop closes | posted-edited action (tested) + rank-tune (typechecks) + weights table | ✅ |
| Reads only / no ban risk | x-read-lane ToS doc; no credential reads | ✅ design |
| Supermemory per-flow | data-architecture + memory docs; mirrorFeedback typechecks | ✅ design + code |
| Convex reactive backend | functions typecheck; listQueued reactive | ✅ code |

## NOT tested offline (deploy-gated — needs your accounts)
`tofu apply`; wrangler/convex **deploy**; **Hermes** skill execution + cron + MCP ports connecting;
**Supermemory**/**Convex** live calls & reactivity; end-to-end enrich→rank→queue with real data;
the Access login round-trip (M0.5 + runbook §3 prove-the-gate).
