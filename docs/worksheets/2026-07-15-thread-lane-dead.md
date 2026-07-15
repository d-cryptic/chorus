# Thread / long-form lane is plumbed but never fires

**Status:** diagnosed, prototype works, NOT finished. Do not claim threads work.

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

## The open problem

~1/3 of classify calls return an EMPTY response body from deepseek via OpenRouter
(`json.loads` -> "Expecting value: line 1 column 1 (char 0)"). A different case fails each
run, so it is reliability, not prompt. Needs retry + a fail-safe default (`post` on failure:
never pad, never block a draft).

## Next step

1. Take `box/shape_classify_prototype.py` (works; run: `./run.sh python3
   shape_classify_prototype.py [model]`).
2. Add retry-on-empty (2 tries) and default to `post` on failure.
3. Wire as a SEPARATE cheap call before `draft_post`; pass the decided shape in, and make
   `drafts[]` conditional on `shape=post` so the post-centric framing cannot reassert itself.
4. Verify against all three fixtures in the prototype before believing it.

## Traps found the hard way

- `run.sh` sources `.env` AFTER the caller's env, so `OPENROUTER_MODEL=x ./run.sh ...` is
  SILENTLY IGNORED and you test the .env model (`deepseek/deepseek-chat`) while believing
  otherwise. Pass the model as an argv instead.
- Rule 4 ("under 280 chars per tweet") made `shape=longform` literally impossible; it is now
  scoped to post/thread. Necessary but NOT sufficient — it alone did not make threads fire.
- The prompts themselves contained 8 em-dashes while banning em-dashes. Prompts must obey
  the rules they state, or they teach the habit.
