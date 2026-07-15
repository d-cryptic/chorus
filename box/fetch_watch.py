#!/usr/bin/env python3
"""Poll the dashboard's Fetch flag and run a cycle on demand.

The Worker has no provider key (and must not — it is internet-facing), so it cannot
fetch tweets itself. The dashboard's Fetch button raises settings.fetch_now; this runs
every 1m, claims the flag atomically (claim clears it), and runs one real cycle.
5m was the old cadence and it made the dashboard feel broken: you click Fetch, nothing
visibly happens for up to five minutes, so you click again. The claim is a single cheap
GET, so the cadence was never a cost decision.
"""
import os, subprocess, sys, urllib.request, json

base = os.environ.get("INGEST_URL", "").rstrip("/")
token = os.environ.get("INGEST_TOKEN", "")
r = urllib.request.Request(f"{base}/api/box/fetch-claim", data=b"{}", method="POST")
r.add_header("authorization", f"Bearer {token}")
r.add_header("content-type", "application/json")
r.add_header("user-agent", "chorus-box/1.0")
try:
    with urllib.request.urlopen(r, timeout=15) as resp:
        claimed = json.loads(resp.read() or "{}").get("requested")
except Exception as e:
    print("fetch-claim failed:", repr(e)[:60]); sys.exit(0)

if not claimed:
    sys.exit(0)
print("fetch requested from dashboard -> running a cycle")
here = os.path.dirname(os.path.abspath(__file__))
sys.exit(subprocess.call(["python3", os.path.join(here, "ranker.py"), "--pages", "1", "--cap", "10"]))
