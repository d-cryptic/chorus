#!/usr/bin/env python3
"""GEO agent: score = fraction of pillars where an answer-engine cites you; gaps are named.

Verifies the citation detection (handle/name match), the score math, and that a query failure
degrades (skips the pillar) rather than crashing the sweep.
"""
import os, sys
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo


def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    class A:
        dry_run = True

    # answers: cited on pillar 1, invisible on 2, query fails on 3
    def fake_ask(pillar, provider):
        if pillar == "boom":
            raise RuntimeError("engine down")
        return "top voices: @someone, @barundebnath, @another" if pillar == "ai" else "@x, @y, @z"

    with mock.patch.dict(os.environ, {"CHORUS_HANDLE": "@barundebnath",
                                      "CHORUS_PILLARS": "ai, kubernetes, boom",
                                      "INGEST_URL": "http://x", "INGEST_TOKEN": "t"}, clear=False), \
         mock.patch.object(geo, "_ask", fake_ask):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            geo.run(A())
        out = buf.getvalue()

    chk("cited on 'ai'" in out, "detects citation when handle appears")
    chk("invisible on 'kubernetes'" in out, "detects a gap when handle absent")
    chk("skipping" in out, "a failed engine query is skipped, not fatal")
    # cited 1 of 2 answered (boom failed) -> score 0.5
    chk("GEO score: 0.5" in out, "score = cited / answered (failed queries excluded)")
    chk("['kubernetes']" in out, "names the gap pillars")

    # missing config -> graceful
    with mock.patch.dict(os.environ, {"CHORUS_HANDLE": "", "CHORUS_PILLARS": ""}, clear=False):
        import io as _io
        from contextlib import redirect_stdout as _rs
        b2 = _io.StringIO()
        with _rs(b2):
            geo.run(A())
        chk("need CHORUS_HANDLE" in b2.getvalue(), "missing config -> clear message, no crash")

    print(f"GEO UNIT: {p} passed, {f} failed")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(run())
