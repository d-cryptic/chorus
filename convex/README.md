# Chorus — Convex backend (M1)

Reactive operational state + durable orchestration. The Convex half of
[../docs/data-architecture.md](../docs/data-architecture.md). Semantic/identity memory lives in
Supermemory. **Self-hosted on the Hetzner box behind the tunnel** so the "everything behind
Access" invariant holds (G3).

## Schema (`schema.ts`)
`suggestions` (the queue) · `feedback` · `spendLedger` · `outcome` (FE1) · `weights` (rank-tune
output) · `settings` (pause/ceiling/denylist) · `runLog` (heartbeat).

## Functions
| file | exports |
|---|---|
| `suggestions.ts` | `listQueued` (reactive; hides expired, surfaces due-snoozed) · `enqueue` (idempotent upsert) · `act` |
| `spend.ts` | `today` · `record` (IST day) |
| `settings.ts` | `get` · `update` (dashboard toggles) |
| `runs.ts` | `latest` (heartbeat) · `start` · `finish` |
| `outcome.ts` | `set` · `needingMeasurement` |
| `rankTune.ts` | `run` (weekly, in-DB learning loop — outcome-weighted weight nudge) |
| `crons.ts` | daily cycle (02:30 UTC = 08:00 IST) · daily outcome · weekly rank-tune |
| `actions.ts` | `runDailyCycle` / `measureOutcomes` (call the box) · `mirrorFeedback` (→ Supermemory chorus:self) |

## How it composes
Convex cron → `runDailyCycle` action → POSTs the box (Hermes runs target-tiering → budget-guard →
scrape → Supermemory write → opportunity-rank) → the box calls `enqueue()`/`spend.record()` back →
the dashboard's `listQueued` subscription updates **live**. `act` writes `feedback`; `rankTune.run`
turns feedback+outcomes into updated `weights` that opportunity-rank reads next run.

## Setup
```bash
cd convex && npm install
npx convex dev            # dev deployment + _generated/; or `npx convex deploy`
# set env in the Convex dashboard: HERMES_CYCLE_URL, HERMES_OUTCOME_URL, HERMES_TOKEN, SUPERMEMORY_API_KEY
```
Self-host: run `get-convex/convex-backend` on the box; point the client at it.

## Reactive dashboard swap (supersedes the D1 fetch loop)
Replace the polling `fetch` in `../dashboard/public/index.html` with the vanilla Convex client:
```html
<script type="module">
  import { ConvexClient } from "https://esm.sh/convex/browser";
  const client = new ConvexClient(CONVEX_URL);
  client.onUpdate("suggestions:listQueued", { status: "queued" }, (rows) => render(rows)); // live
  // actions: await client.mutation("suggestions:act", { id, action, finalText });
</script>
```
No polling — the queue re-renders the instant the box enqueues. Gate the deployment behind the
same Access app. The Worker+D1 dashboard stays as the **M0** fallback.

## Not durable-retry yet
Crons re-fire daily, so a failed cycle logs an error and retries next run. For per-step durability
(async tool loops, automatic retry mid-cycle) upgrade `actions.ts` to the `@convex-dev/workflow`
component — optional, not needed for a daily cadence.
