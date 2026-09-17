"""Project SDK discovery must work without modifying the user's shell PATH."""

import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lab.android_sdk import find_sdk, tool_path
from lab.cli import main
from lab.core import Runner


class SDKTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.sdk = self.home / "Library/Android/sdk"
        (self.sdk / "platform-tools").mkdir(parents=True)
        self.adb = self.sdk / "platform-tools/adb"
        self.adb.write_text('#!/bin/sh\nprintf "fake adb: %s\\n" "$*"\n')
        self.adb.chmod(0o700)
        self.env = patch.dict(
            os.environ,
            {"ANDROID_HOME": str(self.home / "gone"), "PATH": "/usr/bin:/bin"},
            clear=True,
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        self.home_patch = patch("pathlib.Path.home", return_value=self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)

    def test_stale_environment_falls_back_to_conventional_sdk(self):
        self.assertEqual(find_sdk(), self.sdk)
        self.assertEqual(tool_path("adb"), str(self.adb))

    def test_explicit_missing_sdk_never_silently_falls_back(self):
        self.assertIsNone(find_sdk(str(self.home / "missing")))
        with patch.dict(os.environ, {"FML_ANDROID_SDK": str(self.home / "missing")}):
            self.assertIsNone(find_sdk())

    def test_project_override_wins(self):
        other = self.home / "other-sdk"
        other.mkdir()
        with patch.dict(os.environ, {"FML_ANDROID_SDK": str(other)}):
            self.assertEqual(find_sdk(), other)

    def test_runner_executes_sdk_adb_without_global_path_changes(self):
        before = dict(os.environ)
        result = Runner().run(["adb", "version"])
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["stdout"].strip(), "fake adb: version")
        self.assertEqual(dict(os.environ), before)

    def test_connection_plan_uses_same_discovered_adb(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(
                main(
                    [
                        "--host",
                        "frame.invalid",
                        "connection-plan",
                        "--method",
                        "ssh",
                        "--guest-port",
                        "5556",
                    ]
                ),
                0,
            )
        self.assertIn(str(self.adb) + " connect 127.0.0.1:15555", output.getvalue())


if __name__ == "__main__":
    unittest.main()
