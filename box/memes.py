#!/usr/bin/env python3
"""Chorus meme lane — DORMANT until a key exists (by your choice: "build it dormant").

Every meme source needs a credential this project does not have:
  GIPHY_API_KEY    free, 30s at developers.giphy.com   -> search reaction GIFs (v0 spec:
                   "Giphy search -> images.original.mp4", SEARCH never generate, and
                   "Powered By GIPHY" attribution is required by their ToS)
  REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET   free, 2min at reddit.com/prefs/apps ("script"
                   app) -> r/ProgrammerHumor etc. NOTE: Reddit now 403s EVERY
                   unauthenticated request (all UAs, both hosts), which is also why
                   enrich.py's reddit lane is silently dead.
  IMGFLIP_USER / IMGFLIP_PASS   free account -> GENERATE a captioned meme image from a
                   template (v0's mediaIntent='meme' lane)

With no key, every function returns [] / None and the caller degrades quietly — the queue
simply carries no meme, rather than a broken image. Nothing here fabricates media.
"""
from __future__ import annotations
import os, time, json, urllib.parse, urllib.request

UA = "chorus/1.0"


def _get(url, headers=None, timeout=10):
    r = urllib.request.Request(url)
    r.add_header("user-agent", UA)
    for k, v in (headers or {}).items():
        r.add_header(k, v)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read() or "{}")


def available() -> dict:
    """What the meme lane can actually do right now. Honest, not aspirational."""
    return {
        "giphy": bool(os.environ.get("GIPHY_API_KEY")),
        "reddit": bool(os.environ.get("REDDIT_CLIENT_ID") and os.environ.get("REDDIT_CLIENT_SECRET")),
        "imgflip": bool(os.environ.get("IMGFLIP_USER") and os.environ.get("IMGFLIP_PASS")),
    }


# ---- giphy: SEARCH a reaction gif (never generate) --------------------------

_GIPHY_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".giphy_calls")
_GIPHY_MAX_PER_HOUR = int(os.environ.get("GIPHY_MAX_PER_HOUR", "100"))
_GIPHY_WARNED = False


def _giphy_ratelimit_ok():
    """True if we are under the 100-calls/hour Giphy cap. Persists a sliding hour window to
    .giphy_calls so a burst right after a box reboot cannot blow the cap. Fail-safe: a file
    error allows the call (a GIF is cosmetic; we never crash a cycle over rate-limit bookkeeping),
    but the common path enforces the limit exactly."""
    global _GIPHY_WARNED
    now = time.time()
    try:
        stamps = json.load(open(_GIPHY_LOG)) if os.path.exists(_GIPHY_LOG) else []
    except Exception:
        stamps = []
    stamps = [t for t in stamps if isinstance(t, (int, float)) and now - t < 3600]
    if len(stamps) >= _GIPHY_MAX_PER_HOUR:
        if not _GIPHY_WARNED:
            print(f"  giphy rate limit hit ({_GIPHY_MAX_PER_HOUR}/hr) - skipping GIFs until the "
                  f"window clears. Drafts still queue, just without a gif.")
            _GIPHY_WARNED = True
        return False
    _GIPHY_WARNED = False
    stamps.append(now)
    try:
        json.dump(stamps, open(_GIPHY_LOG, "w"))
    except Exception:
        pass
    return True


def giphy_search(q, n=3):
    key = os.environ.get("GIPHY_API_KEY")
    if not key or not q:
        return []
    if not _giphy_ratelimit_ok():   # honour the 100/hour cap the account is limited to
        return []
    try:
        d = _get("https://api.giphy.com/v1/gifs/search?"
                 + urllib.parse.urlencode({"api_key": key, "q": q, "limit": n,
                                           "rating": "pg-13", "bundle": "messaging_non_clips"}))
    except Exception:
        return []
    out = []
    for g in d.get("data", []):
        img = (g.get("images") or {}).get("original") or {}
        if img.get("url"):
            out.append({"type": "animated_gif", "url": img.get("url"),
                        "page": g.get("url"), "attribution": "Powered By GIPHY"})
    return out


# ---- reddit: real dev memes (needs a free OAuth app) ------------------------

def _reddit_token():
    cid, sec = os.environ.get("REDDIT_CLIENT_ID"), os.environ.get("REDDIT_CLIENT_SECRET")
    if not (cid and sec):
        return None
    try:
        import base64
        body = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
        r = urllib.request.Request("https://www.reddit.com/api/v1/access_token", data=body, method="POST")
        r.add_header("authorization", "Basic " + base64.b64encode(f"{cid}:{sec}".encode()).decode())
        r.add_header("user-agent", UA)
        with urllib.request.urlopen(r, timeout=10) as resp:
            return json.loads(resp.read()).get("access_token")
    except Exception:
        return None


def reddit_memes(subs=("ProgrammerHumor", "devops"), n=5, min_ups=500):
    tok = _reddit_token()
    if not tok:
        return []
    out = []
    for sub in subs:
        try:
            d = _get(f"https://oauth.reddit.com/r/{sub}/top?t=day&limit=15",
                     {"authorization": f"bearer {tok}"})
        except Exception:
            continue
        for c in d.get("data", {}).get("children", []):
            p = c.get("data", {})
            url = str(p.get("url") or "")
            if p.get("over_18") or (p.get("ups") or 0) < min_ups:
                continue
            if not (p.get("post_hint") == "image" or url.endswith((".jpg", ".png", ".gif"))):
                continue
            out.append({"type": "photo", "url": url,
                        "page": "https://reddit.com" + str(p.get("permalink") or ""),
                        "title": p.get("title"), "signal": f"{p.get('ups')} ups r/{sub}"})
    return sorted(out, key=lambda m: -int(str(m["signal"].split()[0]))) [:n]


# ---- imgflip: GENERATE a captioned meme -------------------------------------

def imgflip_make(template_id, top, bottom=""):
    u, pw = os.environ.get("IMGFLIP_USER"), os.environ.get("IMGFLIP_PASS")
    if not (u and pw):
        return None
    try:
        body = urllib.parse.urlencode({"template_id": template_id, "username": u,
                                       "password": pw, "text0": top, "text1": bottom}).encode()
        r = urllib.request.Request("https://api.imgflip.com/caption_image", data=body, method="POST")
        r.add_header("user-agent", UA)
        with urllib.request.urlopen(r, timeout=12) as resp:
            d = json.loads(resp.read())
        return d["data"]["url"] if d.get("success") else None
    except Exception:
        return None


def for_draft(gif_query):
    """What the ranker calls. Returns media[] for a draft, or [] when dormant."""
    return giphy_search(gif_query, n=1) if gif_query else []


if __name__ == "__main__":
    a = available()
    print("meme lane status:")
    for k, v in a.items():
        print(f"  {k:8s} {'READY' if v else 'dormant — no key'}")
    if not any(a.values()):
        print("\nAll dormant. To wake it up:")
        print("  GIPHY_API_KEY=...            developers.giphy.com (free, 30s)")
        print("  REDDIT_CLIENT_ID/_SECRET=... reddit.com/prefs/apps -> 'script' (free, 2min)")
        print("  IMGFLIP_USER/_PASS=...       imgflip.com account (free)")
