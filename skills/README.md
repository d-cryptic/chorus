# Chorus — Hermes skills

SKILL.md files for the Chorus personal-CMO agent, copied into `~/.hermes/skills/` on the
runtime box. **Suggest-only**: the agent reads, ranks, drafts, and queues — it never posts
to X. You post manually.

| Skill | Role |
|---|---|
| `opportunity-rank` | core — score candidate tweets, draft replies, emit to the queue |
| `x-read-lane` | all X reads (timeline/targets/mentions), budget + delta gated |
| `enrich-target` | cross-platform context on a person → memory |
| `voice-model` | cached voice/persona synthesis for authentic drafts |
| `research-digest` | multi-source topic sweep → cited brief |
| `target-tiering` | deep/medium/shallow classification → sources + cadence |
| `delta-refresh` | re-scrape only what changed (TTL + hash) |
| `budget-guard` | gate metered scrapes against the daily ceiling |
| `rank-tune` | weekly — personalize weights/denylist from feedback + outcomes |
| `onboard-self` | day-0 cold start — build chorus:self (pillars, goals, voice) |
| `outcome-track` | measure how posted replies performed → reward for rank-tune |
| `morning-digest` | daily Telegram digest + cycle heartbeat/alert |

Data ports (MCP) live in `../mcp/`. Runtime + gating infra in `../infra/cmo-agent/`.
There is deliberately **no `x-write-lane`** — writes are manual.
