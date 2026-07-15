#!/usr/bin/env python3
"""Chorus fast lane — the actual follower-growth engine.

WHY THIS EXISTS. The daily ranker was structurally incapable of growth. Measured on the
live queue: suggested tweets averaged fresh=0.79-0.83 (8-10h old), worst 0.557 (21h). A
reply-guy strategy only works if you land in the first ~10-20 replies while the thread is
still being read; hours later the reply section is buried and impressions collapse. An
8-21h-late reply earns ~0 impressions, therefore ~0 followers. Cadence WAS the bottleneck.

So: poll the high-reach anchors every ~10 min, catch their originals within minutes, and
draft immediately. Cost is not the constraint — anchors-only is 1 chunked query per poll:
~15,120 credits/day at 10-min cadence = $0.15/day against a $0.65 ceiling.

This lane is deliberately NARROW (few accounts, very fresh, still-early) because that is
where reach actually comes from. The daily cycle still runs for breadth.
"""
from __future__ import annotations
import os, sys, time, json, argparse
import budget as B
import generate as G
from ranker import (_req, _alert, get_budget, get_voice, voice_context, niche_context,
                    llm_draft, judge_draft, ingest, content_id, already_said,
                    flush_spend, run_log, DEFAULT_WEIGHTS, TIER)

# A reply is only worth making while the thread is live.
MAX_AGE_MIN   = int(os.environ.get("CHORUS_FAST_MAX_AGE_MIN", "120"))   # hard: >2h is late
PRIME_AGE_MIN = int(os.environ.get("CHORUS_FAST_PRIME_MIN", "25"))      # the money window
MAX_REPLIES   = int(os.environ.get("CHORUS_FAST_MAX_REPLIES", "60"))    # still early enough to be seen
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".fast_seen")


def _seen() -> set:
    try:
        return set(json.load(open(STATE)))
    except Exception:
        return set()


def _remember(ids, keep=400):
    try:
        json.dump(list(ids)[-keep:], open(STATE, "w"))
    except Exception:
        pass


def opportunity(c, now_ms) -> float:
    """Reach-weighted urgency. This is NOT the daily ranker's score — that one optimises
    'is this on-pillar?'. This optimises 'will replying here be SEEN?', which is what
    actually converts to followers:
      reach     — a big account's reply section is a bigger stage
      earliness — being reply #5 beats reply #200; decays hard with reply_count
      freshness — cliff-edges after PRIME_AGE_MIN; a late reply is worth ~nothing
    """
    age_min = max(0.5, (now_ms - c.get("ts", now_ms)) / 60000)
    followers = max(1, int(c.get("author_followers") or 0))
    replies = int(c.get("reply_count") or 0)

    import math
    reach = min(1.0, math.log10(followers) / 5.0)            # 100k followers -> 1.0
    early = 1.0 / (1.0 + replies / 12.0)                     # 12 replies -> 0.5
    if age_min <= PRIME_AGE_MIN:
        fresh = 1.0
    else:                                                     # sharp decay past prime
        fresh = max(0.0, 1.0 - (age_min - PRIME_AGE_MIN) / (MAX_AGE_MIN - PRIME_AGE_MIN))
    return round(reach * 0.35 + early * 0.30 + fresh * 0.35, 4)


