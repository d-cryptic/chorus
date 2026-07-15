#!/usr/bin/env python3
"""GEO agent -- Generative Engine Optimization. Measures whether the answer-engines mention YOU
when someone asks about your niche, and surfaces the gaps.

The competitive teardown (Okara) flagged this: visibility inside ChatGPT/Claude/Perplexity/Grok
is a growth surface no X tool measures. Chorus already has the LLM plumbing (Hermes -> grok,
which is web-aware), so this is nearly free to run.

For each pillar it asks a web-aware model "who are the notable voices on <pillar>?" and checks
whether CHORUS_HANDLE / CHORUS_NAME appears. GEO score = fraction of pillars where you surface.
Stores a `geo_visibility` insight and names the pillars you are invisible in, so the drafter can
be pointed at them. Weekly cron. Best-effort: a query failure never crashes the run.

Env: CHORUS_HANDLE, CHORUS_PILLARS (csv), CHORUS_NAME (optional), INGEST_URL, INGEST_TOKEN,
     CHORUS_DRAFT_PROVIDER (routes the query to grok, subscription -> $0).
"""
from __future__ import annotations
import os, json, argparse
from ranker import _req, _alert


def _ask(pillar, provider):
    """Ask a web-aware model who the notable voices on a pillar are. Returns the answer text."""
    import hermes_backend as H
    prompt = (
        f"On X (Twitter), who are the notable people and accounts worth following about "
        f"\"{pillar}\"? List 10-15 handles (with @) and names, most influential first. "
        f"Answer with the list only."
    )
    body = {"model": "grok-4.5", "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}]}
    out = H.route(body, provider)
    return (out["choices"][0]["message"]["content"] or "").lower()


def run(args):
    handle = (os.environ.get("CHORUS_HANDLE") or "").lstrip("@").lower()
    name = (os.environ.get("CHORUS_NAME") or "").lower()
    pillars = [p.strip() for p in (os.environ.get("CHORUS_PILLARS") or "").split(",") if p.strip()]
    base = os.environ.get("INGEST_URL", "http://localhost:8787").rstrip("/")
    token = os.environ.get("INGEST_TOKEN", "")
    provider = os.environ.get("CHORUS_GEO_PROVIDER") or os.environ.get("CHORUS_DRAFT_PROVIDER") \
        or "hermes:xai-oauth:grok-4.5"
    if not handle or not pillars:
        print("  GEO: need CHORUS_HANDLE + CHORUS_PILLARS"); return

    cited, gaps = 0, []
    for pillar in pillars:
        try:
            ans = _ask(pillar, provider)
        except Exception as e:
            print(f"  geo query failed for {pillar!r} ({repr(e)[:40]}) - skipping"); continue
        hit = (handle and handle in ans) or (name and len(name) > 3 and name in ans)
        if hit:
            cited += 1
            print(f"  ✓ cited on '{pillar}'")
        else:
            gaps.append(pillar)
            print(f"  ✗ invisible on '{pillar}'")

    checked = cited + len(gaps)
    if not checked:
        print("  GEO: no pillars answered"); return
    score = round(cited / checked, 3)
    print(f"  GEO score: {score} ({cited}/{checked} pillars cite you). gaps: {gaps}")

    if args.dry_run:
        return
    # Store as an insight so the dashboard shows it and the drafter can target the gaps.
    payload = {"claim": f"cited on {cited}/{checked} niche topics in AI answers",
               "score": score, "cited_pillars": [p for p in pillars if p not in gaps],
               "gap_pillars": gaps}
    try:
        _req(f"{base}/api/box/insights", "POST", token,
             {"insights": [{"id": "geo:visibility", "kind": "geo_visibility", "scope": "user",
                            "subject_id": "self", "payload": payload,
                            "confidence": score, "evidence": [f"answer-engine sweep, {checked} pillars"]}]})
        print(f"  stored geo_visibility insight (score {score})")
    except Exception as e:
        _alert(f"geo: insight store failed ({repr(e)[:40]})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="GEO: are you cited in AI answers about your niche?")
    ap.add_argument("--dry-run", action="store_true")
    run(ap.parse_args())
