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

---

## Part 2 (later the same day): the reward signal was dead three ways over

Everything above was found by reading the user's DATA. This half was found by not believing
the logs.

**Every bug that actually hurt today REPORTED SUCCESS.** None threw. That is the through-line:

| what it printed | what was true |
|---|---|
| queue merely looked idle | `fast_lane` crashed on EVERY run, 144x/day |
| `matched+measured 4` | every outcome row was an ORPHAN keyed to a feedback id; `verified` was always 0 |
| `spent $0.003 of $10.0` | a fake ceiling: dry-runs made REAL paid calls the breaker never saw |
| `10 posted` | 4. `posted` means the user CLICKED; the intent URL only opens X's composer |
| voice/niche/repeat "nothing to say" | three `except: pass` sites swallowing real failures |

### The outcome chain (three independent bugs, each hiding the next)
1. `outcome_track` discovered **replies only** -> 7 of 10 posts structurally invisible
2. it keyed writes on **`f.id`** (the FEEDBACK autoincrement) because `/api/box/feedback`
   never returned `s.id` -> every row an orphan, joining to nothing
3. `posted` meant **clicked, not published** -> 6 of 10 never reached X

Any ONE would have emptied the reward signal. All three printed success. Fixed; 4 outcomes
now attach, and the insights engine immediately produced real claims from data it already
had — including `best_time: 01:00`, which independently confirms the 01:00 session found in
the feedback clock, from a different code path.

### What I retracted
I shipped "you post statements, not questions" from claimed-posted data. Re-derived from
VERIFIED posts the MIN_SAMPLE guard correctly refuses: *4 posted, need 5. No claims.* The
guard was right all along; I fed it a lie. Live doc retracted (202 chars -> 0).

### Testing: the suite could not fail
Mutation audit (`box/mutation_audit.py`, committed and repeatable) found **MIN_SAMPLE pinned
by NOBODY** — all 53 insights tests passed `min_sample=` explicitly, so the DEFAULT was
untested. Someone could set it to 1 and stay green while the engine invented claims from n=1.
Also: `already_said`'s production branch never entered; the founding invariant (**Chorus never
posts**) had NO test at all; `session_mine` (private sessions -> public tweets) had ZERO tests
while its own threat model says the output is a public tweet.

Now 14/14 mutants caught, including both suggest-only attacks and both redaction layers.

**Four decorative tests found**, two by hand and two by mutation. The only way to know a test
works is to break it on purpose:
- the provider-leak test: playwright's `webServer` runs `npm run build` on start and silently
  rebuilt over the injected leak, so it "passed"
- the X-blue test: scanned only the queue tab, where the offending bars do not exist
- MIN_SAMPLE and the repeat guard: defaults never asserted

## The trap that bit me FOUR times

A rule gets caught by its own text:
- the em-dash ban rule has to contain an em-dash
- the provider-leak test has to name the provider
- `mutation_audit.py` contains an `api.x.com` POST as an injectable mutant, so the invariant
  scanner flagged the detector itself
- the `or f.get("id")` assertion matched my own COMMENT explaining what not to do

Any tool that must DESCRIBE a violation to hunt it will trip a naive detector. Scan production
only; check the code line, not the prose.

## And the one I reproduced inside its own fix

`str.replace` with guessed indentation is a SILENT NO-OP. While fixing the silent-failure
class, three of my replaces did nothing and reported nothing, leaving `failed`/`stuck`
declared and read with nothing appending — warnings that could never fire, worse than the
silence they replaced. Caught by a dead-code check (appends vs reads). **Assert every
replace, or patch by line number.**

## Next session

1. `useful_account`: @TheAhmadOsman 3/4 posted, @tom_doerr 0/6 — n=4, below MIN_SAMPLE. The
   guard is RIGHT. Do not override it.
2. Follower attribution is n=2. Replies are 25% accepted but they are the growth mechanism.
   Do not amputate the lane on a coin flip.
3. Threads/longform have never fired on real HN input — correctly: headlines are single-beat.
   They need richer input (captures, session-mined).
4. Watch `"the real test is whether..."` (2 of ~180 drafts). Same shape as the tic that hit 14.
5. **Open question, not a code bug:** a 40% click-to-publish rate. Either the user reconsiders
   at X's composer (legitimate, and worth capturing as its own signal) or the intent flow
   loses drafts. Do not assume which.
