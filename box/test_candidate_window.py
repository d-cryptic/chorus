"""The age window must cut COST without cutting CAPABILITY — and must not touch the callers
that legitimately need history.

The ranker gate()s to WINDOW_H (48h) and discards the rest, so paying to read older tweets
can never pay off. Measured on the box: 80 tweets billed, 54 usable, window returns exactly
those 54 (32% off the biggest line item). But style_mine mines WINNING posts (often old) and
discover_anchors measures posting CLOCKS over time — a hardcoded window would lobotomise both,
silently. Hence opt-in.
"""
import os, time, types

# Hermetic: fetch_candidates SystemExits without a key/targets, and targets.json is
# git-ignored (box-only). Supply both from env so this test runs on a laptop and in CI, not
# just on the box that happens to have the real files.
os.environ.setdefault("CANDIDATE_API_KEY", "test-key")
os.environ.setdefault("CHORUS_TARGETS_A", "alice,bob")
os.environ.setdefault("CHORUS_TARGETS_B", "carol")

import candidate_source as cs
import ranker as R


def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    now = int(time.time() * 1000)
    seen = []
    # force the env path even where targets.json exists, so the test is identical everywhere
    _exists = os.path.exists
    cs.os.path.exists = lambda p: False if p.endswith("targets.json") else _exists(p)
    orig = cs._fetch
    cs._fetch = lambda q, key, **kw: (seen.append(q), [])[1]
    try:
        # no since_h (style_mine / discover_anchors) -> NO window
        seen.clear()
        try: cs.fetch_candidates(types.SimpleNamespace(pages=1, query=None), now)
        except SystemExit: pass
        chk(len(seen) > 0, "queries were built")
        chk(all("since_time" not in q for q in seen),
            "callers that need history get NO window (style_mine mines old winning posts)")

        # since_h set (ranker) -> every query windowed
        seen.clear()
        try: cs.fetch_candidates(types.SimpleNamespace(pages=1, query=None, since_h=48), now)
        except SystemExit: pass
        chk(seen and all("since_time:" in q for q in seen), "ranker-style call windows every query")

        # the window must be derived from the caller's number, not a magic constant
        seen.clear()
        try: cs.fetch_candidates(types.SimpleNamespace(pages=1, query=None, since_h=2), now)
        except SystemExit: pass
        ts2 = int(seen[0].split("since_time:")[1].split()[0])
        seen.clear()
        try: cs.fetch_candidates(types.SimpleNamespace(pages=1, query=None, since_h=48), now)
        except SystemExit: pass
        ts48 = int(seen[0].split("since_time:")[1].split()[0])
        chk(ts2 > ts48, "a smaller since_h means a TIGHTER (later) cutoff")
        chk(abs((ts2 - ts48) - 46 * 3600) < 5, "the gap between 2h and 48h is exactly 46h")
    finally:
        cs._fetch = orig
        cs.os.path.exists = _exists

    # the ranker must window to exactly what its gate keeps, or it pays for what it discards
    import inspect
    chk("args.since_h = WINDOW_H" in inspect.getsource(R.load_candidates),
        "ranker windows to WINDOW_H — the same number gate() enforces")

    print(f"CANDIDATE WINDOW UNIT: {p} passed, {f} failed"); return f
import sys; sys.exit(run())
