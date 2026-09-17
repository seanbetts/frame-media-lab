import json
import tempfile
import unittest
from pathlib import Path
from lab.core import Config, Bundle, Runner, redact, parse_properties, parse_lepton_ps


TEST_TMP = Path(__file__).resolve().parents[1] / "build/tmp"
TEST_TMP.mkdir(parents=True, exist_ok=True)


class CoreTests(unittest.TestCase):
    def test_redaction_nested_and_log_payloads(self):
        secret = {
            "token": "SECRET",
            "deviceUniqueId": "UNIQUE",
            "text": "Authorization: Bearer SECRET\nmail me sean@example.org https://x.test/a?token=SECRET\nlicense response: BASE64SECRET\nro.serialno=UNIQUE",
        }
        clean = json.dumps(redact(secret))
        for value in [
            "SECRET",
            "UNIQUE",
            "sean@example.org",
            "BASE64SECRET",
            "https://x.test",
        ]:
            self.assertNotIn(value, clean)
        self.assertEqual(
            redact({"security_level": "L1", "vendor": "Widevine"})["security_level"],
            "L1",
        )

    def test_properties(self):
        self.assertEqual(
            parse_properties(
                "[ro.build.version.sdk]: [34]\nnoise\n[ro.product.model]: [Lepton]"
            ),
            {"ro.build.version.sdk": "34", "ro.product.model": "Lepton"},
        )

    def test_lepton_ports(self):
        self.assertEqual(
            parse_lepton_ps(
                "dev (10.0.0.2, adb on 5556, gdb on 6000, lldb on 7000, packages: example)"
            )[0]["adb_port"],
            5556,
        )

    def test_bundle_unique_and_provenance(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as d:
            a = Bundle.create(Path(d), Config(), True)
            b = Bundle.create(Path(d), Config(), True)
            self.assertNotEqual(a.path, b.path)
            self.assertTrue(a.metadata["synthetic"])
            with self.assertRaises(ValueError):
                Bundle.open(a.path, False)
            a.write("android/properties.json", {"token": "SECRET"})
            self.assertNotIn("SECRET", (a.path / "android/properties.json").read_text())
            with self.assertRaises(ValueError):
                a.write("../escape.json", {})

    def test_config_rejects_options_and_bad_ports(self):
        for values in [
            {"host": "-oProxyCommand=evil"},
            {"ssh_port": 0},
            {"ssh_user": "x;id"},
            {"context": "--help"},
        ]:
            with self.assertRaises(ValueError):
                Config(**values).validate()

    def test_missing_command_and_timeout(self):
        r = Runner().run(["frame-media-lab-nonexistent-tool"])
        self.assertEqual(r["status"], "FAIL")
        self.assertEqual(r["returncode"], 127)
        r = Runner().run(["python3", "-c", "import time;time.sleep(2)"], timeout=0.05)
        self.assertEqual(r["status"], "FAIL")
        self.assertTrue(r["timed_out"])

    def test_remote_arguments_are_quoted(self):
        c = Config(host="frame.test")
        r = Runner(c)
        argv = r.ssh_argv(["printf", "%s", "$(touch /tmp/unsafe)"])
        self.assertIn("'$(touch /tmp/unsafe)'", argv[-1])
        self.assertIn("BatchMode=yes", argv)


if __name__ == "__main__":
    unittest.main()


class BindingTests(unittest.TestCase):
    def test_resume_rejects_different_host_or_context(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as d:
            a = Bundle.create(Path(d), Config(host="frame-a", serial="a:5555"), False)
            with self.assertRaises(ValueError):
                a.check_target(Config(host="frame-b", serial="a:5555"))
            with self.assertRaises(ValueError):
                a.check_target(Config(host="frame-a", context="other", serial="a:5555"))
            a.check_target(Config(host="frame-a", serial="a:5555"))

    def test_endpoint_change_requires_explicit_rebind(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as d:
            a = Bundle.create(Path(d), Config(host="frame-a", serial="a:5555"), False)
            with self.assertRaises(ValueError):
                a.check_target(Config(host="frame-a", serial="a:5556"))
            a.check_target(Config(host="frame-a", serial="a:5556"), rebind_adb=True)
            self.assertNotIn("a:5556", (a.path / "metadata.json").read_text())
