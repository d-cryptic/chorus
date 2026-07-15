# v0 parity — what Chorus ported from the original nakama, and what it deliberately did not

Chorus is a rebuild of the pre-pivot nakama "social companion" (archived on the nakama
branch `v0-pre-pivot`). That product's PRDs — `architecture/{insights-engine,
insights-flows, insights-cost-model, generation-engine, generation-flows, agentic-infra,
data-flow}.md` + `adr/0001-e2e-scraping-provider.md` — are the source of truth this
document tracks against.

Read the first 7 lines of any section to know its status. Statuses:
**PORTED** · **PARTIAL** (with the honest reason) · **NOT PORTED** (deliberate).

## The one rule that overrides the PRDs

v0 assumed an eventual X write lane (auto-publish behind `confirm=true`). **Chorus has no
write lane and never will.** The human posts manually; the agent only ever drafts. Any v0
capability that depends on outward action is therefore refused, not stubbed.

---

## Budget / kill-switch — PORTED

| v0 | Chorus |
|---|---|
| `wouldExceed` before **every** paid call | `budget.BudgetTracker.check()`, re-checked per LLM call |
| pause + checkpoint + **alert**, "no silent skip/shallow" | breach stops the cycle, logs `error=`, calls `notify` |
| per-user/day ceiling | `settings.daily_ceiling_usd` (default 0.65) |
| global kill-switch (`flags:scraping_kill`) | `settings.killed` — absolute, beats `paused` |
| provider breaker: closed→open→cooldown→fallback→DLQ | `budget.CircuitBreaker`, wired in the read adapter. **PARTIAL:** no fallback provider and no DLQ — Chorus has a single read provider, so the breaker fails fast rather than failing over. |
| LLM tokens metered into the same budget | `RATES` covers reads, drafts, judge, synthesis, embeds |

Defects the port exposed and fixed: the ceiling was checked once per cycle (not per call);
spend was estimated post-hoc so a failed ledger POST silently unbound the ceiling;
`quiet_hours` was dead schema; budget-read failure silently assumed "safe to spend".

## Autonomy levels — PARTIAL (deliberate)

v0: L0 suggest-only · L1 draft-and-queue · L2 act-with-approval · L3 autonomous
(whitelisted). v0 gates **outward actions** at the enqueue boundary; insights bypass the
gate entirely.

Chorus implements `settings.autonomy_level` with **L0/L1 only**. L2/L3 exist in v0 to gate
posting — Chorus has no write lane, so they are **refused at the enforcement point** with
an explicit reason rather than becoming dead code that pretends to work.

## Insights — PARTIAL (data-bound, not effort-bound)

PORTED: the `insight` row model (kind/scope/subject/payload/confidence/evidence/status,
deterministic id so a re-run supersedes), cost tiering (L1 free arithmetic; L3 LLM
synthesis **change-gated** on a fingerprint of the L1 claims), Bayesian shrinkage toward a
prior, `confidence(n)=n/(n+k)`, min-sample guard, playbook synthesis over computed stats
only (never raw tweets, so there is nothing to hallucinate from).

Kinds emitted: `winning_format`, `useful_account`, `best_time`, `post` verdicts (only where
an outcome was measured), `dominant_topic`.

NOT PORTED, and why:
- `eng_rate = likes/views` — **not computable**: Chorus has no impressions data. We use raw
  likes+replies and label it as such rather than fake a rate.
- EWMA shadowban/churn detection, thread analytics, follower-churn attribution, keyword
  discovery, gap-analysis vs cohort, account teardown/AKB — need own-post metrics, an edge
  graph, or a cohort benchmark that Chorus does not collect.
- Thompson sampling / logistic diffusion curves / predicted-eng-rate model — v0 designs for
  a multi-user SaaS at ~$0.39/user/day. Chorus is single-user with n≈0; these would be
  ceremony over noise.

> Note: Wilson ranking alone does **not** prevent small-n overclaiming —
> `wilson(3/3)=0.4385` beats `wilson(6/8)=0.4093`. `MIN_SAMPLE` is the real guard. A test
> asserts this so it cannot be optimised away.

## Generation — PARTIAL

PORTED: the Router ("the spine") — reply | quote | retweet | drop; per-day, per-author/day
and cooldown anti-spam; the G3 judge (demote + exactly one regenerate, never discard);
untrusted text isolated as DATA (injection hardening); deterministic ids so a re-run
supersedes.

Deviation that matters: v0 routes **before** generation. Chorus routes **after** the draft,
because the only honest distinctness signal is the judge's — the drafting model's
self-reported `angle_strength` measured 0.80–0.85 on *every* draft (it marks its own
homework) and sent 100% of candidates to `quote`. Routing on the judge costs no extra call
and yields real variance (0.3–0.8).

NOT PORTED:
- **G5 publish** — deliberate: no write lane.
- **Self-originated posts/threads** (cadence slots, breaking-trend preemption, captures) —
  **genuinely missing**; Chorus is replies-only today.
- Media/image/gif/video rendering (R2, Durable Objects, fal async jobs), alt-text gate,
  carousels — wrong fit for a 3.7 GB box; v0 defers video itself.
- True RAG voice priming (semantic nearest-neighbour over your own posts) — Chorus stores
  style docs, not a post corpus, and the memory store is keyword-only. It primes from the
  voice doc and says so; it does not claim semantic RAG.

## Providers — PARTIAL

v0: a `ScrapingProvider` factory with a per-operation PRIMARY/FALLBACK routing matrix
(Apify/Sorsa/Bright Data/Nitter/X API) and breaker-driven failover.

Chorus: a single pluggable read adapter behind a git-ignored `candidate_source.py`
(kept private so the read method is not discoverable), plus swappable `research`
(linkup/firecrawl) and `notify` (telegram/discord/whatsapp/console) layers. No failover
matrix — one provider, so the breaker fails fast instead.

## Memory

v0 assumed Supermemory. Chorus runs `box/memory_service.py` — a small
Supermemory-API-compatible store (stdlib + SQLite, localhost-only) implementing the exact
`/v3/documents` surface used. Upstream is a drop-in swap via `SUPERMEMORY_BASE_URL`.

## Cost model (measured, 2026-07-14)

The read provider: **100,000 credits = $1.00**. A tweet costs **$0.00015 = 15 credits**;
minimum **15 credits per request**. So:

| source | queries/cycle | credits/cycle | $/month (1 cycle/day) |
|---|---|---|---|
| targets only | 3 | ~630 | $0.19 |
| **timeline(120) + targets** (default) | 10 | ~2,310 | **$0.69** |
| full following (400) | 34 | ~7,710 | $2.31 |

The X official API is ~**33x more** ($0.005/read = $5/1k vs $0.15/1k), so the read provider
is already the cheap lane; there is no cheaper credible source to switch to.

**The ceiling was watching the wrong meter.** `settings.daily_ceiling_usd` counts our own
*estimated* USD. The real constraint is the provider credit balance: $0.65/day = 65,000
credits/day, which is 6.5x a 10,000-credit ($0.10) trial balance — so Chorus reported
"$0.0857 of $0.65 spent" while the account hit zero and every query started 402ing.
`candidate_source.balance()` (via `/oapi/my/info`) is now checked pre-flight: zero credits
stops the cycle with an alert; low credits warn. The USD ceiling still guards LLM spend.
