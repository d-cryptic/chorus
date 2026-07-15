# The Hetzner box that runs the Hermes daemon + cloudflared connector.
# It has NO public inbound app ports — all ingress rides the Cloudflare Tunnel
# (outbound-only), gated by Access. Only SSH (key-only) is optionally reachable.

resource "hcloud_ssh_key" "cmo" {
  name       = var.server_name
  public_key = file(pathexpand(var.ssh_public_key_path))
}

resource "hcloud_firewall" "cmo" {
  name = "${var.server_name}-fw"

  # Inbound SSH for bootstrap — toggle off once Cloudflare-gated SSH works (tunnel-only).
  dynamic "rule" {
    for_each = var.enable_public_ssh ? [1] : []
    content {
      direction  = "in"
      protocol   = "tcp"
      port       = "22"
      source_ips = var.ssh_source_ips
    }
  }

  # Allow inbound ICMP (ping) for basic diagnostics.
  rule {
    direction  = "in"
    protocol   = "icmp"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  # NOTE: no inbound rule for the Hermes UI port — the tunnel is outbound, so the app is never
  # exposed publicly. This hcloud firewall is the real backstop: if hermes_install_cmd runs
  # Docker, published ports would bypass the box's ufw, so keep app ports OUT of this allow-list.
}

resource "hcloud_server" "cmo" {
  name         = var.server_name
  server_type  = var.server_type
  image        = var.image
  location     = var.location
  ssh_keys     = [hcloud_ssh_key.cmo.name]
  firewall_ids = [hcloud_firewall.cmo.id]

  labels = {
    project = "cmo-agent"
    role    = "hermes-runtime"
  }

  public_net {
    ipv4_enabled = true
    ipv6_enabled = true
  }

  # SAFETY: user_data only takes effect at FIRST BOOT, but the provider marks it
  # ForceNew — so any drift (e.g. applying without the same TF_VAR_* secrets in env)
  # silently plans "destroy + recreate" and would wipe the live box (/opt/chorus, the
  # memory DB, cron). Ignoring it makes a stray `tofu apply` non-destructive. To
  # genuinely re-provision, taint/replace the server deliberately.
  lifecycle {
    ignore_changes = [user_data, ssh_keys, image]
  }

  # First-boot: install cloudflared (joins the tunnel with the provider-issued
  # token → auto-wires ingress), harden SSH, drop Hermes env, run the install cmd.
  user_data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    tunnel_token        = cloudflare_zero_trust_tunnel_cloudflared.hermes.tunnel_token
    cloudflared_arch    = var.cloudflared_arch
    cloudflared_version = var.cloudflared_version
    hermes_ui_port      = var.hermes_ui_port
    hermes_install_cmd  = var.hermes_install_cmd
    openrouter_api_key  = var.openrouter_api_key
    supermemory_api_key = var.supermemory_api_key
    candidate_api_key   = var.candidate_api_key
    firecrawl_api_key   = var.firecrawl_api_key
    ingest_token        = var.ingest_token
    telegram_bot_token  = var.telegram_bot_token
    telegram_chat_id    = var.telegram_chat_id
    github_token        = var.github_token
    reddit_client_id    = var.reddit_client_id
    reddit_secret       = var.reddit_secret
    youtube_api_key     = var.youtube_api_key
    use_doppler         = var.use_doppler
    doppler_token       = var.doppler_token
    healthcheck_url     = var.healthcheck_url
  })
}
