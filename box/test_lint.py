#!/usr/bin/env python3
"""ruff's F-rules are pyflakes: real bugs, not style. Nothing ran them over box/ until now.

F821 (undefined name) is the one that matters. ranker.already_said referenced an undefined
`r` for weeks; every near-miss raised NameError into an `except Exception` that announced
"REPETITION GUARD IS OFF - drafts may repeat" — indistinguishable from Supermemory being
down, so it read as expected noise. ruff finds it in 40ms.

Scoped deliberately to the bug-classes, not style: a lint gate people learn to ignore is
worse than no gate. F401 (unused import) is excluded — it cannot break a run.

Skips where ruff is absent (the box has no dev tooling) rather than failing: a gate that
fails for want of a tool teaches everyone to skip it.
"""
import shutil, subprocess, sys, pathlib

# real-bug rules only:
#   F821 undefined name        -> NameError at runtime (the already_said bug)
#   F811 redefinition          -> the second def silently wins; the first is dead
#   F841 unused local variable -> an accumulator declared, read, never appended to
#   F632 `is` on a literal     -> silently always-False comparisons
RULES = "F821,F811,F841,F632"


def run():
    box = pathlib.Path(__file__).parent
    ruff = shutil.which("ruff")
    if not ruff:
        print("LINT UNIT: skipped (no ruff here — laptop/CI only)")
        return 0
    r = subprocess.run([ruff, "check", "--select", RULES, "--no-cache", str(box)],
                       capture_output=True, text=True)
    if r.returncode == 0:
        print(f"LINT UNIT: 1 passed, 0 failed ({RULES} clean)")
        return 0
    print(r.stdout.strip()[:1200])
    print(f"LINT UNIT: 0 passed, 1 failed — {RULES} are runtime bugs, not style")
    return 1


if __name__ == "__main__":
    sys.exit(run())
