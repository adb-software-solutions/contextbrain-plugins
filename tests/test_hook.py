"""Tests for the session hooks. Run with: python3 -m unittest discover tests"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "plugins" / "contextbrain" / "hooks" / "contextbrain_hook.py"


def run(command: str, event: dict, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        [sys.executable, str(HOOK), command],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
        check=True,
    )
    return result.stdout


def repo(path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(
        ["git", "-C", str(path), "remote", "add", "origin", "https://example.com/acme/app.git"],
        check=True,
    )
    return path


def claude_edit() -> dict:
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Edit"}]}}


def claude_save() -> dict:
    name = "mcp__plugin_contextbrain_contextbrain__save_session"
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name}]}}


def codex_call(name: str, code: str = "") -> dict:
    return {"type": "response_item", "payload": {"type": "function_call", "name": name, "input": code}}


class SessionStart(unittest.TestCase):
    def test_in_a_repository_it_asks_for_resume_with_the_remote(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = run("session-start", {"cwd": str(repo(Path(tmp)))})
        self.assertIn("`resume`", out)
        self.assertIn("remote_url=https://example.com/acme/app.git", out)

    def test_after_compaction_it_asks_again(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = run("session-start", {"cwd": str(repo(Path(tmp))), "source": "compact"})
        self.assertIn("compacted", out)

    def test_outside_a_repository_it_asks_for_guidelines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = run("session-start", {"cwd": tmp})
        self.assertIn("`guidelines`", out)

    def test_bad_input_never_fails(self) -> None:
        result = subprocess.run(
            [sys.executable, str(HOOK), "session-start"], input="not json", capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)


class Stop(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cwd = repo(self.root / "app")
        self.env = {"CONTEXTBRAIN_STATE_DIR": str(self.root / "state"), "CONTEXTBRAIN_SAVE_THRESHOLD": "3"}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def stop(self, entries: list[dict], **extra: object) -> str:
        transcript = self.root / "t.jsonl"
        transcript.write_text("\n".join(json.dumps(e) for e in entries))
        event = {"cwd": str(self.cwd), "session_id": "s1", "transcript_path": str(transcript), **extra}
        return run("stop", event, self.env)

    def test_asks_to_save_after_enough_work_then_waits_for_more(self) -> None:
        self.assertEqual(self.stop([claude_edit()] * 2), "")
        asked = json.loads(self.stop([claude_edit()] * 3))
        self.assertEqual(asked["decision"], "block")
        self.assertIn("save_session", asked["reason"])
        self.assertEqual(self.stop([claude_edit()] * 4), "")
        self.assertNotEqual(self.stop([claude_edit()] * 6), "")

    def test_saving_resets_the_count(self) -> None:
        self.assertEqual(self.stop([claude_edit()] * 5 + [claude_save()]), "")

    def test_codex_work_and_saves_count(self) -> None:
        work = [codex_call("apply_patch")] * 3
        self.assertNotEqual(self.stop(work), "")
        self.tearDown()
        self.setUp()
        saved = work + [codex_call("exec", "await tools.mcp__contextbrain__save_session({})")]
        self.assertEqual(self.stop(saved), "")

    def test_never_asks_twice_in_a_row(self) -> None:
        self.assertEqual(self.stop([claude_edit()] * 5, stop_hook_active=True), "")


if __name__ == "__main__":
    unittest.main()
