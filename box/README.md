# Chorus box — the ranker (product core)

`ranker.py` is the actual product: candidates → **gate** → cheap **heuristic pre-score** →
top-K → **one LLM call each** (angle + drafts) → `POST /api/box/ingest`. Suggest-only — never
posts to X. Two-stage so the LLM only touches survivors (budget-safe). Verified end-to-end
against the local Worker (ranker → queue → run_log heartbeat).

## Run
```bash
export INGEST_URL=https://chorus-app.barundebnath.com INGEST_TOKEN=...  # the Worker + box token
export OPENROUTER_API_KEY=... OPENROUTER_MODEL=deepseek/deepseek-chat
export CHORUS_PILLARS="leverage,writing,priorities" CHORUS_HANDLE=you CHORUS_VOICE="concise, specific"
python3 ranker.py --input candidates.json            # live: posts to /api/box/ingest
python3 ranker.py --input candidates.json --dry-run  # no network; prints what would queue
# flags: --tau 0.6  --cap 25  --topk 50  --denylist nsfw giveaway airdrop
```

## Candidates format
List of `{id, text, author, author_tier (A|B|C), ts (epoch MS — MUST be recent), url,
impressions_per_min, reply_count}`. **`ts` is epoch milliseconds**; stale (>48h) tweets are
gated out — `candidates.example.json` uses `ts:0` only as a shape example.
v1 feeds candidates via `--input`. **TODO:** wire the private X read adapter (target-lists +
keyword search + mentions — NOT the home timeline; X read adapter has no user auth). Do this after
M0.5 (validate Hermes) per docs/review-actions.md.

## Tests
```bash
python3 test_ranker.py   # 10 pure-logic assertions (gate / pre_score / prerank / finalize), no network
```
Caught a real ms→hours unit bug during integration. Live-verified: ranker → /api/box/ingest → queue.

## Config
Copy `.env.example` → `box/.env` (git-ignored), fill in, then `set -a; source box/.env; set +a`.

