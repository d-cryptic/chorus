#!/usr/bin/env python3
"""Weekly learning loop (M0 — the box twin of convex/rankTune.ts). Aggregates feedback
(posted vs dismissed, FOLLOWER-weighted), nudges ranking weights toward what actually grows
the account, POSTs
/api/box/weights. opportunity-rank/ranker reads them next run. Env: INGEST_URL, INGEST_TOKEN."""
import os, json, urllib.request
DEFAULTS = {"pillar": 0.22, "author": 0.18, "upside": 0.16, "fresh": 0.12,
            "saturation": 0.15, "relationship": 0.10, "angle": 0.24}

def _req(url, method="GET", token=None, body=None):
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method)
    r.add_header("user-agent", "chorus-box/1.0")
    r.add_header("content-type", "application/json")
    if token: r.add_header("authorization", "Bearer " + token)
    with urllib.request.urlopen(r, timeout=25) as resp: return json.loads(resp.read() or "{}")

def main():
    base = os.environ.get("INGEST_URL", "http://localhost:8787").rstrip("/"); tok = os.environ.get("INGEST_TOKEN", "")
    fol_for = follower_attribution(base, tok)
    fb = _req(f"{base}/api/box/feedback?since=0", token=tok).get("feedback", [])
    if len(fb) < 5:
        print(f"only {len(fb)} feedback rows — need >=5 to tune"); return
    pos, neg, nP, nN = {}, {}, 0.0, 0.0
    for f in fb:
        fac = f.get("factors")
        fac = json.loads(fac) if isinstance(fac, str) else (fac or {})
        if not fac: continue
        positive = (f.get("action", "") or "").startswith("posted")
        if positive:
            # REWARD = FOLLOWERS GAINED, not likes. The goal is followers; likes are a
            # proxy that diverges badly — a viral joke earns 500 likes and 0 follows, a
            # sharp technical take earns 20 likes and 5 follows. Tuning on likes taught
            # the ranker to chase the wrong thing.
            gained = fol_for(f.get("ts"))
            if gained is not None:
                w = 1.0 + gained * 3.0          # followers dominate when we have the data
            else:                                # no snapshot covers this reply yet
                w = 1.0 + ((f.get("likes") or 0) + 2 * (f.get("replies") or 0)) / 10
            nP += w
            for k, v in fac.items(): pos[k] = pos.get(k, 0) + float(v) * w
        else:
            nN += 1
            for k, v in fac.items(): neg[k] = neg.get(k, 0) + float(v)
    if not nP or not nN:
        print("need both accepted and dismissed feedback"); return
    tuned = 0
    for k in set(pos) | set(neg):
        disc = pos.get(k, 0) / nP - neg.get(k, 0) / nN  # >0 => predicts acceptance
        base_w = DEFAULTS.get(k, 0.10)
        nextw = max(0.01, min(0.5, round(base_w + 0.05 * disc, 4)))
        _req(f"{base}/api/box/weights", "POST", tok, {"key": k, "value": nextw}); tuned += 1
    print(f"tuned {tuned} weights from {len(fb)} feedback rows")

if __name__ == "__main__":
    main()
