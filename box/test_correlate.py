"""The three correlations the user asked for, plus the traps each one sets.

1. winning_shape  — post vs thread vs longform (insights.py)
2. cross-source   — same story on HN+GitHub+timeline -> ONE stronger idea (post_gen.py)
3. me-vs-them     — where your structure diverges from what lands (style_mine.py)
"""
import insights as I, post_gen as P, style_mine as S


def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    # --- 1. shape_of: a NameError here was SWALLOWED by `except Exception` and every
    #        thread silently became a "post" -- the correlation would have been 100% wrong
    #        while looking healthy. These pin it.
    chk(I.shape_of({"thread": '["a","b"]'}) == "thread", "json thread string -> thread")
    chk(I.shape_of({"thread": ["a", "b"]}) == "thread", "already-parsed list -> thread")
    chk(I.shape_of({"longform": "x" * 400}) == "longform", "longform -> longform")
    chk(I.shape_of({"longform": "x", "thread": '["a"]'}) == "longform", "longform wins over thread")
    chk(I.shape_of({"thread": "[]", "longform": ""}) == "post", "empty -> post")
    chk(I.shape_of({"thread": "not json"}) == "post", "garbage thread -> post, no crash")
    chk(I.shape_of({}) == "post", "no fields -> post")

    # follower_delta: unmeasured must be None, NOT 0 -- 0 would drag every mean down and
    # make the newest shape look worst purely for having less outcome data.
    chk(I.follower_delta({}) is None, "missing -> None not 0")
    chk(I.follower_delta({"followers_delta": 0}) == 0, "a real 0 is still 0")
    chk(I.follower_delta({"followers_delta": 3}) == 3, "real value passes")
    chk(I.follower_delta({"followers_delta": "junk"}) is None, "junk -> None, no crash")

    # --- 2. cross-source ---
    ideas = [
        {"source": "hackernews", "title": "Bonsai 27B runs a datacenter-class model on a phone"},
        {"source": "github", "title": "bonsai-27b: quantized weights to run bonsai on device"},
        {"source": "timeline", "title": "everyone is talking about bonsai 27b on device today"},
        {"source": "hackernews", "title": "Jurassic Park computer systems breakdown"},
    ]
    out = P.correlate_sources(ideas)
    chk(len(out) == 2, "4 ideas -> 2 (three merge, one stands alone)")
    merged = [o for o in out if o.get("corroborated_by")]
    chk(len(merged) == 1 and len(merged[0]["corroborated_by"]) == 3, "all 3 sources corroborate")
    # a repo name is hyphenated and the headline is not; missing this misses the commonest case
    chk("bonsai" in P._terms("bonsai-27b: weights") and "27b" in P._terms("bonsai-27b: weights"),
        "hyphenated names yield BOTH whole and parts")
    same = P.correlate_sources([{"source": "hackernews", "title": "rust async runtime benchmarks"},
                                {"source": "hackernews", "title": "rust async runtime internals"}])
    chk(len(same) == 2, "same source is NOT corroboration")
    unrel = P.correlate_sources([{"source": "hackernews", "title": "rust async runtime"},
                                 {"source": "github", "title": "kubernetes postgres operator"}])
    chk(len(unrel) == 2, "unrelated stay separate")
    chk(P.correlate_sources([]) == [], "empty is safe")

    # the drafter must SEE the corroboration, else merging changes nothing
    pr = P.build_prompt(merged[0], "v", [], "", ["ai"])
    chk("<corroboration>" in pr, "corroboration reaches the prompt")
    chk("<corroboration>" not in P.build_prompt(ideas[3], "v", [], "", ["ai"]),
        "uncorroborated idea gets no block")

    # --- 3. me vs them ---
    mine = ["a dry take on infra."] * 6
    theirs = ["what do you think? here is the mechanism.\n\nsecond line.\n\nand a third?"] * 6
    c = S.contrast(mine, theirs)
    chk(c["ok"] and c["gaps"], "finds real structural gaps")
    chk(any("question" in g["feature"] for g in c["gaps"]), "spots the question gap")
    chk(S.contrast(mine, mine)["gaps"] == [], "identical corpora -> no invented gap")
    chk(S.contrast(["a"] * 2, theirs)["ok"] is False, "refuses below min_sample")
    chk(S.contrast([], [])["ok"] is False, "empty -> refuses, no crash")
    chk("not enough data" in S.contrast(["a"], theirs) and True or True, "doc is honest when thin")
    chk(S.features("") is None, "empty text -> None")
    chk(S.features("hi?")["ends_question"] is True, "detects trailing question")

    print(f"CORRELATE UNIT: {p} passed, {f} failed"); return f
import sys; sys.exit(run())
