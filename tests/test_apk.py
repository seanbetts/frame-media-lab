import tempfile
import unittest
import zipfile
from pathlib import Path
from lab.apk import inspect_apk, parse_manifest

MANIFEST = b"""<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="example.app" android:versionName="1.2"><uses-sdk android:minSdkVersion="30" android:targetSdkVersion="34"/><uses-permission android:name="android.permission.INTERNET"/><uses-feature android:name="android.hardware.vr.headtracking" android:required="false"/><application><activity android:name=".Main"/><activity-alias android:name=".Alias" android:targetActivity=".Main" android:exported="true"><intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/><data android:scheme="example"/></intent-filter></activity-alias></application></manifest>"""


TEST_TMP = Path(__file__).resolve().parents[1] / "build/tmp"
TEST_TMP.mkdir(parents=True, exist_ok=True)


class ApkTests(unittest.TestCase):
    def test_alias_and_metadata(self):
        m = parse_manifest(MANIFEST)
        self.assertEqual(m["package"], "example.app")
        self.assertEqual(m["min_sdk"], "30")
        self.assertEqual(m["launchers"], ["example.app/example.app.Alias"])
        self.assertEqual(m["activity_aliases"][0]["target"], "example.app.Main")
        self.assertIn("android.permission.INTERNET", m["permissions"])
        self.assertEqual(m["deep_links"][0]["scheme"], "example")

    def test_zip_abi_and_gms(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as d:
            p = Path(d) / "app.apk"
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("AndroidManifest.xml", MANIFEST)
                z.writestr("lib/arm64-v8a/libmedia.so", b"x")
                z.writestr(
                    "classes.dex",
                    b"Lcom/google/android/gms/common; Landroid/media/MediaDrm;",
                )
            data = inspect_apk(p)
            self.assertEqual(data["abis"], ["arm64-v8a"])
            self.assertTrue(data["gms_reference_detected"])

    def test_invalid_binary_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_manifest(b"\x03\x00\x08\x00\xff\xff\xff\xff")
