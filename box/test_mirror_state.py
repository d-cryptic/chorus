#!/usr/bin/env python3
"""The mirror watermark must advance on EVERY row, not only on batches containing a post.

Regression: `since = max(since, f["ts"])` lived inside `if corpus:`, so a batch of pure
dismissals/expiries left the watermark parked while the state file saved it regardless.
Every subsequent run (*/30) re-fetched and re-POSTed the same rows forever.

Supermemory's content-hash dedupe means this wasted writes rather than poisoning the corpus
-- so these tests assert on the WRITE COUNT, not on the resulting doc count. Asserting on
docs would pass against the bug, because the store absorbs it.
"""
import os, sys, json, tempfile, unittest
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mirror_feedback as M


class Args:
    dry_run = False


def _rows(*specs):
    return [{"ts": ts, "action": a, "author_handle": "x", "final_text": "t",
             "posted_text": "t" if a.startswith("posted") else None,
             "angle": "", "target": "t", "draft_index": 0} for ts, a in specs]


class WatermarkTest(unittest.TestCase):
    def _run(self, rows, start=0):
        d = tempfile.mkdtemp(); state = os.path.join(d, ".mirror_state")
        if start:
            open(state, "w").write(str(start))
        env = {"CHORUS_STATE": state, "INGEST_URL": "http://x", "INGEST_TOKEN": "t",
               "SUPERMEMORY_BASE_URL": "http://sm"}
        sent = []

        def fake(url, method="GET", token=None, body=None, timeout=20):
            if "feedback" in url:
                return {"feedback": rows}
            sent.append(body)
            return {}

        with mock.patch.dict(os.environ, env, clear=False), mock.patch.object(M, "_req", fake):
            M.run(Args())
        saved = int(open(state).read().strip()) if os.path.exists(state) else 0
        return saved, sent

    def test_advances_without_any_posted_reply(self):
        """THE BUG: dismissals only -> watermark must still reach the newest row."""
        saved, _ = self._run(_rows((100, "dismissed"), (200, "expired")), start=50)
        self.assertEqual(saved, 200, "watermark parked -> these rows re-mirror every 30 min")

    def test_advances_with_a_posted_reply(self):
        saved, _ = self._run(_rows((100, "dismissed"), (300, "posted")), start=50)
        self.assertEqual(saved, 300)

    def test_no_duplicate_mirroring_across_runs(self):
        """Two consecutive runs over a non-posting batch must not write the row twice."""
        d = tempfile.mkdtemp(); state = os.path.join(d, ".mirror_state")
        rows = _rows((100, "dismissed"))
        env = {"CHORUS_STATE": state, "INGEST_URL": "http://x", "INGEST_TOKEN": "t",
               "SUPERMEMORY_BASE_URL": "http://sm"}
        writes = []

        def fake(url, method="GET", token=None, body=None, timeout=20):
            if "feedback" in url:
                # a real worker filters by ?since=; emulate that or the test proves nothing
                since = int(url.split("since=")[1])
                return {"feedback": [r for r in rows if r["ts"] > since]}
            writes.append(body)
            return {}

        with mock.patch.dict(os.environ, env, clear=False), mock.patch.object(M, "_req", fake):
            M.run(Args()); M.run(Args())
        self.assertEqual(len(writes), 1, f"row mirrored {len(writes)}x -> corpus poisoned")

    def test_dry_run_never_moves_the_watermark(self):
        class A: dry_run = True
        d = tempfile.mkdtemp(); state = os.path.join(d, ".mirror_state")
        open(state, "w").write("50")
        with mock.patch.dict(os.environ, {"CHORUS_STATE": state, "INGEST_URL": "http://x",
                                          "INGEST_TOKEN": "t"}, clear=False), \
             mock.patch.object(M, "_req", lambda *a, **k: {"feedback": _rows((900, "dismissed"))}):
            M.run(A())
        self.assertEqual(int(open(state).read().strip()), 50, "dry-run advanced real state")


if __name__ == "__main__":
    unittest.main(verbosity=2)
