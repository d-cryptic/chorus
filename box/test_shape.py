"""The thread/longform lane: plumbed for months, never fired once until 2026-07-15.

Root cause was FRAMING, not the model: build_prompt always required `drafts: [2 post
strings]` with `thread`/`longform` as optional extras, so the required field won and every
idea came back a post -- even one literally enumerating three beats, and even on
claude-sonnet-4.5. Shape is now decided in a SEPARATE call and the chosen shape becomes the
REQUIRED field. These tests pin the pieces that made it work.
"""
import post_gen as P

def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    # --- scrub: the model ignores the em-dash ban, so code enforces it ---
    chk(P.scrub("quality control—it's a way") == "quality control, it's a way", "em-dash -> comma")
    chk(P.scrub("a–b") == "a, b", "en-dash -> comma")
    chk(P.scrub("it’s fine") == "it's fine", "smart apostrophe -> plain")
    chk(P.scrub("wait… what") == "wait... what", "ellipsis -> ...")
    chk(P.scrub("") == "", "empty is safe")
    chk(P.scrub(None) is None, "None is safe")
    chk("—" not in P.scrub("a—b—c"), "no em-dash survives")

    # --- each shape asks for ITS OWN required field (the whole fix) ---
    idea = {"source": "hn", "title": "t", "url": ""}
    pp = P.build_prompt(idea, "v", (), "", ["ai"], shape="post")
    tp = P.build_prompt(idea, "v", (), "", ["ai"], shape="thread")
    lp = P.build_prompt(idea, "v", (), "", ["ai"], shape="longform")
    chk('"drafts": [2 post strings]' in pp, "post asks for 2 drafts")
    chk('"thread": [3-7 strings, REQUIRED]' in tp, "thread makes thread REQUIRED")
    chk('"longform": str (REQUIRED' in lp, "longform makes longform REQUIRED")
    chk('"thread": []' in pp and '"longform": ""' in pp, "post shape forbids the other two")
    chk("280 limit does NOT apply" in lp, "longform is exempt from 280")
    chk(P.build_prompt(idea, "v", (), "", ["ai"], shape="bogus") == pp, "unknown shape -> post")

    # --- prompts must obey the rules they state ---
    for name, pr in (("post", pp), ("thread", tp), ("longform", lp)):
        offenders = [l for l in pr.split("\n") if ("—" in l or "–" in l) and "em-dash" not in l]
        chk(not offenders, f"{name} prompt does not itself use the em-dash it bans")

    print(f"SHAPE UNIT: {p} passed, {f} failed"); return f
import sys; sys.exit(run())
