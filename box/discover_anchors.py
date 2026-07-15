#!/usr/bin/env python3
"""Find anchors you can ACTUALLY reach — the real 10x lever.

Measured constraint: the current 24 anchors (@theo, @steipete, @dabit3, @jxnlco,
@tom_doerr...) are US-timezone. 40% of their posts land 01:00-07:59 IST, and their PEAK
(03:00-05:00 IST = US afternoon = peak X) is exactly when the user is asleep. A ~25min
reply window is physically unreachable there, and no amount of code fixes it.

So: find high-reach on-pillar accounts whose posting clock overlaps the user's waking
hours. Every one added converts unreachable opportunity into reachable opportunity, which
is the only thing that moves 1,093 -> 10,930 given the timezone.

Method: take who the current anchors themselves engage with (their reply targets are
on-pillar by construction), score by follower count AND by the share of their posts landing
in the user's awake window, and propose the winners for targets_b.
"""
from __future__ import annotations
import os, json, time, argparse, collections

AWAKE = range(9, 24)   # 09:00-23:59 local — when a 25min window is actually actionable


def clock_overlap(tweets, tz_offset_h=0.0):
    """Share of an account's posts that land while the user is awake."""
    if not tweets:
        return 0.0
    hits = 0
    for t in tweets:
        lt = time.localtime(t["ts"] / 1000)
        if lt.tm_hour in AWAKE:
            hits += 1
    return round(hits / len(tweets), 3)


def main():
    ap = argparse.ArgumentParser(description="Find anchors whose clock overlaps yours")
    ap.add_argument("--min-followers", type=int, default=60000)
    # A CEILING matters more than the floor. First pass found @jack (9.9M), @satyanadella
    # (7.1M), @aplusk (14M): their tweets take 500+ replies within minutes, so earliness ->
    # 0 and you are reply #2000 — invisible. Reach you cannot get early on is worthless.
    ap.add_argument("--max-followers", type=int, default=800000)
    ap.add_argument("--max-median-replies", type=int, default=80,
                    help="if their posts routinely draw more than this, you can never be early")
    ap.add_argument("--min-overlap", type=float, default=0.5, help="share of posts in your awake window")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    import candidate_source as cs
    key = os.environ["CANDIDATE_API_KEY"]
    here = os.path.dirname(os.path.abspath(__file__))
    d = json.load(open(os.path.join(here, "targets.json")))
    known = {h.lower() for h in (d.get("targets_a") or []) + (d.get("targets_b") or [])}
    now = int(time.time() * 1000)

    # who do your anchors reply TO? those accounts are on-pillar by construction and are
    # a far better pool than topic search (which is crypto-polluted).
    seeds = (d.get("targets_b") or [])[:12]
    pool = collections.Counter()
    for i in range(0, len(seeds), 12):
        q = "(" + " OR ".join(f"from:{h.lower()}" for h in seeds[i:i+12]) + ") filter:replies"
        for t in cs._fetch(q, key, max_pages=2, now=now):
            for tok in (t.get("text") or "").split():
                if tok.startswith("@") and len(tok) > 2:
                    h = tok[1:].strip(".,:!?").lower()
                    if h not in known and h.isalnum():
                        pool[h] += 1
    cands = [h for h, n in pool.most_common(40) if n >= 2]
    print(f"  {len(cands)} candidate accounts your anchors engage with")

    found = []
    for h in cands[:20]:
        try:
            tw = cs._fetch(f"from:{h} -filter:replies", key, max_pages=1, now=now)
        except Exception:
            continue
        if not tw:
            continue
        fol = max((t.get("author_followers") or 0) for t in tw)
        if not (args.min_followers <= fol <= args.max_followers):
            continue
        # can you realistically be early? median replies is the honest test.
        reps = sorted(int(t.get("reply_count") or 0) for t in tw)
        med = reps[len(reps) // 2] if reps else 0
        if med > args.max_median_replies:
            continue
        # on-pillar? a 200k art account is reach you cannot convert.
        pillars = [p.strip().lower() for p in os.environ.get("CHORUS_PILLARS", "").split(",") if p.strip()]
        blob = " ".join((t.get("text") or "") for t in tw).lower()
        if pillars and not any(p in blob for p in pillars):
            continue
        ov = clock_overlap(tw)
        found.append((ov, fol, h, med))
    found.sort(reverse=True)

    print(f"\n  reachable band {args.min_followers:,}-{args.max_followers:,} followers, "
          f"<={args.max_median_replies} median replies, on-pillar, by AWAKE-OVERLAP:")
    keep = []
    for ov, fol, h, n in found:
        ok = ov >= args.min_overlap
        print(f"   {'✓' if ok else ' '} @{h:<20s} {fol:>8,} followers · {ov:.0%} awake-overlap · ~{n} replies/post")
        if ok:
            keep.append(h)
    if not keep:
        print("\n  none cleared the overlap bar — your niche may simply be US-clocked.")
        return
    print(f"\n  -> {len(keep)} reachable anchor(s): {', '.join('@'+k for k in keep)}")
    if args.dry_run:
        print("  (dry-run: targets.json unchanged)")
        return
    d["targets_b"] = list(dict.fromkeys((d.get("targets_b") or []) + keep))[:32]
    json.dump(d, open(os.path.join(here, "targets.json"), "w"), indent=2)
    print(f"  targets_b now {len(d['targets_b'])}")


if __name__ == "__main__":
    main()
