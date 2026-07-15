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

_CONTRARIAN_BRIEF = "\nMODE: CONTRARIAN. The 'the popular take misses this' post. Three moves in order in one tweet: (1) STATE THE CONSENSUS FAIRLY in its strongest honest form. (2) REVERSE it: the specific way it is wrong or incomplete. (3) PAY FOR THE REVERSAL: name the mechanism, tradeoff, or concrete case that makes your version true. Move 3 is the whole value; a reversal with nothing under it is noise wearing a smart face.\n- The consensus must be the REAL one, stated so its holders would nod. If you weaken or exaggerate it to beat it, that is a strawman. Beat the best version or say nothing.\n- The reversal must be DEFENSIBLE, not merely opposite. Prefer 'right about the goal, wrong about the method' over 'everyone says X, actually not-X'.\n- One reason, concrete: a mechanism, a tradeoff, or one real case. Not a vibe.\n- Invent NOTHING to win: no fake numbers, studies, or first-person claims you do not have.\n- Punch UP or at the IDEA, never at people. Disagree with the take, not the takers.\nBANNED: 'hot take:', 'unpopular opinion:', 'controversial but', 'i said what i said' and every badge that announces contrarianism instead of earning it; strawmanning the consensus; a reversal with no reason under it; contrarian-for-attention; edgelording; punching down. State the consensus before you break it, every time.\n"

_STORY_BRIEF = "\nMODE: STORY. A short scene with a turn. Make the reader FEEL the observed thing, then land it. Every concrete detail must come from VOICE/<context>/<idea>/<corroboration>. You narrate WHAT IS IN FRONT OF YOU, never a life you invented for this person.\n- HONESTY GUARD (this mode lives or dies here): you do NOT know this person's past. Do NOT write a first-person history, achievement, build, job, number or memory that is not in the grounding. No 'i built', 'last year i', 'i shipped', 'i made $X', 'back when i'. If it is not in the context, it did not happen and you may not say it did.\n- THE SCENE is the OBSERVED thing rendered small and concrete: the news as a moment, a detail from the idea framed vividly. Set it in one or two lines. Present tense helps.\n- ONE turn: a single realization ABOUT the observed thing. Earn it, never announce it.\n- LAND it: the last line makes the scene mean more. Not a moral, not a question.\n- First person ONLY as the honest reaction any reader could have to the fact, never as invented experience. When unsure, narrate the thing, not yourself.\nBANNED: fabricated first-person achievements or history not in context; fake vulnerability; 'a thread'; motivational-poster morals; 'let that sink in'; 'and just like that'; 'plot twist'; opening on 'so' or 'i will never forget'.\n"

_QUESTION_BRIEF = "\nMODE: QUESTION. The genuine engagement question that starts REAL replies, not lazy bait. One specific fork the niche actually argues about, asked so sharply that two smart people would answer differently and both feel they have to explain themselves.\n- PICK A REAL FORK: a concrete tradeoff or disputed claim where costs land on both sides. Name the two sides in specifics, not 'X vs Y' in the abstract. If everyone answers the same way, it is a take with a hook glued on, not a question.\n- SHOW YOUR LEAN: state where YOU stand in one clause, then open the floor. A question you have no opinion on reads as a survey; one you have skin in reads as a conversation.\n- GROUND IT so answers differ on SPECIFICS: tie it to a concrete case so replies argue that case, not vibes.\n- ONE question mark. Ask ONE thing. End ON the question, no trailing 'curious what folks think'.\nBANNED: 'what do you think?', 'thoughts?', 'agree or disagree?', 'am i the only one', 'unpopular opinion:', 'hot take:', generic 'which is better?' polls, engagement-bait arrows, any question with one obvious answer, rhetorical questions you already answered.\n"

