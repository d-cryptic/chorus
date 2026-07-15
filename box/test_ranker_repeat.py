#!/usr/bin/env python3
"""The near-miss diagnostic is the only source of repetition-tau tuning data.

It referenced an undefined `r`, so every near-miss raised NameError into already_said's
`except Exception`, which then (a) reported "REPETITION GUARD IS OFF" though the guard was
fine and (b) latched _WARNED, suppressing the next -- possibly real -- degradation warning.
"""
import os, sys, io, unittest
from unittest import mock
from contextlib import redirect_stdout
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ranker as R


def _hits(sc):
    return lambda out: [("i already said exactly this thing", sc, False)]


class NearMissTest(unittest.TestCase):
    def _call(self, sc):
        R._WARNED.clear()
        buf = io.StringIO()
        with mock.patch.object(R, "_req", lambda *a, **k: {}), \
             mock.patch.object(R, "_sm_hits", _hits(sc)), redirect_stdout(buf):
            out = R.already_said("some text", threshold=1.0)
        return out, buf.getvalue()

    def test_near_miss_prints_the_score(self):
        out, log = self._call(0.8)
        self.assertIsNone(out, "a near-miss must not count as a repeat")
        self.assertIn("near-miss 0.80", log, "the ONLY tau-tuning signal never printed")

    def test_near_miss_does_not_claim_the_guard_is_off(self):
        _, log = self._call(0.8)
        self.assertNotIn("REPETITION GUARD IS OFF", log,
                         "false alarm: a near-miss is the guard WORKING")

    def test_near_miss_does_not_latch_the_warn_once_flag(self):
        """The real cost: a spurious warn burns the once-per-site budget."""
        self._call(0.8)
        self.assertEqual(len(R._WARNED), 0, "_WARNED latched -> next real warning is silenced")

    def test_a_real_repeat_is_still_caught(self):
        out, _ = self._call(1.6)
        self.assertIsNotNone(out)
        self.assertIn("already said", out[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
