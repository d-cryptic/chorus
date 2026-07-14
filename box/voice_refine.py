#!/usr/bin/env python3
"""Refine chorus:self voice from your ACTUAL posted replies (ground truth). Reads recent
posted/posted_edited feedback, LLM-synthesizes an updated voice model, stores to Supermemory.
Run weekly. Env: INGEST_URL, INGEST_TOKEN, OPENROUTER_API_KEY, SUPERMEMORY_BASE_URL."""
import os, json, time, urllib.request

def _req(url, method="GET", token=None, body=None, t=25):
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method)
    r.add_header("content-type", "application/json")
    if token: r.add_header("authorization", "Bearer " + token)
    with urllib.request.urlopen(r, timeout=t) as resp: return json.loads(resp.read() or "{}")

def main():
    base = os.environ.get("INGEST_URL", "http://localhost:8787").rstrip("/"); tok = os.environ.get("INGEST_TOKEN", "")
    fb = _req(f"{base}/api/box/feedback?since=0", token=tok).get("feedback", [])
    posted = [f["final_text"] for f in fb if f.get("action", "").startswith("posted") and f.get("final_text")]
    if len(posted) < 5:
        print(f"only {len(posted)} posted replies — need >=5 to refine voice"); return
    or_key = os.environ.get("OPENROUTER_API_KEY", ""); model = os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    sample = "\n".join(f"- {t}" for t in posted[:60])
    prof = {"voice": f"(from {len(posted)} posted replies)", "dos": [], "donts": []}
    if or_key:
        out = _req("https://openrouter.ai/api/v1/chat/completions", "POST", or_key,
                   {"model": model, "response_format": {"type": "json_object"}, "max_tokens": 500,
                    "messages": [{"role": "user", "content": f"These are one person's actual X replies:\n{sample}\n\nReturn JSON {{\"voice\": one-paragraph style, \"dos\":[..], \"donts\":[..]}}."}]})
        try: prof = json.loads(out["choices"][0]["message"]["content"])
        except Exception: pass
    sbase = os.environ.get("SUPERMEMORY_BASE_URL", "http://localhost:8000").rstrip("/")
    skey = os.environ.get("SUPERMEMORY_API_KEY", "")
    payload = {"content": f"voice (refined from posted replies): {prof.get('voice')}\ndos: {prof.get('dos')}\ndonts: {prof.get('donts')}",
               "containerTags": ["chorus:self"], "metadata": {"kind": "voice_model", "refined": True, "ts": int(time.time()*1000)}}
    try:
        _req(os.environ.get("SUPERMEMORY_ADD_URL", f"{sbase}/v3/documents"), "POST", skey or None, payload)
        print(f"refined voice from {len(posted)} replies -> chorus:self")
    except Exception as e:
        print("stored locally only (supermemory unreachable):", repr(e)[:50])

if __name__ == "__main__":
    main()
