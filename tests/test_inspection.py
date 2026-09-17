import importlib.util
import tempfile
import unittest
from pathlib import Path
from lab.collect import HOST_QUERIES, ANDROID_QUERIES, android_identity
from lab.compare import compare_components


TEST_TMP = Path(__file__).resolve().parents[1] / "build/tmp"
TEST_TMP.mkdir(parents=True, exist_ok=True)


class InspectionTests(unittest.TestCase):
    def test_default_queries_do_not_invoke_lepton_or_mutate(self):
        for query in HOST_QUERIES.values():
            text = " ".join(query)
            for forbidden in [
                "sudo",
                "system reset",
                "systemctl",
                "lepton ps",
                "lepton help",
                "setprop",
                "install ",
            ]:
                self.assertNotIn(forbidden, text)
        self.assertEqual(ANDROID_QUERIES["properties"], ["getprop"])

    def test_package_presence_does_not_claim_certification(self):
        result = android_identity(
            "[ro.build.version.sdk]: [34]", "package:/x=com.google.android.gms"
        )
        self.assertTrue(result["gms_package_present"])
        self.assertEqual(result["certification"], "UNKNOWN")

    def test_compare_missing_source_is_not_absence_of_binary(self):
        rows = compare_components(
            [], [{"path": "vendor/lib64/libwidevine.so", "sha256": "abc"}], [], []
        )
        self.assertEqual(rows[0]["status"], "UNKNOWN")

    def test_compare_same_and_effective_matching(self):
        p = {"path": "vendor/lib64/libcodec.so", "sha256": "abc"}
        rows = compare_components(
            [p],
            [p],
            [p],
            [
                {
                    "source": "/usr/share/guestos/android/vendor/lib64/libcodec.so",
                    "destination": "/vendor/lib64/libcodec.so",
                }
            ],
        )
        self.assertEqual(rows[0]["status"], "SAME")
        self.assertEqual(rows[0]["effective_hash_matches"], "shipping overlay")

    def test_inventory_no_symlink_or_secret_reads(self):
        spec = importlib.util.spec_from_file_location(
            "inventory", "scripts/inspect/overlay_inventory.py"
        )
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as d:
            p = Path(d)
            (p / "keybox.bin").write_text("PRIVATE")
            (p / "codec.so").write_text("ELF test")
            (p / "link.so").symlink_to(p / "keybox.bin")
            rows = m.inventory(p, owners=False)["files"]
            by = {r["path"]: r for r in rows}
            self.assertIsNone(by["keybox.bin"]["sha256"])
            self.assertIsNone(by["link.so"]["sha256"])
            self.assertIsNotNone(by["codec.so"]["sha256"])
            self.assertNotIn("PRIVATE", str(rows))


if __name__ == "__main__":
    unittest.main()
