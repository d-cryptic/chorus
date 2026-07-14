# Cloudflare Tunnel fronting the Hermes UI/API on the box — NO public exposure.
# Same shape as the parent module's dev tunnel (../tunnel.tf), gated by Access to
# the single owner identity. config_src=cloudflare → ingress managed remotely; the
# box's cloudflared just needs the token (wired via cloud-init).

data "cloudflare_zone" "this" {
  name = var.zone_name
}

resource "cloudflare_zero_trust_tunnel_cloudflared" "hermes" {
  account_id = var.account_id
  name       = "cmo-hermes"
  secret     = var.tunnel_secret
  config_src = "cloudflare"
}

resource "cloudflare_zero_trust_tunnel_cloudflared_config" "hermes" {
  account_id = var.account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.hermes.id

  config {
    ingress_rule {
      hostname = var.hermes_hostname
      service  = "http://localhost:${var.hermes_ui_port}"
    }
    ingress_rule {
      hostname = var.ssh_hostname
      service  = "ssh://localhost:22"
    }
    ingress_rule {
      service = "http_status:404" # required catch-all
    }
  }
}

resource "cloudflare_record" "hermes" {
  zone_id = data.cloudflare_zone.this.id
  name    = trimsuffix(var.hermes_hostname, ".${var.zone_name}")
  type    = "CNAME"
  content = "${cloudflare_zero_trust_tunnel_cloudflared.hermes.id}.cfargotunnel.com"
  proxied = true
}

resource "cloudflare_zero_trust_access_application" "hermes" {
  account_id           = var.account_id
  name                 = "cmo-hermes"
  domain               = var.hermes_hostname
  type                 = "self_hosted"
  session_duration     = "24h"
  app_launcher_visible = false
}

resource "cloudflare_zero_trust_access_policy" "hermes_owner" {
  account_id     = var.account_id
  application_id = cloudflare_zero_trust_access_application.hermes.id
  name           = "allow-owner-only"
  precedence     = 1
  decision       = "allow"

  include {
    email = var.access_emails # ONLY barundebnath91@gmail.com by default
  }
}

# ---- Cloudflare-gated SSH: chorus-ssh.barundebnath.com via the same tunnel ----
resource "cloudflare_record" "ssh" {
  zone_id = data.cloudflare_zone.this.id
  name    = trimsuffix(var.ssh_hostname, ".${var.zone_name}")
  type    = "CNAME"
  content = "${cloudflare_zero_trust_tunnel_cloudflared.hermes.id}.cfargotunnel.com"
  proxied = true
}

resource "cloudflare_zero_trust_access_application" "ssh" {
  account_id           = var.account_id
  name                 = "chorus-ssh"
  domain               = var.ssh_hostname
  type                 = "self_hosted"
  session_duration     = "24h"
  app_launcher_visible = false
}

resource "cloudflare_zero_trust_access_policy" "ssh_owner" {
  account_id     = var.account_id
  application_id = cloudflare_zero_trust_access_application.ssh.id
  name           = "allow-owner-only"
  precedence     = 1
  decision       = "allow"

  include {
    email = var.access_emails
  }
}
