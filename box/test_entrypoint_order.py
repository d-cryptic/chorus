#!/usr/bin/env python3
"""Nothing may be defined BELOW a module's `if __name__ == "__main__"` entry point.

style_mine.py had features()/contrast()/TAG_CONTRAST defined after it. Running as a script
executed main() before those names existed -> NameError -> caught by a "non-fatal" handler ->
"contrast skipped (non-fatal)". Contrast and taste extraction NEVER ran in production, and
chorus:niche was built without them for the module's entire life.

No test could catch it, because tests IMPORT the module: an import executes every def first,
so the module looks complete. The suite and production were running different programs. This
checks the SCRIPT shape statically, which is the only view that matches production.
"""
import ast, pathlib, sys


def run():
    p = f = 0
    box = pathlib.Path(__file__).parent
    for path in sorted(box.glob("*.py")):
        tree = ast.parse(path.read_text(), filename=path.name)
        guard_line = None
        for node in tree.body:
            if (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                    and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__"):
                guard_line = node.lineno
                break
        if guard_line is None:
            continue
        late = [n for n in tree.body
                if n.lineno > guard_line
                and isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Assign))]
        if late:
            names = []
            for n in late:
                if isinstance(n, ast.Assign):
                    names += [t.id for t in n.targets if isinstance(t, ast.Name)]
                else:
                    names.append(n.name)
            print(f"  ❌ {path.name}: defined AFTER __main__ (line {guard_line}) -> "
                  f"NameError when run as a script: {names[:5]}")
            f += 1
        else:
            p += 1
    print(f"ENTRYPOINT ORDER UNIT: {p} passed, {f} failed")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(run())
