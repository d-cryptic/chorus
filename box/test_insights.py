import time, insights as I

NOW = int(time.time() * 1000)

def R(action="posted", pillar="infra", author="a", likes=None, replies=None, ts=None, id_="x"):
    return {"id": id_, "action": action, "author_handle": author, "angle": "ang",
            "factors": {"pillar_name": pillar}, "pillar": pillar,
            "likes": likes, "replies": replies, "ts": ts or NOW}

def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    # ---- confidence ----
    chk(I.confidence(0) == 0.0, "n=0 -> zero confidence (we know nothing)")
    chk(I.confidence(10, k=10) == 0.5, "n=k -> 0.5 confidence")
    chk(I.confidence(1000) > 0.98, "large n -> near-certain")
    chk(I.confidence(5) < I.confidence(50), "confidence rises with n")

    # ---- shrinkage ----
    chk(I.shrink(0, 0) == round(I.PRIOR_ACCEPT, 4), "n=0 returns the PRIOR, not 0/0")
    chk(I.shrink(1, 1) < 1.0, "1/1 must NOT be reported as 100%")
    chk(abs(I.shrink(300, 1000) - 0.30) < 0.02, "large n converges to observed rate")
    chk(I.shrink(0, 5) < I.PRIOR_ACCEPT, "zero successes pulls below prior")

    # ---- wilson: the anti-overclaim property ----
    chk(I.wilson_lower(0, 0) == 0.0, "no data -> 0 bound")
    chk(I.wilson_lower(3, 3) < I.wilson_lower(30, 40),
        "3/3 (100%) must NOT outrank 30/40 (75%) — the whole point")
    chk(I.wilson_lower(50, 100) < 0.5, "bound sits below the point estimate")
    chk(I.wilson_lower(10, 10) > I.wilson_lower(1, 1), "more evidence -> higher bound")

    # ---- decay ----
    chk(I.decay(1.0, 0) == 1.0, "no decay at age 0")
    chk(I.decay(1.0, 14) < 0.6, "confidence decays with staleness")
    chk(I.decay(1.0, 30) < I.decay(1.0, 10), "older decays further")

    # ---- tally ----
    rows = [R(action="posted"), R(action="dismissed"), R(action="posted_edited")]
    t = I.tally(rows, lambda r: r["pillar"])
    chk(t["infra"] == {"posted": 2, "total": 3}, "posted_edited counts as posted")

    # ---- rank_buckets EXCLUDES under-sampled buckets ----
    b = {"a": {"posted": 3, "total": 3}, "b": {"posted": 6, "total": 8}}
    rk = I.rank_buckets(b, min_sample=5)
    chk(len(rk) == 1 and rk[0]["key"] == "b",
        "n=3 bucket excluded entirely (not ranked #1 on a fake 100%)")
    # NOTE: wilson(3/3)=0.4385 > wilson(6/8)=0.4093 — a perfect 3/3 legitimately edges
    # 6/8 at 95%. So wilson ALONE does not stop small-n overclaiming; MIN_SAMPLE does.
    # This asserts that real behaviour so nobody "fixes" the guard away later.
    chk(I.rank_buckets(b, min_sample=2)[0]["key"] == "a",
        "wilson alone lets 3/3 win -> MIN_SAMPLE is the actual small-n guard")
    chk(I.wilson_lower(3, 3) < I.wilson_lower(30, 40),
        "with enough n, 30/40 beats 3/3 (wilson does its job at scale)")

    # ---- THE core guarantee: no claims at n=0 ----
    got = I.build_insights([], now_ms=NOW)
    kinds = {g["kind"]: g for g in got}
    for k in ("winning_format", "useful_account", "best_time"):
        chk(kinds[k]["payload"]["state"] == "insufficient_data", f"{k}: no data -> insufficient")
        chk(kinds[k]["confidence"] == 0.0, f"{k}: zero confidence at n=0")
    chk(all("best" not in g["payload"] for g in got), "n=0 emits NO 'best' claim at all")
    chk(not any(g["kind"] == "post" for g in got), "no post verdicts without outcomes")

    # ---- still refuses just below MIN_SAMPLE ----
    few = [R(author="solo") for _ in range(I.MIN_SAMPLE - 1)]
    k2 = {g["kind"]: g for g in I.build_insights(few, now_ms=NOW)}
    chk(k2["useful_account"]["payload"]["state"] == "insufficient_data",
        f"n={I.MIN_SAMPLE-1} still refuses to name a useful account")

    # ---- with enough data it DOES claim ----
    many = ([R(action="posted", pillar="infra", author="good") for _ in range(6)] +
            [R(action="dismissed", pillar="crypto", author="bad") for _ in range(6)])
    k3 = {g["kind"]: g for g in I.build_insights(many, now_ms=NOW)}
    chk(k3["winning_format"]["payload"]["best"] == "infra", "picks the winning pillar")
    chk(k3["winning_format"]["confidence"] > 0, "real confidence once n is sufficient")
    chk(k3["useful_account"]["payload"]["ranked"][0]["key"] == "good", "ranks the useful account first")
    chk(k3["dominant_topic"]["payload"]["dominant"] in ("infra", "crypto"), "dominant topic emitted")

    # ---- post verdicts only for measured outcomes ----
    meas = [R(action="posted", likes=10, replies=2, id_="hi"),
            R(action="posted", likes=0, replies=0, id_="lo"),
            R(action="posted", likes=5, replies=0, id_="mid")]
    verdicts = {g["subject_id"]: g["payload"]["verdict"]
                for g in I.build_insights(meas, now_ms=NOW) if g["kind"] == "post"}
    chk(verdicts.get("hi") == "worked", "high engagement -> worked")
    chk(verdicts.get("lo") == "underperformed", "low engagement -> underperformed")
    unmeasured = [R(action="posted", likes=None) for _ in range(3)]
    chk(not any(g["kind"] == "post" for g in I.build_insights(unmeasured, now_ms=NOW)),
        "posted-but-unmeasured yields NO verdict (no invented numbers)")

    # ---- change-gating protects the budget ----
    a = I.build_insights(many, now_ms=NOW)
    chk(I.fingerprint(a) == I.fingerprint(I.build_insights(many, now_ms=NOW)),
        "fingerprint is stable for identical data")
    chk(I.fingerprint(a) != I.fingerprint(I.build_insights(many + [R(author="new")] * 6, now_ms=NOW)),
        "fingerprint moves when the aggregate moves")
    chk(not I.should_synthesize("fp", "fp", have_claims=True), "unchanged -> skip paid L3")
    chk(I.should_synthesize("fp2", "fp", have_claims=True), "moved -> run L3")
    chk(not I.should_synthesize("fp2", "fp", have_claims=False),
        "no claims -> never pay for synthesis (the n=0 case)")

    # ---- regression: the insufficient placeholder MUST share the real claim's id ----
    # id = hash(kind|scope|subject_id). If the placeholder's scope/subject differ from the
    # real claim's, the real claim inserts a NEW row and the stale insufficient_data row
    # stays active forever — silently breaking "deterministic replacement, never duplicates".
    empty = {g["kind"]: g for g in I.build_insights([], now_ms=NOW)}
    real  = {g["kind"]: g for g in I.build_insights(many, now_ms=NOW)}
    for kind in ("winning_format", "useful_account", "best_time"):
        chk(empty[kind]["scope"] == real[kind]["scope"]
            and empty[kind]["subject_id"] == real[kind]["subject_id"],
            f"{kind}: placeholder shares scope/subject with the real claim (same id)")
    chk(empty["useful_account"]["scope"] == "network", "useful_account placeholder uses network scope")

    print(f"INSIGHTS UNIT: {p} passed, {f} failed"); return f

import sys; sys.exit(run())
