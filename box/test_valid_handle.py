#!/usr/bin/env python3
"""Handle validation for anchor discovery must allow underscores (26% of real X handles).

`h.isalnum()` dropped every handle with an underscore -- @tom_doerr, @Jan_Coutinho, ... --
silently shrinking the discovery pool (the engine that finds new accounts to engage = growth)
by a quarter. Measured live: 228/861 following-graph handles contain '_'.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discover_anchors as D


def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    chk(D._valid_handle("tom_doerr"), "underscore handle kept (was dropped by isalnum)")
    chk(D._valid_handle("barundebnath"), "plain handle kept")
    chk(D._valid_handle("_lead"), "leading underscore is a valid X handle")
    chk(not D._valid_handle(""), "empty rejected")
    chk(not D._valid_handle("___"), "all-underscore rejected (isalnum of '' is False)")
    chk(not D._valid_handle("has space"), "space rejected")
    chk(not D._valid_handle("x" * 16), "over 15 chars rejected (X limit)")

    print(f"VALID HANDLE UNIT: {p} passed, {f} failed")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(run())
