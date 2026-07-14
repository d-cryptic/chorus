#!/usr/bin/env bash
# Quick local secret scan (full history, excluding this script's own patterns). Exit 1 on hits.
set -euo pipefail
cd "$(dirname "$0")/.."
hits=$(git log --all -p -- ':(exclude)scripts/secret-scan.sh' ':(exclude).gitleaks.toml' | grep -inE \
  'sk-or-v1|sk-[a-zA-Z0-9]{40}|ghp_[A-Za-z0-9]{36}|gho_[A-Za-z0-9]{36}|AKIA[0-9A-Z]{16}|-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY|xoxb-[0-9]|OPENROUTER_API_KEY=[A-Za-z0-9]|HCLOUD_TOKEN=[A-Za-z0-9]' \
  | grep -vE 'REPLACE|example|\$\{|testtok' || true)
if [ -n "$hits" ]; then echo "❌ potential secrets:"; echo "$hits"; exit 1; fi
echo "✅ no secrets found in history"
