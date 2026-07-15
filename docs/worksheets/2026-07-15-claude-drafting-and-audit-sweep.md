# 2026-07-15 — Claude drafting via subscription + a full audit sweep

**Status:** 21 commits + box fixes, deployed, validated (box 408/laptop 531/e2e 23, zero drift).
Claude OAuth DONE; blocked on subscription being OUT OF USAGE. Guarded activate script ready.
deepseek active meanwhile. 1,095 followers.

## Goal

User: "a better model (claude/codex/grok) to create tweets" — using their SUBSCRIPTION tokens,
not per-token OpenRouter ("noooo dont use openrouter"). Plus the nakama "playbooks" idea.

## The one lesson (again)

Verify against LIVE DATA before fixing. Two audit findings were FABRICATED and would have
broken working code: discover_anchors `followers`-vs-`followers_count` (live: 861/861 have
`followers`), and a raw sub-token "working" (it authenticates but rate-limits on the raw API).
A subagent even fabricated "all four agents reported" and retracted it. Measure, then act.

## Claude drafting — how it works now

- The subscription token path: a raw `sk-ant-oat` AUTHENTICATES but is hard-rate-limited on
  api.anthropic.com. Subscription auth ONLY works through the SANCTIONED client (the CLI, or
  Hermes emulating it). Proven: `claude -p` drafts cleanly, $0, no rate limit.
- Two backends added (box/hermes_backend.py), dispatched by `_chat()` in post_gen:
  - `CHORUS_DRAFT_PROVIDER=cli:claude|grok|codex` — shells to the logged-in CLI (laptop).
  - `CHORUS_DRAFT_PROVIDER=hermes:<provider>:<model>` — `hermes -z ... --safe-mode` (box).
- Both return the OpenRouter shape so draft_post parses unchanged; prompt is one argv element
  (no shell injection); failure raises so the drafter degrades, never emits an empty draft.
- scrub() now strips a LEADING vocative tell ("bro a 27B..." -> "a 27B...").
- Bake-off (full Supermemory context): Claude Sonnet 4.6 clean + sharper than deepseek;
  gpt-5 failed JSON 2/3. See [[drafter-model-choice]] memory.

## Claude drafting — DONE except the subscription is out of usage

The OAuth completed: `hermes auth add anthropic` succeeded and the FIRST draft test reached the
Claude API -> it returned "You're out of extra usage. Add more at claude.ai/settings/usage."
That is the wall: the Claude subscription has NO usage left, so drafting cannot run yet.

Two user-side steps remain, in order:
1. Restore Claude usage (wait for the reset, or add usage at claude.ai/settings/usage).
2. Re-auth if needed (my premature pkill of the auth process left the credential unreadable:
   `hermes -z --provider anthropic` now reports "No Anthropic credentials found"). Clean re-auth:
     tmux new-session -d -s hauth "hermes auth add anthropic --no-browser"
     tmux capture-pane -t hauth -p -J | grep -oE "https://claude.ai/oauth/authorize\S+"   # open, approve
     tmux send-keys -t hauth "<code>" Enter        # then DO NOT kill the session -- let it finish
3. Activate SAFELY: `/opt/chorus/box/run.sh bash activate_claude.sh`. It tests a real Claude
   draft and ONLY sets CHORUS_DRAFT_PROVIDER=hermes:anthropic:claude-sonnet-4.6 if it succeeds
   -- so it never enables a broken provider. Installed and verified to DECLINE while unavailable.

Until then the drafter stays on deepseek/OpenRouter (working). The cli:claude / cli:grok
backends also remain available where a CLI is logged in.

## Bugs fixed this shift (all deployed)

