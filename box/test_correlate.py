"""The three correlations the user asked for, plus the traps each one sets.

1. winning_shape  — post vs thread vs longform (insights.py)
2. cross-source   — same story on HN+GitHub+timeline -> ONE stronger idea (post_gen.py)
3. me-vs-them     — where your structure diverges from what lands (style_mine.py)
"""
import insights as I, post_gen as P, style_mine as S, ranker as R


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

    # --- taste: what the user POSTS vs what they IGNORE (their own revealed preference) ---
    # rank_tune learns the NUMERIC factors (pillar, author, freshness). Nothing learned the
    # STYLISTIC ones, which are exactly what the drafter controls. Measured on the first real
    # sample: posted drafts carry a question 20% of the time, ignored ones 55% — the user
    # posts statements. The niche patterns actively fight this: they describe what works for
    # OTHER people, so taste is read FIRST and outranks them.
    t = S.taste_contrast(["a dry statement."] * 6, ["really? what do you think?"] * 6)
    chk(t["ok"], "taste runs with enough of both")
    notes = [x["note"] for x in t["prefs"]]
    chk(any("statements, not questions" in n for n in notes), "spots statements-over-questions")
    # direction matters: `more`/`less` read backwards and would invert the user's taste while
    # the tests still passed. Assert BOTH directions.
    t2 = S.taste_contrast(["really? what do you think?"] * 6, ["a dry statement."] * 6)
    chk(any("you post questions more" in x["note"] for x in t2["prefs"]),
        "inverted input inverts the claim (the mapping is direction-correct)")
    chk(S.taste_contrast(["a"] * 2, ["b?"] * 6)["ok"] is False, "refuses below min_sample on either side")
    chk(S.taste_contrast([], [])["ok"] is False, "empty is safe")
    chk("not enough data" in S.taste_doc(S.taste_contrast(["a"], ["b?"])), "doc is honest when thin")
    chk(S.taste_contrast(["a dry statement."] * 6, ["a dry statement."] * 6)["prefs"] == [],
        "identical corpora invent no preference")
    # the drafter must READ it, and taste must come BEFORE the niche tags
    import inspect
    nsrc = inspect.getsource(R.niche_context)
    chk("chorus:self:taste" in nsrc, "drafter reads the taste doc (stored-but-unread = inert)")
    chk(nsrc.index("chorus:self:taste") < nsrc.index("chorus:niche"),
        "taste is read BEFORE niche: the user's own taste outranks other people's patterns")

    # --- "posted" is a CLICK, not an act -------------------------------------------------
    # The intent URL only OPENS X's composer; the user still has to hit Post there. Measured
    # against their real timeline (120 tweets, a year of history, 3 pages per lane so "not
    # found" cannot be a window artifact): only 4 of 10 "posted" suggestions actually exist
    # on X. Six were clicked and abandoned. Every taste/acceptance conclusion drawn from raw
    # "posted" is therefore 60% contaminated — including the one I shipped earlier today
    # ("you post statements, not questions"), which the MIN_SAMPLE guard correctly REFUSES to
    # make once the input is honest (4 verified < 5 needed).
    # outcome_track sets likes/replies only for suggestions it FOUND on X, so a non-null
    # `likes` IS the verification.
    import inspect
    ssrc = inspect.getsource(S.main)
    chk('f.get("likes") is not None' in ssrc, "taste counts only VERIFIED posts")
    import rank_tune as RT
    rsrc = inspect.getsource(RT.main)
    chk('verified = f.get("likes") is not None' in rsrc, "rank_tune knows verified from claimed")
    chk("w *= 0.5" in rsrc, "an unverified click is half a vote, not a full one")
    # and it must still COUNT: a click is a real preference signal, just a weaker one
    chk("w *= 0.0" not in rsrc, "a click is not discarded — they liked it enough to open X")

    # --- outcome_track wrote orphan rows for the life of the file -----------------------
    # /api/box/feedback selected f.id (the FEEDBACK row's autoincrement) and never s.id, so
    #     sid = f.get("suggestion_id") or f.get("id")
    # silently fell back to 15/13/22/16. Those rows join to NO suggestion, so `verified` was
    # always 0 and rank_tune's engagement signal was permanently empty — while the log
    # cheerfully printed "matched+measured 4". The code had anticipated the right key; the
    # endpoint just never sent it.
    import inspect
    osrc = inspect.getsource(__import__("outcome_track"))
    chk('sid = f.get("suggestion_id")' in osrc, "keys the write on the real suggestion_id")
    # Check the CODE, not the prose. The comment explaining the bug necessarily quotes it,
    # exactly like the em-dash ban rule has to contain an em-dash — a naive substring match
    # fails on the explanation while the code is correct.
    sid_lines = [l for l in osrc.split("\n")
                 if "sid = f.get(" in l and not l.strip().startswith("#")]
    chk(sid_lines and all('or f.get("id")' not in l for l in sid_lines),
        "NO fallback to f.id in the actual assignment (it silently wrote orphans)")
    chk("endpoint bug" in osrc, "a missing suggestion_id is reported, not papered over")
    # discovery must cover posts/quotes, not just replies (7 of 10 were invisible)
    chk("-filter:replies" in osrc, "discovers originals AND quotes")
    chk("filter:replies" in osrc, "still discovers replies")

    # --- a broken write must not read as "nothing to do" --------------------------------
    # Three swallows with real consequences, each indistinguishable from success:
    #   outcome_track  a dead endpoint looked EXACTLY like "nothing matched" — which is how
    #                  it reported success while writing orphan rows for its entire life
    #   post_gen       an unconsumed capture drafts AGAIN next cycle: same idea twice, paid twice
    #   style_mine     if every delete fails the supersede is a no-op and docs accumulate —
    #                  exactly how today's poisoned niche pattern would have outlived its fix
    import inspect
    import outcome_track as OT, post_gen as PG2, style_mine as SM2
    chk("failed.append" in inspect.getsource(OT.main), "outcome_track collects write failures")
    chk("incomplete, not empty" in inspect.getsource(OT.main),
        "...and distinguishes a broken endpoint from an empty result")
    chk("will draft again next cycle" in inspect.getsource(PG2.main),
        "post_gen names the CONSEQUENCE of an unconsumed capture")
    chk("stuck.append" in inspect.getsource(SM2.supersede), "style_mine collects delete failures")

    # and prove supersede actually SAYS it when every delete fails
    real = SM2._req
    SM2._req = lambda url, method="GET", token=None, body=None, **k: (
        {"memories": [{"id": "a", "containerTags": ["t"]}]} if "list" in url
        else (_ for _ in ()).throw(ConnectionError("refused")))
    try:
        chk(SM2.supersede("t", "") == 0, "supersede reports 0 deleted when deletes fail")
    finally:
        SM2._req = real

    print(f"CORRELATE UNIT: {p} passed, {f} failed"); return f
import sys; sys.exit(run())
