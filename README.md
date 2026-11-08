# ContextBrain plugins for Claude Code and Codex

[ContextBrain](https://context-brain.com) is shared project memory for you and
your AI agents: project context, decisions, runbooks and session notes, kept as
Markdown in a Git repository you own.

This plugin connects Claude Code or Codex to ContextBrain and adds:

- **The ContextBrain MCP server**, so your agent can search, read and save
  knowledge in the Brains you've authorised.
- **A session-start hook** that tells the agent which project it is in and to
  `resume` from ContextBrain before starting work, and again after the
  context is compacted.
- **A stop hook** that, after a substantial amount of work, asks the agent to
  `save_session` before it finishes. It asks once per batch of changes, so
  routine work isn't interrupted.
- **Skills**: `resume`, `save` and `doc`.

You need a ContextBrain account with at least one Brain.
[Start a trial](https://context-brain.com/pricing).

## Claude Code

```sh
claude plugin marketplace add adb-software-solutions/contextbrain-plugins
claude plugin install contextbrain@contextbrain
```

Or inside Claude Code:

```
/plugin marketplace add adb-software-solutions/contextbrain-plugins
/plugin install contextbrain@contextbrain
```

Then run `/mcp`, choose **contextbrain** and sign in. You'll choose which
Brains the connection can use.

## Codex

```sh
codex plugin marketplace add adb-software-solutions/contextbrain-plugins
codex plugin add contextbrain@contextbrain
```

Codex asks you to sign in to ContextBrain when the plugin is installed.

## Without the plugin

The MCP server works on its own if you'd rather not install hooks:

```sh
claude mcp add --transport http contextbrain https://context-brain.com/mcp
codex mcp add contextbrain --url https://context-brain.com/mcp
```

## Settings

| Variable                      | Default                         | What it does                                            |
| ----------------------------- | ------------------------------- | ------------------------------------------------------- |
| `CONTEXTBRAIN_SAVE_THRESHOLD` | `25`                            | Changes (edits, writes, commands) before asking to save |
| `CONTEXTBRAIN_MCP_URL`        | `https://context-brain.com/mcp` | Claude Code only: the MCP server to connect to          |
| `CONTEXTBRAIN_STATE_DIR`      | the plugin's data folder        | Where the stop hook remembers when it last asked        |

## Privacy

The hooks run on your machine. They read the repository's `origin` remote and
count tool calls in the local session transcript; they send nothing anywhere.
Only your agent talks to ContextBrain, through the MCP connection you
authorise. See the [privacy policy](https://context-brain.com/privacy).

## Development

The hooks use the Python standard library only.

```sh
python3 -m unittest discover tests
```

Bump `version` in both `plugins/contextbrain/plugin.json` and
`plugins/contextbrain/.claude-plugin/plugin.json` for each release.

## Support

Email [support@context-brain.com](mailto:support@context-brain.com), or open an
issue here. Never include passwords, tokens or private keys.

## Licence

[MIT](LICENSE)