def main():
    ap = argparse.ArgumentParser(description="Fast lane: reply early to high-reach accounts")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cap", type=int, default=2, help="max suggestions per poll")
    ap.add_argument("--tau", type=float, default=0.45)
    args = ap.parse_args()

    base = os.environ.get("INGEST_URL", "http://localhost:8787").rstrip("/")
    token = os.environ.get("INGEST_TOKEN", "")
    model = os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    pillars = [p.strip() for p in os.environ.get("CHORUS_PILLARS", "").split(",") if p.strip()]
    now = int(time.time() * 1000)

    # A find is only worth money if YOU can reply inside the window. Measured anchor posting
    # by hour (IST): 01:00-07:59 carries 40% of posts but is unreachable — you are asleep and
    # a 4h-old reply earns ~0. Skip most of those; keep 1-in-3 for the 07:00 tail.
    #
    # MUST use the USER's timezone, never the box's. The box runs UTC, so time.localtime()
    # made "quiet 01:00-07:59" mean 06:30-13:29 IST — it skipped the user's MORNING and
    # polled while they slept. Exactly inverted. CHORUS_TZ_OFFSET_H is the user's UTC offset.
    tz_off = float(os.environ.get("CHORUS_TZ_OFFSET_H", "5.5"))   # IST
    hr = time.gmtime(time.time() + tz_off * 3600).tm_hour
    if not args.dry_run and 1 <= hr <= 7 and (int(time.time()) // 600) % 3 != 0:
        print(f"quiet window ({hr:02d}:00 your time) — skipping poll (you cannot reply in time)")
        return

    if args.dry_run:
        tracker = B.BudgetTracker(spent=0.0, ceiling=10.0)
        voice = os.environ.get("CHORUS_VOICE", "concise")
    else:
        try:
            spent, ceiling, paused, killed, quiet, autonomy, _dl = get_budget(base, token)
        except Exception as e:
            msg = repr(e)[:40]
            _alert(f"fast-lane aborted: cannot read budget ({msg})"); return
        tracker = B.BudgetTracker(spent=spent, ceiling=ceiling, paused=paused, killed=killed,
                                  quiet=quiet, hour_local=time.localtime().tm_hour)
        try:
            tracker.check("llm_draft", 1)
        except B.BudgetError as e:
            print(f"fast-lane refused ({e.reason})"); return
        voice = get_voice(os.environ.get("CHORUS_VOICE", "concise"))

    import candidate_source as cs
    tf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "targets.json")
    d = json.load(open(tf)) if os.path.exists(tf) else {}
    # anchors first (reach), then the top peers. NARROW on purpose: 1 chunked query.
    anchors = (d.get("targets_b") or [])[:24] + (d.get("targets_a") or [])[:6]
    if not anchors:
        print("no anchors in targets.json"); return

    key = os.environ.get("CANDIDATE_API_KEY", "")
    ta = tuple(h.lower() for h in (d.get("targets_a") or []))
    tb = tuple(h.lower() for h in (d.get("targets_b") or []))
    # chunk: one OR-query gets unreliable past ~12 handles (the bug that returned 0 tweets)
    cands = []
    for i in range(0, len(anchors), 12):
        q = "(" + " OR ".join(f"from:{h.lower()}" for h in anchors[i:i + 12]) + ") -filter:replies"
        cands += [cs.map_tweet_tier(c, ta, tb) for c in cs._fetch(q, key, max_pages=1, now=now)]
    tracker.record("candidate_read", len(cands))

    seen = _seen()
    live = []
    for c in cands:
        age_min = (now - c.get("ts", now)) / 60000
        if c.get("id") in seen or age_min > MAX_AGE_MIN or age_min < 0:
            continue
        if int(c.get("reply_count") or 0) > MAX_REPLIES:      # already a crowded room
            continue
        live.append((opportunity(c, now), c))
    live.sort(key=lambda x: -x[0])
    print(f"fast lane: {len(cands)} fetched, {len(live)} live (<{MAX_AGE_MIN}m, <{MAX_REPLIES} replies)")

    examples = [] if args.dry_run else voice_context(",".join(pillars))
    niche = "" if args.dry_run else niche_context()
    emitted = 0
    for score, c in live:
        if emitted >= args.cap or score < args.tau:
            break
        age_min = int((now - c.get("ts", now)) / 60000)
        if args.dry_run:
            print(f"  [{score}] {age_min}m old · {c.get('reply_count')} replies · "
                  f"{c.get('author_followers')} followers · @{c.get('author')}: {(c.get('text') or '')[:60]}")
            emitted += 1
            continue

        if already_said(c.get("text") or ""):
            continue
        try:
            tracker.check("llm_draft", 1)
        except B.BudgetError as e:
            print(f"  stopped ({e.reason})"); break
        pillar = next((p for p in pillars if p.lower() in (c.get("text") or "").lower()), None)
        # read the room before speaking: reply #21 saying what 20 people said is invisible
        room = cs.existing_replies(c.get("id"), key, limit=10, now=now)
        tracker.record("candidate_read", len(room))
        if room:
            print(f"  room: {len(room)} replies already under @{c.get('author')}")
        dr = llm_draft(c, pillar, voice, model=model, api_key=api_key,
                       examples=examples, niche=niche, room=room)
        tracker.record("llm_draft", 1)
        drafts = dr.get("drafts") or []
        if not drafts:
            continue
        scores = judge_draft(c, drafts[0], voice, model=model, api_key=api_key, tracker=tracker,
                             examples=examples + tuple(f"(already said) {r['text'][:90]}"
                                                       for r in room[:5]))
        passed, failed = G.judge_verdict(scores)
        if not passed:
            print(f"  judge rejected @{c.get('author')} ({','.join(failed)})")
            continue
        route, why = G.route_post(c, distinct=scores.get("distinct"), pillar_hit=pillar, drafts=drafts)
        if route == G.DROP:
            continue
        ingest(base, token, {
            "id": content_id(c.get("id") or ""), "tweet_id": c.get("id"),
            "tweet_url": c.get("url"), "tweet_text": c.get("text"),
            "author_handle": c.get("author"), "author_tier": c.get("author_tier"),
            "score": round(0.60 + 0.40 * score, 4),   # fast-lane finds outrank the daily batch
            "factors": {"opportunity": score, "age_min": age_min, "fast_lane": 1,
                        "reply_count": c.get("reply_count"),
                        **{f"judge_{k}": v for k, v in scores.items()}},
            "pillar": pillar, "angle": dr.get("angle"), "drafts": drafts,
            "thread": dr.get("thread") or [], "gif": dr.get("gif"),
            "media": c.get("media") or [], "target": route,
            "rationale": f"FAST LANE · {age_min}m old · {c.get('reply_count')} replies · {why}",
            "expires_at": now + 3 * 3600 * 1000,   # a fast-lane find is worthless in 3h
        })
        seen.add(c.get("id"))
        emitted += 1
        _alert(f"⚡ reply now ({age_min}m old, {c.get('reply_count')} replies): "
               f"@{c.get('author')} — {(c.get('text') or '')[:70]}")

    if not args.dry_run:
        _remember(seen)
        flush_spend(base, token, tracker, source="fast_lane")
    print(f"queued {emitted}, spent ${tracker.spent}")


if __name__ == "__main__":
    main()
