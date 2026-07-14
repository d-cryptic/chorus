#!/usr/bin/env python3
"""Cross-platform enrichment — pull structured signals (GitHub / HN / Reddit) for a topic or
person and store to Supermemory. Complements research.py (web search). All public/official APIs.
Env: GITHUB_TOKEN (optional), SUPERMEMORY_BASE_URL, SUPERMEMORY_API_KEY (optional)."""
import os, json, time, argparse, urllib.request, urllib.parse

def _get(url, headers=None, timeout=20):
    r = urllib.request.Request(url)
    for k, v in (headers or {}).items(): r.add_header(k, v)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read() or "{}")

def github(q, n=5):
    h = {"accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"): h["authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    d = _get(f"https://api.github.com/search/repositories?q={urllib.parse.quote(q)}&sort=stars&per_page={n}", h)
    return [{"src": "github", "title": r["full_name"], "url": r["html_url"],
             "content": (r.get("description") or "") + f" (★{r.get('stargazers_count', 0)})"} for r in d.get("items", [])]

def hn(q, n=5):
    d = _get(f"https://hn.algolia.com/api/v1/search?query={urllib.parse.quote(q)}&tags=story&hitsPerPage={n}")
    return [{"src": "hn", "title": h.get("title") or "",
             "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
             "content": f"{h.get('points', 0)} pts, {h.get('num_comments', 0)} comments"} for h in d.get("hits", [])]

def reddit(q, n=5):
    try:
        d = _get(f"https://www.reddit.com/search.json?q={urllib.parse.quote(q)}&sort=top&limit={n}", {"user-agent": "chorus/1.0"})
        return [{"src": "reddit", "title": c["data"].get("title", ""),
                 "url": "https://reddit.com" + c["data"].get("permalink", ""),
                 "content": f"r/{c['data'].get('subreddit')} · {c['data'].get('ups', 0)} ups"} for c in d.get("data", {}).get("children", [])]
    except Exception:
        return []

def store(items, tag):
    base = os.environ.get("SUPERMEMORY_BASE_URL", "http://localhost:8000").rstrip("/")
    key = os.environ.get("SUPERMEMORY_API_KEY", "")
    url = os.environ.get("SUPERMEMORY_ADD_URL", f"{base}/v3/documents")
    for it in items:
        payload = {"content": f"[{it['src']}] {it['title']} — {it['content']} ({it['url']})",
                   "containerTags": [tag], "metadata": {"kind": "enrichment", "src": it["src"], "ts": int(time.time() * 1000)}}
        r = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
        r.add_header("content-type", "application/json")
        if key: r.add_header("authorization", "Bearer " + key)
        try: urllib.request.urlopen(r, timeout=15)
        except Exception: pass

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query"); ap.add_argument("--tag", default="chorus:research"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    items = github(a.query) + hn(a.query) + reddit(a.query)
    print(f"enriched {len(items)} items for '{a.query}'")
    for it in items: print(f"  [{it['src']}] {it['title'][:60]}")
    if not a.dry_run:
        store(items, a.tag); print(f"stored to {a.tag}")

if __name__ == "__main__":
    main()
