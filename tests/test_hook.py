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


class PostToolUse(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cwd = repo(self.root / "app")
        self.env = {"CONTEXTBRAIN_STATE_DIR": str(self.root / "state"), "CONTEXTBRAIN_SAVE_THRESHOLD": "3"}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def call(self, name: str, tool_input: object = None, cwd: Path | None = None) -> str:
        event = {
            "cwd": str(cwd or self.cwd),
            "session_id": "s1",
            "hook_event_name": "PostToolUse",
            "tool_name": name,
            "tool_input": tool_input or {},
        }
        return run("post-tool-use", event, self.env)

    def reminder(self, out: str) -> str:
        data = json.loads(out)
        self.assertNotIn("decision", data)  # Never blocks.
        self.assertEqual(data["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        return data["hookSpecificOutput"]["additionalContext"]

    def test_reminds_once_per_batch_before_the_final_reply(self) -> None:
        outs = [self.call("Edit") for _ in range(5)]
        self.assertEqual(outs[:2], ["", ""])
        self.assertIn("BEFORE writing your final reply", self.reminder(outs[2]))
        self.assertEqual(outs[3:], ["", ""])
        self.assertIn("6 changes", self.reminder(self.call("Bash")))

    def test_reads_dont_count(self) -> None:
        for _ in range(5):
            self.assertEqual(self.call("Read"), "")
            self.assertEqual(self.call("mcp__plugin_contextbrain_contextbrain__search"), "")

    def test_saving_resets_the_count(self) -> None:
        saves = [
            ("mcp__plugin_contextbrain_contextbrain__save_session", None),
            ("save_session", None),
            ("exec", {"code": "await tools.mcp__contextbrain__save_session({})"}),
        ]
        for name, tool_input in saves:
            self.call("apply_patch")
            self.call("apply_patch")
            self.call(name, tool_input)
            self.assertEqual(self.call("Edit"), "")
            self.assertEqual(self.call("Edit"), "")
            self.assertIn("3 changes", self.reminder(self.call("Write")))
            self.call(name, tool_input)

    def test_outside_a_repository_it_never_reminds(self) -> None:
        outside = self.root / "plain"
        outside.mkdir()
        self.assertEqual([self.call("Edit", cwd=outside) for _ in range(5)], [""] * 5)

    def test_bad_input_never_fails(self) -> None:
        result = subprocess.run(
            [sys.executable, str(HOOK), "post-tool-use"], input="not json", capture_output=True, text=True
        )
        self.assertEqual((result.returncode, result.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
