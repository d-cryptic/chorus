"""The Worker is 446 lines, 9 endpoints, and had ZERO tests.

It is the API every box script and the UI depend on. Today I added `longform` to the
suggestion INSERT and left 20 columns against 19 values — every ingest would have 500'd. I
caught it by counting on my fingers, which is not a strategy.

This checks the arity of every INSERT statically: columns == values == bind() args. No test
runner, no worker deps, no network — it reads the TypeScript as text, which is exactly the
level this bug lives at.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
WORKER = os.path.join(os.path.dirname(HERE), "dashboard", "src", "index.ts")


def split_args(s):
    """Top-level comma split: JSON.stringify(b.x ?? []) is ONE arg, not two."""
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip()); cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    if not os.path.exists(WORKER):
        # The box has no repo checkout, only /opt/chorus/box. This suite reads the worker's
        # TypeScript, so it is a laptop/CI test by nature. SKIP is the honest report; failing
        # here would cry wolf on every box run and teach everyone to ignore the suite.
        print("WORKER SQL UNIT: skipped (no worker source here — laptop/CI only)")
        return 0
    src = open(WORKER, encoding="utf-8").read()

    inserts = re.findall(r"INSERT INTO (\w+)\s*\(([^)]*)\)\s*\n?\s*VALUES\s*\(([^)]*)\)", src)
    chk(len(inserts) >= 2, f"found INSERT statements to check ({len(inserts)})")

    for table, cols_s, vals_s in inserts:
        cols = [c.strip() for c in cols_s.split(",") if c.strip()]
        vals = [v.strip() for v in vals_s.split(",") if v.strip()]
        chk(len(cols) == len(vals),
            f"{table}: {len(cols)} columns vs {len(vals)} values "
            f"(a mismatch 500s EVERY write to this table)")

    # the suggestion INSERT is the one that carries the queue; check bind() arity too
    m = re.search(r"INSERT INTO suggestion \(([^)]*)\)\s*\n\s*VALUES\s*\(([^)]*)\)", src)
    chk(bool(m), "the suggestion INSERT is parseable")
    if m:
        placeholders = m.group(2).count("?")
        tail = src[m.end():]
        b = re.search(r"\)\.bind\((.*?)\)\.run\(\)", tail, re.S)
        chk(bool(b), "its .bind(...) is parseable")
        if b:
            args = split_args(b.group(1))
            chk(placeholders == len(args),
                f"suggestion: {placeholders} placeholders vs {len(args)} bind args "
                f"(D1 throws on a mismatch, so the whole ingest path dies)")

    # a literal in VALUES (like 'queued') consumes a column but NOT a placeholder — the exact
    # asymmetry that made the 20/19 miscount easy to make and easy to miss
    if m:
        literals = [v for v in m.group(2).split(",") if "'" in v]
        cols = [c.strip() for c in m.group(1).split(",")]
        chk(len(cols) == m.group(2).count("?") + len(literals),
            "columns == placeholders + literals (the asymmetry that hid the 20/19 bug)")

    # box_state carries the only copy of 216 curated handles + 15 human judgements
    chk("box_state" in src, "the box-state backup endpoint exists")
    chk("ON CONFLICT(k) DO UPDATE" in src, "a re-backup UPDATES rather than erroring")

    print(f"WORKER SQL UNIT: {p} passed, {f} failed"); return f
import sys; sys.exit(run())
