# Chorus

A single-user, **suggest-only personal CMO** — an accountability + research + social-growth
partner that knows you. It reads X, enriches context from many platforms, ranks which tweets
are worth commenting on, and drafts replies in your voice. **You post manually** — the agent
never writes to X, so there's zero automation ban-risk and $0 write cost. Target **~$0.20–0.65/day**.

## Stack
- **Runtime**: [Hermes Agent](https://github.com/NousResearch/hermes-agent) (self-hosted, MIT) on a Hetzner box
- **Memory**: Supermemory (or Hermes-native)
- **Data ports**: MCP servers (firecrawl, github, reddit, youtube, hn, gcal, X read adapter)
- **Serving/gating**: Cloudflare — Pages dashboard + D1 queue + Access (single email) + Tunnel

## Layout
```
infra/cmo-agent/   Terraform/OpenTofu — Hetzner box + CF Tunnel + Access (validated)
skills/            Hermes SKILL.md — opportunity-rank + enrichment logic
mcp/               MCP data-port config
dashboard/         suggestion-queue app (Cloudflare Worker + UI) — schema + API + UI
docs/              architecture
```

## Quickstart (infra)
```bash
cd infra/cmo-agent
cp terraform.tfvars.example terraform.tfvars   # set account_id, ssh_source_ips
export CLOUDFLARE_API_TOKEN=… HCLOUD_TOKEN=… AWS_ACCESS_KEY_ID=… AWS_SECRET_ACCESS_KEY=…
export TF_VAR_tunnel_secret=$(openssl rand -base64 32)
make init && make plan     # review before apply
```

## Status
Codified + validated: infra module, Hermes skills, MCP config, docs, and the dashboard
app (Worker API + UI + D1 schema). Not yet done: Hermes install cmd (see infra README),
first `tofu apply`, and deploying the dashboard (`dashboard/README.md`).
See [AGENTS.md](AGENTS.md) for the map.

## Security
Public repo — **no credentials committed** (verified across full history; the pasted API tokens never entered git). The CF **account id** appeared in an early commit's backend config and remains in history — an identifier, not a credential (access still needs the R2 keys, which are env-only). New state config lives in a git-ignored `backend.hcl`. **Recommended: `use_doppler=true`** so runtime secrets never touch TF state. gitleaks runs in CI + locally (`scripts/secret-scan.sh`).

## Domain
`chorus.barundebnath.com` (landing, public) · `chorus-app.` (dashboard) · `chorus-hermes.` (agent UI) · `chorus-ssh.` (SSH) — every gated surface behind Cloudflare Access to `barundebnath91@gmail.com`. One-level hosts → free Universal SSL.
