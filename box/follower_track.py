#!/usr/bin/env python3
"""Chorus follower tracker — measure the ONLY metric that matters.

outcome_track measures likes/replies on your replies. Those are proxies. The goal is
followers, and nothing measured it — so nothing could optimise for it.

This snapshots your follower count every hour and attributes deltas to the replies you
posted in that window. Over weeks that answers the question the whole product exists to
answer: WHICH replies actually bought followers? Then rank-tune can chase that instead of
chasing likes.

Honest about attribution: with one account and no control group this is correlational,
not causal. A spike right after a reply to a 500k account is evidence, not proof. It is
still infinitely better than optimising likes, which correlate with followers only loosely.
"""
from __future__ import annotations
import os, time, json, argparse
from ranker import _req


def my_followers():
    """Your live follower count, via the read adapter.

    The provider call lives in candidate_source (git-ignored, box-only) ON PURPOSE: this repo
    is PUBLIC and the standing instruction is to keep the read-provider integration out of it.
    This file owns the LOGIC (snapshot, attribution); the adapter owns the vendor.
    """
    import candidate_source as cs
    handle = os.environ.get("CHORUS_HANDLE", "barundebnath")
    return cs.user_followers(handle)


def main():
    ap = argparse.ArgumentParser(description="Snapshot followers + attribute growth")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    base = os.environ.get("INGEST_URL", "http://localhost:8787").rstrip("/")
    token = os.environ.get("INGEST_TOKEN", "")

    n = my_followers()
    if n is None:
        print("no follower count — skipping"); return
    now = int(time.time() * 1000)
    print(f"followers: {n:,}")
    if args.dry_run:
        return

    try:
        _req(f"{base}/api/box/followers", "POST", token, {"count": n, "ts": now})
    except Exception as e:
        print(f"  snapshot POST failed: {repr(e)[:50]}"); return

    # attribute the delta since the previous snapshot to replies posted in that window
    try:
        d = _req(f"{base}/api/box/followers", token=token)
        hist = d.get("history") or []
        if len(hist) >= 2:
            prev, cur = hist[1], hist[0]
            delta = cur["count"] - prev["count"]
            acted = d.get("acted_between") or 0
            per = round(delta / acted, 2) if acted else 0
            arrow = "+" if delta >= 0 else ""
            print(f"  {arrow}{delta} followers since last snapshot "
                  f"({acted} replies posted in window -> {per}/reply)")
            if delta >= 10:
                from ranker import _alert
                _alert(f"📈 +{delta} followers in the last window ({acted} replies posted)")
    except Exception as e:
        print(f"  attribution read failed: {repr(e)[:40]}")


if __name__ == "__main__":
    main()
