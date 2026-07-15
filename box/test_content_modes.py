#!/usr/bin/env python3
"""The content-modes registry: each mode's brief carries its craft rules and bans, routes to
the right model, and is scrub-compatible (no em-dashes/vocatives for the scrubber to fight).

Built from 5 parallel design passes (short/sarcastic/research/longform/thread). Model routing:
grok for the punchy X-native modes, codex for the structured/faithful ones -- the user wants
both used heavily.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import content_modes as CM
from ranker import scrub


def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    # --- registry completeness ---
    for m in ("short", "sarcastic", "research", "longform", "thread"):
        chk(m in CM.MODES, f"mode {m} registered")
        chk(bool(CM.MODES[m]["brief"]), f"mode {m} has a brief")

    # --- model routing (the user's grok+codex requirement) ---
    chk(CM.provider_for("short") == CM.MODES["short"] and CM.MODES["short"]["model_pref"] == "grok"
        or "grok" in (CM.provider_for("short") or ""), "short -> grok")
    chk("grok" in (CM.provider_for("sarcastic") or ""), "sarcastic -> grok")
    chk("codex" in (CM.provider_for("research") or ""), "research -> codex")
    chk("codex" in (CM.provider_for("longform") or ""), "longform -> codex")
    chk("codex" in (CM.provider_for("thread") or ""), "thread -> codex")

    # --- every brief is scrub-compatible: no em/en-dashes, unchanged by scrub ---
    for m, mode in CM.MODES.items():
        b = mode["brief"]
        chk("—" not in b and "–" not in b, f"{m}: no em/en-dashes in brief")

    # --- per-mode craft assertions (from the 5 design passes) ---
    short = CM.MODES["short"]["brief"]
    chk("FIRST 5 WORDS" in short, "short: hook-in-first-5-words rule")
    chk("the real X is" in short, "short: bans the 'the real X' tic")

    sar = CM.MODES["sarcastic"]["brief"]
    chk("cruelty" in sar and "punching down" in sar, "sarcastic: bans cruelty/punching down")
    chk("/s" in sar, "sarcastic: bans the '/s' tell")
    chk("\U0001F921" in sar or "clown" in sar.lower(), "sarcastic: bans clown-emoji pileon")

    res = CM.MODES["research"]["brief"]
    chk("Invent NOTHING" in res, "research: invent-nothing rule")
    chk("VERBATIM" in res, "research: facts must be verbatim from grounding")
    chk("studies show" in res, "research: bans vague authority laundering")

    lf = CM.MODES["longform"]["brief"]
    chk("400-1500" in lf, "longform: 400-1500 char range")
    chk("listicle" in lf.lower(), "longform: bans listicle scaffolding")
    chk("LinkedIn" in lf, "longform: bans LinkedIn cadence")

    th = CM.MODES["thread"]["brief"]
    chk("SEGMENT 1 IS A HOOK" in th, "thread: hook-first rule")
    chk("STANDS ALONE" in th, "thread: each beat stands alone")
    chk("\U0001F9F5" not in th, "thread: brief itself has no thread-emoji")
    chk("thread emoji" in th.lower(), "thread: bans the thread emoji explicitly")

    # --- default mode mapping from shape ---
    chk(CM.default_mode_for_shape("post") == "short", "post -> short default")
    chk(CM.default_mode_for_shape("thread") == "thread", "thread -> thread default")
    chk(CM.default_mode_for_shape("longform") == "longform", "longform -> longform default")


    # --- batch 2 modes ---
    for m in ("contrarian", "story", "question", "quote", "listicle"):
        chk(m in CM.MODES, f"mode {m} registered")
        chk("—" not in CM.MODES[m]["brief"] and "–" not in CM.MODES[m]["brief"], f"{m}: no em/en-dashes")

    con = CM.MODES["contrarian"]["brief"]
    chk("hot take:" in con and "unpopular opinion:" in con, "contrarian: bans the attention badges")
    chk("consensus" in con.lower() and "mechanism" in con.lower(), "contrarian: consensus + mechanism required")

    st = CM.MODES["story"]["brief"]
    chk("i built" in st, "story: bans fabricated first-person")
    chk("observed" in st.lower(), "story: narrates the OBSERVED thing")

    q = CM.MODES["question"]["brief"]
    chk("what do you think?" in q and "thoughts?" in q, "question: bans lazy bait")
    chk("lean" in q.lower(), "question: requires the asker's lean")

    qt = CM.MODES["quote"]["brief"]
    chk("so true" in qt and "restat" in qt.lower(), "quote: bans empty agreement + restating")
    chk("card" in qt.lower() and "add" in qt.lower(), "quote: names the card + requires adding")

    li = CM.MODES["listicle"]["brief"]
    chk("be consistent" in li and "add value" in li, "listicle: bans generic filler tips")
    chk("filler" in li.lower() and "specific" in li.lower(), "listicle: specific/independent items required")

    # --- fallback: codex modes fall back to grok; grok modes have no fallback ---
    chk(CM.fallback_provider_for("research") == "hermes:xai-oauth:grok-4.5", "research falls back to grok")
    chk(CM.fallback_provider_for("short") is None, "short (grok) has no fallback")

    print(f"CONTENT MODES UNIT: {p} passed, {f} failed")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(run())
