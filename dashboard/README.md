# Chorus dashboard — suggestion queue

A Cloudflare **Worker + static UI** on `chorus-app.barundebnath.com`, behind Cloudflare
Access (only `barundebnath91@gmail.com`). It reads the queue store and lets you copy drafts
and record what you did. **No write path to X** — you post manually.

## Pieces
- `public/index.html` — the UI: ranked cards (score + factor chips, tweet, angle, 2–3
  copyable drafts, `posted / snooze / dismiss`), status filters, today's spend meter.
- `src/index.ts` — Worker API: `GET /api/suggestions?status=`, `GET /api/spend`,
  `POST /api/suggestions/:id/action`. Actions update `suggestion.status` and write a
  `feedback` row (fuel for the weekly `rank-tune` learning pass).
- `schema.sql` — D1 tables (`suggestion`, `feedback`, `spend_ledger`).
- `seed.sql` — two demo rows so the UI renders before `opportunity-rank` is live.

## Deploy
```bash
cd dashboard
npm install
wrangler d1 create chorus                 # paste the returned database_id into wrangler.toml
npm run db:init                            # apply schema.sql
npm run db:seed                            # optional demo rows
npm run deploy                             # wrangler deploy
```
Then front it on `chorus-app.barundebnath.com` (custom domain / route) — the Access app in
`../infra/cmo-agent/dashboard.tf` (an explicit Access app) locks it to your email.
Local dev: set `DEV_OPEN=1` for `npm run dev` (skips the identity check). The box writes the
queue via `POST /api/ingest` + `POST /api/spend` with `Authorization: Bearer $INGEST_TOKEN`
(`wrangler secret put INGEST_TOKEN`; same value in `/etc/hermes/hermes.env`). **`workers_dev=false`**
— the API is reachable only on the Access-gated custom domain (F1). This is the **M0** backend; M1 = Convex.

## Contract with the ranker
`opportunity-rank` (`../skills/opportunity-rank`) INSERTs `suggestion` rows with
`status='queued'`; the dashboard is the read/act surface. Same DB, one direction.
