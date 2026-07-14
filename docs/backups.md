# Chorus — backups & recovery (G6)

Detailed summary: The one dataset you can't regenerate is your accumulated voice/feedback corpus
(Supermemory) — export it. Everything else is rebuildable: Terraform state (R2, enable
versioning), D1 queue (nightly export → R2 + CF Time Travel), the box (cloud-init, once
`hermes_install_cmd` is set). Drill the rebuild before you rely on it.

## What to back up
| Asset | Store | Backup |
|---|---|---|
| Supermemory corpus (voice, feedback, dossiers) | Supermemory | **weekly export/dump** — the irreplaceable one (vendor lock otherwise) |
| Queue (suggestions/feedback/outcomes/weights) | D1 (M0) / Convex (M1) | nightly `wrangler d1 export chorus --remote` → R2; CF D1 Time Travel (30d) |
| Terraform state | R2 (bucket in git-ignored `backend.hcl`) | **enable R2 bucket versioning** |
| The box | Hetzner | rebuildable from cloud-init IF `hermes_install_cmd` is filled in |

## Nightly D1 export (box cron)
```bash
wrangler d1 export chorus --remote --output=/tmp/chorus-$(date +%F).sql
# upload to R2 (aws s3 cp against the R2 S3 endpoint), keep ~14 days
```
(M1: Convex snapshots via `npx convex export`.)

## Rebuild-from-zero drill (do it once)
1. `tofu apply` in a scratch state → box + tunnel + Access come up.
2. Set `hermes_install_cmd`; confirm Hermes + MCP + one cron (M0.5 gate).
3. Restore the latest D1 export (`wrangler d1 execute chorus --file=<export>`), Supermemory import.
4. Verify the gate (runbook §3) and one enrich→rank→queue cycle.

If step 2 needs a doc you don't have, the backup is theater — run the drill.
