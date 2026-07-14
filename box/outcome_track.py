#!/usr/bin/env python3
"""Measure how your posted replies performed -> feeds rank-tune. Reads posted suggestions with a
posted_url, looks up the reply's live metrics via the local adapter, POSTs /api/box/outcome.
Run daily. Env: INGEST_URL, INGEST_TOKEN (+ local candidate_source for the metrics lookup)."""
import os, json, re, urllib.request

def _req(url, method="GET", token=None, body=None):
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method)
    r.add_header("user-agent", "chorus-box/1.0")
    r.add_header("content-type", "application/json")
    if token: r.add_header("authorization", "Bearer " + token)
    with urllib.request.urlopen(r, timeout=20) as resp: return json.loads(resp.read() or "{}")

def main():
    base = os.environ.get("INGEST_URL", "http://localhost:8787").rstrip("/"); tok = os.environ.get("INGEST_TOKEN", "")
    try:
        import candidate_source  # local/private adapter (git-ignored)
    except ImportError:
        print("no local candidate_source adapter — cannot measure"); return
    pending = _req(f"{base}/api/box/pending-outcomes", token=tok).get("pending", [])
    n = 0
    for p in pending:
        m = re.search(r"/status/(\d+)", p.get("posted_url", "") or "")
        if not m: continue
        try:
            mx = candidate_source.tweet_metrics(m.group(1))
        except Exception:
            continue
        _req(f"{base}/api/box/outcome", "POST", tok,
             {"suggestion_id": p["id"], "likes": mx["likes"], "replies": mx["replies"], "profile_clicks": 0})
        n += 1
    print(f"measured {n} posted replies")

if __name__ == "__main__":
    main()
