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


def _valid_handle(h: str) -> bool:
    """X handles are [A-Za-z0-9_], 1-15 chars. isalnum() used to drop every underscore
    handle -- 26% of real handles (measured live, e.g. @tom_doerr) -- shrinking discovery."""
    return bool(h) and len(h) <= 15 and h.replace("_", "").isalnum()

# When a 25min reply window is actually actionable, in the USER's clock. Measured from their
# posted-feedback, not assumed: 09:00, 10:00, 13:00, 14:00 IST — and a real 01:00 session
# (01:36 and 01:48, replying to @TheAhmadOsman and @DhravyaShah). 01:00 IST is 19:30 UTC, US
# afternoon, so their late session overlaps US anchors. I had previously written that window
# off as "asleep" and scored US anchors down for it, which was an assumption, not a finding.
# Their real dead zone is 02:00-08:00: zero posts, ever.
AWAKE = frozenset([1] + list(range(9, 24)))


def clock_overlap(tweets, tz_offset_h=None):
    """Share of an account's posts that land while the USER is awake.

    Must use the user's timezone, not the box's (the box is UTC). Getting this wrong is how
    fast_lane ended up skipping the user's morning and polling their sleep.
    """
    if not tweets:
        return 0.0
    if tz_offset_h is None:
        tz_offset_h = float(os.environ.get("CHORUS_TZ_OFFSET_H", "5.5"))
    hits = sum(1 for t in tweets
               if time.gmtime(t["ts"] / 1000 + tz_offset_h * 3600).tm_hour in AWAKE)
    return round(hits / len(tweets), 3)



PILLAR_RE = None



def rejected():
    """Handles a human already looked at and said no to.

    Without this the tool re-proposes them EVERY run and the same judgement gets re-litigated
    from scratch: @refikanadol (an AI *artist* — passes pillar keywords, fails pillar intent)
    has now been proposed three times across three sessions. The rejects live in
    box/rejected_anchors.txt (box-only, like targets.json) because the reasoning is about
    specific real people and does not belong in a public repo.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "rejected_anchors.txt")
    out = set()
    if os.path.exists(p):
        for line in open(p):
            h = line.split("#")[0].strip().lstrip("@").lower()
            if h:
                out.add(h)
    return out

def graph_candidates(d, min_f, max_f):
    """Seed from the user's OWN graph. Free: followings.json/followers.json are already local.

    Why this exists: the anchor-engagement seed inherits your anchors' timezone, so it can
    never surface a reachable account if your anchors are all US-centric. Your own graph can.
    """
    import re
    here = os.path.dirname(os.path.abspath(__file__))
    pillar = re.compile(r"\b(ai|ml|llm|agent|infra|devops|kubernetes|cloud|backend|distributed|"
                        r"database|platform|engineer|open.?source|systems|rust|golang|python)", re.I)
    anchors = {h.lower() for h in (d.get("targets_a") or []) + (d.get("targets_b") or [])}
    anchors |= rejected()          # a human already said no; do not ask again
    out, seen = [], set()
    for fn in ("followings.json", "followers.json"):
        p = os.path.join(here, fn)
        if not os.path.exists(p):
            continue
        for u in json.load(open(p)):
            h = (u.get("userName") or "").lower()
            if not h or h in anchors or h in seen:
                continue
            if not (min_f <= (u.get("followers") or 0) <= max_f):
                continue
            if not pillar.search(u.get("description") or ""):
                continue
            seen.add(h)
            out.append(h)
    return out


def main():
    ap = argparse.ArgumentParser(description="Find anchors whose clock overlaps yours")
    # The FLOOR was the bug. 60000 was cargo-culted from advice written for large accounts.
    # Measured against the user's own following graph (2026-07-15): every account in the
    # 60k-800k band posts on a US clock -- @thdxr 30% awake-overlap, @championswimmer 14% --
    # while the 12k-60k band is full of on-pillar accounts at 80-100% overlap with ~0 median
    # replies (@eatonphil 29k/90%, @asmah2107 36k/84%, @johncrickett 13k/80%). At 1,093
    # followers a 20k account is still ~20x amplification AND far likelier to notice a reply.
    # A high floor did not filter for quality, it filtered for the wrong timezone.
    ap.add_argument("--min-followers", type=int, default=12000)
    # A CEILING matters more than the floor. First pass found @jack (9.9M), @satyanadella
    # (7.1M), @aplusk (14M): their tweets take 500+ replies within minutes, so earliness ->
    # 0 and you are reply #2000 — invisible. Reach you cannot get early on is worthless.
    ap.add_argument("--max-followers", type=int, default=800000)
    ap.add_argument("--max-median-replies", type=int, default=80,
                    help="if their posts routinely draw more than this, you can never be early")
    ap.add_argument("--min-overlap", type=float, default=0.5, help="share of posts in your awake window")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--from-graph", action="store_true",
                    help="seed from YOUR OWN following/follower graph (followings.json + "
                         "followers.json) instead of who your anchors reply to. Free -- that "
                         "data is already on disk -- and it is the only seed that can escape "
                         "your anchors' timezone. This is how the 2026-07-15 IST cohort was found.")
    args = ap.parse_args()

    import candidate_source as cs
    key = os.environ["CANDIDATE_API_KEY"]
    here = os.path.dirname(os.path.abspath(__file__))
    d = json.load(open(os.path.join(here, "targets.json")))
    known = {h.lower() for h in (d.get("targets_a") or []) + (d.get("targets_b") or [])}
    now = int(time.time() * 1000)

    # who do your anchors reply TO? those accounts are on-pillar by construction and are
    # a far better pool than topic search (which is crypto-polluted).
    # NOTE: seeding from who your anchors engage with INHERITS THEIR TIMEZONE. If your anchors
    # are US-centric, this pool can only ever return US-centric accounts -- it structurally
    # cannot fix a timezone ceiling. The complementary (and free) source is the user's own
    # following/follower graph: followings.json + followers.json, no API spend. See
    # docs/growth-anchors.md.
    seeds = (d.get("targets_b") or [])[:12]
    pool = collections.Counter()
    for i in range(0, len(seeds), 12):
        q = "(" + " OR ".join(f"from:{h.lower()}" for h in seeds[i:i+12]) + ") filter:replies"
        for t in cs._fetch(q, key, max_pages=2, now=now):
            for tok in (t.get("text") or "").split():
                if tok.startswith("@") and len(tok) > 2:
                    h = tok[1:].strip(".,:!?").lower()
                    # X handles are [A-Za-z0-9_], max 15. isalnum() dropped every handle with
                    # an underscore -- 26% of real handles (measured on the live graph, e.g.
                    # @tom_doerr), silently shrinking the discovery pool by a quarter.
                    if h not in known and _valid_handle(h):
                        pool[h] += 1
    _rej = rejected()
    cands = [h for h, n in pool.most_common(40) if n >= 2 and h not in _rej]
    print(f"  {len(cands)} candidate accounts your anchors engage with")

    if args.from_graph:
        g = graph_candidates(d, args.min_followers, args.max_followers)
        fresh = [h for h in g if h not in cands]
        cands = cands + fresh
        print(f"  + {len(fresh)} from YOUR OWN graph (free, and not bound to your anchors' "
              f"timezone) -> {len(cands)} total")

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
