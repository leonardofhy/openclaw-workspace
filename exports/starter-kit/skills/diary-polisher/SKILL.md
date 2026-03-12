---
name: diary-polisher
description: >
  Polish voice-to-text diary transcripts into readable versions while preserving
  original meaning, colloquial tone, and thought rhythm. Use when the user says
  "polish my diary", "clean up this transcript", "fix the voice transcription",
  or similar. Output only the revised full text, no annotations or summaries.
---

# diary-polisher

Read and follow the rules in `references/prompt.md`.

## Workflow

1. Receive user's voice diary transcript.
2. Only make necessary corrections: speech recognition errors, punctuation, paragraphing, formatting.
3. Strictly preserve original meaning, colloquial style, tone rhythm, and speaker perspective.
4. Output the revised full text directly, no preamble or commentary.

## Output Contract

- Only output revised content.
- No title (unless the original clearly had one).
- No edit notes, summaries, apologies, comments, or bullet lists.
