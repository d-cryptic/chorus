output "server_ipv4" {
  value       = hcloud_server.cmo.ipv4_address
  description = "Hetzner box public IPv4 (SSH only; no app ports exposed)."
}

output "ssh_command" {
  value       = "ssh root@${hcloud_server.cmo.ipv4_address}"
  description = "SSH in (key-only). Restrict ssh_source_ips to your IP for real use."
}

output "ssh_via_cloudflare" {
  value       = "cloudflared access ssh --hostname ${var.ssh_hostname}"
  description = "Gated SSH through Cloudflare Access — no public port needed once enable_public_ssh=false."
}

output "hermes_url" {
  value       = "https://${var.hermes_hostname}"
  description = "Hermes UI/API — reachable ONLY after Cloudflare Access login as an allowed email."
}

output "dashboard_url" {
  value       = "https://${var.dashboard_hostname}"
  description = "Suggestion-queue dashboard (once the Pages app is deployed)."
}

output "access_allowed_emails" {
  value       = var.access_emails
  description = "The only identities that can pass the Access gate."
}

output "tunnel_token" {
  value       = cloudflare_zero_trust_tunnel_cloudflared.hermes.tunnel_token
  sensitive   = true
  description = "Injected into the box automatically; exposed for manual `cloudflared` runs if needed."
}

output "dashboard_access_aud" {
  value       = var.enable_dashboard_access ? cloudflare_zero_trust_access_application.dashboard[0].aud : null
  description = "Set as ACCESS_AUD in dashboard/wrangler.toml (with ACCESS_TEAM_DOMAIN) for JWT verification (F2)."
}
