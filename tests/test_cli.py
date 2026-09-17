import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from lab.cli import main
from lab.core import Config, Bundle


TEST_TMP = Path(__file__).resolve().parents[1] / "build/tmp"
TEST_TMP.mkdir(parents=True, exist_ok=True)


class CliTests(unittest.TestCase):
    def test_synthetic_cli_never_calls_transport(self):
        with (
            tempfile.TemporaryDirectory(dir=TEST_TMP) as d,
            patch("lab.core.Runner.ssh", side_effect=AssertionError("network")),
            patch("lab.core.Runner.adb", side_effect=AssertionError("device")),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(
                main(["--results", d, "--synthetic", "l1", "first-hour"]), 0
            )
            report = next(Path(d).glob("*/report.json"))
            data = json.loads(report.read_text())
            self.assertTrue(data["synthetic"])
            self.assertEqual(data["drm"]["protected_playback"], "NOT TESTED")

    def test_synthetic_cannot_install(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(
                main(["--synthetic", "l1", "install-apk", "missing.apk"]), 2
            )

    def test_report_existing_synthetic_without_repopulation(self):
        with (
            tempfile.TemporaryDirectory(dir=TEST_TMP) as d,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            b = Bundle.create(Path(d), Config(), True)
            self.assertEqual(main(["report", str(b.path)]), 0)
            self.assertTrue(
                json.loads((b.path / "report.json").read_text())["synthetic"]
            )

    def test_redact_json_cli_masks_arbitrary_secret_value(self):
        with (
            tempfile.TemporaryDirectory(dir=TEST_TMP) as d,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            source = Path(d) / "input.json"
            target = Path(d) / "redacted.json"
            source.write_text('{"token":"TOP_SECRET_VALUE"}')
            self.assertEqual(main(["redact", str(source), str(target)]), 0)
            self.assertNotIn("TOP_SECRET_VALUE", target.read_text())

    def test_report_requires_explicit_input(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["report"]), 2)
