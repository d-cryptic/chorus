#!/usr/bin/env python3
"""A playbook synthesis that PAYS but returns None must still flush its spend to the ledger.

synthesize_playbook records spend the instant the paid call returns, then can raise on a
malformed reply and hand back None. `tracker.flush()` lived inside `if doc:`, so that spend
never reached /api/box/spend -> paid off the books, tomorrow's ceiling under-counts. Same
shape as the mirror-watermark bug: the money moved, the accounting did not.
"""
import os, sys, io, ast
from contextlib import redirect_stdout
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run():
    import os as _eo, importlib as _il, budget as _b
    _saved = _eo.environ.pop("CHORUS_DRAFT_PROVIDER", None)
    _il.reload(_b)
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "insights.py")).read()
    tree = ast.parse(src)
    main = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "main")

    # find the flush() call and the `if doc:` that used to wrap it
    flush_lines, ifdoc_ranges = [], []
    for node in ast.walk(main):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "flush":
            flush_lines.append(node.lineno)
        if (isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == "doc"):
            ifdoc_ranges.append((node.body[0].lineno, node.body[-1].end_lineno))
    chk(bool(flush_lines), "tracker.flush() vanished from insights.main()")
    for fl in flush_lines:
        inside = any(lo <= fl <= hi for lo, hi in ifdoc_ranges)
        chk(not inside, f"flush() at line {fl} is INSIDE `if doc:` -> a paid+None synth spends off-ledger")

    # behavioural: synthesize records, then returns None on bad JSON -> the recorded spend
    # must be non-zero so the always-flush actually posts it.
    import insights as I, budget as B
    tr = B.BudgetTracker(spent=0.0, ceiling=999.0)
    def fake_req(url, *a, **k):
        return {"choices": [{"message": {"content": "not json at all"}}]}   # forces the parse to fail
    orig = I._req; I._req = fake_req
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            doc = I.synthesize_playbook([{"kind":"x","payload":{},"confidence":0.9}],
                                        model="m", api_key="k", tracker=tr)
    finally:
        I._req = orig
    chk(doc is None, "a malformed reply must return None")
    chk(tr.spent > 0, "synthesize_playbook must RECORD spend before it fails -> flush has something to post")

    if _saved is not None:
        _eo.environ["CHORUS_DRAFT_PROVIDER"] = _saved
    _il.reload(_b)
    print(f"PLAYBOOK FLUSH UNIT: {p} passed, {f} failed")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(run())
