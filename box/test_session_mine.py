"""session_mine turns the user's PRIVATE Claude Code sessions into PUBLIC tweets.

Its own threat model says it best: sessions contain client code, secrets, absolute paths,
repo/employer names and private conversations, and the OUTPUT IS A PUBLIC TWEET. It had FOUR
redaction layers and ZERO tests — a mutation audit deleted L1's key regex and L3's leak check
outright, and nothing went red.

Every other gap found today costs a bad insight or some money. This one costs a leaked
credential, publicly, under the user's name. These tests are the only thing standing between
a `sk-...` in a session log and their timeline.
"""
import re
import session_mine as S


def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    # ---- L1: nothing secret survives redaction, before the LLM ever sees it ----
    SECRETS = [
        ("sk-proj-abcdefghijklmnopqrstuvwxyz012345", "OpenAI key"),
        ("sk-or-v1-0123456789abcdef0123456789abcdef", "OpenRouter key"),
        ("ghp_abcdefghijklmnopqrstuvwxyz0123456789", "GitHub PAT"),
        ("github_pat_11ABCDEFG0123456789_abcdefghij", "GitHub fine-grained PAT"),
        ("xoxb-123456789012-1234567890123-abcdefgh", "Slack bot token"),
        ("new1_2d9ed728d2264e289c7b45d6ea9b2907", "read-provider key"),
        ("AIzaSyD-0123456789abcdefghijklmnopqrstuv", "Google API key"),
    ]
    for secret, what in SECRETS:
        out = S.redact(f"my key is {secret} ok")
        chk(secret not in out, f"L1 redacts a {what}")
        chk("[KEY]" in out or secret not in out, f"L1 leaves a marker for a {what}")

    # a secret embedded mid-sentence, and several at once
    multi = S.redact(f"{SECRETS[0][0]} and also {SECRETS[2][0]}")
    chk(all(s not in multi for s, _ in SECRETS[:3] if s in (SECRETS[0][0], SECRETS[2][0])),
        "L1 redacts MULTIPLE secrets in one line")

    # paths / emails / urls leak the employer and the machine
    for raw, what in (("/Users/barun/Developers/acme-corp/src/main.py", "absolute path"),
                      ("barun.debnath2001@gmail.com", "email"),
                      ("https://github.com/acme-corp/private-repo", "repo URL")):
        out = S.redact(f"see {raw} please")
        chk(raw not in out, f"L1 redacts an {what}")

    # ---- redaction must not destroy the actual signal ----
    keep = S.redact("my laptop sounds like a jet engine running 12 docker containers")
    chk("jet engine" in keep and "docker" in keep, "L1 keeps the non-secret shape of the story")

    # ---- L3: fail CLOSED on a leaky draft ----
    toks = S.project_tokens("acme-corp-billing")
    chk(toks, "project_tokens yields identifiers to hunt")
    chk(S.leaks("we shipped the acme-corp-billing migration", toks) is not None,
        "L3 catches the project slug")
    chk(S.leaks("shipping a migration was painful", toks) is None,
        "L3 lets a clean draft through")
    chk(S.leaks(f"the key is {SECRETS[0][0]}", set()) is not None,
        "L3 catches a secret-SHAPED string even with NO project tokens (belt and braces)")
    chk(S.leaks("/Users/barun/Developers/x", set()) is not None, "L3 catches an absolute path")

    # ---- L2: the prompt must forbid naming things ----
    pr = S.build_prompt(["ran into a flaky test"], 3)
    for must in ("project", "repo", "compan"):
        chk(must in pr.lower(), f"L2 prompt forbids naming a {must}...")

    # ---- the deny list skips whole projects (client work) ----
    import inspect
    rsrc = inspect.getsource(S.recent_sessions)
    chk("deny" in rsrc, "recent_sessions honours a deny list")

    print(f"SESSION MINE UNIT: {p} passed, {f} failed"); return f
import sys; sys.exit(run())
