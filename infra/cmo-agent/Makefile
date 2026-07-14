# CMO-agent infra (Hetzner + Cloudflare Tunnel + Access). Requires OpenTofu (tofu).
# Env expected: HCLOUD_TOKEN, CLOUDFLARE_API_TOKEN, AWS_ACCESS_KEY_ID/SECRET (R2 state),
# TF_VAR_tunnel_secret, and optionally TF_VAR_*_api_key. See README.md.

.PHONY: init plan apply destroy fmt validate output ssh token

init:
	tofu init

fmt:
	tofu fmt -recursive

validate:
	tofu validate

plan:
	tofu plan

apply:
	tofu apply

destroy:
	tofu destroy

output:
	tofu output

ssh:
	@ssh root@$$(tofu output -raw server_ipv4)

token:
	@tofu output -raw tunnel_token
