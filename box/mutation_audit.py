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
    # THE founding invariant. If any of these three go uncaught, the product's one safety
    # property is decorative and the failure mode is the user's ACCOUNT, not a bad insight.
    ("ranker.py", 'if autonomy not in ("L0", "L1"):', 'if autonomy not in ("L0", "L1", "L2"):',
     "SUGGEST-ONLY: autonomy gate widened past L1"),
    # session_mine turns PRIVATE sessions into PUBLIC tweets. The failure mode here is a
    # leaked credential on the user's timeline, so these mutants matter more than any other.
    ("session_mine.py", 'new1_|AIza)[A-Za-z0-9_\\-]{8,}', 'ZZZZ_NEVER_MATCHES)',
     "REDACTION: L1 key regex neutered"),
    ("session_mine.py", "def leaks(", "def _dead_leaks(", "REDACTION: L3 leak check removed"),
    # 50% precision on real data before this: a false merge writes a post claiming "this is
    # everywhere" about two unrelated stories.
    ("post_gen.py", "and any(_identifier(t) for t in common)", "and True",
     "CORRELATE: false merges on shared vocabulary"),
    # scrub was wired into post_gen alone, so 25% of replies and 39% of quotes shipped a
    # machine tell while the prompt "banned" them.
    ("ranker.py", '"drafts": [scrub(x) for x in d.get("drafts", []) if x][:3],',
     '"drafts": [x for x in d.get("drafts", []) if x][:3],',
     "VOICE: reply/quote drafts stop being scrubbed"),
    # The worker had ZERO tests. I nearly shipped 20 columns against 19 values there today —
    # every ingest would have 500'd, and I caught it by counting on my fingers.
    ("../dashboard/src/index.ts", "gif, thread, longform, media, status",
     "gif, thread, longform, media, extra_col, status",
     "WORKER SQL: INSERT column/value arity broken"),
    # If auth fails OPEN, the user's private queue and every draft in it are public.
    ("../dashboard/src/index.ts", "return payload.email === env.ALLOWED_EMAIL;", "return true;",
     "AUTH: any valid Access token accepted, not just the owner"),
    ("../dashboard/src/index.ts", 'if (env.DEV_OPEN === "1" && /^(localhost|127\\.|0\\.0\\.0\\.0)/.test(url.hostname)) return true;',
     'if (env.DEV_OPEN === "1") return true;',
     "AUTH: DEV_OPEN disables auth in PROD"),
    # --dry-run was a hole straight through the breaker: fake $10 ceiling, real paid calls.
    ("post_gen.py", "if not args.no_budget:\n        flush_spend", "if False:\n        flush_spend",
     "BUDGET: dry-run spend goes unbooked again"),
    # --no-budget skips the ceiling, so it must also make no paid call. Otherwise it is the
    # same hole with a friendlier name — which is exactly what I shipped first.
    ("post_gen.py", '        api_key = ""\n        tracker = B.BudgetTracker(spent=0.0, ceiling=10.0)',
     "        tracker = B.BudgetTracker(spent=0.0, ceiling=10.0)",
     "BUDGET: --no-budget spends past the ceiling again"),
    # Silence is what hid three bugs in one day. If the voice pipeline degrades quietly again,
    # the next person gets generic drafts and no idea why.
    ("ranker.py", "def _degraded(site: str, exc: Exception) -> None:\n    if site in _WARNED:",
     "def _degraded(site: str, exc: Exception) -> None:\n    return\n    if site in _WARNED:",
     "SILENCE: voice pipeline degrades without saying so"),
    ("ranker.py", "def get_voice(fallback):",
     'def _autopost(t, k):\n    return _req("https://api.x.com/2/tweets", "POST", k, {"text": t})\n\n\ndef get_voice(fallback):',
     "SUGGEST-ONLY: a real write lane added"),
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
