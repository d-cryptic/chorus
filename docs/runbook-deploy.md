# Chorus — deploy runbook (you run this; it acts on your live accounts)

Detailed summary: The 🔴 steps I can't do for you — they spend money (Hetzner ~EUR3.8/mo) and
provision outward-facing infra on YOUR Cloudflare + Hetzner accounts. Run each block, read the
output, and only `apply`/`deploy` when the plan looks right. Order: env → infra (tofu) → dashboard
(wrangler) → prove the gate → M0.5 validate Hermes → onboard + first ranker run. Everything is
already tested locally (docs/TESTS.md); this is the live wiring.

## 0. Prereqs
- `barundebnath.com` is a zone on your Cloudflare account.
- **Zero Trust enabled** on that account with a login method (One-time PIN or Google SSO).
- Load creds into the shell (from your env file — they go into the ENV, not into git):
  ```bash
  set -a; source ~/Developers/personal/emulated/.env; set +a
  ```
- Chorus expects these names (export/alias if your .env differs):
  `CLOUDFLARE_API_TOKEN` (zone+dns+access+tunnel edit), `HCLOUD_TOKEN`,
  `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` (R2 state), `OPENROUTER_API_KEY`,
  `CANDIDATE_API_KEY` (reads only — you post manually), `LINKUP_API_KEY` (research; swap via
  `RESEARCH_PROVIDER`), `GITHUB_TOKEN`. **Supermemory = self-hosted** on the box (no key).
  **Telegram deferred** for v1. Plus a chosen `INGEST_TOKEN` (`openssl rand -hex 24`).

## 1. Infra — Hetzner box + Cloudflare Tunnel/Access (spends money at `apply`)
```bash
cd infra/cmo-agent
cp backend.hcl.example backend.hcl        # set your R2 state bucket + account-id endpoint
cat > terraform.tfvars <<TF
account_id = "YOUR_CF_ACCOUNT_ID"
ssh_source_ips = ["$(curl -s ifconfig.me)/32"]
use_doppler = false
TF
export TF_VAR_tunnel_secret=$(openssl rand -base64 32)
export TF_VAR_openrouter_api_key="$OPENROUTER_API_KEY" TF_VAR_supermemory_api_key="$SUPERMEMORY_API_KEY"
export TF_VAR_candidate_api_key="$CANDIDATE_API_KEY" TF_VAR_firecrawl_api_key="$FIRECRAWL_API_KEY"
export TF_VAR_ingest_token="$INGEST_TOKEN" TF_VAR_telegram_bot_token="$TELEGRAM_BOT_TOKEN"
export TF_VAR_telegram_chat_id="$TELEGRAM_CHAT_ID" TF_VAR_github_token="$GITHUB_TOKEN"
make init && make plan          # local state (R2 opt-in later). REVIEW: box + tunnel + 3 Access apps + 2 DNS records
make apply                      # ← spends money. type yes only if the plan is right.
make output                     # note server_ipv4, hermes_url, dashboard_url, dashboard_access_aud
```

## 2. Dashboard — Cloudflare Worker + D1
```bash
cd ../../dashboard && npm install
npx wrangler d1 create chorus                 # paste database_id into wrangler.toml
# set ACCESS_TEAM_DOMAIN + ACCESS_AUD in wrangler.toml (aud = `tofu output dashboard_access_aud`)
npx wrangler secret put INGEST_TOKEN          # paste the same $INGEST_TOKEN
npm run db:init                               # apply schema.sql (remote)
npx wrangler deploy                           # custom domain chorus-app.barundebnath.com (workers_dev=false)
```

## 3. Prove the gate (do NOT skip — see runbook-m0.md §3)
```bash
curl -sSI -o /dev/null -w '%{http_code} %{redirect_url}\n' https://chorus-app.barundebnath.com   # want 302 -> ...cloudflareaccess.com
curl -sSI -o /dev/null -w '%{http_code}\n' https://chorus-dashboard.<acct>.workers.dev            # want 404 (workers_dev=false)
# browser: non-allowed email -> denied; barundebnath91@gmail.com -> in.
```

## 4. M0.5 — validate Hermes (the one unproven assumption)
```bash
cloudflared access ssh --hostname chorus-ssh.barundebnath.com   # or ssh root@<server_ipv4>
# on the box: set hermes_install_cmd (github.com/NousResearch/hermes-agent) or install manually.
# PROVE: one skill runs, one MCP port connects, one cron fires, and a skill can do an authed POST:
curl -X POST https://chorus-app.barundebnath.com/api/box/spend \
  -H "authorization: Bearer $INGEST_TOKEN" -H 'content-type: application/json' -d '{"source":"test","usd":0}'
# If Hermes can't reliably POST, skip Hermes: run box/*.py directly from cron (box/crontab.example).
```

## 5. Onboard + first ranker run
```bash
cd box   # env still loaded; also: export INGEST_URL=https://chorus-app.barundebnath.com CHORUS_HANDLE=<you> CHORUS_PILLARS="..." CHORUS_TARGETS_A="dankoe,thisiskp_"
# Supermemory: run it self-hosted on the box first (docker; github.com/supermemoryai/supermemory),
# then SUPERMEMORY_BASE_URL=http://localhost:8000.
python3 onboard.py                       # build chorus:self (pillars+voice) from your X history
python3 ranker.py --targets              # fetch via X read adapter -> rank -> POST /api/box/ingest
python3 digest.py                        # Telegram digest
# open https://chorus-app.barundebnath.com -> your first ranked suggestions.
```
Then wire `box/crontab.example` on the box for the daily loop.
