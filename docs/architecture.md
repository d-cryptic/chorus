# Chorus — architecture

Detailed summary (first lines are the greppable overview): Chorus is a single-user,
suggest-only personal CMO. It reads X + enriches from many platforms, ranks which tweets
are worth commenting on, drafts replies in your voice, and queues them — you post
manually. Runtime = Hermes daemon on a Hetzner box; Cloudflare hosts the dashboard, queue
store, and gates everything to one email. Cost target ~$0.20–0.65/day. No automated
posting → zero ban risk. Data ports = MCP; logic = Hermes SKILL.md; memory = Supermemory.

## Funnel (suggest-only)
```
candidates (500–2000/day)  → gates → score+draft (top 15–25) → you copy/post
   x-read-lane                opportunity-rank                   dashboard / Telegram
        └───────────── feedback (posted/edited/dismissed) → memory → weekly rank-tune
```

## Layers
- **Runtime**: Hermes (learning loop, cron, web/search, MCP) on Hetzner `cax11` (fsn1).
- **Data ports (MCP)**: firecrawl, github, reddit, youtube, hn, gcal, X read adapter, supermemory. See `../mcp/`.
- **Logic (skills)**: opportunity-rank, x-read-lane, enrich-target, voice-model,
  research-digest, target-tiering, delta-refresh, budget-guard. See `../skills/`.
- **Memory**: Supermemory — person records, edges, voice models, pillars, `profile()` grounding.
- **App backend**: Convex — reactive state (queue/feedback/spend/settings) + durable workflows
  (enrich/rank/insights pipelines) + live dashboard data. See [data-architecture.md](data-architecture.md)
  for the full Supermemory×Convex split across every PRD flow.
- **Serving/gating (Cloudflare)**: Pages dashboard + D1 queue + Access (single email) +
  Tunnel. See `../infra/cmo-agent/`.

## Domain (one-level hosts → free TLS; gated to barundebnath91@gmail.com)
`chorus.` landing (public) · `chorus-app.` dashboard · `chorus-hermes.` agent UI · `chorus-ssh.` gated SSH. Each gated host has its own Access app (no wildcard — kept one-level for free certs).

## Cost
Reads $0.15 + LLM $0.05–0.30 + enrichment $0.05–0.30 (bounded, delta) + host ~$0.14 +
Cloudflare free = **~$0.20–0.65/day**. Writes = $0 (manual). Skip Supermemory Pro.

## Reads & ToS (honest)
Candidate sources = target-lists + keyword search + mentions via the private X read adapter (unofficial,
public-only, **no user credentials**). Accepted grey-area risk; **your account can't be banned
for reading** (you post by hand) — a core safety property. Queue store: **M0 = D1 (shipped),
M1 = Convex**.

## Key decisions
- **Suggest-only** — human posts; removes write cost + ban risk. No `x-write-lane`.
- **Hermes on Hetzner** (Option A) — keeps off-the-shelf value; CF for everything else.
- **Single-email Access gate** — every surface behind Cloudflare Access.
- Design detail lives in the companion artifacts (feasibility, enrichment spec,
  opportunity-rank spec) under `~/.claude/artifacts/`.
