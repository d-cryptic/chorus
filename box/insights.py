#!/usr/bin/env python3
"""Chorus insights engine — L1 free analytics + L3 gated LLM synthesis.

Summary: turns the feedback/outcome rows Chorus already collects into typed `insight`
rows (kind, confidence, evidence, lifecycle) per the v0 nakama insights spec. The
non-negotiable property: NEVER claim anything at low n. v0's rules are "min-sample
before any claim" and "zero invented numbers" — so every estimate is shrunk toward a
prior, ranked by a Wilson lower bound, and suppressed entirely below MIN_SAMPLE.
Cost-tiered: L1 is pure SQL/arithmetic ($0); L3 (LLM playbook synthesis) only runs when
the aggregate actually MOVED (change-gating), so a quiet week costs nothing.

Pure core (no network) so it is unit-testable; ranker/cron own the I/O.
"""
from __future__ import annotations
import os, json, math

MIN_SAMPLE = 5      # below this we refuse to make a claim (v0: min-sample guard)
PRIOR_K = 10        # shrinkage strength: est = (n*mean + k*prior)/(n+k)
PRIOR_ACCEPT = 0.30 # cold-start prior for "share of suggestions worth posting"
DECAY_LAMBDA = 0.05 # confidence half-life ~14d


# ---- statistics -------------------------------------------------------------

def confidence(n: int, k: int = PRIOR_K) -> float:
    """v0: confidence(n) = n/(n+k). n=0 -> 0.0 (we know nothing)."""
    if n <= 0:
        return 0.0
    return round(n / (n + k), 4)


def shrink(successes: int, n: int, prior_mean: float = PRIOR_ACCEPT,
           k: int = PRIOR_K) -> float:
    """Bayesian shrinkage toward a prior. With n=0 this returns the prior, NOT 0/0."""
    if n <= 0:
        return round(prior_mean, 4)
    return round((successes + k * prior_mean) / (n + k), 4)


def wilson_lower(successes: int, n: int, z: float = 1.96) -> float:
    """Wilson score lower bound — rank small samples without overclaiming.

    3/3 (100%) must NOT outrank 30/40 (75%); the lower bound encodes that.
    """
    if n <= 0:
        return 0.0
    p = successes / n
    d = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return round(max(0.0, (centre - margin) / d), 4)


def decay(conf0: float, age_days: float, lam: float = DECAY_LAMBDA) -> float:
    """v0: conf = conf0 * e^(-lambda*age). Stale insights lose confidence."""
    return round(conf0 * math.exp(-lam * max(0.0, age_days)), 4)


# ---- L1 aggregation ---------------------------------------------------------

POSTED = ("posted", "posted_edited")


def tally(rows, key_fn):
    """-> {key: {'posted': int, 'total': int}}. Rows are /api/box/feedback shape."""
    out: dict = {}
    for r in rows:
        k = key_fn(r)
        if k is None or k == "":
            continue
        b = out.setdefault(k, {"posted": 0, "total": 0})
        b["total"] += 1
        if (r.get("action") or "") in POSTED:
            b["posted"] += 1
    return out


def engagement(r) -> int:
    """Raw engagement for a posted reply. Chorus has no impressions, so v0's
    eng_rate = likes/views is NOT computable — we use a raw count and say so."""
    return int(r.get("likes") or 0) + int(r.get("replies") or 0)


def rank_buckets(buckets, *, min_sample: int = MIN_SAMPLE):
    """Rank by Wilson lower bound. Buckets under min_sample are EXCLUDED, not
    ranked low — an unranked bucket is honest; a confidently-ranked n=1 is not."""
    ranked = []
    for k, b in buckets.items():
        if b["total"] < min_sample:
            continue
        ranked.append({
            "key": k,
            "posted": b["posted"],
            "total": b["total"],
            "rate": round(b["posted"] / b["total"], 4),
            "shrunk": shrink(b["posted"], b["total"]),
            "wilson": wilson_lower(b["posted"], b["total"]),
            "confidence": confidence(b["total"]),
        })
    ranked.sort(key=lambda x: x["wilson"], reverse=True)
    return ranked


