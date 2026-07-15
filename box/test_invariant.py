"""THE founding invariant: Chorus never posts. The human posts.

This is the property the whole product rests on — it is why there is zero ban risk, and it is
the reason the user accepted a suggest-only tool at all. Until now it was protected by
INTENTION: a runtime guard in ranker.main() and the absence of any write code. Nothing stopped
a future change (or a future me, at 2am, "just to test") from adding one, and no test would
have gone red.

A mutation audit found MIN_SAMPLE unpinned today. This is the same class, with worse stakes:
the failure mode is not a bad insight, it is the user's account.
"""
import os
import re
import glob

# X's write surface. Reading is fine (that is the whole read lane); WRITING is not.
WRITE_SIGNS = [
    (r"api\.twitter\.com/[0-9.]+/statuses/update", "v1.1 tweet"),
    (r"api\.twitter\.com/[0-9.]+/statuses/retweet", "v1.1 retweet"),
    (r"api\.x\.com/[0-9.]+/tweets", "v2 tweets endpoint"),
    (r"api\.twitter\.com/[0-9.]+/tweets", "v2 tweets endpoint"),
    (r"tweepy", "tweepy client"),
    (r"twitter[_-]?oauth|oauth1|OAuth1Session", "X OAuth (a write needs user-context auth)"),
    (r"create_tweet|update_status|post_tweet", "write helper"),
]
# Reading X through the provider is expected; these must NOT be flagged.
ALLOWED = re.compile(r"oauth\.reddit\.com|intent/post|intent/retweet|intent/tweet")


def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    files = (glob.glob(os.path.join(here, "*.py"))
             + glob.glob(os.path.join(root, "dashboard", "src", "*.ts"))
             + glob.glob(os.path.join(root, "dashboard", "web", "src", "**", "*.tsx"), recursive=True))
    # Exclude the TOOLING that must describe a violation in order to hunt it: mutation_audit
    # literally contains an api.x.com POST as an injectable mutant, so scanning it flags the
    # detector itself. Same shape as the em-dash rule needing an em-dash, and the provider
    # test needing the provider's name — third time today. Only PRODUCTION code is in scope.
    SKIP = ("test_", "mutation_audit")
    files = [x for x in files if not any(k in os.path.basename(x) for k in SKIP)]
    chk(len(files) > 15, f"scanning a real file set ({len(files)} files)")

    for pat, what in WRITE_SIGNS:
        hits = []
        for path in files:
            try:
                src = open(path, encoding="utf-8").read()
            except Exception:
                continue
            for line in src.split("\n"):
                if ALLOWED.search(line):
                    continue
                if re.search(pat, line, re.I):
                    hits.append(f"{os.path.basename(path)}: {line.strip()[:60]}")
        chk(not hits, f"NO WRITE LANE: {what} -> {hits[:2]}")

    # the runtime gate must still refuse anything past L1. Read the FILE, not main():
    # the gate lives in cycle(), and inspecting the wrong function silently proves nothing.
    rsrc = open(os.path.join(here, "ranker.py"), encoding="utf-8").read()
    chk('autonomy not in ("L0", "L1")' in rsrc, "autonomy gate still caps at L1")
    chk("suggest-only" in rsrc, "and says why when it refuses")

    # The UI may open X to READ (the target tweet) or to COMPOSE (an intent URL). What it may
    # never do is send. An intent URL cannot post by itself: X shows the composer and the
    # human presses Post. That is the entire safety model, in one property.
    app = open(os.path.join(root, "dashboard", "web", "src", "App.tsx"), encoding="utf-8").read()
    opens = re.findall(r"window\.open\(([^;]{0,140})", app, re.S)
    chk(opens, "the UI does open something (else this test proves nothing)")
    for o in opens:
        composes = "intent" in o
        reads = "status/" in o or "tweet_url" in o
        chk(composes or reads,
            f"window.open only composes (intent) or reads (a tweet URL): {o[:60]}")

    # ---- auth must fail CLOSED. If it fails open, the user's private queue is public. ----
    # The Worker had zero tests. verifyAccess is well built — DEV_OPEN gated by hostname,
    # missing config returns false, a bad JWT returns false, the email must match — but every
    # one of those is one careless edit from failing OPEN, and nothing checked them.
    # Read as text on purpose: no worker deps, no network, no runner. The bug class lives here.
    wsrc = open(os.path.join(root, "dashboard", "src", "index.ts"), encoding="utf-8").read()
    va = wsrc[wsrc.index("async function verifyAccess"):]
    va = va[:va.index("\n}")]

    chk("DEV_OPEN" in va, "the dev escape hatch is in verifyAccess (else this test is aimed wrong)")
    # the escape MUST be gated on hostname, or DEV_OPEN=1 in prod turns auth off entirely
    dev_line = next(l for l in va.split("\n") if "DEV_OPEN" in l and "if" in l)
    # NB: the source holds the REGEX `127\.` (escaped), so a naive `"127." in line` is False
    # and would fail on correct code — my first version did exactly that.
    chk("localhost" in dev_line and "127" in dev_line,
        "DEV_OPEN is gated on localhost — a prod DEV_OPEN=1 must NOT disable auth")
    chk("url.hostname" in dev_line, "...and the gate reads the real hostname")

    # every failure path must return FALSE, never true
    chk("catch" in va and re.search(r"catch\s*\{\s*\n?\s*return false", va),
        "a JWT that fails verification -> false (fail CLOSED)")
    chk(re.search(r"if \(!token \|\| !env\.ACCESS_TEAM_DOMAIN \|\| !env\.ACCESS_AUD\) return false", va),
        "missing token or Access config -> false (a misconfigured deploy is CLOSED, not open)")
    chk("payload.email === env.ALLOWED_EMAIL" in va,
        "a VALID token for the wrong person is still refused")
    chk("issuer: iss" in va and "audience: env.ACCESS_AUD" in va,
        "the JWT is checked against issuer AND audience (a token from another team is not enough)")
    # `return true` may appear ONCE: the localhost dev escape. Anywhere else is a hole.
    chk(va.count("return true") == 1,
        f"exactly ONE `return true` in verifyAccess (found {va.count('return true')})")

    print(f"INVARIANT UNIT: {p} passed, {f} failed"); return f
import sys; sys.exit(run())
