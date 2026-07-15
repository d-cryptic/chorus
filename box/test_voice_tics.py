"""A phrase tic is the fastest way for an account to read as a bot.

Measured on the real queue: "the most charitable reading is" opened 14 of 174 drafts (8%) —
the single most common opener by 7x. It came from style_mine, which extracted it as a "hook
that works" and stored a fill-in-the-blank TEMPLATE in chorus:niche. The drafter was then
told these are hooks that work, so it parroted the phrase.

style_mine's own docstring says "we extract PATTERNS, never content" — but its prompt ASKED
for "each a short template", and its CRITICAL rule forbade only claims/numbers/opinions/
topics, never WORDING. The model complied perfectly and the damage happened anyway. This is
the same class as "ngl opened 4/5 drafts".
"""
import inspect
import style_mine as S, ranker as R


def run():
    p = f = 0
    def chk(c, l):
        nonlocal p, f
        if c: p += 1
        else: print("  ❌", l); f += 1

    # --- the extractor must not ASK for templates ---
    pr = S.build_prompt([{"text": "x", "like_count": 9}])
    chk("each a short template" not in pr, "no longer requests templates")
    chk("WORDING" in pr, "the boundary now names wording, not just claims/numbers/topics")
    chk("no [brackets]" in pr or "no templates" in pr, "fill-in-the-blank shapes are refused")
    chk("The most charitable reading is that [observation]." in pr,
        "shows the real leaked template as the BAD example (concrete beats abstract)")
    chk("opens by granting the opposing view" in pr, "and shows the GOOD form: a described move")

    # --- the drafter must refuse to parrot even if a bad pattern slips through ---
    src = inspect.getsource(R.llm_draft)
    chk("OR THEIR" in src and "WORDING" in src, "drafter forbids borrowed wording")
    chk("execute the move in your OWN words" in src, "patterns are moves, not scripts")
    chk("take the idea and throw the phrasing away" in src,
        "a template-shaped pattern is treated as a bug, not an instruction")

    # --- prompts must obey the rules they state (they kept failing this) ---
    for name, text in (("drafter", src), ("style_mine", pr)):
        offenders = [l for l in text.split("\n")
                     if ("—" in l or "–" in l) and "em-dash" not in l and l.strip().startswith('"')]
        chk(not offenders, f"{name} prompt does not itself use the em-dash it bans")

    # --- do not ban the user's ACTUAL voice on taste -------------------------------------
    # I wrote "Do not open with 'ngl' - it is a crutch" and "NEVER ... 🔥🚀💯" from my own
    # aesthetic judgement ("so it stays classy"). Then I read what the user actually posts:
    #   ngl opens 3 of their 10 posted replies
    #   a single 🔥/🚀 appears in 3 of 10 posted — including their BEST performer
    #       ("my laptop sounds like a jet engine ... 🔥", 4 likes / 80 views)
    # The original bug was FREQUENCY (ngl opened 4 of 5 drafts = 80%), not the word. Banning
    # it outright made the voice LESS like the user, which is the opposite of the job.
    chk("Do not open with 'ngl'" not in src, "does not ban a word the user demonstrably uses")
    chk("ngl' IS in this person's voice" in src, "ngl is treated as voice, with a frequency cap")
    chk("never in more than one draft of a set" in src, "the cap is on FREQUENCY, which was the real bug")
    chk("never STACKED" in src, "stacked emoji (the actual hype tell) stay banned")
    chk("'bro'" in src and "'goated'" in src, "genuinely off-voice slang stays banned")
    # the same over-correction was in post_gen
    import post_gen as PG
    psrc = PG.build_prompt({"source": "hn", "title": "t", "url": ""}, "v", (), "", ["ai"])
    chk("Do not open with 'ngl'" not in psrc, "post_gen does not ban ngl either")
    chk("never stacked" in psrc, "post_gen still bans stacking")

    # --- the scrub guarantee covered 18 drafts and missed 156 ---------------------------
    # I banned em-dashes in the prompt, then said "prompt adherence is a request; scrub is a
    # guarantee" — and wired scrub into post_gen ONLY. Measured across every draft ever
    # generated: 25% of REPLIES and 39% of QUOTES carry a machine tell (em/en dash, smart
    # quote, ellipsis), including one the user POSTED ("the skill set here is clutch-inference").
    # Replies and quotes are made by ranker.llm_draft, which never scrubbed.
    import ranker as R2, post_gen as P2
    chk(R2.scrub is P2.scrub, "ONE scrub, shared — two copies drift apart silently")
    chk("scrub(x)" in inspect.getsource(R2.llm_draft),
        "ranker.llm_draft scrubs its drafts (replies + quotes: 156 of 174 drafts)")
    chk("scrub(x)" in inspect.getsource(P2.draft_post), "post_gen still scrubs its own")
    # and the scrub must actually kill the tells that were measured in real drafts
    for raw, why in (("clutch\u2014inference", "the em-dash the user actually posted"),
                     ("a\u2013b", "en-dash"),
                     ("it\u2019s", "smart apostrophe"),
                     ("wait\u2026", "ellipsis")):
        out = R2.scrub(raw)
        chk(not any(c in out for c in "\u2014\u2013\u2019\u2026"), f"scrub kills {why}")

    # --- the REAL invariant: no draft reaches the user unscrubbed -----------------------
    # 4 of 6 prompts still contain the em-dash they ban (the judge prompt, style_mine,
    # session_mine). I am NOT fixing those, and the reason is worth writing down: a prompt's
    # em-dash can only NUDGE the model, and scrub kills it at the OUTPUT. Traced every path
    # that produces user-visible text:
    #   ranker.llm_draft   -> drafts                      scrubbed
    #   post_gen.draft_post-> drafts/thread/longform      scrubbed
    #   session_mine -> capture -> post_gen.draft_post    scrubbed (the draft is what ships)
    #   style_mine   -> chorus:niche -> drafter's PROMPT  its output is scrubbed
    #   generate.build_judge_prompt -> JSON scores + a "why" that is never published
    # So prompt prose that never reaches the user is tidying, not a fix. What matters is that
    # EVERY producer of visible text scrubs — this catches a NEW path that forgets to.
    import ranker as R3, post_gen as P3
    producers = [("ranker.llm_draft", R3.llm_draft), ("post_gen.draft_post", P3.draft_post)]
    for name, fn in producers:
        src = inspect.getsource(fn)
        returns_drafts = '"drafts"' in src
        chk(not returns_drafts or "scrub(" in src,
            f"{name} returns drafts, so it MUST scrub them")
    # a producer that returns text but never scrubs is the bug this pins
    chk(len(producers) == 2,
        "exactly 2 producers of user-visible drafts (add one, and it must scrub too)")

    print(f"VOICE TICS UNIT: {p} passed, {f} failed"); return f
import sys; sys.exit(run())
