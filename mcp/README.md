# MCP data ports

Each external platform = one MCP server exposing read tools; Hermes skills orchestrate
them. `mcp.json` is a representative config — verify exact package names against
`modelcontextprotocol/servers` and awesome-mcp before install.

| Port | Data | Auth | Cost | Risk |
|---|---|---|---|---|
| research (linkup/firecrawl) | web / search | key | usage | clean — **swappable** via `box/research.py` (`RESEARCH_PROVIDER`) |
| github | repos, dev activity | PAT | free | clean |
| reddit | posts, user history | OAuth | free | clean |
| youtube | video meta + transcripts | key | free quota | clean |
| hn | HN posts/comments | Algolia public | free | clean (thin MCP/firecrawl) |
| gcal | calendar | OAuth | free | clean |
| X read adapter | X reads | key | $0.15/1k (100k free) | grey |
| supermemory | memory backbone | key optional | **self-hosted local** (OSS) | clean — `SUPERMEMORY_BASE_URL` |

**Pin exact, verified package names + versions before first install** — `npx -y <unverified>` as
root on the brain box is a typosquat risk. LinkedIn/IG/TikTok (apify) is CUT — no place in a
zero-ban-risk product. Secrets via env / Doppler only. HN, X read adapter, apify may need a ~30-line thin MCP
wrapper around their REST API rather than a published server.
