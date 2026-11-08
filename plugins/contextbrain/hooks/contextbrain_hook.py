"""Claude Code and Codex hooks that make sessions use ContextBrain without
being asked.

session-start: in a Git repository, tells the session which project it is in
    and to call `resume` (which returns your development guidelines and the
    project's context) before starting a task, and again after the context is
    compacted. Outside a repository, tells it to call `guidelines` before
    development work.
stop: once a session has made enough changes since it last saved, asks it to
    call `save_session` before finishing. It asks once per batch of changes,
    so declining for routine work doesn't loop.

Everything runs locally: the hook reads the repository's `origin` remote and
counts tool calls in the local session transcript. It sends nothing anywhere.
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
CODEX_CALLS = {"function_call", "custom_tool_call", "local_shell_call"}
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
        "a substantial piece of work, call `save_session`."
    )


def _is_save(name: str, code: str = "") -> bool:
    return (
        name.endswith(f"{SERVER}__save_session")
        or name == "save_session"
        or f"{SERVER}__save_session(" in code
    )


def tool_calls(entry: dict) -> list[tuple[str, bool]]:
    """(name, is_save) for each tool call in a Claude Code or Codex transcript line."""
    if entry.get("type") == "assistant":
        content = (entry.get("message") or {}).get("content")
        if not isinstance(content, list):
            return []
        names = [
            str(item.get("name", ""))
            for item in content
            if isinstance(item, dict) and item.get("type") == "tool_use"
        ]
        return [(name, _is_save(name)) for name in names]
    # Codex rollout: MCP tools are function calls named `save_session` in an
    # `mcp__contextbrain` namespace, or `tools.mcp__contextbrain__save_session(...)`
    # inside a code-mode `exec`.
    payload = entry.get("payload")
    if entry.get("type") != "response_item" or not isinstance(payload, dict):
        return []
    if payload.get("type") not in CODEX_CALLS:
        return []
    name = str(payload.get("name") or "local_shell")
    return [(name, _is_save(name, str(payload.get("input") or "")))]


def work_counts(transcript: Path) -> tuple[int, int]:
    """Changes made in the whole session, and since the last `save_session`."""
    total = since_save = 0
    with transcript.open(encoding="utf-8") as lines:
        for line in lines:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if not isinstance(entry, dict):
                continue
            for name, is_save in tool_calls(entry):
                if is_save:
                    since_save = 0
                elif name in WORK_TOOLS or name in CODEX_WORK_TOOLS:
                    total += 1
                    since_save += 1
    return total, since_save


def stop(event: dict) -> None:
    # Already continuing because of a Stop hook: never ask twice in a row.
    if event.get("stop_hook_active"):
        return
    transcript = event.get("transcript_path")
    session = str(event.get("session_id") or "")
    if not transcript or not session or git_remote(event.get("cwd") or os.getcwd()) is None:
        return
    total, work = work_counts(Path(transcript))
    limit = threshold()
    folder = state_dir()
    state_file = folder / f"{Path(session).name}.json"
    try:
        asked_at = int(json.loads(state_file.read_text()).get("asked_at", 0))
    except (OSError, ValueError):
        asked_at = 0
    # Enough unsaved work, and enough new work since we last asked.
    if work < limit or total - asked_at < limit:
        return
    folder.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({"asked_at": total}))
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": (
                    f"ContextBrain: this session has made {work} changes since it last "
                    "saved. If that completed a substantial piece of work, or you are "
                    "stopping with work unfinished, call the ContextBrain `save_session` "
                    "tool now (concise summary, current_state, next_steps, decisions, "
                    "gotchas, key files), then finish your reply. If the work was routine, "
                    "just finish."
                ),
            },
        ),
    )


def main() -> None:
    try:
        event = json.load(sys.stdin)
        {"session-start": session_start, "stop": stop}[sys.argv[1]](event)
    except Exception:  # A hook must never break the session.
        return


if __name__ == "__main__":
    main()