def insufficient(kind: str, n: int, need: int = MIN_SAMPLE, *,
                 scope: str = "user", subject_id: str = "self") -> dict:
    """An honest 'we don't know yet' insight. Better than a fabricated claim.

    scope/subject_id MUST match the real claim's, because the row id is
    hash(kind|scope|subject_id): if they differ, the real claim inserts a NEW row and
    this placeholder stays active forever instead of being superseded.
    """
    return {
        "kind": kind, "scope": scope, "subject_id": subject_id, "term": "short",
        "confidence": 0.0, "status": "active",
        "payload": {"state": "insufficient_data", "n": n, "need": need,
                    "note": f"need >= {need} acted-on suggestions; have {n}"},
        "evidence": [],
    }


def apply_decay(stored, *, now_ms: int, floor: float = 0.05) -> list:
    """Age existing insights. v0's lifecycle is Derived->Active->Refreshed->Decayed->Archived,
    but decay() was implemented, unit-tested, and never called — so a month-old claim kept
    its birth confidence forever and rank_tune trusted it exactly as much as this morning's
    (0.55 vs a decayed 0.12: 4.5x over-confident).

    A claim the world has moved past should fade, not vanish: below `floor` it is marked
    'decayed' rather than deleted, so the evidence survives for audit.
    """
    out = []
    for i in stored:
        created = i.get("created_at") or i.get("createdAt") or now_ms
        age_d = max(0.0, (now_ms - created) / 86_400_000)
        c0 = float(i.get("confidence") or 0)
        c = decay(c0, age_d)
        out.append({**i, "confidence": c,
                    "status": "decayed" if c < floor else (i.get("status") or "active"),
                    "decayed_from": c0, "age_days": round(age_d, 2)})
    return out



def shape_of(r) -> str:
    """post | thread | longform, from a feedback row.

    The shape lives on the suggestion (thread JSON array / longform text), not on the
    feedback row itself, so /api/box/feedback must select s.thread and s.longform or this
    silently reports "post" for everything and the whole correlation is a lie.
    """
    lf = r.get("longform")
    if lf and str(lf).strip():
        return "longform"
    th = r.get("thread")
    if isinstance(th, str):
        try:
            th = json.loads(th or "[]")
        except Exception:
            th = []
    if th:
        return "thread"
    return "post"


def follower_delta(r):
    """Followers gained while this was live. None when unmeasured -- NOT 0.

    Conflating "unmeasured" with "gained nothing" would drag every average toward zero and
    make whichever shape is newest look worst, purely because it has less outcome data.
    """
    v = r.get("followers_delta")
    if v is None:
        v = (r.get("outcome") or {}).get("followers_delta") if isinstance(r.get("outcome"), dict) else None
    try:
        return None if v is None else int(v)
    except (TypeError, ValueError):
        return None

