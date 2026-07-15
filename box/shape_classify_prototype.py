"""Isolate the diagnosis: is shape=post always chosen because the prompt is post-centric?

If a STANDALONE classifier (no drafts[], no voice rules, no '280 chars' anywhere) picks
thread/longform correctly, the framing was the bug and the fix is a separate call.
"""
import os, sys, json, urllib.request

MODEL = sys.argv[1] if len(sys.argv) > 1 else "deepseek/deepseek-chat"
KEY = os.environ["OPENROUTER_API_KEY"]

def classify(title):
    p = ("Classify how this idea should be published on X. Nothing else.\n"
         f"<idea>{title}</idea>\n"
         "STEP 1. EXTRACT the beats ALREADY PRESENT in the idea text. A beat is a distinct "
         "claim the idea ACTUALLY MAKES. Quote the words from the idea for each one.\n"
         "  You may NOT invent, extrapolate or elaborate a beat. If a beat is not literally "
         "in the idea text, it does not exist. 'GitHub is down again' contains exactly ONE "
         "beat, not three: turning it into three would be padding, which is forbidden.\n"
         "STEP 2. Pick the shape from what you extracted:\n"
         "  3+ extracted beats, each standing alone -> thread\n"
         "  1-2 beats but the idea states a MECHANISM or CAUSAL argument that breaks if "
         "split -> longform\n"
         "  otherwise -> post\n"
         'Return JSON {"beats": [each beat quoted from the idea], "invented_any": bool, '
         '"shape": "post"|"thread"|"longform"}')
    body = {"model": MODEL, "response_format": {"type": "json_object"}, "max_tokens": 400,
            "messages": [{"role": "user", "content": p}]}
    r = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    d = json.loads(json.loads(urllib.request.urlopen(r, timeout=60).read())["choices"][0]["message"]["content"])
    return d.get("shape"), d.get("beats", [])

tests = [
    ("want thread  ", "Three ways a self-hosted memory engine silently breaks: cosine vs BM25 score "
                      "scales, list endpoints returning empty content, and missing idempotency keys on ingest."),
    ("want longform", "Why a high follower floor when picking anchors is actually a timezone filter in "
                      "disguise, and how that one bad default silently caps a small account's growth."),
    ("want post    ", "GitHub is down again."),
]
print("MODEL:", MODEL)
for label, t in tests:
    try:
        shape, beats = classify(t)
        print(f"  {label} -> {str(shape):9s} beats={len(beats)}  {[str(b)[:28] for b in beats][:3]}")
    except Exception as e:
        print(f"  {label} -> ERR {str(e)[:60]}")
