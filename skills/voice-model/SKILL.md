---
name: voice-model
description: Synthesize a person's voice/persona from their content; cache it.
---

# voice-model

## Purpose
Produce a reusable voice + tone + topics + "playbook" model for a person (you or a
target), so drafts sound authentic and non-generic.

## Inputs
`person_id` — reads their collected posts/transcripts from memory.

## Uses
`memory.recall` · a synthesis-tier LLM.

## Steps
1. **collect** — pull the person's recent posts, threads, video transcripts from memory.
2. **synthesize** — derive: voice/tone, sentence shape, recurring topics/pillars, do/don't,
   signature moves. Output structured JSON.
3. **version** — key by content hash; only re-run when the underlying content drifts.
4. **store** — write `kind:voice_model` to the person's tag (`chorus:self` or
   `chorus:target:<handle>`). See [docs/memory.md](../../docs/memory.md).

## Output
A cached `voice_model{tone, pillars, dos, donts, examples}` used by opportunity-rank drafts.

## Notes
Cheap and high-value: one-shot then ~$0 steady-state. Feed edit-diffs from the feedback
loop (posted-but-edited) back in to tighten YOUR own voice model over time.
