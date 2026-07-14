#!/usr/bin/env python3
"""onboard-self: bootstrap chorus:self (pillars + voice) from your own X history so the ranker
isn't cold-starting. Fetch your recent tweets (local candidate adapter, from:CHORUS_HANDLE) -> LLM synthesize
{pillars, voice, dos, donts} -> POST to Supermemory /v3/documents containerTags ['chorus:self'].

Env: CANDIDATE_API_KEY, OPENROUTER_API_KEY, OPENROUTER_MODEL, SUPERMEMORY_BASE_URL, CHORUS_HANDLE.
"""
import os, sys, json, time, argparse, urllib.request
from ranker import _req  # http helper (candidate fetch = local git-ignored adapter)

SM_BASE = os.environ.get("SUPERMEMORY_BASE_URL", "http://localhost:8000").rstrip("/")
SM_URL = os.environ.get("SUPERMEMORY_ADD_URL", f"{SM_BASE}/v3/documents")

def synthesize(tweets, *, model, api_key):
    """LLM -> {pillars:[...], voice:str, dos:[...], donts:[...]}. Fallback when no key."""
    sample = "\n".join(f"- {t.get('text','')}" for t in tweets[:40])
    if not api_key:
        return {"pillars": [], "voice": f"(un-synthesized; {len(tweets)} tweets sampled)", "dos": [], "donts": []}
    prompt = ("From these tweets by one person, infer their content pillars + writing voice.\n"
              "Describe the voice CONCRETELY and usably: sentence length, capitalisation, "
              "punctuation habits, slang, how they open/close, how technical, whether they "
              "hedge, use of numbers. Quote 2-3 short phrases that are characteristically "
              "theirs. Do NOT write a flattering summary - write what a ghostwriter needs.\n"
              f"{sample}\n\nReturn JSON {{\"pillars\":[3-6 short topics], \"voice\": one-paragraph style, "
              "\"dos\":[..], \"donts\":[..], \"samples\":[3-5 verbatim tweets that best show the voice]}}.")
    out = _req("https://openrouter.ai/api/v1/chat/completions", "POST", api_key,
               {"model": model, "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"}, "max_tokens": 900})
    txt = (out["choices"][0]["message"]["content"] or "").strip()
    if txt.startswith("```"):  # models fence JSON despite response_format
        txt = txt.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        # never crash the onboard on one bad response - degrade to raw samples, which
        # are still the most useful thing we can store for voice priming.
        print("WARN: could not parse voice JSON; storing raw samples only")
        return {"pillars": [], "voice": "(unparsed)", "dos": [], "donts": [],
                "samples": [t.get("text", "") for t in tweets[:5]]}

def sm_add(content, kind, key, *, dry):
    payload = {"content": content, "containerTags": ["chorus:self"],
               "metadata": {"kind": kind, "ts": int(time.time() * 1000)}}
    if dry:
        print(f"  would POST /v3/documents [{kind}]: {content[:70]}")
    else:
        _req(SM_URL, "POST", key or None, payload)  # key optional (self-host)

def run(args):
    handle = os.environ.get("CHORUS_HANDLE", "")
    if not handle:
        raise SystemExit("set CHORUS_HANDLE (your @, no @)")
    tw_key = os.environ.get("CANDIDATE_API_KEY", "")
    sm_key = os.environ.get("SUPERMEMORY_API_KEY", "")
    model = os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    or_key = os.environ.get("OPENROUTER_API_KEY", "")
    now = int(time.time() * 1000)

    if args.input:
        tweets = json.load(open(args.input))
    else:
        try:
            import candidate_source  # local/private adapter (git-ignored)
        except ImportError:
            raise SystemExit("no --input and no local candidate_source.py adapter")
        if not tw_key:
            raise SystemExit("no --input and CANDIDATE_API_KEY unset")
        tweets = candidate_source.fetch(f"from:{handle} -filter:replies", tw_key, max_pages=args.pages, now=now)
    print(f"fetched {len(tweets)} of your tweets")
    prof = synthesize(tweets, model=model, api_key=or_key)
    print("synthesized:", json.dumps(prof)[:200])
    sm_add("pillars: " + ", ".join(prof.get("pillars", [])), "pillars", sm_key, dry=args.dry_run)
    sm_add(f"voice: {prof.get('voice','')}\ndos: {prof.get('dos')}\ndonts: {prof.get('donts')}",
           "voice_model", sm_key, dry=args.dry_run)
    print("onboard-self done" + (" (dry-run)" if args.dry_run else ""))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="your tweets JSON (skip the adapter fetch)")
    ap.add_argument("--pages", type=int, default=2)
    ap.add_argument("--dry-run", action="store_true")
    run(ap.parse_args())
