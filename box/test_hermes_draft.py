#!/usr/bin/env python3
"""The Hermes drafting backend + the leading-vocative scrub guard.

Hermes lets the box draft with a Claude/Codex SUBSCRIPTION ($0 marginal) instead of per-token
OpenRouter. hermes_complete must (a) return the exact OpenAI shape the drafter parses, (b) pass
the tweet text as an argv element not a shell string (no injection), (c) raise on failure so the
drafter degrades rather than emitting an empty draft. scrub must strip a LEADING 'bro'/'yo'
vocative (a tell a stronger model slips) without mangling 'brother' or a mid-sentence 'bro'.
"""
import os, sys, subprocess
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hermes_backend as H
import ranker as R


def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    # --- spec parsing ---
    with mock.patch.dict(os.environ, {"CHORUS_DRAFT_PROVIDER": ""}, clear=False):
        chk(H.hermes_spec() is None, "no env -> OpenRouter path (spec None)")
    with mock.patch.dict(os.environ, {"CHORUS_DRAFT_PROVIDER": "hermes:anthropic:claude-sonnet-4.6"}):
        chk(H.hermes_spec() == ("anthropic", "claude-sonnet-4.6"), "parses provider+model")
    with mock.patch.dict(os.environ, {"CHORUS_DRAFT_PROVIDER": "hermes:bad"}):
        try:
            H.hermes_spec(); chk(False, "malformed spec must raise, not silently misroute")
        except ValueError:
            chk(True, "malformed spec raises")

    # --- hermes_complete shape + argv safety ---
    captured = {}
    def fake_run(cmd, **k):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout='```json\n{"drafts":["hi"]}\n```', stderr="")
    with mock.patch.dict(os.environ, {"CHORUS_DRAFT_PROVIDER": "hermes:anthropic:claude-sonnet-4.6"}), \
         mock.patch.object(subprocess, "run", fake_run):
        out = H.hermes_complete({"messages": [{"content": "topic: $(rm -rf /) `evil`"}], "model": "x"})
    chk(out["choices"][0]["message"]["content"].startswith("```json"),
        "returns the OpenAI {choices:[{message:{content}}]} shape")
    chk(any("$(rm -rf /) `evil`" in part for part in captured["cmd"]), "tweet text is an ARGV element, verbatim, not a shell string")
    chk("--safe-mode" in captured["cmd"], "--safe-mode: a completion, not a tool-using agent run")

    # --- failure raises (drafter degrades, never emits empty) ---
    def boom(cmd, **k):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="provider not authed")
    with mock.patch.dict(os.environ, {"CHORUS_DRAFT_PROVIDER": "hermes:anthropic:x"}), \
         mock.patch.object(subprocess, "run", boom):
        try:
            H.hermes_complete({"messages": [{"content": "x"}]}); chk(False, "non-zero exit must raise")
        except RuntimeError:
            chk(True, "hermes non-zero exit raises -> caller degrades")

    # --- the scrub guard ---
    chk(R.scrub("bro a 27B is not the flex") == "a 27B is not the flex", "leading 'bro' stripped")
    chk(R.scrub("yo, local AI is huge") == "local AI is huge", "leading 'yo,' stripped")
    chk(R.scrub("brother it works") == "brother it works", "'brother' NOT mangled")
    chk(R.scrub("this bro is mid-sentence") == "this bro is mid-sentence", "mid-sentence 'bro' left alone")
    chk(R.scrub("clean—line") == "clean, line", "em-dash guard still works")



    # --- CLI subscription backend (claude/grok/codex) ---
    with mock.patch.dict(os.environ, {"CHORUS_DRAFT_PROVIDER": "cli:claude"}):
        chk(H.cli_spec() == "claude", "cli:claude parses")
    with mock.patch.dict(os.environ, {"CHORUS_DRAFT_PROVIDER": "cli:nope"}):
        try:
            H.cli_spec(); chk(False, "unknown cli must raise, not misroute")
        except ValueError:
            chk(True, "unknown cli name raises")
    cap = {}
    def fake_cli(cmd, **k):
        cap["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout='{"drafts":["hi"]}', stderr="")
    with mock.patch.dict(os.environ, {"CHORUS_DRAFT_PROVIDER": "cli:claude"}), \
         mock.patch.object(subprocess, "run", fake_cli):
        out = H.cli_complete({"messages": [{"content": "topic `evil`"}]})
    chk(out["choices"][0]["message"]["content"] == '{"drafts":["hi"]}', "cli returns OpenAI shape")
    chk(cap["cmd"][:2] == ["claude", "-p"], "cli:claude shells to `claude -p`")
    chk(any("topic `evil`" in part for part in cap["cmd"]), "prompt is an argv element, not a shell string")
    def missing(cmd, **k):
        raise FileNotFoundError("no claude")
    with mock.patch.dict(os.environ, {"CHORUS_DRAFT_PROVIDER": "cli:claude"}), \
         mock.patch.object(subprocess, "run", missing):
        try:
            H.cli_complete({"messages": [{"content": "x"}]}); chk(False, "missing CLI must raise")
        except RuntimeError:
            chk(True, "missing CLI raises -> drafter degrades, not a silent empty draft")

    print(f"HERMES DRAFT UNIT: {p} passed, {f} failed")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(run())
