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

def _numeric(fac):
    """Only numeric factors are tunable weights. post_gen writes {"source":"session"} and
    fast_lane writes provenance like {"fast_lane":1,"age_min":11} — a bare float() over
    every factor crashed the whole tuner on the first string. Skip, never crash.
    """
    out = {}
    for k, v in (fac or {}).items():
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            out[k] = float(v)
    return out


def follower_attribution(base, tok):
    """ts -> followers gained per reply posted in that snapshot window.

    follower_track snapshots hourly; feedback rows carry a ts. A reply is credited an equal
    share of the delta over the window it landed in.

    HONEST: one account, no control group, and several replies can share a window — so this
    is correlational, not causal, and noisy at low volume. Still strictly better than
    optimising likes, which are only loosely coupled to follows, and it self-corrects as
    volume grows because noise averages out while a real signal does not.
    """
    try:
        hist = (_req(f"{base}/api/box/followers", token=tok).get("history") or [])  # newest first
    except Exception:
        return lambda ts: None
    if len(hist) < 2:
        return lambda ts: None
    windows = [(prev["ts"], cur["ts"], cur["count"] - prev["count"])
               for cur, prev in zip(hist, hist[1:])]
    try:
        fb = _req(f"{base}/api/box/feedback?since=0", token=tok).get("feedback", [])
    except Exception:
        fb = []
    posted = [x for x in fb if (x.get("action") or "").startswith("posted")]

    def per(ts):
        if not ts:
            return None
        for lo, hi, delta in windows:
            if lo < ts <= hi:
                n = sum(1 for x in posted if lo < (x.get("ts") or 0) <= hi) or 1
                return delta / n
        return None
    return per



def active_days(fb):
    """Days on which the user demonstrably LOOKED (they acted on something).

    Expiry only means "rejected" if they were present to reject it. If they were away for a
    day, everything expires and that is not a preference — treating it as one would teach the
    ranker that whatever it suggested on a busy Tuesday is bad.
    """
    import datetime
    out = set()
    for f in fb:
        if (f.get("action") or "").startswith("posted") or f.get("action") == "dismissed":
            ts = f.get("ts")
            if ts:
                out.add(datetime.date.fromtimestamp(ts / 1000).isoformat())
    return out


def negative_weight(action, present):
    """How much a rejection counts. An explicit Dismiss is a considered no; an expiry is a
    shrug, and only counts at all if the user was around to shrug."""
    if action == "dismissed":
        return 1.0
    if action == "expired":
        return 0.35 if present else 0.0     # 0 => ignored entirely, not counted as evidence
    return 0.0

def main():
    base = os.environ.get("INGEST_URL", "http://localhost:8787").rstrip("/"); tok = os.environ.get("INGEST_TOKEN", "")
    fol_for = follower_attribution(base, tok)
    fb = _req(f"{base}/api/box/feedback?since=0", token=tok).get("feedback", [])
    if len(fb) < 5:
        print(f"only {len(fb)} feedback rows — need >=5 to tune"); return
    pos, neg, nP, nN = {}, {}, 0.0, 0.0
    _active = active_days(fb)
    for f in fb:
        fac = f.get("factors")
        fac = json.loads(fac) if isinstance(fac, str) else (fac or {})
        if not fac: continue
        action = (f.get("action") or "")
        positive = action.startswith("posted")
        if positive:
            # REWARD = FOLLOWERS GAINED, not likes. The goal is followers; likes are a
            # proxy that diverges badly — a viral joke earns 500 likes and 0 follows, a
            # sharp technical take earns 20 likes and 5 follows. Tuning on likes taught
            # the ranker to chase the wrong thing.
            # "posted" means the user CLICKED Post on X. The intent URL only opens X's
            # composer; they still have to hit Post. Measured against their real timeline:
            # only 4 of 10 "posted" suggestions are actually ON X. A click is a genuine
            # preference signal (they liked it enough to open it) but it is weaker than an
            # act, so it must not carry the same vote as a tweet that really shipped.
            # outcome_track sets likes/replies only for suggestions it FOUND on X.
            verified = f.get("likes") is not None
            gained = fol_for(f.get("ts"))
            if gained is not None:
                w = 1.0 + gained * 3.0          # followers dominate when we have the data
            else:                                # no snapshot covers this reply yet
                w = 1.0 + ((f.get("likes") or 0) + 2 * (f.get("replies") or 0)) / 10
            if not verified:
                w *= 0.5                         # an intent, not an act
            nP += w
            for k, v in _numeric(fac).items(): pos[k] = pos.get(k, 0) + v * w
        else:
            import datetime
            day = datetime.date.fromtimestamp((f.get("ts") or 0) / 1000).isoformat() if f.get("ts") else None
            w = negative_weight(action, day in _active)
            if w <= 0:
                continue                     # expired while the user was away: not evidence
            nN += w
            for k, v in _numeric(fac).items(): neg[k] = neg.get(k, 0) + v * w
    if not nP or not nN:
        print(f"need both accepted and rejected feedback "
              f"(have {nP:.1f} accepted, {nN:.1f} rejected; expiries only count on days you "
              f"were active)"); return
    tuned = 0
    for k in set(pos) | set(neg):
        disc = pos.get(k, 0) / nP - neg.get(k, 0) / nN  # >0 => predicts acceptance
        base_w = DEFAULTS.get(k, 0.10)
        nextw = max(0.01, min(0.5, round(base_w + 0.05 * disc, 4)))
        _req(f"{base}/api/box/weights", "POST", tok, {"key": k, "value": nextw}); tuned += 1
    print(f"tuned {tuned} weights from {len(fb)} feedback rows")

if __name__ == "__main__":
    main()
