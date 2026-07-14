# ---------- Cloudflare account / zone (your existing CF account) ----------
variable "account_id" {
  type        = string
  description = "Cloudflare account id (same as parent infra)."
}

variable "zone_name" {
  type        = string
  default     = "barundebnath.com"
  description = "Cloudflare zone. zone_id is looked up from this via a data source."
}

# ---------- The single-identity gate (the whole point) ----------
variable "access_emails" {
  type        = list(string)
  default     = ["barundebnath91@gmail.com"] # ONLY this identity may reach anything here
  description = "Emails allowed through Cloudflare Access. Deliberately just the owner."
}

# ---------- Hostnames ----------
variable "hermes_hostname" {
  type        = string
  default     = "chorus-hermes.barundebnath.com"
  description = "Private hostname fronting the Hermes UI/API on the box (via the tunnel)."
}

variable "dashboard_hostname" {
  type        = string
  default     = "chorus-app.barundebnath.com"
  description = "Hostname for the suggestion-queue dashboard (Cloudflare Pages, built later)."
}

variable "enable_dashboard_access" {
  type        = bool
  default     = true
  description = "Create the Access app gating the dashboard hostname (harmless before Pages exists)."
}

variable "ssh_hostname" {
  type        = string
  default     = "chorus-ssh.barundebnath.com"
  description = "Hostname for Cloudflare-gated SSH via `cloudflared access ssh` (no public port)."
}

# ---------- Hetzner server ----------
variable "server_name" {
  type    = string
  default = "cmo-hermes"
}

variable "server_type" {
  type        = string
  default     = "cax11" # ARM Ampere, 2 vCPU / 4GB, ~EUR 3.8/mo. Bump to cax21 (8GB) for heavy browser-use.
  description = "Hetzner server type. ARM (cax*) only in fsn1/nbg1/hel1."
}

variable "location" {
  type    = string
  default = "fsn1" # Falkenstein (EU). ARM available here.
}

variable "image" {
  type    = string
  default = "ubuntu-24.04"
}

variable "cloudflared_version" {
  type        = string
  default     = ""
  description = "Pin cloudflared (e.g. \"2025.1.0\") for reproducibility; empty = latest. See github.com/cloudflare/cloudflared/releases."
}

variable "cloudflared_arch" {
  type        = string
  default     = "arm64" # matches cax* (ARM). Use "amd64" for cx*/ccx* (x86).
  description = "cloudflared .deb architecture — MUST match server_type CPU arch."
}

variable "ssh_public_key_path" {
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
  description = "Public key uploaded to Hetzner + injected into the box for SSH."
}

variable "ssh_source_ips" {
  type        = list(string)
  default     = ["0.0.0.0/0", "::/0"] # SECURITY: restrict to your IP(s), e.g. ["203.0.113.4/32"].
  description = "CIDRs allowed to SSH (port 22). Key-only auth is enforced regardless."
}

variable "enable_public_ssh" {
  type        = bool
  default     = true
  description = "Open public SSH (22, restricted to ssh_source_ips) for bootstrap. Set false once Cloudflare-gated SSH (ssh_hostname) works → SSH becomes tunnel-only."
}

# ---------- Cloudflare Tunnel ----------
variable "tunnel_secret" {
  type        = string
  sensitive   = true
  description = "Tunnel secret — `openssl rand -base64 32`. Pass via TF_VAR_tunnel_secret."

  validation {
    condition     = length(var.tunnel_secret) >= 32
    error_message = "tunnel_secret must be >= 32 chars — `openssl rand -base64 32`."
  }
}

variable "hermes_ui_port" {
  type        = number
  default     = 3000
  description = "Local port Hermes serves its UI/API on. VERIFY against Hermes docs and adjust."
}

# ---------- Hermes install + secrets (baked into first-boot cloud-init) ----------
variable "hermes_install_cmd" {
  type        = string
  default     = ""
  description = "Official Hermes install command (see github.com/NousResearch/hermes-agent). If empty, the box comes up with cloudflared only + an INSTALL_ME marker."
}

variable "openrouter_api_key" {
  type      = string
  default   = ""
  sensitive = true
}
variable "supermemory_api_key" {
  type      = string
  default   = ""
  sensitive = true
}
variable "candidate_api_key" {
  type      = string
  default   = ""
  sensitive = true
}
variable "firecrawl_api_key" {
  type      = string
  default   = ""
  sensitive = true
}

# G9 — the rest of what the skills/box actually need.
variable "ingest_token" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Bearer secret the box uses to write the queue (Worker /api/ingest). Also `wrangler secret put INGEST_TOKEN`."
}
variable "telegram_bot_token" {
  type      = string
  default   = ""
  sensitive = true
}
variable "telegram_chat_id" {
  type        = string
  default     = ""
  description = "Your chat id — the bot MUST ignore messages from anyone else."
}
variable "github_token" {
  type      = string
  default   = ""
  sensitive = true
}
variable "reddit_client_id" {
  type    = string
  default = ""
}
variable "reddit_secret" {
  type      = string
  default   = ""
  sensitive = true
}
variable "youtube_api_key" {
  type      = string
  default   = ""
  sensitive = true
}

variable "use_doppler" {
  type        = bool
  default     = false
  description = "Pull app secrets from Doppler at runtime instead of baking them into cloud-init/TF state (stricter hygiene)."
}
variable "doppler_token" {
  type      = string
  default   = ""
  sensitive = true
}
variable "healthcheck_url" {
  type        = string
  default     = ""
  description = "Optional liveness ping URL (e.g. healthchecks.io) — box cron pings every 15m (G5)."
}
