"""Two backends speak /v3/search and they DISAGREE on shape and on score scale.

  upstream Supermemory (self-hosted :6767) -> {"results":[{"chunks":[{"content"}],"score"}]}
                                              no top-level "content"; score = cosine 0..1
  box/memory_service.py (the shim, :8000)  -> {"results":[{"content","score"}]}
                                              score = BM25, unbounded

Every ranker call site is wrapped in `except: pass`, so a mismatch is SILENT: Chorus
just quietly stops using its learned voice and starts repeating itself. That is exactly
the "learned voice never used" bug, twice. These tests are the alarm.

Payloads below were curl'd off the running box, not invented.
"""
import os, ranker as R

UPSTREAM = {"results": [{"chunks": [{"content": "voice: short, punchy sentences, minimal fluff",
                                     "position": 0, "isRelevant": True, "score": 0.615}],
                         "documentId": "abc", "score": 0.615, "metadata": {}, "type": "text"}],
            "timing": 36, "total": 1}
SHIM = {"results": [{"id": "x", "content": "voice: short, punchy sentences, minimal fluff",
                     "containerTags": ["chorus:self"], "metadata": {}, "score": 3.7}],
        "count": 1}


def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    # --- shape: text must survive BOTH backends ---
    up = R._sm_hits(UPSTREAM)
    chk(up[0][0].startswith("voice:"), "upstream: text extracted from chunks[]")
    chk(up[0][2] is True, "upstream: flagged semantic (=> cosine scale)")

    sh = R._sm_hits(SHIM)
    chk(sh[0][0].startswith("voice:"), "shim: top-level content still works")
    chk(sh[0][2] is False, "shim: NOT flagged semantic (=> BM25 scale)")

    # the bug we fixed: reading r["content"] against upstream yields nothing
    chk(UPSTREAM["results"][0].get("content") is None,
        "upstream really has no top-level content (the silent-empty bug)")
    chk(R._sm_texts(UPSTREAM) and R._sm_texts(UPSTREAM)[0].startswith("voice:"),
        "_sm_texts normalises upstream")

    # --- empty query: upstream 400s "Search query cannot be empty" ---
    chk(R._sm_q("") == R._SM_ANY, "empty q substituted")
    chk(R._sm_q("   ") == R._SM_ANY, "whitespace q substituted")
    chk(R._sm_q("real") == "real", "real q passed through untouched")

    # --- score scale: tau=1.0 vs cosine 0..1 disables the repeat guard entirely ---
    _t, score, semantic = R._sm_hits(UPSTREAM)[0]
    chk(semantic and score < 1.0, "cosine score is below the BM25 tau of 1.0")
    chk(score < float(os.environ.get("CHORUS_REPEAT_TAU", "1.0")),
        "=> a single tau CANNOT serve both backends (guard would never fire)")
    chk(R._sm_hits(SHIM)[0][1] > 1.0, "BM25 score can exceed 1.0 (tau is meaningful there)")

    # empty/degenerate payloads must not explode
    chk(R._sm_hits({}) == [], "empty payload -> []")
    chk(R._sm_hits({"results": [{"chunks": []}]})[0][0] == "", "no chunks -> empty text, no crash")

    print(f"SM COMPAT UNIT: {p} passed, {f} failed"); return f
import sys; sys.exit(run())
