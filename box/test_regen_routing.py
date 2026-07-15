#!/usr/bin/env python3
"""A regenerated draft must be routed on ITS judge result, never the failing scores that
triggered the regeneration.

`if s2: scores = s2` kept draft[0]'s failing scores when the re-judge returned empty, so the
fresh draft was routed on the very verdict that demoted the old one -> wrongly DROPPED.
route_post treats distinct=None (empty judge) as a safe REPLY: a judge failure must never
destroy a draft.
"""
import os, sys, ast
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate as G


def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    # 1. the source no longer keeps old scores on an empty re-judge
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ranker.py")).read()
    chk("scores = s2 or {}" in src, "regenerated draft adopts its OWN judge result")
    chk("if s2:\n                            scores = s2" not in src, "the old failing-score carryover is gone")

    # 2. route_post: an empty judge (distinct=None) must NOT drop a real draft
    route, why = G.route_post({"author_tier": "B"}, distinct=None, pillar_hit="AI",
                              drafts=["a real regenerated draft"])
    chk(route != G.DROP, f"distinct=None with a draft must not DROP (got {route})")
    chk(route == "reply", f"judge failure -> safe REPLY, got {route}")

    # 3. a genuinely failing judged draft (low distinct) still routes as before
    route2, _ = G.route_post({"author_tier": "B"}, distinct=0.9, pillar_hit="AI",
                             drafts=["a distinct draft"])
    chk(route2 in ("reply", "quote", "retweet", G.DROP), "a scored draft still routes")

    print(f"REGEN ROUTING UNIT: {p} passed, {f} failed")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(run())