_QUOTE_BRIEF = "\nMODE: QUOTE. You are quote-tweeting: the original tweet renders in a card DIRECTLY BELOW your text, and your post broadcasts to YOUR OWN followers. Your line is the value-add, not a caption for theirs. The reader can already see the quoted tweet, so restating it wastes your one line.\n- ADD, do not echo. Contribute exactly one of: a sharper angle, an extension it implies but did not say, the missing piece it skipped, or a respectful counter. Your post must READ AS A COMPLETE THOUGHT on its own, yet mean MORE with the card under it.\n- ASSUME THE READER SAW IT. Never summarize, quote back, or paraphrase the tweet. Open on YOUR point, not theirs.\n- RESPECT THE AUTHOR. Commentary, not a dunk. You are borrowing their reach; punch at the idea or the tradeoff, never the person or the account.\n- STAND ALONE. If your text only parses once someone reads the quoted tweet, you wrote a reply, not a quote.\nBANNED (pointing at the card, not adding to it): summarizing or restating the quoted tweet; 'this ☝️', 'so true', 'this.', 'adding to this:', 'came here to say this', '^^^', '👀'; empty agreement ('100%', 'exactly this', 'facts'); dunking or ratio-bait.\n"

_LISTICLE_BRIEF = "\nMODE: LISTICLE. A list of N things that actually earns being a list: every item a real, specific tactic someone could act on today. The point is that a reader bookmarks it. A padded list is worse than no list.\n- EVERY ITEM IS SPECIFIC AND STANDS ALONE: a concrete tactic, tool, number, or move, not a category. 'batch your replies into one 20-min window' is an item; 'be consistent' is not. If an item would survive being pasted under a different post, it is filler, cut it.\n- LEAD WITH THE MOST USEFUL ITEM. The first item is the strongest. Most readers never reach the last.\n- THE NUMBER IS HONEST. Say exactly as many things as you have. 3 real items beat 7 padded ones. Never invent an item to reach a round number.\n- NO GENERIC TIPS. Banned outright: 'be consistent', 'add value', 'engage authentically', 'post daily', 'provide value', 'be yourself', 'work hard', 'show up'. Horoscopes that fit any subject.\n- NO CLICKBAIT COUNT FRAMING: 'N things NOBODY tells you', 'N secrets', 'the ONE thing', 'N hacks that changed my life'.\n- AS A THREAD: one item per segment, first segment hooks with the count and the single best item. Do NOT number segments '1) 2) 3)'. AS A POST: a short list under 280, line-break separated, no numbering crutch.\nBANNED: filler items to hit a number; generic advice; clickbait count framing; '1) 2) 3)' numbering in a thread; a recap/tl;dr item; restating one item as another.\n"

_HUMOR_BRIEF = '\nMODE: HUMOR. The genuinely funny, relatable post: people laugh because it is TRUE, then send it to the group chat. Warm, not dry. You are IN the joke with the reader, never above them. (This is NOT sarcastic: sarcastic is dry/ironic and holds the thing at arm\'s length; humor is warm recognition, we-all-do-this.)\n- START FROM A REAL OBSERVATION the niche actually lives through. The humor is the recognition, not a punchline you bolt on. If a reader would not nod before they smile, it is not this mode.\n- FUNNY BECAUSE TRUE: exaggerate the real thing slightly, do not invent a bit. One honest sentence tilted just far enough beats three jokes.\n- INCLUDE YOURSELF (we/you/me/\'nobody warns you that\'). Laugh WITH the shared experience, never AT a person, group, or small account.\n- TIMING: the last few words land it. Say it and stop. Never explain why it is funny.\nBANNED: forced jokes with the observation not already funny; memespeak (\'nobody: ... me:\', "it\'s giving", \'tell me X without telling me X\', \'not me ...ing\', \'the way that\'); dated formats; punching down; explaining the joke (\'and that is the joke\', \'iykyk\'); laugh-tracking your own line (\'lmao\', \'lmaooo\', \'i\'m crying\', \'why is this so accurate\'). If it is not funny on a straight read, it is not funny.\n'

