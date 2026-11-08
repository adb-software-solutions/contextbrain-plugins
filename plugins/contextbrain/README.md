# ContextBrain

Connects Claude Code or Codex to [ContextBrain](https://context-brain.com),
shared project memory kept as Markdown in a Git repository you own. It adds
the ContextBrain MCP server, a session-start hook that has the agent resume
the project's context, a stop hook that asks it to save the session after
substantial work, and `resume`, `save` and `doc` skills. You need a
ContextBrain account; after installing, sign in to the MCP server and choose
which Brains the connection can use. Installation, settings and privacy notes
are in the [repository README](https://github.com/adb-software-solutions/contextbrain-plugins#readme).