| bug | how it hid | serves |
|---|---|---|
| Quote drafts built as REPLIES (`&in_reply_to=` not `&url=`) | 6/6 quotes never reached X vs 8/8 posts/replies; "posted" = the CLICK | GROWTH |
| Regenerated draft routed on the OLD draft's failing scores | judge hiccup -> good draft silently DROPPED | quality |
| Insights never decayed (status forced 'active', created_at reset each pass) | stale claims served forever; decay age reset to ~0 | dashboard |
| Outcome POST unguarded -> one 500 killed the fallback that measures 8/8 | rank_tune's reward stayed empty; the loop never learned | learning |
| Freshness FAILED OPEN (unparseable ts -> now) | a provider format change would make every tweet look fresh+viral | relevance |
| Handle filter `isalnum()` dropped 26% of the graph (every `_` handle) | @tom_doerr etc. silently excluded from discovery | GROWTH |
| Quiet-hours on box UTC clock in fast_lane/post_gen (half-migration) | would refuse during waking hours, 5.5h inverted, once enabled | GROWTH |
| Mirror watermark parked; playbook flush inside `if doc:`; budget holes | off-ledger spend / re-POSTs / silent | correctness |

## Playbooks (nakama idea)

Already the architecture: style_mine (mine others -> chorus:niche) + contrast (your style vs
theirs) + synthesize_playbook (-> playbook table). Was dormant (contrast/taste never ran due
to an entry-point-order bug, fixed earlier). Verified running end-to-end; thin data (theirs=1)
until a fuller mine.

## Traps worth remembering

- SSH stdin over the cloudflared tunnel is flaky; use `base64 <file | tr -d '\n'` as an ARG,
  not piped stdin. tmux survives across calls for interactive flows (OAuth).
- macOS has no `timeout`; a loop guarded on it silently runs 0 iterations and reports green.
- `npm run build` (vite) does NOT typecheck — it shipped an undefined name as "✓ built".
  Now gated: `tsc --noEmit && vite build`, plus a predeploy check that refuses "REPLACE" vars.
- candidate_source.py / discover graph files are git-ignored (provider details) — box-only.
- Piecemeal base64 deploys SILENTLY DESYNC the box: this shift left 6 files stale (tests +
  hermes_backend), so the box ran different code than committed. End-of-shift validation
  caught it. ALWAYS finish with `md5sum *.py` box-vs-laptop + a full on-box suite run.


## 2026-07-16 continuation -- content modes, RAG, budget, GEO

Massive feature build after Claude/grok/codex drafting landed.

- **15 content modes** (3 batches x 5 parallel subagents): short, sarcastic, research, longform,
  thread, contrarian, story, question, quote, listicle, humor, announcement, prediction,
  explainer, analogy. Each = a craft brief + model_pref, in box/content_modes.py. grok for the
  punchy/X-native modes, codex for the structured/faithful ones (cli:codex), env-overridable.
  codex->grok fallback so a slow codex never loses a cron draft.
- **Mode auto-selection**: classify_mode() (grok, $0) picks the mode per idea from the shape's
  candidates. Verified: news->announcement, mockable->sarcastic, relatable->humor. CHORUS_AUTO_MODE=0
  disables; CHORUS_FORCE_MODE overrides.
- **Full draft context** (the "are they getting memory/research/analytics" audit): every draft now
  carries memory (voice/niche/posts from Supermemory) + <link> real-time grounding (link_context,
  was MISSING for original posts) + <research> gated web search + <what_works> own-outcome insights.
- **Semantic RAG**: the store was already semantic (real Supermemory embeddings); the QUERY was by
  pillar names. Now voice_context is queried by the IDEA/tweet content -> per-idea nearest-neighbour
  over your own posts. Both post_gen (originals) and ranker (per-reply).
- **Budget phantom-cost fix**: subscription LLM ops are $0 (real cost is the flat sub fee), so they
  no longer eat the read ceiling. This was why "the dashboard stopped loading new tweets". Ceiling is
  now managed in the dashboard (spend/ceiling stat + inline editor), not a D1 hack.
- **Giphy**: activated + rate-limited to 100/hr (sliding window), rendered in the UI with attribution.
- **GEO agent** (box/geo.py, weekly): asks grok who the niche voices are, checks if you are cited,
  scores visibility, names the gaps -> geo_visibility insight.

Suite: box 517 + geo 6, laptop parity. codex-via-Hermes is blocked on a separate `hermes auth add
openai-codex` (interactive) -- cli:codex kept, env-swappable via CHORUS_CODEX_PROVIDER.
