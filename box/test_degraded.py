#!/usr/bin/env python3
"""_degraded must not launder a bug as a graceful degradation.

already_said raised NameError on every near-miss for weeks. _degraded printed
"unavailable ... - degrading", which is what it also prints when Supermemory is genuinely
down — so the bug was indistinguishable from expected noise, AND it latched _WARNED,
suppressing the real warning for that site.
"""
import os, sys, io, unittest
from contextlib import redirect_stdout
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ranker as R


class DegradedTest(unittest.TestCase):
    def setUp(self):
        R._WARNED.clear()

    def _emit(self, exc):
        buf = io.StringIO()
        with redirect_stdout(buf):
            R._degraded("some_site", exc)
        return buf.getvalue()

    def test_network_failure_is_a_degradation(self):
        out = self._emit(ConnectionError("refused"))
        self.assertIn("degrading", out)
        self.assertNotIn("BUG", out)

    def test_name_error_is_reported_as_a_bug(self):
        out = self._emit(NameError("name 'r' is not defined"))
        self.assertIn("BUG in some_site", out)
        self.assertIn("NameError", out)
        self.assertNotIn("degrading", out, "a bug must not read as expected noise")

    def test_a_bug_never_latches_the_warn_once_budget(self):
        """The compounding harm: a spurious warn silences the NEXT, real one."""
        self._emit(TypeError("boom"))
        self.assertEqual(len(R._WARNED), 0, "bug latched _WARNED -> real warning suppressed")
        out = self._emit(ConnectionError("refused"))
        self.assertIn("degrading", out, "the real degradation was swallowed by the bug's latch")

    def test_a_bug_is_loud_every_time_not_once(self):
        self.assertIn("BUG", self._emit(AttributeError("x")))
        self.assertIn("BUG", self._emit(AttributeError("x")), "rate-limited a bug into silence")

    def test_real_degradations_still_warn_only_once(self):
        self.assertIn("degrading", self._emit(ConnectionError("refused")))
        self.assertEqual(self._emit(ConnectionError("refused")), "", "warn-once budget broken")


if __name__ == "__main__":
    unittest.main(verbosity=2)
