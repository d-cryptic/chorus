#!/usr/bin/env python3
"""chorus:niche was wiped and nothing noticed. These pin the self-heal's refusal rules.

niche_context() returns "" for BOTH "memory down" and "memory empty", and the drafter degrades
silently by design -- so a wipe on a Wednesday meant 5 days of unguided drafts (style_mine is
Mon-only). --if-empty lets a daily cron heal it within 24h for free on a normal day.

The dangerous mistake is the inverse: mining because the store was unreachable would burn
budget re-deriving patterns that already exist. Unreachable != empty.
"""
import os, sys, io, json
from contextlib import redirect_stdout
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style_mine as S


def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    def probe(docs=None, boom=None):
        class R:
            def read(self_): return json.dumps({"memories": docs or []}).encode()
            def __enter__(self_): return self_
            def __exit__(self_, *a): return False
        def op(*a, **k):
            if boom: raise boom
            return R()
        buf = io.StringIO()
        with mock.patch("urllib.request.urlopen", op), redirect_stdout(buf):
            return S.niche_is_empty("http://sm", ""), buf.getvalue()

    # --- the probe ---
    out, _ = probe(docs=[])
    chk(out is True, "no docs -> empty")
    out, _ = probe(docs=[{"containerTags": ["chorus:niche"]}])
    chk(out is False, "a niche doc -> NOT empty (must not re-mine)")
    out, _ = probe(docs=[{"containerTags": ["chorus:niche:replies"]}])
    chk(out is False, "the :replies subtag also counts as populated")
    out, _ = probe(docs=[{"containerTags": ["chorus:self"]}, {"containerTags": ["chorus:posts"]}])
    chk(out is True, "self/posts populated but niche gone = the ACTUAL wipe state -> empty")
    out, log = probe(boom=ConnectionError("refused"))
    chk(out is None, "unreachable must be None, never True -- it is not an empty store")
    chk("not mining" in log, "an unreachable store must say why it did not act")

    # --- the gate: only `True` may spend ---
    class A:
        dry_run = False; if_empty = True; pages = 1; top = 15; mode = "posts"
    for verdict, should_spend in ((False, False), (None, False), (True, True)):
        spent = {"n": 0}
        def fake_fetch(*a, **k):
            spent["n"] += 1
            return []
        buf = io.StringIO()
        with mock.patch.object(S, "niche_is_empty", lambda *a, **k: verdict), \
             mock.patch.dict(os.environ, {"CANDIDATE_API_KEY": "k", "OPENROUTER_API_KEY": "k"}), \
             mock.patch.object(S, "top_posts", lambda *a, **k: []), redirect_stdout(buf):
            import candidate_source
            with mock.patch.object(candidate_source, "fetch_candidates", fake_fetch):
                try: S.main_with(A()) if hasattr(S, "main_with") else _main(S, A())
                except SystemExit: pass
        chk((spent["n"] > 0) == should_spend,
            f"verdict={verdict!r} -> {'must spend' if should_spend else 'MUST NOT spend'}")

    print(f"NICHE HEAL UNIT: {p} passed, {f} failed")
    return 1 if f else 0


def _main(S, args):
    """Call main() with our args, bypassing argparse."""
    import argparse
    with mock.patch.object(argparse.ArgumentParser, "parse_args", lambda self: args):
        return S.main()


if __name__ == "__main__":
    import sys; sys.exit(run())
