#!/usr/bin/env python3
"""Measure how your posted replies performed -> feeds rank-tune. Reads posted suggestions with a
posted_url, looks up the reply's live metrics via the local adapter, POSTs /api/box/outcome.
Run daily. Env: INGEST_URL, INGEST_TOKEN (+ local candidate_source for the metrics lookup)."""
import os, json, re, time, urllib.request

def _req(url, method="GET", token=None, body=None):
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method)
    r.add_header("user-agent", "chorus-box/1.0")
    r.add_header("content-type", "application/json")
    if token: r.add_header("authorization", "Bearer " + token)
    with urllib.request.urlopen(r, timeout=20) as resp: return json.loads(resp.read() or "{}")

def _norm(t):
    import re
    t = re.sub(r"@\w+", " ", (t or "").lower())        # strip the @mentions X prepends
    t = re.sub(r"https?://\S+", " ", t)
    return set(w for w in re.findall(r"[a-z0-9']+", t) if len(w) > 3)


def discover_posted(handle, key, *, now=None, pages=1):
    """Find EVERYTHING you posted on X and match it to the suggestions it came from.

    posted_url was optional in the UI and you skipped it on 10/10 — correctly, it is friction.
    Without it outcome_track could measure nothing, so rank_tune's engagement signal was
    permanently empty. Your tweets are public: fetch them and match by token overlap against
    the draft we suggested. No pasting, no extra step.

    `filter:replies` used to be hardcoded here, so this discovered ONLY replies. Measured:
    of 10 posted suggestions, 3 were replies and 7 were posts/quotes — structurally invisible
    to a reply search. The reward signal was 70% blind by construction, and rank_tune fell
    back to follower attribution at n=2. Two queries now: replies AND originals.
    """
    import candidate_source as cs
    out, seen = [], set()
    for q in (f"from:{handle} filter:replies",      # replies to anchors
              f"from:{handle} -filter:replies"):    # your own posts AND quote-tweets
        try:
            for t in cs._fetch(q, key, max_pages=pages, now=now):
                tid = t.get("id")
                if tid and tid not in seen:
                    seen.add(tid)
                    out.append(t)
        except Exception as e:
            print(f"  discover ({q.split()[-1]}) failed: {repr(e)[:40]}")
    return out


def match(reply_text, drafts, *, min_overlap=0.45):
    """Is this reply one of our drafts? Jaccard over content words — the user edits lightly,
    so exact match is too strict and substring is too loose."""
    a = _norm(reply_text)
    best, score = None, 0.0
    for d in drafts or []:
        b = _norm(d)
        if not a or not b:
            continue
        j = len(a & b) / max(1, len(a | b))
        if j > score:
            best, score = d, j
    return (best, round(score, 3)) if score >= min_overlap else (None, round(score, 3))


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
        try:
            _req(f"{base}/api/box/outcome", "POST", tok,
                 {"suggestion_id": p["id"], "likes": mx["likes"], "replies": mx["replies"], "profile_clicks": 0})
            n += 1
        except Exception:
            # tweet_metrics above is guarded; this POST was NOT. One 500 on the first pending
            # row raised out of main() and skipped the FALLBACK below -- the token-overlap path
            # that actually fires (posted_url is skipped on 8/8 real posts). A single bad row
            # must never kill the measurement that feeds rank_tune's reward.
            continue
    print(f"measured {n} via posted_url")

    # FALLBACK — the path that actually fires. posted_url is optional in the UI and was
    # skipped on 8/8 real posts (it is friction), so the URL path measured NOTHING and
    # rank_tune's engagement signal was permanently empty. Your replies are public: fetch
    # them and match by token overlap against the draft we suggested. Zero extra steps.
    key = os.environ.get("CANDIDATE_API_KEY", "")
    handle = os.environ.get("CHORUS_HANDLE", "")
    if not (key and handle):
        return
    now = int(time.time() * 1000)
    try:
        mine = discover_posted(handle, key, now=now)
    except Exception as e:
        print(f"  discovery failed: {repr(e)[:44]}"); return
    fb = _req(f"{base}/api/box/feedback?since=0", token=tok).get("feedback", [])
    posted = [f for f in fb if (f.get("action") or "").startswith("posted") and f.get("posted_text")]
    seen, d, failed = 0, 0, []
    for t in mine:
        for f in posted:
            best, sc = match(t.get("text") or "", [f["posted_text"]])
            if not best:
                continue
            # NOT `or f.get("id")`: f.id is the FEEDBACK row's autoincrement, and falling back
            # to it wrote orphan outcome rows keyed "15.0"/"13.0" that join to no suggestion.
            # Outcome measurement silently produced nothing for the life of this file. If the
            # endpoint stops sending suggestion_id, that is a bug to see, not to paper over.
            sid = f.get("suggestion_id")
            if not sid:
                print("  outcome: feedback row has no suggestion_id — skipping (endpoint bug)")
                continue
            try:
                _req(f"{base}/api/box/outcome", "POST", tok,
                     {"suggestion_id": sid,
                      "likes": t.get("like_count") or 0,
                      "replies": t.get("reply_count") or 0,
                      "profile_clicks": 0})
                d += 1
            except Exception as e:
                # A persistent failure here looks EXACTLY like "nothing matched" — which is
                # how this file reported success while writing orphan rows for its whole life.
                failed.append(repr(e)[:40])
            break
        seen += 1
    print(f"discovered {len(mine)} of your tweets (replies + originals), matched+measured {d} (no URL needed)")
    if failed:
        print(f"  WARN {len(failed)} outcome write(s) FAILED ({failed[0]}) - measurement is incomplete, not empty")

if __name__ == "__main__":
    main()
