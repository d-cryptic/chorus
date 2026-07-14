#!/usr/bin/env python3
"""Mirror new feedback rows into Supermemory chorus:self so accept/reject becomes profile.dynamic
(docs/memory.md). Runs as a box cron. M0 path (M1 uses the Convex act mutation's mirrorFeedback).

Env: INGEST_URL, INGEST_TOKEN, SUPERMEMORY_BASE_URL (self-host, default localhost:8000; key optional),
     CHORUS_STATE (last-seen ts file, default box/.mirror_state).
"""
import os, sys, json, time, argparse, urllib.request

def _req(url, method="GET", token=None, body=None, timeout=20):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("user-agent", "chorus-box/1.0")
    r.add_header("content-type", "application/json")
    if token: r.add_header("authorization", f"Bearer {token}")
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read() or "{}")

def to_memory(f):
    """feedback row -> Supermemory add payload for chorus:self."""
    txt = f.get("final_text") or ""
    return {
        "content": f'{f["action"]} reply to @{f.get("author_handle")}: "{txt}" (angle: {f.get("angle") or ""})',
        "containerTags": ["chorus:self"],
        "metadata": {"kind": "feedback", "action": f["action"], "ts": f["ts"]},
    }

def run(args):
    base = os.environ.get("INGEST_URL", "http://localhost:8787").rstrip("/")
    token = os.environ.get("INGEST_TOKEN", "")
    sm_key = os.environ.get("SUPERMEMORY_API_KEY", "")  # empty for local self-host
    sm_base = os.environ.get("SUPERMEMORY_BASE_URL", "http://localhost:8000").rstrip("/")
    sm_url = os.environ.get("SUPERMEMORY_ADD_URL", f"{sm_base}/v3/documents")
    state = os.environ.get("CHORUS_STATE", os.path.join(os.path.dirname(__file__), ".mirror_state"))
    since = 0
    if os.path.exists(state):
        since = int(open(state).read().strip() or 0)

    rows = _req(f"{base}/api/box/feedback?since={since}", token=token).get("feedback", [])
    n = 0
    for f in rows:
        payload = to_memory(f)
        if args.dry_run:
            print("  would mirror:", payload["content"][:70])
        else:
            _req(sm_url, "POST", sm_key or None, payload)  # key optional (self-host)
        n += 1
        since = max(since, f["ts"])
    if not args.dry_run and rows:
        open(state, "w").write(str(since))
    print(f"mirrored {n} feedback rows (since={since})")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    run(ap.parse_args())
