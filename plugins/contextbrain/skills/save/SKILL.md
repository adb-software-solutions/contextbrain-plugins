---
name: save
description: Save this session to ContextBrain. Use when the user asks to save, record or summarise the session, or after finishing a substantial piece of work.
---

1. Run `git remote get-url origin` in the working repository (skip if not in
   a repository).
2. Call the ContextBrain `save_session` tool once with:
    - title: a few words.
    - summary: concise markdown covering what was done and why, what was
      verified, and anything a fresh session would need. No transcript, no
      restating the obvious; aim for under 300 words.
    - current_state: where the project stands now (replaces the old one).
    - next_steps: the remaining work, most important first.
    - decisions: only real decisions with lasting effect, each with its
      context and consequences.
    - gotchas: traps that cost time and would again (new ones only).
    - working_notes: only if you learned or changed how to run, test, lint,
      commit or deploy here: the whole "Working on this repo" section, short
      and current (it replaces the old one).
    - files: the key files touched.
3. If living docs under docs/ or projects/<slug>/docs/ are now out of date,
   `search` for them and `patch_note` the affected sections.
4. Reply with one line saying what was saved.
