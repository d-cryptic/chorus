#!/usr/bin/env python3
"""forget-target <handle> — remove a person from Chorus completely: delete their queue rows and
their Supermemory container tag. Makes docs/data-policy's "one command" real.
Env: INGEST_URL, INGEST_TOKEN, SUPERMEMORY_BASE_URL, SUPERMEMORY_API_KEY (optional)."""
import os, sys, json, urllib.request

def _req(url, method="GET", token=None, body=None):
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method)
    r.add_header("content-type", "application/json")
    if token: r.add_header("authorization", "Bearer " + token)
    with urllib.request.urlopen(r, timeout=20) as resp: return json.loads(resp.read() or "{}")

def main():
    if len(sys.argv) < 2:
        sys.exit("usage: forget_target.py <handle>")
    h = sys.argv[1].lstrip("@")
    base = os.environ.get("INGEST_URL", "http://localhost:8787").rstrip("/"); tok = os.environ.get("INGEST_TOKEN", "")
    r = _req(f"{base}/api/box/forget", "POST", tok, {"handle": h})
    print(f"queue rows removed: {r.get('removed')}")
    sbase = os.environ.get("SUPERMEMORY_BASE_URL", "http://localhost:8000").rstrip("/")
    skey = os.environ.get("SUPERMEMORY_API_KEY", "")
    try:
        _req(f"{sbase}/v3/documents?containerTags=chorus:target:{h}", "DELETE", skey or None)
        print(f"supermemory tag chorus:target:{h} deleted")
    except Exception as e:
        print("supermemory delete (best-effort, verify endpoint for your build):", repr(e)[:60])

if __name__ == "__main__":
    main()
