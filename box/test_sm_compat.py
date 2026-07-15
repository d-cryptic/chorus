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

    # --- already_said's PRODUCTION path (threshold=None) was never exercised -----------
    # Mutation audit: changing `if threshold is None:` to `if False:` was caught by NOBODY.
    # Every test passed an explicit threshold, so the branch that PICKS the threshold — the
    # one production uses, and the one carrying the cosine-vs-BM25 scale logic — was untested.
    # That branch is the whole repetition guard: get it wrong and Chorus repeats itself
    # forever, silently, which is exactly what a tau of 1.0 against cosine 0..1 already did.
    calls = []
    real_req = R._req
    def fake_req(url, method="GET", token=None, body=None, timeout=8):
        calls.append(body)
        return UPSTREAM if "search" in url else {}
    R._req = fake_req
    try:
        hit = R.already_said("voice: short, punchy sentences, minimal fluff")   # NO threshold arg
        chk(hit is None, "cosine 0.615 < the cosine default (0.88): correctly not a repeat")
        R._sm_hits_orig = R._sm_hits
        R._sm_hits = lambda out: [("x", 0.99, True)]        # a near-identical, semantic backend
        chk(R.already_said("anything") is not None, "cosine 0.99 IS a repeat at the default")
        R._sm_hits = lambda out: [("x", 0.99, False)]       # BM25 backend: 0.99 is NOT a repeat
        chk(R.already_said("anything") is None, "BM25 0.99 is below the BM25 default (1.0)")
        R._sm_hits = lambda out: [("x", 3.7, False)]
        chk(R.already_said("anything") is not None, "BM25 3.7 IS a repeat")
    finally:
        R._req = real_req
        if hasattr(R, "_sm_hits_orig"): R._sm_hits = R._sm_hits_orig

    # --- best-effort must not mean SILENT ------------------------------------------------
    # get_voice / niche_context / already_said all swallow broadly on purpose: memory being
    # down must never block a cycle. That silence hid THREE real bugs in a single day —
    # the learned voice was never read (the env string was used instead), niche_context 400'd
    # on an empty query, and already_said compared cosine against a BM25 tau so the repetition
    # guard never fired. Each looked exactly like "nothing to say".
    real_req2 = R._req
    R._req = lambda *a, **k: (_ for _ in ()).throw(ConnectionError("refused"))
    R._WARNED.clear()
    try:
        chk(R.get_voice("ENV_FALLBACK") == "ENV_FALLBACK", "get_voice still falls back safely")
        chk(R.niche_context() == "", "niche_context still returns empty safely")
        chk(R.already_said("x") is None, "already_said still returns None safely")
        chk(len(R._WARNED) == 3, f"...but ALL THREE now SAY they degraded (got {len(R._WARNED)})")
        n_before = len(R._WARNED)
        R.get_voice("f"); R.get_voice("f")
        chk(len(R._WARNED) == n_before, "warns ONCE per site: per-candidate spam is just silence with extra steps")
    finally:
        R._req = real_req2
        R._WARNED.clear()

    print(f"SM COMPAT UNIT: {p} passed, {f} failed"); return f
import sys; sys.exit(run())
