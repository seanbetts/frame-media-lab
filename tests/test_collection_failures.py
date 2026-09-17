import tempfile
import unittest
from pathlib import Path
from lab.core import Bundle, Config
from lab.collect import inspect_host, android_status, retrieve_app


TEST_TMP = Path(__file__).resolve().parents[1] / "build/tmp"
TEST_TMP.mkdir(parents=True, exist_ok=True)


class FakeRunner:
    def __init__(self, fail=False, export=None):
        self.config = Config(host="SYNTHETIC-host", serial="SYNTHETIC:5555")
        self.calls = []
        self.fail = fail
        self.export = export

    def ssh(self, argv, **kwargs):
        self.calls.append(argv)
        return {
            "status": "FAIL",
            "stderr": "SYNTHETIC connection refused",
            "stdout": "",
        }

    def require_android(self):
        return {"status": "PASS", "stdout": "34"}

    def shell(self, argv, **kwargs):
        return {
            "status": "FAIL" if self.fail else "PASS",
            "stdout": "",
            "stderr": "SYNTHETIC permission denied" if self.fail else "",
        }

    def adb(self, argv, **kwargs):
        import json

        return {"status": "PASS", "stdout": json.dumps(self.export), "stderr": ""}


class CollectionFailureTests(unittest.TestCase):
    def test_unreachable_host_does_not_continue_probes(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as d:
            r = FakeRunner()
            b = Bundle.create(Path(d), r.config)
            inspect_host(b, r)
            self.assertEqual(len(r.calls), 1)
            self.assertEqual(b.metadata["stages"]["host"]["status"], "FAIL")

    def test_failed_package_query_leaves_presence_unknown(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as d:
            r = FakeRunner(fail=True)
            b = Bundle.create(Path(d), r.config)
            android_status(b, r)
            self.assertEqual(
                b.read("android/identity.json")["gms_package_present"], "UNKNOWN"
            )

    def test_stale_app_export_is_not_persisted(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as d:
            r = FakeRunner(
                export={
                    "schema_version": 1,
                    "synthetic": False,
                    "complete": True,
                    "run_id": "old",
                    "launch_id": "old",
                }
            )
            b = Bundle.create(Path(d), r.config)
            with self.assertRaises(ValueError):
                retrieve_app(b, r, "media", expected_launch_id="new")
            self.assertFalse((b.path / "media/playback.json").exists())

    def test_incomplete_diagnostic_is_not_interpreted(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as d:
            r = FakeRunner(
                export={
                    "schema_version": 1,
                    "synthetic": False,
                    "complete": False,
                    "widevine": {"supported": True},
                }
            )
            b = Bundle.create(Path(d), r.config)
            with self.assertRaises(ValueError):
                retrieve_app(b, r)
            self.assertFalse((b.path / "drm/widevine.json").exists())
