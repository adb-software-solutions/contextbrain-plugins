---
name: doc
description: Write or update living documentation in ContextBrain. Use when the user asks to document how something works, or after learning how a server, service or deploy works that a later session would otherwise have to rediscover.
---

1. `search` the brain for existing notes on the topic first; update rather
   than duplicate.
2. Shared knowledge (infrastructure, services, runbooks) goes under docs/;
   knowledge about one repository goes under projects/<slug>/docs/.
3. For an existing note, `read_note` with `outline_only`, then `patch_note`
   the sections that changed. For a new note, `write_note` with frontmatter
   (title, tags) and clear headings so later sessions can read single
   sections.
4. Write for a future reader with no context: what it is, how it works, how
   to operate it, and the gotchas. Commands in fenced blocks. Never write
   secrets; say where a secret lives instead.
5. Reply with the paths you changed.
