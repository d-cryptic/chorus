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
def hermes_spec():
    """(provider, model) if drafting is configured to go through Hermes, else None."""
    raw = os.environ.get("CHORUS_DRAFT_PROVIDER", "")
    if not raw.startswith("hermes:"):
        return None
    parts = raw.split(":", 2)
    if len(parts) != 3 or not parts[1] or not parts[2]:
        raise ValueError(f"CHORUS_DRAFT_PROVIDER must be hermes:<provider>:<model>, got {raw!r}")
    return parts[1], parts[2]


def _extract(stdout):
    """Hermes echoes only the completion for a -z one-shot with tools off. Belt-and-braces:
    drop any leading 'hermes -z:' notices and trailing blank lines, keep the body."""
    lines = [l for l in stdout.splitlines() if not l.startswith("hermes -z:")]
    return "\n".join(lines).strip()


def hermes_complete(body, *, timeout=90):
    """Run one completion through `hermes -z`, shaped like an OpenRouter response.

    Raises on a non-zero exit or empty output, so the caller's existing `except` treats a
    Hermes failure exactly like an OpenRouter failure -- degrade, never a silent empty draft.
    """
    spec = hermes_spec()
    if spec is None:
        raise RuntimeError("hermes_complete called but CHORUS_DRAFT_PROVIDER is not hermes:*")
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