## Running the M0 cycle
The daily cycle is just cron running these scripts (`crontab.example`) — no HTTP cycle-runner /
`HERMES_CYCLE_URL` needed for v1 (that's the frozen M1 approach). ranker → digest → mirror on a
schedule.

## Feature scripts (build-complete; test when deployed)
- `telegram_bot.py` — interactive bot: /queue + posted/snooze/dismiss buttons + open-reply URL (daemon; Telegram deferred).
- `enrich.py` — cross-platform enrichment (GitHub/HN/Reddit) -> Supermemory. Live-verified (GitHub+HN).
- `voice_refine.py` — refine chorus:self voice from your ACTUAL posted replies (weekly).
- `outcome_track.py` — measure posted replies' metrics -> /api/box/outcome -> rank-tune (needs posted_url + local adapter lookup).
- `backup.py` — nightly D1 export (14-day retention).
- `embed.py` — optional semantic pillar relevance (EMBED_PILLARS=1; one batched call).
- Mutuals weighting: ranker boosts accounts that follow you back (relationship factor, from targets.json).

## Other box scripts
- `mirror_feedback.py` — reads new feedback (`GET /api/box/feedback`) and mirrors it to Supermemory
  `chorus:self` (M0 personalization loop). `--dry-run` tested; verify `SUPERMEMORY_ADD_URL` vs SDK.
- `digest.py` — daily Telegram digest + heartbeat (`GET /api/box/digest` → Telegram sendMessage).
  `format_digest` unit-tested offline (populated + empty/alert). Needs `TELEGRAM_BOT_TOKEN`/`_CHAT_ID`.

## research (swappable)
`research.py` — swappable search layer for research-digest. `RESEARCH_PROVIDER=linkup` (default,
`LINKUP_API_KEY`) or `firecrawl` (`FIRECRAWL_API_KEY`). Normalized `[{title,url,content}]`; the
response mappers are unit-tested. Add a provider = add one class + a PROVIDERS entry.

## Supermemory / memory (self-hosted)
`mirror_feedback.py`/`onboard.py`/`enrich.py`/`voice_refine.py` write memory to
`SUPERMEMORY_BASE_URL` (default `http://localhost:8000`, key optional). The box runs
**`memory_service.py`** — a tiny Supermemory-API-compatible store (stdlib + SQLite, no
deps, bound to 127.0.0.1) implementing the `/v3/documents` surface Chorus uses
(POST store, GET/`?containerTags=` list, DELETE by tag, POST `/v3/search`). Runs as the
`chorus-memory` systemd unit (`MEMORY_DB=/opt/chorus/memory.db`). Drop-in swap for upstream
`github.com/supermemoryai/supermemory`: just point `SUPERMEMORY_BASE_URL` at it.

## Cloudflare Bot Fight Mode / User-Agent
The Worker sits behind Cloudflare, which **403s the default `Python-urllib` User-Agent**.
Every box→Worker request sets `User-Agent: chorus-box/1.0` so the write path (ingest, spend,
weights, run-log, feedback) is not silently blocked. Keep the header when adding new callers.

## notify (swappable — Telegram / WhatsApp / console)
`notify.py` — `NOTIFY_PROVIDER = telegram | whatsapp | console`. digest.py calls `notify.send()`.
- **telegram**: bot sendMessage (simplest, free) — recommended for v1.
- **whatsapp**: POST to `WHATSAPP_WEBHOOK_URL` — route via a Hermes WhatsApp connector or a bridge
  (WhatsApp Business API needs Meta approval; unofficial bridges carry ban risk).
- **console**: print (default).

## Live-verified adapters
- **the private X read adapter** ✅ — fetched 20 real `@elonmusk` tweets, `map_tweet` mapped all correctly.
- **Linkup** ✅ — real `/v1/search` results normalized. Swap via `RESEARCH_PROVIDER`.

## Telegram digest — DEFERRED (v1)
`digest.py` is built + tested but OFF for v1 (no Telegram creds yet). Enable later with
`TELEGRAM_BOT_TOKEN`/`_CHAT_ID`. Heartbeat still visible in the dashboard header.

## onboard-self
`onboard.py` — fetch your X history (X read adapter `from:you`) → LLM synthesize pillars+voice →
Supermemory `chorus:self`. Dry-run tested. Run once before the first ranker cycle.

## X read adapter
`ranker.py --targets` (from `CHORUS_TARGETS_A/B`) or `--query '<advanced search>'` fetches via
`GET /twitter/tweet/candidate-search` (the adapter key header), maps the real response schema
(`{tweets:[{id,text,author.userName,createdAt,replyCount,viewCount,url}]}`) → candidates.
`map_tweet`/`_parse_ts` unit-tested; live fetch verified at deploy (needs the key).

## Deploy
See [../docs/runbook-deploy.md](../docs/runbook-deploy.md) — the live wiring you run with your creds.

## Design notes
- Weights loaded from `GET /api/box/weights` (rank-tune output); budget/ceiling/pause from
  `GET /api/box/spend` + `/api/box/settings`; run bracketed with `/api/box/run-log`.
- No embeddings in v1 — keyword pillar match + tier + freshness + upside − saturation is enough.
- LLM step has a deterministic fallback when `OPENROUTER_API_KEY` is unset (un-voiced drafts) so
  `--dry-run` and testing work offline.

## Budget guard, kill-switch, autonomy (`budget.py`)

Ports the v0 nakama `BudgetTracker` semantics — see [`docs/v0-parity.md`](../docs/v0-parity.md).

- **`would_exceed` before every paid call.** `ranker.py` re-checks the ceiling before
  each LLM draft, so a long cycle cannot blow the budget mid-run (it used to be checked
  once, before the loop). On breach: stop + checkpoint + **alert** — never a silent skip.
- **Spend is recorded as incurred**, not estimated post-hoc, and counted locally so the
  ceiling binds *even if the ledger POST fails*. Flushed every 10 calls + at cycle end.
- **`killed`** = global kill-switch in `settings`. Absolute: beats `paused` and any
  remaining budget. `paused` is the soft, resumable stop.
- **`quiet_hours`** is now actually enforced (the column existed but nothing read it).
- **Fail-closed**: if the ceiling/kill-switch can't be read, the cycle aborts + alerts
  rather than assuming it's safe to spend.
- **`autonomy_level`**: `L0` suggest-only | `L1` draft-and-queue (default). v0's `L2`
  act-with-approval / `L3` autonomous gate *outward actions* — Chorus has no write lane
  by design, so they are **refused** at the enforcement point rather than faked.
- **`CircuitBreaker`** (closed→open→cooldown→half_open) is for *provider reliability*
  and is deliberately separate from the budget ceiling. Wrap any provider call with it.

Rates live in `budget.RATES` (USD/unit). Unknown ops raise — never assume free.

## Insights engine (`insights.py`)

Ports the v0 nakama insights spec, scoped to the data Chorus actually has.
Runs daily at 05:00 (after `outcome_track.py`).

**The core property: it refuses to claim anything at low n.** v0's rules are
"min-sample before any claim" and "zero invented numbers", so:
- every rate is shrunk toward a prior (`shrink`: n=0 returns the PRIOR, not 0/0);
- buckets under `MIN_SAMPLE` (5) are **excluded**, not ranked low — an unranked bucket
  is honest, a confidently-ranked n=1 is not;
- `confidence(n) = n/(n+k)`, so a perfect 7/7 reports ~0.41 confidence, never 1.0;
- with no data it emits `payload.state = "insufficient_data"` and confidence 0.

Note: Wilson ranking alone does NOT stop small-n overclaiming — `wilson(3/3)=0.4385`
beats `wilson(6/8)=0.4093`. `MIN_SAMPLE` is the actual guard. Don't remove it.

**Kinds emitted**: `winning_format` (pillar), `useful_account` (author),
`best_time` (hour), `post` (per-reply verdict, only where an outcome was measured),
`dominant_topic`. Chorus has no impressions, so v0's `eng_rate = likes/views` is not
computable — we use raw likes+replies and say so rather than fake a rate.

**Cost tiers**: L1 (all of the above) is pure arithmetic, $0. L3 (LLM playbook
synthesis) is **change-gated** on a fingerprint of the L1 claims — an unchanged week
costs nothing — and is additionally gated by `budget.BudgetTracker`. The synthesis
prompt receives ONLY computed stats, never raw tweets, so there is nothing to
hallucinate from.

```bash
python3 insights.py --dry-run   # print what would be emitted, no writes
python3 insights.py --force     # synthesize even if nothing moved (still budget-gated)
```

## Generation: router, caps, judge (`generate.py`)

Ports the v0 nakama generation decision layer. Chorus stays **suggest-only**: every
route produces a draft/decision row for you, never a post (v0's G5-publish is dropped).

**The Router** (v0 calls it "the spine") decides the target per candidate. Split in two
to respect the two-stage budget design:
- `route_pre()` — cheap, pre-LLM. Drops only what is clearly not ours (no pillar, no
  mutual, low-value author) *before* we pay for a draft. Deliberately conservative:
  a wrongly-dropped candidate is invisible, so we bias toward spending ~$0.0003 to look.
- `route_post()` — uses `angle_strength`, which the draft call **already returns**, so
  reply/quote/retweet costs **zero extra LLM calls**:
  - `angle >= 0.70` -> **quote** (a distinct take deserves its own post)
  - `angle <= 0.25` -> **retweet** if on-pillar AND tier A/B (nothing to add, worth
    amplifying), else **drop**. Retweet rows carry NO drafts, just a rationale.
  - otherwise -> **reply** (the default)

**Anti-spam caps** (`CapState`): per-day, per-author/day (2), and a 6h cooldown between
replies to the same author. Cooldown reads prior queue history, not just this cycle, and
caps are checked *before* paying for a draft.

**G3 judge**: scores `voice_match` / `contract` / `grounded` (0..1); anything below 0.5
fails -> **demote + exactly one regenerate**. It never discards work: a judge error or
missing score counts as a PASS. Live-verified to catch an invented statistic
(`grounded: 0.1`) and off-voice hype (`voice_match: 0.1`) at ~$0.0002/judgement.
Disable with `--no-judge`.

**Voice priming** (`ranker.voice_context`): pulls your stored voice from the memory
service. NOTE: v0 does true semantic RAG over your own past posts — Chorus cannot yet
(chorus:self holds style docs, not a post corpus, and the store is keyword-only), so it
tries a topic match then falls back to the voice docs. Honest priming, not fake RAG.

**Zero candidates now ALERTS** rather than silently no-opping — an out-of-credit
provider (402) drops every query and would otherwise look like "a quiet day" forever.

## Voice: why drafts stopped sounding like AI (`style_mine.py`, onboard, judge)

Three compounding bugs made every draft read as AI slop — and worse, made them lie:

1. **The learned voice was never used.** `onboard.py`/`voice_refine.py` synthesise your
   real voice into `chorus:self`, but the drafter read the static `CHORUS_VOICE` env
   string ("concise, specific, no hype") and nothing ever read the doc back. Every
   voice update was inert. `ranker.get_voice()` now prefers the stored voice_model.
2. **`onboard.py` crashed** on any fenced/non-JSON LLM reply, so the voice was never
   captured in the first place. Fence-strip + non-fatal fallback added.
3. **The prompt demanded specificity but banned nothing**, so the model manufactured it:
   *"Our testnet processed 1.2M XRP txs/day"*, *"our logs show 37%"*. All invented. The
   judge waved them through because `grounded` allowed claims "supported by the tweet OR
   **the author's own experience**" — an unfalsifiable escape hatch. Both fixed: the
   drafter is forbidden from inventing first-person claims/numbers (having no data is
   explicitly fine — opinion, question, counterexample, mechanism), and `grounded` now
   scores 0 for ANY unverifiable first-person data claim.

Also added a `human` judge dimension (AI-tells: invented-stat-then-tradeoff, "Key
insight:", tricolons, over-polish). `human` and `grounded` both FAIL a draft -> demote +
one regenerate.

**`style_mine.py`** (weekly) mines high-engagement posts from your targets and extracts
the STRUCTURAL moves that earn replies (hook shapes, reply-bait, what winners avoid) ->
`chorus:niche` -> fed to the drafter. HARD BOUNDARY: patterns only, never content —
Chorus must never launder someone else's claims into your mouth. Your voice always wins;
if a pattern fights the voice, the pattern is dropped.

## Source model: your timeline + targets

twitterapi.io is **X-API-Key only with no home-timeline endpoint**, so the timeline is
**reconstructed** from your following list (`refresh_targets` emits a capped, filtered
`timeline` handle list). Same tweets, minus X's ranking — and no account session, which
this project forbids. Topic-discovery is **opt-in** (`CHORUS_DISCOVERY=1`): live testing
showed it is dominated by crypto spam and costs an extra query.

**Cost (measured):** 100k credits = $1; a tweet = 15 credits; min 15/request.
timeline(120)+targets ≈ 200 candidates/cycle. `candidate_source.balance()` is checked
pre-flight — 0 credits stops the cycle with an alert (the USD ceiling can't see credits).

## Humour, gifs, threads

The drafter is **bullish on sarcasm, dry wit, memes and relatable jokes** — the best
replies in this niche are sharp or funny, not polite. Emoji/slang are allowed *if the
learned voice uses them* (an earlier prompt banned emoji while the voice doc said the
opposite — the prompt was fighting the voice).

Still banned, because they read as a bot: "Great point", "Absolutely", "Key insight:",
tricolons, restating the tweet. **And tics**: live output opened 4/5 drafts with "ngl", so
the prompt now forces a different opener per draft — a verbal tic reads as botlike as
corporate copy.

- **`gif`**: a Giphy SEARCH phrase (v0 spec: search, never generate), rendered as a chip
  linking to Giphy. Null when a gif would be try-hard.
- **`thread`**: only when the take genuinely needs >280 chars — never padding.
- **`style_mine --mode replies`** mines high-engagement **comments** aimed at your targets
  (`filter:replies`) — the thing you actually compete with — into `chorus:niche:replies`,
  which the drafter prefers over post-patterns. Patterns only, never content.

## post_gen.py — what to POST (not just what to reply to)

Implements the v0 G1 idea priority (PRD-11 / generation-flows), which is LOCKED order:
1. **user capture** — "a direct request always wins". `box/captures.txt`, one idea per
   line. Lowest-friction capture that needs no OAuth.
2. **breaking trend** — preempts evergreen when fresh + on-topic.
3. **evergreen pillar** — fills an open cadence slot.

Sources wired (keyless unless noted): **HackerNews** (Algolia front page, pillar-filtered),
**GitHub** (repos pushed this week on your pillars), **X timeline** (what your own network
is actually engaging with; costs credits — `--no-timeline` to skip).

**Not wired, and why** — these need credentials the project does not have:
- **Reddit**: 403s *every* unauthenticated request now (all UAs, both hosts). Needs a free
  OAuth app. NOTE: this also means `enrich.py`'s reddit lane is dead — it swallows the error.
- **Google Calendar / Photos / Maps**: needs Google OAuth on the user's account.
- **Memes**: Giphy/Imgflip need an API key.

**Provenance honesty**: Reddit/HN/Photos are NOT in the v0 PRDs — only Calendar, Maps, X
and LinkedIn are. HN/GitHub here are our own extension of "breaking trend".

**Source previews**: `og_image()` pulls the source's OpenGraph image — GitHub
auto-generates a repo card, most articles set `og:image`. That is a free "screenshot" of
the source. A real headless screenshot would need Chromium on the box (~400MB) or a paid
API; this gets the same value for $0.

Rules the drafter follows for posts: never invent first-person claims/numbers; do NOT
summarise the link (take a position, or ask the question everyone is dancing around);
classy/light (<=1 emoji, <=1 slang, no bro/fire/!!!); thread ONLY if the idea has 3+
distinct beats (PRD-11), never padding.

A post is queued with `target='post'` and a **synthetic** `tweet_id` (`post:<id>`) because
that column is NOT NULL + UNIQUE — v0 uses the same tagged-synthetic-ref trick, and it
doubles as the dedup key so the same HN story never queues twice.

## session_mine.py — your own work as post ideas (shape-only)

Reads recent Claude Code sessions + your public GitHub activity and extracts abstract
SHAPES for the capture lane ("a direct request always wins", v0 G1 priority #1).

**Threat model — read before touching this.** Sessions hold client code, secrets, absolute
paths, repo/employer names and private conversations. The OUTPUT is a public tweet. So:

- **L1 local redaction**: only the USER's own prompt lines are read (never assistant
  output, tool results or file contents — that is where code lives), then secrets / paths /
  URLs / emails / IPs / repo-shaped tokens are stripped BEFORE the LLM sees anything.
- **L2 prompt**: forbids naming any company, client, repo, project, file, URL or person.
- **L3 output check**: `leaks()` rejects a shape containing any project-slug token or
  secret-shaped string. **Fails closed** — the idea is dropped, not published.
- **L4**: every idea still lands in the queue for you to approve. Nothing self-posts.
- `CHORUS_SESSION_DENY` (csv substrings) skips whole projects — use it for client work.

Runs on the **laptop** (that is where sessions are) and POSTs to `/api/box/capture`;
`post_gen.py` on the box consumes them, drafts once, then marks them consumed.

Verified live: 9 active projects -> 7 shapes, **0 leaks** in a full audit of the queue
(no repo names, paths, emails or keys).

## memes.py — DORMANT by design

Every meme source needs a credential this project does not have, so the lane is built and
inert; with no key it returns `[]` and the queue simply carries **no** meme rather than a
broken image. Nothing fabricates media.

| source | unlocks | cost |
|---|---|---|
| `GIPHY_API_KEY` | reaction GIFs (SEARCH only per v0 + "Powered By GIPHY" attribution) | free, 30s |
| `REDDIT_CLIENT_ID`/`_SECRET` | r/ProgrammerHumor memes; also revives enrich.py's dead reddit lane | free, 2min |
| `IMGFLIP_USER`/`_PASS` | GENERATE a captioned meme (v0 mediaIntent='meme') | free |

Run `python3 memes.py` to see live status.

## Memory: BM25 retrieval, a real post corpus, and a repetition guard

Three gaps closed. Chorus had **no memory of its own output** and its "search" was a
substring match.

**1. `memory_service` now ranks with BM25** (Okapi, stdlib+math, ~40 lines). The old
`/v3/search` was `q in content.lower()`: it could not rank, missed morphology, and
returned *nothing* for a multi-word query. `embed.py` existed but needed an OpenAI key
this project does not have, so the semantic path was dead code. BM25 needs no key, no
model, no deps. Proof: `"retrieval benchmark"` -> ranks the right doc at 1.12 where
substring returned nothing. Honest limit: BM25 is **lexical** — `"gpu heat"` will not
match `"thermally limited"`. True semantics needs embeddings, hence a key.

**2. `chorus:posts` — a corpus of what you ACTUALLY posted.** `mirror_feedback` now
mirrors every posted/edited reply into it. A draft you dismissed or rewrote is not
evidence of your voice; a reply you shipped is. This is what makes v0's
`searchSimilarPosts` real: `voice_context()` retrieves your own nearest posts by topic
(BM25) and only falls back to the voice doc when the corpus is empty.

**3. Repetition guard (`already_said`).** Chorus would happily re-suggest the same take
every time a topic recurred — the fastest way to look like a bot. Every candidate is now
checked against `chorus:posts` BEFORE we pay for a draft (free + cheap).

Threshold, **measured against the live corpus, not guessed**:
| case | score |
|---|---|
| same-topic | 1.73 |
| near-duplicate | 1.15 – 1.44 |
| related | 0.58 |
| unrelated | 0.00 |

-> `CHORUS_REPEAT_TAU=1.0`. **Caveat learned the hard way:** an absolute BM25 threshold is
brittle — the *same* near-duplicate scored 1.44 and 1.15 depending on one extra shared
word, and idf drifts as the corpus grows. A first pass at 1.2 silently caught nothing.
So the tau is env-tunable and every **near-miss is logged**, so it can be re-derived from
real data instead of vibes. Re-calibrate as `chorus:posts` grows.

## The growth engine: fast_lane.py + follower_track.py

**The daily ranker was structurally incapable of growing followers.** Measured on the live
queue: suggested tweets averaged `fresh` 0.79–0.83 — **8–10h old**, worst 0.557 (**21h**).
Reply-guy growth only works if you land in the first ~10–20 replies while the thread is
still being read. Hours later the reply section is buried, impressions collapse, and a
reply earns ~0 followers. **Cadence was the bottleneck, and cadence was never a cost
decision** — anchors-only polling is 1 chunked query:

| cadence | credits/day | $/day |
|---|---|---|
| every 10m | 15,120 | **$0.151** |
| every 30m | 5,040 | $0.050 |
| daily (old) | 2,310 | $0.023 → **~0 growth** |

against a **$0.65/day** ceiling. It was wrong, not expensive.

`fast_lane.py` (every 10m) polls the high-reach anchors, keeps only tweets **<120m old with
<60 replies**, and scores by `opportunity()` — deliberately NOT the daily ranker's score:

- **reach** `log10(followers)/5` — a big account's reply section is a bigger stage
- **earliness** `1/(1+replies/12)` — reply #5 beats reply #200
- **freshness** — cliff-edges after 25m; a late reply is worth ~nothing

It drafts + judges immediately, alerts `⚡ reply now`, and **expires the suggestion in 3h**
because a fast-lane find is worthless once stale. First live run found @theo **7 minutes
old, 24 replies, 360k followers** — an opportunity the daily cron would never have seen.

`follower_track.py` (hourly) snapshots your follower count and attributes deltas to replies
posted in that window. Nothing measured the actual goal before — `outcome_track` measures
likes/replies, which are proxies, so nothing could optimise for followers.
**Baseline: 1,093 → 10x = 10,930.** (`targets.json` said 400 only because that fetch is
capped at 2 pages.)
Honest: with one account and no control group this is **correlational, not causal** — a
spike after replying to a 500k account is evidence, not proof. Still far better than
optimising likes.

## The reward function (rank_tune) — followers, not likes

`rank_tune` used to reward `action.startswith("posted")` weighted by
`(likes + 2*replies)/10`. **It was optimising likes.** Likes are a proxy that diverges from
the goal: a viral joke earns 500 likes and 0 follows; a sharp technical take earns 20 likes
and 5 follows. The ranker was being taught to chase the wrong number.

Reward is now **followers gained**, via `follower_attribution()`: `follower_track` snapshots
hourly, and each posted reply is credited an equal share of the delta over the window it
landed in. Likes remain only as a fallback when no snapshot covers a reply yet.

**Honest about attribution:** one account, no control group, and several replies can share a
window — so this is *correlational, not causal*, and noisy at low volume. It is still
strictly better than optimising likes, and it self-corrects as volume grows: noise averages
out, a real signal does not.

## The timezone ceiling (the finding that outranks the code)

Sampled 40 recent anchor originals by IST hour: **40% land 01:00–07:59, and the peak
(03:00–05:00 IST = US afternoon = peak X) is when you are asleep.** The anchor set is
US-clocked; you are IST. A ~25min reply window is physically unreachable there — **no code
fixes this.** `fast_lane` now skips most of those polls (saving ~3,800 cr/day of provably
dead spend), and `discover_anchors.py` hunts high-reach on-pillar accounts whose clock
overlaps your waking hours.

Calibration note, because the first version was wrong: with only a follower FLOOR it
proposed @jack (9.9M), @satyanadella (7.1M), @aplusk (14M) — useless, because 500+ replies
land within minutes, earliness → 0, and you are reply #2000. **Reach you cannot get early
on is worthless.** It now applies a follower CEILING (800k), a median-replies test (≤80 —
the honest "can I be early?" check) and an on-pillar test. It runs `--dry-run` weekly: it
proposes, a human decides.
