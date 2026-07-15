# Thread / long-form lane: was dead, now FIRES

**Status: FIXED and verified 2026-07-15.** 3/3 on the fixtures, end-to-end.
Kept for the diagnosis, which is the useful part.

**Goal:** user asked for thread posts + long-form + correlation. Threads/long-form are built
end-to-end (post_gen -> D1 `thread`/`longform` -> Worker -> App.tsx renders connectors + LONG
badge) but have **never emitted once**. This also BLOCKS the format-correlation ask: you
cannot measure which shape wins when only one shape is ever produced.

## What is proven (measured, not guessed)

1. **The inline prompt always returns `shape=post`.** Given an idea literally enumerating
   three beats ("cosine vs BM25 score scales, empty-content list endpoints, missing
   idempotency keys") post_gen returns `post`.
2. **Not a model limitation.** `deepseek/deepseek-chat` AND `anthropic/claude-sonnet-4.5`
   both collapse to `post`; Sonnet rationalises "three failure modes share a single insight".
3. **The framing is the bug — CONFIRMED.** A *standalone* classifier (no `drafts[]`, no voice
   rules, no "280 chars" anywhere) on the SAME idea returns `thread` and extracts all 3 beats
   correctly. post_gen's prompt is post-centric (`drafts: [2 post strings]` is always
   required), so `shape` reads as an afterthought and loses.
4. **A naive standalone classifier OVER-fires.** "GitHub is down again." -> `thread` with
   three INVENTED beats (`['GitHub is down.', "It's happening again.", 'Service reliability
   is questionable']`). "Count the beats" invites the model to CREATE beats. Padding a
   one-liner into a thread is exactly what PRD-11 forbids.
5. **Extract-don't-invent fixes the over-fire.** Requiring beats be QUOTED from the idea plus
   an `invented_any` self-report (force `post` when true) gives correct `longform` on the
   causal-argument case.

## The fix (all of it shipped)

1. `post_gen.classify_shape()` -- a SEPARATE call. Extract-don't-invent + an `invented_any`
   self-report; a claimed thread with <3 extracted beats is downgraded to post. Retries 3x
   (~1/3 of calls returned an EMPTY body from deepseek via OpenRouter -- flakiness, not
   prompt) and fails safe to `post`: a wrong post costs a little reach, a wrong thread
   publishes padding under the user's name.
2. `build_prompt(..., shape=)` asks for ONE shape, and the chosen shape is the REQUIRED
   field. This was the whole bug: `drafts: [2 post strings]` was always required with
   thread/longform optional, and the required field always won.
3. `scrub()` strips em/en dashes, smart quotes and ellipses from every output. The em-dash
   ban is stated in the prompt and the model ignored it anyway ("isn't about quality
   control—it's a sneaky way"). Prompt adherence is a request; scrub is a guarantee.

## Verified

    ./run.sh python3 shape2.py     # classifier: 3/3
    ./run.sh python3 shape3.py     # end-to-end: thread=5 segments, longform=491ch, post=post

box/test_shape.py (16 tests) pins it. Full suite 182 green.

**Note on real data:** a live post_gen run returns `post` for all 3 HN ideas. That is
CORRECT, not a regression: HN titles are single-beat headlines. Threads should fire on
richer input (user captures, session-mined material), not on "Show HN: X". Cost went
$0.0009 -> $0.0018 per run for the extra classify call.

## Traps found the hard way

- `run.sh` sources `.env` AFTER the caller's env, so `OPENROUTER_MODEL=x ./run.sh ...` is
  SILENTLY IGNORED and you test the .env model (`deepseek/deepseek-chat`) while believing
  otherwise. Pass the model as an argv instead.
- Rule 4 ("under 280 chars per tweet") made `shape=longform` literally impossible; it is now
  scoped to post/thread. Necessary but NOT sufficient — it alone did not make threads fire.
- The prompts themselves contained 8 em-dashes while banning em-dashes. Prompts must obey
  the rules they state, or they teach the habit.

## Why threads still never fire on REAL input (and why that is correct)

The lane works: 3/3 on fixtures, end to end — thread 5 segments, longform 491 chars, one-liner
stays a post. It has still never fired in production. That is not a bug. Measured:

**Every real idea is single-beat.**
- HN/GitHub: headlines. "Bonsai 27B runs on a phone" is one claim.
- Session captures, all 5 of them, 0 plausibly multi-beat:
    "Found that a backfill script hadn't been tested on staging..."
    "Diagnosed maxed-out laptop fan as likely caused by numerous dev containers..."
    "Explored running development agents on ephemeral cloud infrastructure..."
    "Investigated whether development sessions could persist when moved..."
    "Considering whether a specific Kubernetes policy engine is actually needed..."

classify_shape calling these `post` is CORRECT. Forcing a thread onto one beat is padding,
which is what PRD-11 forbids and what makes an account read as a bot.

### The real opportunity, and why I did NOT build it

Three of those five captures are beats of ONE story: moving a dev environment to the cloud
(fan/containers -> ephemerality -> session persistence). Individually single-beat; together a
genuine thread. So the thread lane needs GROUPING, not a better classifier.

`correlate_sources` already groups — but it deliberately skips same-source pairs ("two HN
stories are not corroboration"), and all captures are source=session. That rule is right for
CORROBORATION (same story, several sources = stronger) and wrong for THEMATIC GROUPING
(different observations, one source, one theme = a thread). They are different operations.

I tested whether the cheap method would work anyway. It does not: the only capture pair
sharing >=2 tokens shares **"development"** and **"running"** — generic dev vocabulary, not a
theme. Grouping on that would fuse unrelated captures into fake threads, which is worse than
no threads.

Real thematic grouping needs embeddings (Supermemory has them, local and free) or an LLM call.
**Not built, on purpose:** n=5 captures, and 0 threads have ever been posted, so there is zero
evidence threads perform for this user. Building semantic clustering on that is speculation —
the same pattern that produced today's retracted taste claim ("you post statements, not
questions", drawn from data that was 60% false).

**Revisit when:** captures reach ~20 AND at least one thread has been posted and measured. Then
cluster with the local embeddings and let winning_shape say whether it was worth it.
