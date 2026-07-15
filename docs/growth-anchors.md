# Growth anchors — the follower FLOOR was filtering for timezone, not quality

Chorus is suggest-only, so every follower comes from the user replying EARLY to a post that
already has reach. Two things gate that, and only one is code:

1. the anchor must post while the user is AWAKE (IST, `CHORUS_TZ_OFFSET_H=5.5`);
2. the post must not already have hundreds of replies, or "early" is unreachable.

`discover_anchors.py --min-followers` defaulted to **60000** — cargo-culted from growth
advice written for large accounts. It was quietly destroying the search.

## Measured 2026-07-15 against the user's own graph (1,946 accounts)

| band | count | what is actually there |
|---|---|---|
| `<10k` | 1,665 | too small to amplify |
| `10-60k` | 212 | **the reachable cohort — was being filtered out** |
| `60-800k` | 63 | on-pillar: 35. **IST-signalled: 0** |
| `>800k` | 6 | unreachable whales (500+ replies in minutes) |

Awake-overlap measured from real post timestamps, not bios (bios lie; clocks don't):

| account | followers | awake overlap |
|---|---|---|
| @thdxr | 146,555 | 30% |
| @championswimmer | 80,970 | 14% |
| **@eatonphil** | 29,412 | **90%** |
| **@asmah2107** | 36,051 | **84%** |
| **@johncrickett** | 13,423 | **80%** |

**A high floor did not filter for quality. It filtered for the wrong timezone.** At 1,093
followers a 20k account is still ~20x amplification and far likelier to notice a reply.
Floor is now **12000**.

## The seed was biased too

`discover_anchors` seeds from *who your anchors reply to*. That pool inherits your anchors'
timezone: a US-centric anchor set can only return US-centric candidates. It structurally
cannot fix a timezone ceiling. With the old floor the whole tool returned **one** candidate
(@refikanadol — an AI *artist*: passes pillar keywords, fails pillar intent).

`--from-graph` adds a free, unbiased seed: `followings.json` + `followers.json` are already
on disk, zero API spend. The same run then returns **12** reachable candidates.

## Keyword match is not pillar intent — this stays human-reviewed

The tool proposes; a human confirms. Verified rejects, recorded so nobody re-adds them:

| rejected | why |
|---|---|
| @startgrowthhack | 172k followers but **0-11 likes/post** — engagement-farmed; would poison ranking |
| @tetsuoai | AI-hype/meme + @elonmusk replies, not technical |
| @refikanadol | AI artist; keyword-matches "AI", off-pillar in intent |
| @suryanshti777 | "Exploring AI & SaaS trends early" — 0 median likes |
| @vazekshitij | firmware + Manchester United |
| @hi_mrinal | bio says backend engineer; feed is croissants and banter |

Added (12): eatonphil, johncrickett, asmah2107, vivekgalatage, jayagup10, risingsayak (ML at
Hugging Face), gabrielchua (Codex @OpenAI), muratcan, mohapatrahemant (VC @lightspeedindia),
kmeanskaran, neural_avb, santoshyadavdev. `targets_b`: 25 -> 37.

## Re-run it

    ./run.sh python3 discover_anchors.py --dry-run --from-graph   # propose, change nothing
    # then read every bio + recent posts before adding. The tool cannot see intent.

`targets.json` is git-ignored (box-only), so the reasoning and the rejects live here.

## Update 2026-07-15 (later): the AWAKE window was an assumption too

`AWAKE = range(9, 24)` was a guess about when the user is up. Their posted-feedback clock
says otherwise:

| IST hour | posts |
|---|---|
| **01:00** | **2** (01:36 @TheAhmadOsman, 01:48 @DhravyaShah) |
| 09:00 | 3 |
| 10:00 | 3 |
| 13:00 | 1 |
| 14:00 | 1 |

**01:00 IST is 19:30 UTC — US afternoon.** They have a real second session that overlaps the
US anchors, and I had written that whole window off as "asleep" and scored US anchors down
for it. `fast_lane` was also throttling to 1-in-3 at 01:00 *while they sat there posting*.
Their actual dead zone is **02:00-08:00**: zero posts, ever.

`AWAKE` now includes 01:00; the fast_lane window is `CHORUS_QUIET_START/END` (2-8) rather
than hardcoded, because n=10 is thin and this must stay easy to adjust.

Effect: reachable candidates went **12 -> 18**, and the run surfaced people the old window
hid — @jonhoo (36k, **90% overlap, ~2 replies/post** — the best ratio found: high reach,
almost no competition), @iavins (13k, **100% overlap**, breaks databases at Turso),
@dok2001 (**CTO of Cloudflare** — the user's entire stack), @charliermarsh (Ruff/uv, OpenAI).

## The tool now REMEMBERS rejections

It re-proposed @refikanadol three times across three sessions because the rejects lived in
this doc and nothing read it. `box/rejected_anchors.txt` (box-only, git-ignored — the
reasoning is about specific real people) is now read by `discover_anchors`, so a human
judgement sticks. 15 handles recorded, with the reason on each line.

`targets_b`: 37 -> 51.
