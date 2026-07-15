#!/usr/bin/env python3
"""Content modes for the Chorus drafter: a registry of {brief, model_pref} per mode.

Two orthogonal axes (a subagent design pass established this):
  - SHAPE  = post | thread | longform   (structure; decided by post_gen.classify_shape)
  - MODE   = short | sarcastic | research | longform | thread  (style/fidelity)

longform/thread are shape-modes (their brief IS the deepened shape brief). short/sarcastic/
research are tone-modes whose briefs are shape-aware. Every brief composes with the shared
_TAIL (angle/strength) that post_gen appends, so draft_post() parses them all unchanged.

MODEL ROUTING (the user wants grok + codex used heavily):
  grok  -> punchy, X-native voice: short, sarcastic         (hermes:xai-oauth:grok-4.5)
  codex -> structured, faithful synthesis: research, longform, thread   (cli:codex)
Overridable by env so the box can retarget without a code change.
"""
import os

_GROK_PROVIDER  = os.environ.get("CHORUS_GROK_PROVIDER",  "hermes:xai-oauth:grok-4.5")
_CODEX_PROVIDER = os.environ.get("CHORUS_CODEX_PROVIDER", "cli:codex")


def provider_for(mode: str):
    """Return the CHORUS_DRAFT_PROVIDER-style spec for a mode's preferred model.

    'either'/unknown -> the global CHORUS_DRAFT_PROVIDER (or None -> OpenRouter default),
    so a mode never forces a provider that is not set up."""
    pref = MODES.get(mode, {}).get("model_pref", "either")
    if pref == "grok":
        return _GROK_PROVIDER
    if pref == "codex":
        return _CODEX_PROVIDER
    return os.environ.get("CHORUS_DRAFT_PROVIDER") or None


# --- the briefs. Each is the mode-voice PREAMBLE; post_gen appends the shape JSON contract
#     + _TAIL, so these never duplicate the drafts/thread/longform keys except where the mode
#     IS the shape (longform/thread carry their own required-field contract).

_SHORT_BRIEF = (
    "\nWrite a SHORT post: one sharp single tweet, under 280 chars, that a real person fires "
    "off from their own account.\n"
    "- HOOK IN THE FIRST 5 WORDS. Open on the concrete noun or the claim, never a wind-up. "
    "No 'so', 'honestly', 'turns out', 'imagine', 'remember when'.\n"
    "- ONE idea. If you need a second sentence to justify the first, that's a thread. Cut to "
    "the one line that carries it.\n"
    "- Land a TURN or a STING at the end: a pivot, an understatement, a deadpan consequence. "
    "The last five words do the work.\n"
    "- No throat-clearing, no restating the headline. Say the thing, then stop.\n"
    "- BANNED: 'the real X is' (the real bottleneck/hack/flex/problem) - a template that "
    "survives any subject, not a thought. Name the thing directly.\n"
    "- Lowercase is fine. No hashtags, no sign-off. At most one emoji, at most one slang term.\n"
    "Two drafts must open DIFFERENTLY and take DIFFERENT angles - not one line reworded.\n"
)

_SARCASTIC_BRIEF = (
    "\nMODE: SARCASTIC. Deadpan, ironic. Say the absurd thing flat and let it hang. "
    "Understate; the joke is in the OBSERVATION, not the punctuation. Read it straight or "
    "flip the premise. Keep a REAL point under the irony (delete the sarcasm and a genuine "
    "take should remain). Punch at the premise/pattern, NEVER at a person or small account.\n"
    "BANNED: cruelty, punching down, '/s' or '(sarcasm)', explaining the joke, 'nobody: ... "
    "me:', \"it's giving\", 'tell me X without telling me X', ALL CAPS, '!!!', stacked emoji, "
    "clown/skull emoji pileons. Lowercase, calm, at most one emoji and never as a reaction-honk.\n"
)

_RESEARCH_BRIEF = (
    "\nMODE: RESEARCH. A grounded 'here is what I found' post. Its entire value is that every "
    "specific is TRUE and traceable to the grounding provided. One invented number destroys "
    "the trust this mode exists to build.\n"
    "- Use ONLY facts, numbers, names, dates, quotes that appear VERBATIM in the <link>/"
    "<research>/<corroboration> grounding. If a figure is not written there, you do not have "
    "it and may not state it. A plausible-sounding number is a lie.\n"
    "- Invent NOTHING: no statistics, benchmarks, percentages, versions, dollar amounts, "
    "dates, citations, no 'studies show', no 'reportedly'. If you cannot point to the exact "
    "words in the grounding, cut the claim.\n"
    "- No false precision: round as the source rounds, carry its hedges ('early benchmark', "
    "'one device'); never upgrade a preliminary number into a settled fact.\n"
    "- ATTRIBUTE by name in the grounding's own words (the repo, paper, post, org). If the "
    "grounding is anonymous, say 'a new benchmark', never a fabricated lab name.\n"
    "- THIN GROUNDING -> SAY LESS, confidently. One solid fact -> one tight post around it. "
    "Do not inflate one data point into a thread. Lower strength when grounding is thin.\n"
)

