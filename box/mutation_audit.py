#!/usr/bin/env python3
"""Mutation audit: break a real behaviour, see if ANY test notices.

A test that cannot fail is worse than no test — it buys confidence it has not earned. This
is the user's own rule #14 (false-confidence audit). Two decorative tests were already
caught today by hand; this checks the rest mechanically.
"""
import subprocess, sys, glob, shutil, os, tempfile

MUTANTS = [
    # (file, find, replace, "what this breaks")
    ("insights.py", "MIN_SAMPLE = 5", "MIN_SAMPLE = 1", "min-sample guard: claims at n=1"),
    ("insights.py", 'return "longform"', 'return "post"', "shape_of: longform misread as post"),
    ("budget.py", 'raise Killed("global kill-switch is on")', "pass", "KILL SWITCH disabled"),
    ("budget.py", "self.spent + usd > self.ceiling", "False", "ceiling never binds"),
    ("fast_lane.py", "since_ts = int(now / 1000) - MAX_AGE_MIN * 60 - OVERLAP_S",
     "since_ts = 0", "cost window removed (back to $1.30/day)"),
    ("ranker.py", 'if threshold is None:', 'if False:', "repeat-guard threshold ignored"),
    ("generate.py", '"grounded"', '"ungrounded"', "judge grounded dim renamed"),
]

def run_all():
    bad = []
    for t in sorted(glob.glob("test_*.py")):
        r = subprocess.run([sys.executable, t], capture_output=True, text=True)
        line = (r.stdout.strip().split("\n") or [""])[-1]
        if "passed" not in line or not line.endswith("0 failed"):
            bad.append(t)
    return bad

print(f"  baseline: {len(run_all())} suites failing (want 0)\n")
print("  MUTANT                                          caught by")
for fn, find, repl, what in MUTANTS:
    if not os.path.exists(fn):
        print(f"  {what:46s} (file missing)"); continue
    src = open(fn).read()
    if find not in src:
        print(f"  {what:46s} ANCHOR MISSING"); continue
    shutil.copy(fn, fn + ".bak")
    open(fn, "w").write(src.replace(find, repl, 1))
    try:
        caught = run_all()
    finally:
        shutil.move(fn + ".bak", fn)
    mark = ", ".join(c.replace("test_", "").replace(".py", "") for c in caught) if caught else "*** NOBODY ***"
    print(f"  {what:46s} {mark}")