def build_insights(rows, *, now_ms: int) -> list:
    """L1: rows (feedback+outcome) -> typed insight dicts. No LLM, no network, $0."""
    n = len(rows)
    out: list = []

    # 1. winning_format — which pillar earns a post
    by_pillar = tally(rows, lambda r: (r.get("factors") or {}).get("pillar_name")
                      or r.get("pillar"))
    ranked = rank_buckets(by_pillar)
    out.append(insufficient("winning_format", n) if not ranked else {
        "kind": "winning_format", "scope": "user", "subject_id": "self",
        "term": "short", "status": "active",
        "confidence": max(x["confidence"] for x in ranked),
        "payload": {"best": ranked[0]["key"], "ranked": ranked},
        "evidence": [f"pillar:{x['key']} {x['posted']}/{x['total']}" for x in ranked],
    })

    # 1b. winning_shape — post vs thread vs longform. This is the question "winning_format"
    # sounds like it answers but does not (it ranks PILLARS). Kept separate rather than
    # renamed: `winning_format` is a stored insight kind, and silently changing what a kind
    # means would corrupt every historical row.
    by_shape = tally(rows, shape_of)
    ranked_s = rank_buckets(by_shape)
    shape_ev = [f"{x['key']} {x['posted']}/{x['total']} accepted" for x in ranked_s]
    # ...and what each shape actually EARNED, where measured. Acceptance is the user's taste;
    # followers are the goal. They are different questions and can disagree.
    gained: dict = {}
    for r in rows:
        d = follower_delta(r)
        if d is None or (r.get("action") or "") not in POSTED:
            continue
        gained.setdefault(shape_of(r), []).append(d)
    per_shape = {k: {"n": len(v), "total_followers": sum(v),
                     "mean": round(sum(v) / len(v), 3)} for k, v in gained.items() if v}
    for k, v in sorted(per_shape.items(), key=lambda kv: -kv[1]["mean"]):
        if v["n"] >= MIN_SAMPLE:
            shape_ev.append(f"{k}: +{v['total_followers']} followers over {v['n']} posts")
        else:
            shape_ev.append(f"{k}: {v['n']} measured post(s) — below min-sample, no claim")
    out.append(insufficient("winning_shape", n) if not ranked_s else {
        "kind": "winning_shape", "scope": "user", "subject_id": "self",
        "term": "short", "status": "active",
        "confidence": max(x["confidence"] for x in ranked_s),
        "payload": {"best_accepted": ranked_s[0]["key"], "ranked": ranked_s,
                    "followers_by_shape": per_shape,
                    # only name a follower winner once it clears MIN_SAMPLE
                    "best_by_followers": next((k for k, v in sorted(
                        per_shape.items(), key=lambda kv: -kv[1]["mean"])
                        if v["n"] >= MIN_SAMPLE), None)},
        "evidence": shape_ev,
    })

    # 2. useful_account — whose tweets are actually worth replying to
    by_author = tally(rows, lambda r: r.get("author_handle"))
    ranked_a = rank_buckets(by_author)
    out.append(insufficient("useful_account", n, scope="network", subject_id="targets")
               if not ranked_a else {
        "kind": "useful_account", "scope": "network", "subject_id": "targets",
        "term": "long", "status": "active",
        "confidence": max(x["confidence"] for x in ranked_a),
        "payload": {"ranked": ranked_a[:20]},
        "evidence": [f"@{x['key']} {x['posted']}/{x['total']}" for x in ranked_a[:20]],
    })

    # 3. best_time — hour-of-day worth engaging, in the USER's clock.
    # localtime() reads the BOX's timezone, and the box is UTC. That made every best_time
    # insight off by the IST offset: "best_hour 14" meant 19:30 to the user, who would read
    # it as 2pm and post at the wrong time. Same bug class that had fast_lane polling the
    # user's sleep and skipping their morning. Never localtime() on this box.
    import time as _t
    tz_off = float(os.environ.get("CHORUS_TZ_OFFSET_H", "5.5"))

    def _hour(r):
        ts = r.get("ts")
        return _t.gmtime(ts / 1000 + tz_off * 3600).tm_hour if ts else None

    by_hour = tally(rows, _hour)
    ranked_h = rank_buckets(by_hour)
    out.append(insufficient("best_time", n) if not ranked_h else {
        "kind": "best_time", "scope": "user", "subject_id": "self",
        "term": "short", "status": "active",
        "confidence": max(x["confidence"] for x in ranked_h),
        "payload": {"best_hour": ranked_h[0]["key"], "ranked": ranked_h},
        "evidence": [f"h{x['key']} {x['posted']}/{x['total']}" for x in ranked_h],
    })

    # 4. post verdicts — only for posted rows that actually have measured outcomes
    measured = [r for r in rows
                if (r.get("action") or "") in POSTED and r.get("likes") is not None]
    if measured:
        eng = sorted(engagement(r) for r in measured)
        mid = eng[len(eng) // 2]
        for r in measured:
            e = engagement(r)
            out.append({
                "kind": "post", "scope": "post",
                "subject_id": str(r.get("id")), "term": "immediate", "status": "active",
                "confidence": confidence(len(measured)),
                "payload": {"verdict": "worked" if e > mid else "underperformed",
                            "engagement": e, "median": mid,
                            "author": r.get("author_handle"), "angle": r.get("angle")},
                "evidence": [f"likes+replies={e} vs median {mid} over n={len(measured)}"],
            })

    # 5. dominant_topic — share of pillars seen (descriptive; safe at any n>0)
    if n:
        shares = {k: round(v["total"] / n, 4) for k, v in by_pillar.items()}
        if shares:
            top = max(shares, key=shares.get)
            out.append({
                "kind": "dominant_topic", "scope": "user", "subject_id": "self",
                "term": "short", "status": "active", "confidence": confidence(n),
                "payload": {"dominant": top, "share": shares[top], "byTopic": shares},
                "evidence": [f"{k}={v}" for k, v in shares.items()],
            })
    return out


# ---- change-gating (L3 only runs when the aggregate MOVED) -------------------

def fingerprint(insights) -> str:
    """Stable digest of the L1 claims. If unchanged, skip the paid L3 synthesis."""
    import hashlib, json
    key = [(i["kind"], json.dumps(i["payload"], sort_keys=True, default=str))
           for i in insights if i["kind"] in ("winning_format", "useful_account",
                                              "best_time", "dominant_topic")]
    key.sort()
    return hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:16]


