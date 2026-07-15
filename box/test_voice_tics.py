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

    print(f"VOICE TICS UNIT: {p} passed, {f} failed"); return f
import sys; sys.exit(run())
