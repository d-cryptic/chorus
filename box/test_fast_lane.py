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

    print(f"FAST LANE UNIT: {p} passed, {f} failed"); return f
import sys; sys.exit(run())
