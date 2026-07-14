# Chorus CMO-agent infra — Hetzner (Hermes) + Cloudflare Tunnel + Access

> Codifies the "brain" host for the Chorus personal-CMO agent. A Hetzner box runs
> the **Hermes daemon** + **cloudflared**; Cloudflare fronts it with a **Tunnel**
> (no public app ports) gated by **Access** to a **single identity**
> (`barundebnath91@gmail.com`).

Self-contained OpenTofu root module. Reuses the parent Cloudflare account + R2 state
bucket, with a **separate state key** (`chorus/cmo-agent.tfstate`). The R2 bucket + endpoint (which contains the CF account id) live in a git-ignored `backend.hcl` (copy `backend.hcl.example`), NOT in the public repo — applying this never
touches the parent's resources. The zone id for `barundebnath.com` is looked up via a
`cloudflare_zone` data source (no hardcoded id).

## Domain layout (one-level `chorus-*.barundebnath.com` → free TLS)

| Host | Role | Exposure |
|---|---|---|
| `chorus.barundebnath.com` | landing page | public (separate Pages app — not in this module) |
| `chorus-app.barundebnath.com` | dashboard | Access-gated, single email |
| `chorus-hermes.barundebnath.com` | Hermes agent UI/API | Tunnel + Access, single email |
| `chorus-ssh.barundebnath.com` | SSH | Cloudflare-gated (`cloudflared access ssh`) |

## What it creates

- `hcloud_server` (`cax11`, ARM 4GB, fsn1) running Hermes + cloudflared
- `hcloud_firewall` — inbound SSH only (toggle), no app ports
- `cloudflare_zero_trust_tunnel_cloudflared` (+ config) → ingress for hermes UI **and** SSH
- `cloudflare_record` CNAMEs (proxied) for hermes + ssh hosts
- `cloudflare_zero_trust_access_application` + `_policy` for hermes / ssh / dashboard —
  each `include { email = var.access_emails }` = **only `barundebnath91@gmail.com`**

## Architecture

```
  you (barundebnath91@gmail.com)
        │  Cloudflare Access (One-time PIN / Google) — single-email allowlist
        ▼
  chorus-hermes / chorus-app / chorus-ssh . barundebnath.com  ── proxied CNAME → tunnel
        │
     Cloudflare Tunnel (outbound from box; NO inbound app ports)
        ▼
  ┌──────────── Hetzner cax11 (fsn1) ────────────┐
  │  cloudflared ─ Hermes (UI :3000) ─ ssh :22   │
  │  /etc/hermes/hermes.env  (OpenRouter, …)     │
  │  ufw deny-inbound; public :22 = bootstrap    │
  └───────────────────────────────────────────────┘
```

## Prerequisites (env — never commit secrets)

```bash
export CLOUDFLARE_API_TOKEN=...    # zone read + dns + access + tunnel on barundebnath.com
export HCLOUD_TOKEN=...            # Hetzner Cloud API token
export AWS_ACCESS_KEY_ID=...       # R2 S3 key (state backend)
export AWS_SECRET_ACCESS_KEY=...
export TF_VAR_tunnel_secret=$(openssl rand -base64 32)
# optional — baked into the box's Hermes env at first boot:
export TF_VAR_openrouter_api_key=...  TF_VAR_supermemory_api_key=...
export TF_VAR_candidate_api_key=...      TF_VAR_firecrawl_api_key=...
```

Then: `cp terraform.tfvars.example terraform.tfvars`, set `account_id`
(and ideally restrict `ssh_source_ips`).

## Usage

```bash
make init && make plan     # review
make apply                 # provision (~1–2 min; ~EUR 3.8/mo for cax11)
make output                # IPs, URLs, allowed emails
cloudflared access ssh --hostname chorus-ssh.barundebnath.com   # gated SSH
make destroy               # tear down
```

## Finish steps (verify-first, not codifiable)

1. **Hermes install** — set `hermes_install_cmd` (see
   <https://github.com/NousResearch/hermes-agent>) and re-apply, or SSH in and run it.
   If empty, the box comes up with cloudflared + `/opt/hermes/INSTALL_ME.txt`.
2. **UI port** — confirm Hermes listens on `hermes_ui_port` (default 3000); adjust + re-apply.
3. **Access login** — enable One-time PIN (or Google SSO) for the org in Zero Trust; the
   email allowlist is already codified here.
4. **Lock down SSH** — once `cloudflared access ssh` works, set `enable_public_ssh=false`
   and re-apply → SSH is tunnel-only, zero public surface.
5. **Landing + dashboard** — deploy `chorus.barundebnath.com` (public) and
   `chorus-app.barundebnath.com` (gated) as Cloudflare Pages apps separately.

## Security posture

- No public app surface — Hermes + SSH reachable only through the tunnel, behind
  Access, for one email. Public SSH is a bootstrap toggle you turn off.
- Key-only SSH, `ufw` deny-inbound, Hetzner firewall.
- Secret caveat — `TF_VAR_*_api_key` land in cloud-init + TF state. Fine for a solo
  box; for stricter hygiene, leave blank and pull from Doppler on the box.

## Cost

~EUR 3.8/mo (cax11) ≈ $0.14/day; Cloudflare Tunnel + Access + DNS free at this scale.
Fits the ~$0.20–0.65/day Chorus envelope.