_LONGFORM_BRIEF = (
    "\nThis idea has been judged LONGFORM: ONE argument with depth, not a list. Splitting it "
    "into separate posts would break it. Write that one argument. 400-1500 chars (the 280 "
    "limit does NOT apply, this account has Premium Plus). Longer is not better.\n"
    "- OPEN on the claim: first sentence is the sharpest, most disputable version of your "
    "position, stated flat. No 'let's talk about', no setup sentence before the real one.\n"
    "- ONE throughline: every sentence advances the same argument. If a sentence could be "
    "lifted out and posted alone, it's a thread beat and does not belong here.\n"
    "- EARN the turns: one or two moves where the argument deepens or pivots (an objection "
    "raised and answered, a mechanism explained). Never announce the turn.\n"
    "- LAND by reframing: the last line makes the opening claim mean more than it did. Not a "
    "summary, not a moral, not a question to the audience.\n"
    "BANNED: listicle scaffolding ('here are 3', numbered '1) 2) 3)', bullets - if it's a "
    "list it's a THREAD); explainer throat-clearing ('Here is why:', 'Let me explain'); "
    "LinkedIn cadence ('Agree?', 'Thoughts?', 'Unpopular opinion:'); motivational-poster "
    "landings ('in conclusion', 'at the end of the day'); padding to hit length.\n"
)

_THREAD_BRIEF = (
    "\nThis idea has been judged a THREAD: it has 3+ SEPARABLE beats (siblings, not a chain). "
    "Write the thread. 3-7 segments, each under 280 chars.\n"
    "- SEGMENT 1 IS A HOOK, not a title: stop the scroll and promise the payoff (the tension, "
    "the count, the surprise). A reader who sees only segment 1 should want more AND get a "
    "real thought. Not a summary, not a label.\n"
    "- EACH MIDDLE SEGMENT carries exactly ONE beat and STANDS ALONE: readable out of order, "
    "worth posting by itself. If a segment only makes sense after the previous one, that's "
    "longform, not a thread - merge or cut it.\n"
    "- THE LAST SEGMENT lands the point or CTAs softly (a question, a 'so' that ties the "
    "beats). No 'follow for more', no sign-off.\n"
    "- Each segment opens differently; none restates another; none exists just to hit a "
    "count. 3 real beats beat 6 padded ones.\n"
    "BANNED: the thread emoji anywhere; '1/'/'2/7' numbering; openers like 'a thread:', "
    "'let me explain', 'buckle up', 'let that sink in'; a final recap/tl;dr segment; any "
    "segment that is only a transition.\n"
)

MODES = {
    "short": {
        "name": "short",
        "tagline": "the sharp single-post hot take: one idea, one turn, under 280.",
        "model_pref": "grok",
        "shape": "post",
        "brief": _SHORT_BRIEF,
    },
    "sarcastic": {
        "name": "sarcastic",
        "tagline": "deadpan the absurdity until it screenshots itself. dry wit, never a clown honk.",
        "model_pref": "grok",
        "shape": "post",
        "brief": _SARCASTIC_BRIEF,
    },
    "research": {
        "name": "research",
        "tagline": "here's what I found. real numbers, real sources, zero invention.",
        "model_pref": "codex",
        "shape": "any",
        "brief": _RESEARCH_BRIEF,
    },
    "longform": {
        "name": "longform",
        "tagline": "one argument that would bleed out if you cut it into a thread.",
        "model_pref": "codex",
        "shape": "longform",
        "brief": _LONGFORM_BRIEF,
    },
    "thread": {
        "name": "thread",
        "tagline": "3-7 separable beats, hook first, no filler. the format that compounds.",
        "model_pref": "codex",
        "shape": "thread",
        "brief": _THREAD_BRIEF,
    },
}

# Default mode for a given shape when no tone is chosen.
_SHAPE_DEFAULT_MODE = {"post": "short", "thread": "thread", "longform": "longform"}


def mode_brief(mode: str) -> str:
    """The mode-voice preamble string (composed with the shape JSON contract by post_gen)."""
    return MODES.get(mode, MODES["short"])["brief"]


def default_mode_for_shape(shape: str) -> str:
    return _SHAPE_DEFAULT_MODE.get(shape, "short")


def list_modes() -> list:
    return list(MODES.keys())
