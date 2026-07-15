#!/usr/bin/env python3
"""Swappable research/search layer. Provider chosen by RESEARCH_PROVIDER (linkup | firecrawl).
Normalized output: [{title, url, content}]. Used by research-digest (+ optional enrichment).
Swap providers by env only — no code change. Env: RESEARCH_PROVIDER, LINKUP_API_KEY, FIRECRAWL_API_KEY.
"""
import os, sys, json, argparse, urllib.request

def _post(url, key, body, timeout=30):
    r = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    r.add_header("user-agent", "chorus-box/1.0")
    r.add_header("content-type", "application/json")
    if key:
        r.add_header("authorization", f"Bearer {key}")
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read() or "{}")

def normalize(title, url, content):
    return {"title": title or "", "url": url or "", "content": content or ""}

# --- pure response mappers (unit-testable, no network) ---
def parse_linkup(d):
    return [normalize(r.get("name"), r.get("url"), r.get("content"))
            for r in d.get("results", []) if r.get("type", "text") == "text"]

def parse_firecrawl(d):
    return [normalize(r.get("title"), r.get("url"), r.get("description") or r.get("markdown"))
            for r in d.get("data", [])]

# --- providers (one interface: .search) ---
class LinkupProvider:
    URL = "https://api.linkup.so/v1/search"
    def __init__(self, key): self.key = key
    def search(self, query, *, depth="standard", max_results=10):
        d = _post(self.URL, self.key, {"q": query, "depth": depth,
                                       "outputType": "searchResults", "maxResults": max_results})
        return parse_linkup(d)

class FirecrawlProvider:
    URL = "https://api.firecrawl.dev/v1/search"
    def __init__(self, key): self.key = key
    def search(self, query, *, depth="standard", max_results=10):
        d = _post(self.URL, self.key, {"query": query, "limit": max_results})
        return parse_firecrawl(d)

PROVIDERS = {"linkup": (LinkupProvider, "LINKUP_API_KEY"),
             "firecrawl": (FirecrawlProvider, "FIRECRAWL_API_KEY")}

def get_provider(name=None):
    name = (name or os.environ.get("RESEARCH_PROVIDER", "linkup")).lower()
    if name not in PROVIDERS:
        raise SystemExit(f"unknown RESEARCH_PROVIDER '{name}' — one of {list(PROVIDERS)}")
    cls, envkey = PROVIDERS[name]
    return cls(os.environ.get(envkey, ""))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--depth", default="standard")
    ap.add_argument("--max", type=int, default=5)
    ap.add_argument("--provider")
    a = ap.parse_args()
    for r in get_provider(a.provider).search(a.query, depth=a.depth, max_results=a.max):
        print(f"- {r['title']}\n  {r['url']}\n  {r['content'][:120]}")
