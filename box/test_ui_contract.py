#!/usr/bin/env python3
"""Static guards on the UI's data contract. These are the bugs a type-checker cannot see.

1. DRAFT DEFAULT DRIFT. selected() posted `drafts[pick ?? heroOffset(s)]` while act() recorded
   `pick ?? 0`. On the common path (you never press 1/2/3) the two defaults disagreed, so the
   hero draft was posted and index 0 was recorded. Measured on the live queue: 5 of 10.
   The learning loop then attributes the outcome to a draft the user never saw.

2. EXPIRY SCOPE. `expires_at > now` was applied to EVERY status, but the sweep only
   re-statuses 'queued', so a posted row keeps a past expires_at forever -> the Posted tab
   returns [] while its badge (an unfiltered GROUP BY status) still says 12. Proven against
   prod: 3 days out, the old WHERE returns 0 posted rows, the scoped one returns 12.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "dashboard", "web", "src", "App.tsx")
WORKER = os.path.join(ROOT, "dashboard", "src", "index.ts")


def run():
    if not os.path.exists(APP):
        print("UI CONTRACT UNIT: skipped (no UI source here — laptop/CI only)")
        return 0
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    app = open(APP).read()
    # 1. every `pick[s.id] ??` default must be heroOffset(s) — never a bare 0
    defaults = re.findall(r"pick\[s\.id\]\s*\?\?\s*([A-Za-z0-9_()\.]+)", app)
    chk(len(defaults) >= 3, f"expected >=3 pick defaults, found {len(defaults)}")
    chk(all("heroOffset" in d for d in defaults),
        f"a pick[] default is not heroOffset -> posts one draft, records another: {defaults}")

    # 2. the worker's expiry filter must be scoped to the queued lane
    w = open(WORKER).read()
    m = re.search(r"AND \(([^)]*)expires_at IS NULL OR s\.expires_at > \?2\)", w)
    chk(m is not None, "the suggestions expiry clause vanished")
    if m:
        chk("?1 != 'queued'" in m.group(1),
            "expiry is unscoped again -> posted/dismissed tabs empty while their badge counts")
    # 3. the snoozed OR must not leak into other tabs
    chk("?1 = 'queued' AND s.status='snoozed'" in w,
        "the snoozed OR is unscoped -> snoozed rows render in the Posted tab")

    print(f"UI CONTRACT UNIT: {p} passed, {f} failed")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(run())
