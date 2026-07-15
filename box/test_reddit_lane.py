#!/usr/bin/env python3
"""Reddit lane: suggest-only. Filters stickied/old/oversaturated threads, drafts a comment,
queues with target='reddit' and the permalink. Verifies filtering + the suggest-only payload."""
import os, sys, time
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reddit_lane as RL


def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    now = int(time.time())
    # a stickied, an oversaturated, an old, and one GOOD thread
    fake = {"data": {"children": [
        {"data": {"id": "a", "title": "stickied", "stickied": True, "created_utc": now, "num_comments": 1, "permalink": "/x"}},
        {"data": {"id": "b", "title": "oversaturated", "created_utc": now, "num_comments": 9999, "permalink": "/y"}},
        {"data": {"id": "c", "title": "old", "created_utc": now - 999999, "num_comments": 1, "permalink": "/z"}},
        {"data": {"id": "d", "title": "good local llm question", "selftext": "how do I run 27B on a phone", "created_utc": now - 3600, "num_comments": 5, "permalink": "/r/LocalLLaMA/good"}},
    ]}}
    with mock.patch.object(RL, "_oauth_token", lambda: None), \
         mock.patch.object(RL, "urllib") as _u:
        _u.request.Request = lambda *a, **k: None
        class Resp:
            def read(self_): import json; return json.dumps(fake).encode()
            def __enter__(self_): return self_
            def __exit__(self_, *a): return False
        _u.request.urlopen = lambda *a, **k: Resp()
        threads = RL.fetch_threads(["LocalLLaMA"], now)
    ids = [t["id"] for t in threads]
    chk(ids == ["d"], f"only the good thread survives filtering (got {ids})")

    # the ingest payload is suggest-only with target=reddit + permalink
    ingested = {}
    with mock.patch.object(RL, "get_voice", lambda x: "concise"), \
         mock.patch.object(RL, "niche_context", lambda: ""), \
         mock.patch.object(RL, "fetch_threads", lambda subs, now: [threads[0]] if threads else []), \
         mock.patch.object(RL, "draft_comment", lambda t, v, n, p: ("a genuinely useful reddit comment about running models locally", 0.8)), \
         mock.patch.object(RL, "ingest", lambda base, tok, payload: ingested.update(payload)), \
         mock.patch.dict(os.environ, {"CHORUS_REDDIT_SUBS": "LocalLLaMA", "INGEST_URL": "http://x", "INGEST_TOKEN": "t"}, clear=False):
        class A: dry_run = False
        RL.run(A())
    chk(ingested.get("target") == "reddit", "ingested with target=reddit")
    chk(ingested.get("tweet_url", "").endswith("/good"), "carries the thread permalink")
    chk(ingested.get("author_handle") == "r/LocalLLaMA", "author = subreddit")
    chk(ingested.get("drafts") and "reddit comment" in ingested.get("drafts", [""])[0], "carries the drafted comment")

    print(f"REDDIT LANE UNIT: {p} passed, {f} failed")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(run())
