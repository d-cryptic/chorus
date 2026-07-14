# Access gate for the suggestion-queue dashboard (Cloudflare Pages, built later).
# Creating the Access app now is harmless — it simply guards the hostname to the
# same single identity as soon as the Pages app is deployed on it. Toggle off with
# enable_dashboard_access=false if you'd rather add it with the Pages project.

resource "cloudflare_zero_trust_access_application" "dashboard" {
  count                = var.enable_dashboard_access ? 1 : 0
  account_id           = var.account_id
  name                 = "cmo-dashboard"
  domain               = var.dashboard_hostname
  type                 = "self_hosted"
  session_duration     = "24h"
  app_launcher_visible = true
}

resource "cloudflare_zero_trust_access_policy" "dashboard_owner" {
  count          = var.enable_dashboard_access ? 1 : 0
  account_id     = var.account_id
  application_id = cloudflare_zero_trust_access_application.dashboard[0].id
  name           = "allow-owner-only"
  precedence     = 1
  decision       = "allow"

  include {
    email = var.access_emails
  }
}
