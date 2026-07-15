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
