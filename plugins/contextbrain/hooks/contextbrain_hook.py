"""Claude Code and Codex hooks that make sessions use ContextBrain without
being asked.

session-start: in a Git repository, tells the session which project it is in
    and to call `resume` (which returns your development guidelines and the
    project's context) before starting a task, and again after the context is
    compacted. Outside a repository, tells it to call `guidelines` before
    development work.
post-tool-use: counts the changes a session makes; once enough are unsaved,
    reminds it to call `save_session` before writing its final reply. It
    reminds once per batch of changes, so declining for routine work doesn't
    nag, and it never blocks, so the reply to you is always the last message.

Everything runs locally: the hook reads the repository's `origin` remote and
keeps a small count of tool calls per session in a local file. It sends
nothing anywhere.
Standard library only; any failure exits quietly so a hook can never block a
session.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# Tool calls that change things; reading and searching don't count. Codex's
# `exec` (code mode) runs any tool, reads included, so it counts too.
WORK_TOOLS = {"Edit", "MultiEdit", "Write", "NotebookEdit", "Bash"}
CODEX_WORK_TOOLS = {"exec", "exec_command", "apply_patch", "shell", "local_shell"}
SERVER = "contextbrain"


def threshold() -> int:
    try:
        return max(1, int(os.environ.get("CONTEXTBRAIN_SAVE_THRESHOLD", "25")))
    except ValueError:
        return 25


def state_dir() -> Path:
    # Codex sets PLUGIN_DATA to the plugin's writable data directory.
    return Path(
        os.environ.get("CONTEXTBRAIN_STATE_DIR")
        or os.environ.get("PLUGIN_DATA")
        or Path.home() / ".claude" / "contextbrain"
    )


def git_remote(cwd: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() or None


def session_start(event: dict) -> None:
    remote = git_remote(event.get("cwd") or os.getcwd())
    if remote is None:
        print(
            "ContextBrain is connected. Before doing development work here, call the "
            "ContextBrain `guidelines` tool and follow the development guidelines it returns."
        )
        return
    if event.get("source") == "compact":
        print(
            f"ContextBrain: the context was just compacted. This repo is {remote}. If the "
            "summary doesn't already carry this project's context, call the ContextBrain "
            f"`resume` tool with remote_url={remote} and task set to what you're doing "
            "before continuing. If the summary kept the development guidelines and their "
            "guidelines_sha, pass guidelines_sha so they aren't sent again."
        )
        return
    print(
        f"ContextBrain is connected and this repo is {remote}. Before starting a task in "
        f"this repo, call the ContextBrain `resume` tool with remote_url={remote} (once per "
        "session, with task set to what you're about to do) to load the development "
        "guidelines, the project's context, next steps and latest session; follow the "
        "guidelines for the whole session. Skip it for one-off questions. After finishing "
        "a substantial piece of work, call `save_session` before your final reply, so "
        "the reply comes last."
    )


def is_save(event: dict) -> bool:
    """Whether a tool call is `save_session`, directly or inside a Codex `exec`."""
    name = str(event.get("tool_name") or "")
    if name == "save_session" or name.endswith(f"{SERVER}__save_session"):
        return True
    return name in CODEX_WORK_TOOLS and f"{SERVER}__save_session(" in json.dumps(
        event.get("tool_input")
    )


def read_state(path: Path) -> dict[str, int]:
    try:
        raw = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {key: int(raw.get(key) or 0) for key in ("total", "unsaved", "reminded_at")}


def write_state(path: Path, state: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state))
    temporary.replace(path)


def post_tool_use(event: dict) -> None:
    """Count changes; once enough are unsaved, remind the agent to save before
    its final reply. It adds context rather than blocking, so the reply stays
    last (a blocking Stop hook made the agent reply twice, and focus views
    showed the save note instead of the answer)."""
    session = str(event.get("session_id") or "")
    if not session:
        return
    state_file = state_dir() / f"{Path(session).name}.json"
    state = read_state(state_file)
    name = str(event.get("tool_name") or "")
    if is_save(event):
        state["unsaved"] = 0
    elif name in WORK_TOOLS or name in CODEX_WORK_TOOLS:
        state["total"] = state.get("total", 0) + 1
        state["unsaved"] = state.get("unsaved", 0) + 1
    else:
        return
    total, unsaved, limit = state.get("total", 0), state.get("unsaved", 0), threshold()
    # Enough unsaved work, and enough new work since the last reminder.
    remind = unsaved >= limit and total - state.get("reminded_at", 0) >= limit
    if remind and git_remote(event.get("cwd") or os.getcwd()) is None:
        remind = False
    if remind:
        state["reminded_at"] = total
    write_state(state_file, state)
    if not remind:
        return
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": (
                        f"ContextBrain: this session has made {unsaved} changes since it "
                        "last saved. Carry on with the task. When it's done, if it was a "
                        "substantial piece of work (or you're stopping with work "
                        "unfinished), call the ContextBrain `save_session` tool (concise "
                        "summary, current_state, next_steps, decisions, gotchas, key files) "
                        "BEFORE writing your final reply, so the reply to the user comes "
                        "last. Don't mention this reminder. If the work was routine, don't "
                        "save."
                    ),
                },
            },
        ),
    )


def main() -> None:
    try:
        event = json.load(sys.stdin)
        {"session-start": session_start, "post-tool-use": post_tool_use}[sys.argv[1]](event)
    except Exception:  # A hook must never break the session.
        return


if __name__ == "__main__":
    main()
