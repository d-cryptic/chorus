#!/usr/bin/env python3
"""A failure in the posted_url measurement path must NOT prevent the fallback from running.

The fallback (token-overlap of your public replies) is the path that ACTUALLY fires -- posted_url
is skipped on 8/8 real posts. The outcome POST in the posted_url loop was unguarded (its sibling
tweet_metrics IS guarded), so one 500 on the first pending row raised out of main() and the
fallback never ran -> rank_tune's engagement reward stayed permanently empty.
"""
import os, sys, types
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import outcome_track as OT


def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    # behavioural: a POST that 500s must not crash main() before the fallback runs
    fake_cs = types.ModuleType("candidate_source")
    fake_cs.tweet_metrics = lambda *a, **k: {"likes": 1, "replies": 0}
    fake_cs.recent_self_replies = lambda *a, **k: []      # fallback finds nothing -> harmless
    calls = {"outcome_posts": 0}
    def fake_req(url, method="GET", token=None, body=None, timeout=20):
        if "pending-outcomes" in url:
            return {"pending": [{"id": "s1", "posted_url": "https://x.com/u/status/123"}]}
        if url.endswith("/outcome"):
            calls["outcome_posts"] += 1
            raise RuntimeError("simulated 500 on the first row")
        return {}
    with mock.patch.dict(sys.modules, {"candidate_source": fake_cs}), \
         mock.patch.object(OT, "_req", fake_req), \
         mock.patch.dict(os.environ, {"INGEST_URL": "http://x", "INGEST_TOKEN": "t",
                                      "CANDIDATE_API_KEY": "k", "CHORUS_HANDLE": "me"}, clear=False):
        try:
            OT.main()
            chk(calls["outcome_posts"] >= 1, "the posted_url POST was actually attempted (loop ran)")
            chk(True, "main() survived a 500 in the posted_url loop -> fallback reachable")
        except RuntimeError:
            chk(False, "a single POST 500 crashed main() -> fallback never runs")

    print(f"OUTCOME FALLBACK UNIT: {p} passed, {f} failed")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(run())
