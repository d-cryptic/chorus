#!/usr/bin/env python3
"""Daily Telegram digest + heartbeat (FE6/G5). Top queued suggestions + spend + cycle health.
A silent empty queue is the default failure mode; this is the actual UI on most days.

Env: INGEST_URL, INGEST_TOKEN, NOTIFY_PROVIDER (telegram|whatsapp|console) + provider vars.
"""
import os, sys, json, time, argparse, urllib.request
import notify

def _req(url, method="GET", token=None, body=None, timeout=20):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("user-agent", "chorus-box/1.0")
    r.add_header("content-type", "application/json")
    if token: r.add_header("authorization", f"Bearer {token}")
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read() or "{}")

def format_digest(d, now_ms):
    top = d.get("top", []); spend = d.get("spend", {}); run = d.get("lastRun")
    lines = []
    if run and run.get("started_at"):
        hrs = round((now_ms - run["started_at"]) / 3600_000, 1)
        health = f"last cycle {hrs}h ago · {run.get('suggested', 0)} suggested"
        if run.get("error"): health = f"⚠️ last cycle ERRORED {hrs}h ago: {run['error'][:80]}"
    else:
        health = "⚠️ no cycle has run — is the daily job alive?"
    if not top:
        lines.append("☀️ Chorus — nothing queued today.")
    else:
        lines.append(f"☀️ Chorus — {len(top)} to review:")
        for s in top:
            lines.append(f"• [{round(s.get('score', 0), 2)}] @{s.get('author_handle')} — {(s.get('tweet_text') or '')[:60]}")
    lines.append(f"spend ${spend.get('total', 0):.2f} · {health}")
    return "\n".join(lines)

def run(args):
    base = os.environ.get("INGEST_URL", "http://localhost:8787").rstrip("/")
    token = os.environ.get("INGEST_TOKEN", "")
    d = _req(f"{base}/api/box/digest", token=token)
    msg = format_digest(d, int(time.time() * 1000))
    if args.dry_run:
        print(msg); return
    notify.send(msg)          # NOTIFY_PROVIDER = telegram | whatsapp | console
    print("digest sent via", os.environ.get("NOTIFY_PROVIDER", "console"))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    run(ap.parse_args())