def should_synthesize(new_fp: str, old_fp: str | None, *, have_claims: bool) -> bool:
    """Gate the paid call: never synthesize with no claims, or if nothing moved."""
    return bool(have_claims) and new_fp != old_fp


# ---- runner (I/O lives here; everything above is pure) ----------------------

def _id(kind: str, scope: str, subject: str) -> str:
    import hashlib
    return hashlib.sha256(f"{kind}|{scope}|{subject}".encode()).hexdigest()[:20]


def synthesize_playbook(claims, *, model, api_key, tracker=None):
    """L3: one gated LLM call -> playbook doc. Returns None when it must not run.

    v0 rule: cite evidence, invent no numbers. We pass ONLY the L1 claims (which are
    already sample-guarded), never raw tweets, so there is nothing to hallucinate from.
    """
    import json as _j
    if not api_key or not claims:
        return None
    if tracker is not None:
        import budget as B
        try:
            tracker.check("llm_synth", 1)
        except B.BudgetError as e:
            print(f"  playbook synthesis skipped ({e.reason})")
            return None
    prompt = (
        "You are summarising a person's X (Twitter) reply strategy from ALREADY-COMPUTED "
        "statistics. Use ONLY the numbers given. Invent nothing. If evidence is weak, say so.\n"
        f"STATS (JSON):\n{_j.dumps(claims, indent=2)[:4000]}\n"
        'Return JSON {"phase":"cold_start|traction|compounding",'
        '"keep_long":[{"rule":str,"evidence":str,"confidence":0..1}],'
        '"keep_short":[...],"dont_keep":[{"rule":str,"evidence":str,"confidence":0..1}]}'
    )
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}, "max_tokens": 700}
    try:
        out = _req("https://openrouter.ai/api/v1/chat/completions", "POST", api_key, body)
        if tracker is not None:
            tracker.record("llm_synth", 1)
        txt = (out["choices"][0]["message"]["content"] or "").strip()
        if txt.startswith("```"):
            txt = txt.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0]
        return _j.loads(txt)
    except Exception as e:
        print(f"  playbook synthesis failed (non-fatal): {repr(e)[:60]}")
        return None


def _req(url, method="GET", token=None, body=None, timeout=30):
    import json as _j, urllib.request
    data = _j.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("user-agent", "chorus-box/1.0")   # CF blocks Python-urllib
    r.add_header("content-type", "application/json")
    if token:
        r.add_header("authorization", f"Bearer {token}")
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return _j.loads(resp.read() or "{}")