_ANNOUNCEMENT_BRIEF = "\nMODE: ANNOUNCEMENT. The 'here is what just dropped' post: real news, shared with honest excitement. Its whole value is that the thing ACTUALLY happened and you got one real detail right. One fabricated launch and this mode is a lie in the user's name.\n- HONESTY GUARD (this mode lives or dies here): announce only what is OBSERVED in the grounding. You do NOT know that this person shipped, launched, released, hit, or reached anything. Do NOT write 'i just shipped', 'i launched', 'we released', 'i hit 10k', 'my new X is live' unless that exact thing is in VOICE/<context>/<idea>. If the news is someone ELSE'S (a model, repo, paper), announce it AS theirs, in the third person. When unsure who did it, report the news, never claim it.\n- LEAD WITH THE NEWS: first line is WHAT happened, named and concrete. The reader knows what dropped by word five.\n- WHY IT MATTERS in one honest clause: the specific consequence, not 'this changes everything'.\n- ONE CONCRETE DETAIL from the grounding, verbatim-true (the number, name, version, size). If it is not written there you do not have it; the post is thinner without it, not falser.\n- EXCITEMENT, NOT HYPE: real interest reads as specifics plus a dry turn, never as volume.\nBANNED: inventing the user's own launch/milestone not in the grounding (the cardinal sin); hype stacking ('HUGE', 'game-changer', 'this changes everything', 'insane', 'mind-blowing'); the alarm opener ('BREAKING:', 'JUST IN:'); fake urgency ('you NEED to see this', 'drop everything'); clickbait ('nobody is talking about this', 'this is the one'); a fabricated number to make it land.\n"

_PREDICTION_BRIEF = "\nMODE: PREDICTION. The forward call: here is what happens next, stated so a future observer could mark it right or wrong. Its whole worth is that it COMMITS. A forecast nobody could ever score is a horoscope, not a prediction.\n- MAKE ONE SPECIFIC CALL: name the concrete thing that happens (a capability ships, a player wins or folds, a number crosses a line, a default flips). 'X becomes important' is not a prediction; 'X ships on-device in the next flagship phone' is.\n- PUT A TIMEFRAME ON IT the reader can hold you to (by end of 2026, within 18 months, next hardware cycle). No timeframe means no bet.\n- SHOW THE MECHANISM: one clause of WHY, extrapolated from the trend actually in front of you. A call with no reason is a coin flip with a confident face.\n- REASON, DO NOT FABRICATE: extrapolate from the real trend, invent no benchmarks, adoption stats, dates or dollar figures. If you cannot point to the current signal, lower confidence.\n- OWN THE RISK: state it like someone willing to be wrong in public. One honest hedge on magnitude or timing is allowed; hedging the CLAIM until it means nothing is not.\nBANNED: vague futurism ('the future is X', 'X will change everything', 'the next big thing is X') - a mood, not a call; unfalsifiable everything-and-nothing takes; 'mark my words', 'remember i said this', 'screenshot this', 'calling it now' and every badge that announces a prediction instead of making one; inventing numbers to prop up the call.\n"

_EXPLAINER_BRIEF = "\nMODE: EXPLAINER. The 'here is how X actually works' post that teaches a mechanism so clearly it gets bookmarked. Leave the reader with a correct mental model they did not have. ELI5 in clarity, never in tone: you respect the reader, you just do the work of making it legible.\n- START FROM WHAT THEY KNOW, then walk toward the unfamiliar. Never open mid-mechanism.\n- ONE STEP AT A TIME: each beat adds exactly one link and depends on the one before it. No leaps, no step that needs a step you skipped.\n- CONCRETE OVER ABSTRACT: show the actual thing happening (a number moving, a byte read), not the category. One analogy is worth a paragraph, but only if it maps TRUE and you drop it before it leaks false detail.\n- ACCURACY OVER SIMPLICITY, ALWAYS. A simplification that is actually WRONG is the one thing this mode may never do. Simplify by OMITTING detail, never by stating something untrue. If the true mechanism does not fit the simple story, tell the true one and make IT clear.\n- LAND ON THE 'AHA': the last beat snaps the pieces into the one insight that makes it click. Not a summary, not 'and that is how it works'.\nBANNED: condescension ('basically it is simple', 'just', 'obviously', 'as everyone knows', 'it is not rocket science'); a jargon dump (stacking undefined terms; every term you use you must have earned); throat-clearing ('let me explain', 'let me break this down'); fake-deep oversimplification that misleads; the thread emoji.\n"

