# AGENTS.md — Chorus router

Chorus = single-user, **suggest-only** personal CMO: read X + enrich from many platforms,
rank which tweets to comment on, draft replies in your voice, queue them — **you post
manually** (no automated writes → zero ban risk). Runtime = Hermes on Hetzner; **Convex** = reactive backend + durable workflows; **Supermemory**
= semantic/identity memory; **Cloudflare** gates everything to `barundebnath91@gmail.com`. Target
~$0.20–0.65/day. See [docs/data-architecture.md](docs/data-architecture.md) for who-owns-what per flow.

## Map
| Need | Go to |
|---|---|
| Architecture overview | [docs/architecture.md](docs/architecture.md) |
| Runtime + gating infra (Terraform) | [infra/cmo-agent/](infra/cmo-agent/) · [README](infra/cmo-agent/README.md) |
| Hermes skills (logic) | [skills/](skills/) · [README](skills/README.md) |
| **The ranker (product core, tested)** | [box/ranker.py](box/ranker.py) · [README](box/README.md) |
| MCP data ports | [mcp/](mcp/) · [mcp.json](mcp/mcp.json) |
| Dashboard + queue schema | [dashboard/](dashboard/) · [schema.sql](dashboard/schema.sql) |
| Memory (Supermemory) integration | [docs/memory.md](docs/memory.md) |
| **Data architecture — Supermemory × Convex split, per PRD flow** | [docs/data-architecture.md](docs/data-architecture.md) |
| Review actions (Fable review triage) | [docs/review-actions.md](docs/review-actions.md) |
| Data policy (retention / deletion) | [docs/data-policy.md](docs/data-policy.md) |
| Backups & recovery | [docs/backups.md](docs/backups.md) |
| **Deploy runbook (you run it)** | [docs/runbook-deploy.md](docs/runbook-deploy.md) |
| Test catalog & verification | [docs/TESTS.md](docs/TESTS.md) |

## Conventions
- Suggest-only: never add an `x-write-lane` / autonomous posting without an explicit decision.
- Secrets via env / Doppler only — never commit. Terraform state in R2.
- Every public surface stays behind Cloudflare Access (single email).
