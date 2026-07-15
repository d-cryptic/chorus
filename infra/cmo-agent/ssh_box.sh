#!/usr/bin/env bash
# SSH to the Chorus box over the Cloudflare tunnel (public port 22 is CLOSED).
#
# Two ways in, both work:
#   1. This script — non-interactive, uses the Access service token in
#      .ssh_service_token (git-ignored). No browser.
#   2. Browser SSO — omit the token file and cloudflared opens an Access login
#      for the owner email:
#        ssh -o ProxyCommand='cloudflared access ssh --hostname %h' root@chorus-ssh.barundebnath.com
#
# Break-glass if the tunnel is ever down: Hetzner Cloud console (web VNC), or
# re-open public SSH with `enable_public_ssh = true` in terraform.tfvars + tofu apply.
#
# Usage:  ./ssh_box.sh              -> interactive shell
#         ./ssh_box.sh 'uptime'     -> run a command
set -euo pipefail
cd "$(dirname "$0")"
HOSTNAME_="${CHORUS_SSH_HOST:-chorus-ssh.barundebnath.com}"
KEY="${CHORUS_SSH_KEY:-$HOME/.ssh/id_ed25519}"

if [[ -f .ssh_service_token ]]; then
  set -a; . ./.ssh_service_token; set +a   # TUNNEL_SERVICE_TOKEN_ID/SECRET
fi

exec ssh -o "ProxyCommand=cloudflared access ssh --hostname %h" \
         -o StrictHostKeyChecking=accept-new \
         -i "$KEY" "root@${HOSTNAME_}" "$@"
