#!/usr/bin/env python3
"""Optional embedding-based pillar relevance (semantic vs keyword). ONE batched call for all
candidate texts + the pillar centroid, so it's cheap. Enable with EMBED_PILLARS=1.
Env: EMBED_API_KEY (or OPENAI_API_KEY), EMBED_URL, EMBED_MODEL (text-embedding-3-small)."""
import os, json, math, urllib.request

def embed(texts):
    key = os.environ.get("EMBED_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    url = os.environ.get("EMBED_URL", "https://api.openai.com/v1/embeddings")
    model = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
    r = urllib.request.Request(url, data=json.dumps({"model": model, "input": texts}).encode(), method="POST")
    r.add_header("content-type", "application/json"); r.add_header("authorization", "Bearer " + key)
    d = json.loads(urllib.request.urlopen(r, timeout=30).read())
    return [e["embedding"] for e in d["data"]]

def cos(a, b):
    dot = sum(x * y for x, y in zip(a, b)); na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0

def pillar_relevance(texts, pillars):
    """[0..1] semantic sim of each text to the pillar centroid. One batch call."""
    if not texts or not pillars:
        return [0.0] * len(texts)
    vecs = embed([", ".join(pillars)] + list(texts))
    pv = vecs[0]
    return [max(0.0, min(1.0, (cos(pv, v) + 0.1) / 0.5)) for v in vecs[1:]]
