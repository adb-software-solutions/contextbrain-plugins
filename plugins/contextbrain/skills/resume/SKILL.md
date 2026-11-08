---
name: resume
description: Load this project's context from ContextBrain. Use when the user asks to resume, pick up where they left off, or catch up on a project.
---

1. Run `git remote get-url origin` in the working repository.
2. Call the ContextBrain `resume` tool with that remote URL, and `task` set
   to a sentence on what you're about to do if you know. If the guidelines
   from an earlier `resume` are still in your context, pass their
   `guidelines_sha`.
3. If it says several brains are available, ask the user which one to use,
   then `switch_brain` to it and call `resume` again.
4. Follow the development guidelines it starts with for the rest of the
   session; don't summarise them back.
5. Reply with a short briefing: current state, the next steps, and anything
   from the latest session that matters now. Don't repeat the notes verbatim.
6. Use `search` and `read_note` (by heading) for anything else as it comes
   up, rather than loading whole notes up front.
