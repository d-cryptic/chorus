#!/usr/bin/env python3
"""Quiet-hours must be evaluated in the USER's timezone, not the box's UTC clock.

ranker computed the hour correctly (gmtime + CHORUS_TZ_OFFSET_H); fast_lane and post_gen handed
time.localtime().tm_hour (box UTC) to the budget tracker's quiet-hours check -- a half-migration.
Once quiet_hours is set (a growth lever: don't post while your audience sleeps), the box-clock
sites would refuse during the user's WAKING hours, 5.5h inverted. All three must agree.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    d = os.path.dirname(os.path.abspath(__file__))
    for fn in ("fast_lane.py", "post_gen.py", "ranker.py"):
        src = open(os.path.join(d, fn)).read()
        # no hour_local may be fed the box's localtime() clock (direct substring, paren-safe)
        chk("hour_local=time.localtime" not in src.replace(" ", ""),
            f"{fn}: hour_local uses the box UTC clock -> quiet-hours misfires 5.5h off")
        # at least one call site references the tz offset (the correct source)
        if "hour_local" in src:
            chk("CHORUS_TZ_OFFSET_H" in src or "hour_local=hr" in src,
                f"{fn}: no user-timezone source for the quiet-hours hour")

    print(f"QUIET TZ UNIT: {p} passed, {f} failed")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(run())
