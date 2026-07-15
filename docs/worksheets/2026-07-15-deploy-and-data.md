# 2026-07-15 — deploy gap, cost bomb, and reading the user's data

**Status:** shipped and verified. 282 unit + 13 e2e green. Box in sync. 1,093 -> 1,095 followers.

## The lesson of this shift

Every real bug came from **reading the user's actual data**, not from reading code. Roughly
half my hypotheses were **wrong** and died on contact with a measurement. Suspect, then
measure, THEN act — announcing a suspicion as a finding cost credibility three times.

## What was actually broken

| bug | how it hid |
|---|---|
| `fast_lane` crashed on EVERY run (`list + tuple`, my own commit) | 60 fetched, 11 live, then died at the judge. 144x/day. Queue never grew. |
| The refresh icon fetches NOTHING (only re-reads D1) | Looks exactly like "get new stuff" to any human. |
| Fetch blind-reloaded after 90s against a 5-MIN cron | Reloaded before anything could happen, found nothing, looked broken. |
| Quiet hours vetoed an explicit human Fetch | The button silently did nothing in the exact window a night owl uses it. |
| Worker/D1/UI were never deployed | Box SENT `longform` into a column that did not exist. Silently dropped. |
| Reply expiry was a flat 48h | 15 of 22 queued replies were past 3h — the bar fast_lane calls "worthless". |
| `rank_tune` had NEVER run | Needs dismissals; user posts the good ones and IGNORES the rest (10 posted, 0 dismissed). |
| One borrowed phrase opened 14/174 drafts | style_mine extracted a TEMPLATE; the boundary forbade claims/numbers/topics, never WORDING. |
| I banned `ngl` and 🔥 on taste | They are in 3/10 POSTED drafts, incl. the best-performing post ever. |
| fast_lane throttled 01:00-07:59 | The user posts at 01:36 and 01:48. |
| `discover_anchors` re-proposed rejects 3 sessions running | The rejects lived in a DOC; nothing read it. |

## The cost bomb I armed and defused

Fixing the fast_lane crash turned a FREE no-op into the top line item: **$1.44/day against a
$0.65 ceiling** (~7 days of runway) because it re-fetched ~60 tweets every 10 minutes and
discarded them as `seen`. It rejects anything older than MAX_AGE_MIN on every run but FETCHED
all of history. Bounded to the usable window: **40 reads -> 1 (98%)**, misses ZERO live
tweets (verified: ages `[104, 133, 151, 172, ...]`, only one under 120min).

Projected tomorrow: **$0.19/day, 3.4x headroom.**

## Traps worth remembering

- `run.sh` sources `.env` AFTER the caller's env, so `OPENROUTER_MODEL=x ./run.sh` is
  SILENTLY IGNORED. Pass the model as argv.
- `INGEST_URL` IS the base. `.rsplit("/",1)[0]` chops the host and you get a DNS error that
  looks like a network fault.
- `getComputedStyle` returns `oklch()` here. Regex-parsing it gave "1.06:1, text invisible"
  and I nearly "fixed" a palette that measured 16.5:1. Paint it on a canvas instead.
- Playwright's `webServer` runs `npm run build` on start, so a leak injected into the BUILT
  bundle is silently overwritten and the test "passes". Inject at SOURCE.
- A failing suite contributes ZERO to a naive test count: the total DROPPED and looked like
  progress. Count failures explicitly.
- `emptyOutDir: true` would DELETE `review.html` + fonts (outDir is `../public`). Use a
  prebuild that clears only `assets/`.

## Next

1. `useful_account` says @TheAhmadOsman is 3/4 posted and @tom_doerr 0/6 — but he has n=4,
   below MIN_SAMPLE. Do NOT tune the target list until the buckets fill.
2. Watch `"the real test is whether..."` (2 of ~180 drafts). Same shape as the last tic.
3. Threads/longform still have NEVER fired on real HN input — correctly (headlines are
   single-beat). They need richer input: captures, session-mined material.
4. Follower attribution is n=2. Nowhere near enough to tune routes. Replies are 25% accepted
   but they are the growth mechanism; do not amputate them on a coin flip.
