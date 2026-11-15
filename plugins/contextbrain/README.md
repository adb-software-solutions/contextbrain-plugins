# ContextBrain

Makes Claude Code or Codex use [ContextBrain](https://context-brain.com),
shared project memory kept as Markdown in a Git repository you own. It adds a
session-start hook that has the agent resume the project's context, a
reminder to save the session before its final reply after substantial work,
and `resume`, `save` and `doc` skills. It doesn't connect ContextBrain
itself: each Brain has its own MCP URL, which you add separately (the Brains
page on ContextBrain shows the commands). Installation, settings and privacy
notes are in the [repository README](https://github.com/adb-software-solutions/contextbrain-plugins#readme).
