# CLAUDE.md — Hackathon Mode

Goal: a working, convincing demo within 1h on ≤ $100 of tokens.

## jury criteria:
Delight: build something surprising (creative), beautiful, or fun with taste.
Aim to get demo working quickly and iterate

## Code principles (Karpathy, tuned for shipping)
Simplicity first. Minimum code for the demo. No single-use abstractions, no unrequested config, no handling of impossible cases. If 200 lines could be 50, rewrite.
Surgical changes. Touch only what the task needs. Don't refactor, reformat or "improve" working code nearby. Remove only orphans you created.
Goal-driven. Turn tasks into checks ("fix bug" → reproduce it, make the repro pass). Loop until the check passes, then stop.
Surface, don't hide. If something is confusing or a simpler route exists, say so in one line, then take the simplest route that demos.
Explicit state. Prefer pure functions and explicit state transitions (return new state, reducers) where cheap; it makes bugs reproducible. Don't fight the framework for it.
Use Fable and Opus 5.5 only for orchestration and complex tasks, use cheaper subagents like sonnet for simpler tasks.

## Testing: test the demo, not the codebase
One smoke/e2e check per demo-path step, written with or before the step.
Unit tests only for tricky logic (parsing, math, scoring, prompt output parsing).
Before any deploy: run the whole demo path. If it broke, fix it before adding anything.
Keep seed/fixture data so the demo is deterministic.