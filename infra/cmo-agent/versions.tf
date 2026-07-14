# CMO-agent runtime infra — Hetzner box (Hermes daemon) + Cloudflare Tunnel + Access.
# Self-contained OpenTofu root module. Reuses the SAME Cloudflare account / zone /
# Access org / R2 state backend as your existing CF account, but a SEPARATE state
# key, so applying this never touches the parent's D1/KV/R2/api resources.
#
# Auth (never committed — pass via env):
#   CLOUDFLARE_API_TOKEN                        → cloudflare provider (tunnel + access + dns)
#   HCLOUD_TOKEN                                → hcloud provider (Hetzner server)
#   AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY   → R2 state backend (CF R2 S3 keys)
#   TF_VAR_tunnel_secret                        → `openssl rand -base64 32`
#   TF_VAR_openrouter_api_key / _supermemory_api_key / _candidate_api_key / _firecrawl_api_key (optional)

terraform {
  required_version = ">= 1.6"

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.52" # match parent module (../versions.tf) — zero_trust_* resource names
    }
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.48"
    }
  }

  # STATE: local by default (simplest for a solo v1 — no R2 S3 keys needed). The private R2
  # bucket `chorus-tfstate` exists for when you want remote state: uncomment the block below,
  # `cp backend.hcl.example backend.hcl` (bucket + account-id endpoint), generate R2 S3 keys
  # (dashboard -> R2 -> Manage API Tokens -> AWS_ACCESS_KEY_ID/SECRET), then
  # `tofu init -backend-config=backend.hcl -migrate-state`.
  #
  # backend "s3" {
  #   key    = "chorus/cmo-agent.tfstate"
  #   region = "auto"
  #   skip_credentials_validation = true
  #   skip_region_validation      = true
  #   skip_requesting_account_id  = true
  #   skip_metadata_api_check     = true
  #   skip_s3_checksum            = true
  #   use_path_style              = true
  # }
}

provider "cloudflare" {
  # api_token read from CLOUDFLARE_API_TOKEN
}

provider "hcloud" {
  # token read from HCLOUD_TOKEN
}
