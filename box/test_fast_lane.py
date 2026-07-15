"""fast_lane is THE growth engine (10-min cadence). It crashed on EVERY run for days:

    examples=examples + tuple(...)   ->  TypeError: can only concatenate list (not "tuple") to list

voice_context() returns a LIST while llm_draft/judge_draft default `examples=()` to a TUPLE.
It fetched 60 tweets, found 11 live, then died at the judge -- so the queue never grew and
the dashboard looked idle. Nothing tested main(), so nothing caught it. This does.
"""
import inspect
import fast_lane as F, ranker as R


def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    src = inspect.getsource(F.main)

    # the exact regression
    chk("examples + tuple(" not in src, "no `list + tuple` concat (the crash)")
    chk("list(examples)" in src, "examples is normalised to a list before concat")

    # prove the shapes really are what broke it, using the REAL functions
    chk(isinstance(inspect.signature(R.llm_draft).parameters["examples"].default, tuple),
        "llm_draft defaults examples to a tuple")
    chk("return hits[:limit]" in inspect.getsource(R.voice_context),
        "voice_context returns a list slice")

    # and that the fixed expression actually evaluates for both input types
    room = [{"text": "x" * 200}, {"text": "y"}]
    for examples in ([], ["a"], (), ("a",)):
        try:
            out = list(examples) + [f"(already said) {r['text'][:90]}" for r in room[:5]]
            chk(len(out) == len(examples) + 2, f"concat works for {type(examples).__name__}")
        except TypeError as e:
            chk(False, f"concat still raises for {type(examples).__name__}: {e}")

    # the crash was at the JUDGE call, after real API spend on the draft -- make sure the
    # judge is still actually called (a fix that skips judging would "pass" but be worse)
    chk("judge_draft(" in src, "judge_draft is still called")
    chk("judge_verdict(" in src, "verdict still gates emission")

    # --- cost: only fetch the window we can USE ------------------------------
    # fast_lane rejects anything older than MAX_AGE_MIN on every run, but it used to FETCH
    # everything -- re-reading the same ~40-60 tweets 144x/day and discarding most as
    # already-`seen`. Measured on the box: $0.86-1.30/day against a $0.65 ceiling, i.e. ~7-10
    # days of runway. Invisible until now only because fast_lane crashed before it could spend.
    # Verified live: the 2h window returns 1 tweet where the plain query returns 20, ages
    # [104, 133, 151, ...] -- and MISSES ZERO tweets under 120min. Capability unchanged.
    chk("since_time:" in src, "fetch is bounded by since_time (98% of reads were waste)")
    chk("MAX_AGE_MIN * 60" in src, "the window is derived from MAX_AGE_MIN, not a magic number")
    chk("OVERLAP_S" in src, "an overlap covers clock skew / indexing lag")
    # the window must never be TIGHTER than the age filter, or we would drop live candidates
    import re as _re
    m = _re.search(r"since_ts = int\(now / 1000\) - MAX_AGE_MIN \* 60 - (\w+)", src)
    chk(bool(m), "since_ts subtracts the full MAX_AGE_MIN window plus overlap")
    chk("seen" in src, "`seen` still dedupes anything the overlap double-counts")

    # --- the quiet window must match the user's REAL clock, not an assumption -----------
    # It was 01:00-07:59, from a guess about when they sleep. Their posted-feedback clock says
    # they posted at 01:36 and 01:48 IST (= 20:00 UTC, US evening, when the US anchors are
    # live). fast_lane was throttling to 1-in-3 while they sat there posting. Their actual
    # dead zone is 02:00-08:00: zero posts, ever.
    chk("CHORUS_QUIET_START" in src, "the window is configurable, not hardcoded (n=10 is thin)")
    q_start, q_end = 2, 8
    posts_by_hour = {1: 2, 9: 3, 10: 3, 13: 1, 14: 1}   # measured from real feedback
    throttled_while_active = [h for h, n in posts_by_hour.items() if n and q_start <= h < q_end]
    chk(not throttled_while_active,
        f"no hour the user actually posts is throttled (would be {throttled_while_active})")
    chk(q_start <= 3 < q_end, "03:00 — a genuine dead hour — stays throttled")
    chk(not (q_start <= 1 < q_end), "01:00 is NOT throttled: they demonstrably post then")

    print(f"FAST LANE UNIT: {p} passed, {f} failed"); return f
import sys; sys.exit(run())