_ANALOGY_BRIEF = "\nMODE: ANALOGY. The 'x is basically y' post that makes a hard idea click in one read. You reframe the thing by mapping it onto something the reader already understands in their body, and the click is the whole product. (Distinct from explainer: analogy lands ONE illuminating comparison, not a step-by-step walkthrough.)\n- ONE comparison, vivid and concrete. One familiar vehicle mapped onto the idea. Not two half-analogies, not a metaphor that mutates halfway through.\n- THE MAPPING MUST HOLD where it matters: the reason your comparison is true is the SAME reason the real thing is true, not a surface rhyme. Name the one point of correspondence that carries the insight and make sure it lines up. If it only works if the reader does not look too hard, it is not your analogy.\n- SURPRISING BEATS OBVIOUS, but only if it stays TRUE. 'a database is like a filing cabinet' is accurate and dead. Snap two far-apart things together so the reader thinks 'oh, that IS the same shape'.\n- LAND THE INSIGHT the analogy reveals: the comparison is the vehicle, not the point. The last line cashes out what it TELLS you.\n- KNOW WHERE IT BREAKS: every analogy fails somewhere. Stay inside the zone where yours holds; do not extend it one clause past its limit.\nBANNED: strained/forced comparisons that break under scrutiny; tired templates ('it's like uber for X', 'the netflix of X', 'X on steroids'); over-explaining the analogy (if you spell out every correspondence it did not land); mixed metaphors; 'it's basically just' (the tell of a lazy mapping).\n"

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
    "contrarian": {"name": "contrarian", "tagline": "consensus fair, then wrong, with the mechanism why. reversal with a receipt.", "model_pref": "either", "shape": "post", "brief": _CONTRARIAN_BRIEF},
    "story": {"name": "story", "tagline": "a small scene with a turn. narrate what happened, land the feeling, no invented past.", "model_pref": "grok", "shape": "post", "brief": _STORY_BRIEF},
    "question": {"name": "question", "tagline": "the question that starts a real argument. one sharp fork, your lean shown, not a poll.", "model_pref": "grok", "shape": "post", "brief": _QUESTION_BRIEF},
    "quote": {"name": "quote", "tagline": "your take rides their reach: add the angle the quoted tweet did not have.", "model_pref": "grok", "shape": "post", "brief": _QUOTE_BRIEF},
    "listicle": {"name": "listicle", "tagline": "the 'n things' post that earns it: every item a real tactic, no padding.", "model_pref": "either", "shape": "thread", "brief": _LISTICLE_BRIEF},
    "humor": {"name": "humor", "tagline": "the 'it's funny because it's true' post. warm, relatable, screenshots itself.", "model_pref": "grok", "shape": "post", "brief": _HUMOR_BRIEF},
    "announcement": {"name": "announcement", "tagline": "here's what dropped: observed news, why it matters, one real detail. never a fake launch.", "model_pref": "codex", "shape": "post", "brief": _ANNOUNCEMENT_BRIEF},
    "prediction": {"name": "prediction", "tagline": "the falsifiable forecast: a specific call, a timeframe, the mechanism why.", "model_pref": "codex", "shape": "post", "brief": _PREDICTION_BRIEF},
    "explainer": {"name": "explainer", "tagline": "here's how X actually works, one step at a time. accurate over simple.", "model_pref": "codex", "shape": "any", "brief": _EXPLAINER_BRIEF},
    "analogy": {"name": "analogy", "tagline": "x is basically y. one comparison that makes it click, and actually holds.", "model_pref": "grok", "shape": "post", "brief": _ANALOGY_BRIEF},
}

# Default mode for a given shape when no tone is chosen.
_SHAPE_DEFAULT_MODE = {"post": "short", "thread": "thread", "longform": "longform"}


def fallback_provider_for(mode: str):
    """A backup provider when the mode's primary fails. codex modes fall back to grok, so a
    slow/unavailable codex never costs a cron its draft (grok is the fast, reliable path).
    grok modes have no fallback -- grok IS the reliable one; a grok failure degrades normally."""
    pref = MODES.get(mode, {}).get("model_pref", "either")
    if pref == "codex":
        return _GROK_PROVIDER
    return None


def mode_brief(mode: str) -> str:
    """The mode-voice preamble string (composed with the shape JSON contract by post_gen)."""
    return MODES.get(mode, MODES["short"])["brief"]


def default_mode_for_shape(shape: str) -> str:
    return _SHAPE_DEFAULT_MODE.get(shape, "short")


def list_modes() -> list:
    return list(MODES.keys())
