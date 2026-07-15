#!/usr/bin/env python3
"""Route a drafting call through the local Hermes agent instead of OpenRouter HTTP.

WHY: the box holds a Claude/Codex SUBSCRIPTION via `hermes auth add`, so drafting through
Hermes costs $0 marginal (the subscription is flat), where OpenRouter bills per token. The
model quality is identical -- anthropic/claude-sonnet-4.6 is the same weights either way --
so the only question was voice adherence, which a measured bake-off settled (clean + sharper
under the full Supermemory context).

CONTRACT: hermes_complete(body) returns the SAME OpenAI shape _req() returns for OpenRouter
({"choices":[{"message":{"content": ...}}]}), so post_gen/classify_shape parse it unchanged.

SAFETY: shells out to the `hermes` CLI. The prompt is passed as a single argv element (never
through a shell string), so no injection from tweet text. Runs with --safe-mode: a pure completion, not an agent run, so Hermes cannot take
destructive actions with the box's credentials on drafting a tweet.
"""
from __future__ import annotations
import os, subprocess


# CHORUS_DRAFT_PROVIDER = "hermes:<provider>:<model>"
#   e.g. "hermes:anthropic:claude-sonnet-4.6"  (subscription, the point of this)
#        "hermes:openrouter:anthropic/claude-sonnet-4.6"  (per-token, for testing the plumbing)
def hermes_spec(raw=None):
    """(provider, model) if drafting is configured to go through Hermes, else None.
    Pass an explicit `raw` spec for per-mode routing; else reads CHORUS_DRAFT_PROVIDER."""
    raw = raw if raw is not None else os.environ.get("CHORUS_DRAFT_PROVIDER", "")
    if not raw.startswith("hermes:"):
        return None
    parts = raw.split(":", 2)
    if len(parts) != 3 or not parts[1] or not parts[2]:
        raise ValueError(f"CHORUS_DRAFT_PROVIDER must be hermes:<provider>:<model>, got {raw!r}")
    return parts[1], parts[2]


def _extract(stdout):
    """Isolate the model's completion from CLI chrome.

    Hermes -z is clean (just drop 'hermes -z:' notices). Codex exec is NOT: it echoes the
    prompt, prints a bubblewrap/sandbox warning, a 'codex' label, 'tokens used\n<n>', and often
    repeats the answer. The drafter then json.loads() the result, so chrome must be stripped.
    Strategy: if the text contains a JSON object, return the LAST balanced {...} that parses
    (codex prints the final answer last); else drop known noise lines and return the body."""
    import json as _j
    text = "\n".join(l for l in stdout.splitlines() if not l.startswith("hermes -z:"))
    # try to recover the last complete top-level JSON object (codex chrome case)
    best = None
    depth = 0; start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                frag = text[start:i+1]
                try:
                    _j.loads(frag); best = frag   # keep the LAST that parses
                except Exception:
                    pass
    if best is not None:
        return best
    # no JSON: drop codex noise lines, keep the rest
    noise = ("tokens used", "codex", "user", "warning:", "assistant")
    lines = [l for l in text.splitlines()
             if l.strip() and l.strip().lower() not in noise
             and not l.startswith("warning:")]
    return "\n".join(lines).strip()


def hermes_complete(body, *, timeout=90, spec=None):
    """Run one completion through `hermes -z`, shaped like an OpenRouter response.

    Raises on a non-zero exit or empty output, so the caller's existing `except` treats a
    Hermes failure exactly like an OpenRouter failure -- degrade, never a silent empty draft.
    """
    spec = hermes_spec(spec)
    if spec is None:
        raise RuntimeError("hermes_complete called but the provider is not hermes:*")
    provider, model = spec
    prompt = "\n\n".join(m.get("content", "") for m in body.get("messages", []) if m.get("content"))
    if not prompt:
        raise ValueError("hermes_complete: empty prompt")
    cmd = ["hermes", "-z", prompt, "-m", model, "--provider", provider, "--safe-mode"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"hermes timed out after {timeout}s") from e
    if r.returncode != 0:
        raise RuntimeError(f"hermes exit {r.returncode}: {(r.stderr or r.stdout)[:120]}")
    content = _extract(r.stdout)
    if not content:
        raise RuntimeError(f"hermes returned nothing (stderr: {r.stderr[:80]})")
    return {"choices": [{"message": {"content": content}}]}


# --- CLI subscription backends: draft with claude/grok/codex using the LOGGED-IN CLI ---
# CHORUS_DRAFT_PROVIDER = "cli:claude" | "cli:grok" | "cli:codex"
# Uses the subscription auth already on the machine (the sanctioned client -> no raw-API
# rate limit, $0 marginal). The CLI must be authed where drafting RUNS (laptop today; the box
# once `hermes auth add` / a claude login is done there).
_CLI = {
    "claude": lambda prompt: ["claude", "-p", prompt],
    "grok":   lambda prompt: ["grok", "-p", prompt],
    "codex":  lambda prompt: ["codex", "exec", "--skip-git-repo-check", prompt],
}


def cli_spec(raw=None):
    raw = raw if raw is not None else os.environ.get("CHORUS_DRAFT_PROVIDER", "")
    if not raw.startswith("cli:"):
        return None
    name = raw.split(":", 1)[1]
    if name not in _CLI:
        raise ValueError(f"CHORUS_DRAFT_PROVIDER cli:<name> must be one of {sorted(_CLI)}, got {name!r}")
    return name


def cli_complete(body, *, timeout=120, spec=None):
    """One completion through a logged-in CLI, shaped like an OpenRouter response.

    Raises on failure so the drafter degrades exactly as it does for an OpenRouter error --
    never a silent empty draft. The prompt is a single argv element (no shell), so tweet text
    cannot inject."""
    name = cli_spec(spec)
    if name is None:
        raise RuntimeError("cli_complete called but the provider is not cli:*")
    prompt = "\n\n".join(m.get("content", "") for m in body.get("messages", []) if m.get("content"))
    if not prompt:
        raise ValueError("cli_complete: empty prompt")
    cmd = _CLI[name](prompt)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"{name} cli timed out after {timeout}s") from e
    except FileNotFoundError as e:
        raise RuntimeError(f"{name} cli not installed where drafting runs") from e
    if r.returncode != 0:
        raise RuntimeError(f"{name} cli exit {r.returncode}: {(r.stderr or r.stdout)[:120]}")
    content = _extract(r.stdout)
    if not content:
        raise RuntimeError(f"{name} cli returned nothing")
    return {"choices": [{"message": {"content": content}}]}


def route(body, provider_spec, *, timeout=None):
    """Dispatch one completion to an EXPLICIT provider spec (per-mode routing).

    provider_spec: "cli:<name>" | "hermes:<provider>:<model>". Raises on an unknown/empty spec
    so the caller can fall back to the global/OpenRouter path. Codex gets a longer default
    timeout (its sandboxed exec is slower than grok)."""
    if not provider_spec:
        raise RuntimeError("route: empty provider spec")
    if provider_spec.startswith("cli:"):
        return cli_complete(body, spec=provider_spec, timeout=timeout or (180 if "codex" in provider_spec else 120))
    if provider_spec.startswith("hermes:"):
        return hermes_complete(body, spec=provider_spec, timeout=timeout or 90)
    raise RuntimeError(f"route: unroutable provider spec {provider_spec!r}")
