# Chorus — system diagram

```mermaid
flowchart TB
  subgraph X["X / Twitter"]
    ANCH["24 anchor accounts<br/>(100k–560k followers)"]
    TL["your timeline<br/>861 following → 120 on-pillar"]
  end

  subgraph BOX["Hetzner cpx22 · €3.8/mo · SSH is tunnel-only"]
    FAST["⚡ fast_lane · every 10m<br/>&lt;120m old, &lt;60 replies<br/>reach × earliness × freshness"]
    DEEP["ranker · daily<br/>timeline + targets, breadth"]
    POST["post_gen · daily<br/>captures &gt; trends &gt; evergreen"]
    MINE["session_mine · your own work<br/>4-layer redaction, fails closed"]
    MEM[("chorus-memory<br/>SQLite + BM25<br/>Supermemory-API-compatible")]
    BUD["budget guard<br/>per-call gate · kill-switch"]
  end

  subgraph CF["Cloudflare"]
    W["Worker + D1"]
    ACC["Access gate<br/>1 email"]
  end

  UI["dashboard<br/>X-faithful drafts<br/>j/k/p/e/x triage"]
  HUMAN(["YOU post it<br/>— always"])

  ANCH --> FAST
  TL --> DEEP
  HN["HackerNews · GitHub"] --> POST
  CC["Claude Code sessions"] --> MINE
  MINE --> POST

  FAST & DEEP & POST --> JUDGE{"LLM judge<br/>grounded · human<br/>distinct · voice"}
  JUDGE -->|"fabricated → rejected"| X2["✗"]
  JUDGE --> W
  MEM <-->|"voice RAG<br/>repetition guard"| JUDGE
  BUD -.->|"gates every paid call"| FAST & DEEP & POST

  W --> ACC --> UI --> HUMAN
  HUMAN -->|"posted / edited / dismissed"| W
  W -->|"what actually worked"| MEM
  FOLLOW["follower_track · hourly<br/>1,093 → 10,930"] --> W

  classDef never fill:#3b0d0d,stroke:#f4212e,color:#fff
  class X2 never
```

## What this actually is (claims you can defend)

- **Suggest-only.** No X write path exists. The agent drafts; you post. Zero ban risk.
- **~$0.15/day.** twitterapi.io reads + DeepSeek drafting, hard-gated by a per-call budget
  check and a kill-switch.
- **The growth thesis is cadence.** Replying 8-21h late earns ~0 impressions. The fast lane
  polls 24 anchors every 10 min and only surfaces tweets <120m old with <60 replies —
  measured live at 0 replies / 213k followers.
- **An LLM judge rejects fabrication.** `grounded=0` for any unverifiable first-person
  claim, because the drafter WILL invent "our logs show 37%" if you let it.
- **Memory is BM25 over what you actually posted** — powering voice priming and a
  repetition guard so it never re-suggests a take you already made.

## Honest footnotes (do NOT tag these)

- **Hermes** — designed for, never installed. `/opt/hermes/` holds one file: `INSTALL_ME.txt`.
  The box runs cron + plain Python. Tagging @NousResearch would be a false claim.
- **Supermemory** — not used. `chorus-memory` is a stdlib+SQLite service that merely speaks
  Supermemory's `/v3/documents` API, so upstream is a drop-in swap via `SUPERMEMORY_BASE_URL`.
  Tagging @supermemoryai would be a false claim.
