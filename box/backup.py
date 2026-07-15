#!/usr/bin/env python3
"""Back up the box-only state that exists NOWHERE else, and restore it.

Summary: targets.json and rejected_anchors.txt are git-ignored on purpose (they name real
people and carry the read-provider's handle list), so they live on ONE Hetzner VM. That is
216 curated handles and 15 human judgements — hours of work, one disk failure from gone.

The previous version of this file backed up D1 and was never scheduled. D1 is Cloudflare-
hosted and already durable: it protected the SAFE thing, ignored the FRAGILE one, and did
neither because no cron ran it.

Supermemory is deliberately not backed up: it is derivable from D1 (chorus:posts comes from
feedback) plus a style_mine run, and 6MB of re-derivable embeddings is not worth the row.
This is 5KB of pure judgement.

Env: INGEST_URL, INGEST_TOKEN.  Usage: backup.py [--restore] [--dry-run]
"""
from __future__ import annotations
import os
import argparse

from ranker import _req, _alert

FILES = ("targets.json", "rejected_anchors.txt")
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description="Back up / restore box-only state")
    ap.add_argument("--restore", action="store_true",
                    help="pull state FROM D1 onto this box (for a rebuilt box)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    base = os.environ.get("INGEST_URL", "").rstrip("/")
    tok = os.environ.get("INGEST_TOKEN", "")
    if not base or not tok:
        print("INGEST_URL/INGEST_TOKEN unset — cannot reach the store"); return

    if args.restore:
        state = (_req(f"{base}/api/box/state", token=tok) or {}).get("state", [])
        if not state:
            print("nothing backed up yet — refusing to touch local files"); return
        for row in state:
            path = os.path.join(HERE, row["k"])
            if args.dry_run:
                print(f"  would restore {row['k']} ({len(row['body'])} bytes)"); continue
            # never clobber a LARGER local file with a smaller backup without saying so:
            # a half-written backup silently truncating a curated list is the failure mode
            # this whole file exists to prevent.
            if os.path.exists(path) and os.path.getsize(path) > len(row["body"]):
                print(f"  SKIP {row['k']}: local ({os.path.getsize(path)}b) is BIGGER than the "
                      f"backup ({len(row['body'])}b). Restore by hand if that is really wanted.")
                continue
            open(path, "w").write(row["body"])
            print(f"  restored {row['k']} ({len(row['body'])} bytes)")
        return

    sent = 0
    for name in FILES:
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            continue
        body = open(path).read()
        if not body.strip():
            print(f"  SKIP {name}: empty — backing up an empty file over a good one is how "
                  f"a backup destroys the thing it protects")
            continue
        if args.dry_run:
            print(f"  would back up {name} ({len(body)} bytes)"); continue
        try:
            _req(f"{base}/api/box/state", "POST", tok, {"k": name, "body": body})
            sent += 1
            print(f"  backed up {name} ({len(body)} bytes)")
        except Exception as e:
            # LOUD: a silent backup failure is indistinguishable from a backup, right up
            # until the day you need it.
            _alert(f"Chorus backup FAILED for {name}: {repr(e)[:60]}")
            print(f"  FAILED {name}: {repr(e)[:60]}")
    print(f"backed up {sent}/{len(FILES)} box-only file(s)")


if __name__ == "__main__":
    main()
