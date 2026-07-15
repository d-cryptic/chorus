#!/usr/bin/env python3
"""Every `args.X` a module reads must be a flag its own parser defines.

fast_lane.py read `args.no_budget` at main()'s TOP LEVEL -- the cron path -- while its parser
only defined --dry-run/--cap/--tau. Every real run raised AttributeError AFTER the paid fetch,
after tracker.record(), and after printing "fast lane: N fetched, M live": it paid, claimed
success, queued nothing, and never flushed the spend to the ledger.

Nothing caught it. Unit tests build their own Namespace (so they define whatever they read),
and the live cron was being refused by the budget ceiling, which masked the crash for a day.
This is a static check because it must not depend on a run happening to reach that line.
"""
import ast, pathlib, sys

# argparse itself supplies these; a parser need not declare them.
BUILTIN = {"help"}


def flags_of(fn):
    """--no-budget -> no_budget, as argparse's dest mangling does."""
    out = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "add_argument":
            for a in n.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.startswith("--"):
                    out.add(a.value[2:].replace("-", "_"))
            for kw in n.keywords:                       # explicit dest= wins
                if kw.arg == "dest" and isinstance(kw.value, ast.Constant):
                    out.add(kw.value.value)
    return out


def run():
    p = f = 0
    for path in sorted(pathlib.Path(__file__).parent.glob("*.py")):
        if path.name.startswith("test_"):
            continue
        tree = ast.parse(path.read_text(), filename=path.name)
        # the function that builds the parser owns the flags for this module
        defined = set()
        for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            defined |= flags_of(fn)
        if not defined:
            continue
        read = {n.attr for n in ast.walk(tree)
                if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                and n.value.id == "args" and isinstance(n.ctx, ast.Load)}
        # getattr(args, "no_budget", False) is the same bug with a default bolted on: the flag
        # does not exist, so it silently reads False FOREVER. style_mine's budget tracker was
        # None on every run because of exactly this, killing its ceiling and kill-switch. A
        # plain args.x at least raises; this one just quietly lies.
        read |= {n.args[1].value for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "getattr"
                 and len(n.args) >= 2 and getattr(n.args[0], "id", "") == "args"
                 and isinstance(n.args[1], ast.Constant)}
        # `args.x = v` CREATES the attribute, so a later read is legitimate (ranker does this
        # to pass a computed window through). Only flag reads that nothing ever defines.
        assigned = {n.attr for n in ast.walk(tree)
                    if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                    and n.value.id == "args" and isinstance(n.ctx, ast.Store)}
        missing = read - defined - assigned - BUILTIN
        if missing:
            print(f"  ❌ {path.name}: reads args.{{{', '.join(sorted(missing))}}} but its parser "
                  f"never defines them -> AttributeError at runtime")
            f += 1
        else:
            p += 1
    print(f"ARGPARSE CONTRACT UNIT: {p} passed, {f} failed")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(run())
