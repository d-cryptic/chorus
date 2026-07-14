# Runbook M0 — provision + PROVE the Cloudflare gate

Detailed summary: stand up the Hetzner+Hermes box via OpenTofu, then VERIFY that every
every `chorus-*` surface is actually gated to `barundebnath91@gmail.com` before
trusting it. The gate is only real once you've confirmed an unauthenticated request is
bounced to the Access login. Also: lock down SSH, finish Hermes.

## 0. Prerequisites (the gate depends on these)
- `barundebnath.com` is a zone on the SAME Cloudflare account as your R2 state + API token.
- **Zero Trust is enabled** on that account and has a login method on — **One-time PIN**
  (email OTP, on by default) or Google SSO. Without a login method, Access can't challenge.
- Your Access team domain exists (e.g. `<team>.cloudflareaccess.com`).
- Tokens: `CLOUDFLARE_API_TOKEN` needs Zone:Read + DNS:Edit + Access:Edit + Cloudflare Tunnel:Edit.

## 1. Configure
```bash
cd infra/cmo-agent
cp terraform.tfvars.example terraform.tfvars   # set account_id; restrict ssh_source_ips
cp backend.hcl.example backend.hcl              # your R2 state bucket + account-id endpoint (git-ignored)
export CLOUDFLARE_API_TOKEN=…  HCLOUD_TOKEN=…
export AWS_ACCESS_KEY_ID=…  AWS_SECRET_ACCESS_KEY=…        # R2 state
export TF_VAR_tunnel_secret=$(openssl rand -base64 32)
# optional (baked into the box's Hermes env):
export TF_VAR_openrouter_api_key=…  TF_VAR_supermemory_api_key=…
export TF_VAR_candidate_api_key=…      TF_VAR_firecrawl_api_key=…
```

## 2. Apply
```bash
make init && make plan     # REVIEW: expect explicit Access apps for chorus-hermes / chorus-app / chorus-ssh,
                           # per-host apps (hermes/ssh/dashboard), tunnel, 2 DNS records, hetzner box.
make apply                 # ~1–2 min; billable (~EUR 3.8/mo for cax11)
make output
```

## 3. PROVE the gate (do not skip)
From a browser/machine NOT logged into Access:
```bash
# Expect a 302 redirect to the Access login (…cloudflareaccess.com/…), NOT app content.
# NOTE: no -L — we WANT to see the 302, not follow it.
curl -sSI -o /dev/null -w '%{http_code} %{redirect_url}\n' https://chorus-hermes.barundebnath.com
curl -sSI -o /dev/null -w '%{http_code} %{redirect_url}\n' https://chorus-app.barundebnath.com
# F1: the ungated workers.dev URL MUST 404 (workers_dev=false):
curl -sSI -o /dev/null -w '%{http_code}\n' https://chorus-dashboard.<account>.workers.dev
```
PASS = redirected to `…cloudflareaccess.com`. FAIL = 200 with app content → **not gated, stop**.

Then in a browser:
1. Visit `https://chorus-hermes.barundebnath.com` → you get the Access login page.
2. Log in as a NON-allowed email → **denied**.
3. Log in as `barundebnath91@gmail.com` (OTP/Google) → allowed. ✅
4. Repeat for `chorus-app.` — each gated host has its own explicit Access app.

Landing check (should be PUBLIC): `https://chorus.barundebnath.com` must load without a
challenge (no Access app fronts it). If it challenges, a stray app is gating it.

## 3b. M0.5 — validate Hermes BEFORE building the ranker (G10)
Prove Hermes works end to end with the smallest possible test: install Hermes, run ONE trivial
skill, wire ONE MCP port (firecrawl), and ONE cron that fires. If Hermes's skill/scheduler/UI-port
model differs from assumptions, the 11 SKILL.md files need rework — find out now, not after.

## 4. Lock down SSH (make it Cloudflare-only)
```bash
cloudflared access ssh --hostname chorus-ssh.barundebnath.com   # confirm gated SSH works
# LOCKOUT RECOVERY: if cloudflared dies with enable_public_ssh=false you lose SSH entirely —
# use the Hetzner web console (rescue) to restart cloudflared. Keep it in mind before flipping.
# then in terraform.tfvars:  enable_public_ssh = false
make apply                                                       # public port 22 closes → tunnel-only
```

## 5. Finish Hermes
- Set `hermes_install_cmd` (from github.com/NousResearch/hermes-agent) + re-apply, or SSH in
  and run the installer. Confirm Hermes serves on `hermes_ui_port` (default 3000).
- Wire the MCP ports from `../../mcp/mcp.json`; copy `../../skills/*` into `~/.hermes/skills/`.

## Scraping budget note
Cheap scrapers make "scrape a lot" affordable: the private X read adapter `$0.15/1k` (100k free credits) →
~6,600 tweets/day for ~$1. The ceiling is `budget-guard` (daily cap), not per-unit price;
`delta-refresh` + `target-tiering` stop you re-paying for unchanged data. Sorsa `$0.09/1k`
(needs $49 prepaid) or Bright Data get cheaper only at high volume (>~18k tweets/day).
