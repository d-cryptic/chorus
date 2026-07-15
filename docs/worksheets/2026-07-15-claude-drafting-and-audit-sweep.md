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