def main():
    import os, time, json, argparse
    import budget as B
    ap = argparse.ArgumentParser(description="Chorus insights: L1 analytics + gated L3 playbook")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="synthesize even if nothing moved")
    args = ap.parse_args()

    base = os.environ.get("INGEST_URL", "http://localhost:8787").rstrip("/")
    token = os.environ.get("INGEST_TOKEN", "")
    model = os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    now = int(time.time() * 1000)

    rows = _req(f"{base}/api/box/feedback?since=0", token=token).get("feedback", [])
    for r in rows:  # factors arrives as a JSON string
        if isinstance(r.get("factors"), str):
            try: r["factors"] = json.loads(r["factors"])
            except Exception: r["factors"] = {}

    ins = build_insights(rows, now_ms=now)
    for i in ins:
        i["id"] = _id(i["kind"], i["scope"], str(i.get("subject_id")))

    # Age anything we are NOT rewriting this run. A fresh claim supersedes its own id, so
    # only untouched kinds need decaying — otherwise a stale claim outlives its evidence.
    fresh_ids = {i["id"] for i in ins}
    try:
        stored = _req(f"{base}/api/box/insights", token=token).get("insights", [])
        stale = [x for x in stored if x.get("id") not in fresh_ids]
        aged = apply_decay(stale, now_ms=now)
        faded = [a for a in aged if a["status"] == "decayed"]
        if aged:
            _req(f"{base}/api/box/insights", "POST", token, {"insights": aged})
            print(f"  aged {len(aged)} untouched insight(s), {len(faded)} decayed out")
    except Exception as e:
        print(f"  decay pass skipped ({repr(e)[:40]})")
    fp = fingerprint(ins)
    claims = [i for i in ins if i["payload"].get("state") != "insufficient_data"
              and i["kind"] != "post"]

    print(f"insights: {len(ins)} from {len(rows)} acted-on rows "
          f"({len(claims)} real claims, rest insufficient_data)")
    if args.dry_run:
        for i in ins:
            print(f"  [{i['confidence']}] {i['kind']}: {json.dumps(i['payload'])[:90]}")
        return

    # The fingerprint is only used to gate the PAID L3 call. A blip reading it must not
    # block the free, always-correct L1 write.
    try:
        prev = _req(f"{base}/api/box/insights", token=token).get("fingerprint")
    except Exception as e:
        print(f"  fingerprint read failed ({repr(e)[:40]}) - will not gate L3 on it")
        prev = None
    try:
        _req(f"{base}/api/box/insights", "POST", token, {"insights": ins, "fingerprint": fp})
    except Exception as e:
        print(f"  WARN: L1 insights not stored: {repr(e)[:60]}")
        return

    if should_synthesize(fp, prev, have_claims=bool(claims)) or (args.force and claims):
        spent, ceiling, paused, killed, quiet, _a = (0, 0.65, 0, 0, None, "L1")
        try:
            s = _req(f"{base}/api/box/settings", token=token).get("settings", {}) or {}
            spent = _req(f"{base}/api/box/spend", token=token).get("total", 0.0)
            ceiling, paused = s.get("daily_ceiling_usd", 0.65), bool(s.get("paused", 0))
            killed, quiet = bool(s.get("killed", 0)), s.get("quiet_hours")
        except Exception as e:
            print(f"  cannot read budget -> skipping paid synthesis ({repr(e)[:40]})")
            return
        tracker = B.BudgetTracker(spent=spent, ceiling=ceiling, paused=paused,
                                  killed=killed, quiet=quiet,
                                  hour_local=time.localtime().tm_hour)
        doc = synthesize_playbook([{ "kind": i["kind"], "payload": i["payload"],
                                     "confidence": i["confidence"]} for i in claims],
                                  model=model, api_key=api_key, tracker=tracker)
        # FLUSH ALWAYS, not inside `if doc:`. synthesize_playbook records the spend the moment
        # the paid call returns, then can still raise on a malformed reply and hand back None.
        # With flush gated on `doc`, that spend never reached the ledger -- paid off the books,
        # tomorrow's ceiling under-counts. Same shape as the mirror-watermark bug: the money
        # moved, the accounting did not. flush() is safe at $0 when nothing was spent.
        usd = tracker.flush()
        if usd > 0:
            # mirror ranker.flush_spend: a failed ledger POST must warn, never crash AFTER the
            # paid call already happened.
            try:
                _req(f"{base}/api/box/spend", "POST", token, {"source": "insights", "usd": usd})
            except Exception as e:
                print(f"  WARN: ${usd} spent but NOT recorded ({repr(e)[:40]})")
        if doc:
            phase = doc.get("phase") or "cold_start"
            _req(f"{base}/api/box/playbook", "POST", token,
                 {"phase": phase, "doc": doc, "fingerprint": fp})
            print(f"  playbook synthesized (phase={phase}, ${usd})")
        elif usd > 0:
            print(f"  playbook synthesis returned nothing, but ${usd} was spent and flushed")
    else:
        print("  L3 skipped: nothing moved (or no real claims) - $0 spent")


if __name__ == "__main__":
    main()
