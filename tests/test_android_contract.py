"""Static safety contracts plus executable build preflight (not Android runtime tests)."""

import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / "android"
NS = "{http://schemas.android.com/apk/res/android}"


class AndroidContractTests(unittest.TestCase):
    def test_sdk_javac_can_compile_android_listener_lambda(self):
        from scripts.build_android import find_sdk, java_bootclasspath, prerequisites

        sdk = find_sdk()
        if prerequisites(sdk):
            self.skipTest("Installed Android SDK/JDK required for lambda compilation")
        with tempfile.TemporaryDirectory(
            dir=ROOT / "build", prefix="android-lambda-"
        ) as d:
            source = Path(d) / "LambdaProbe.java"
            source.write_text("""import android.view.View;
class LambdaProbe {
    View.OnClickListener listener = v -> v.setAlpha(0.5f);
}""")
            result = subprocess.run(
                [
                    "javac",
                    "-source",
                    "8",
                    "-target",
                    "8",
                    "-bootclasspath",
                    java_bootclasspath(sdk),
                    "-d",
                    d,
                    str(source),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(d) / "LambdaProbe.class").is_file())

    def test_launchable_plain_activities_have_only_expected_permissions(self):
        for module, package in [
            ("flatscreen-test", "flatscreen"),
            ("diagnostics", "diagnostics"),
            ("media-test", "media"),
        ]:
            manifest = ANDROID / module / "src/main/AndroidManifest.xml"
            self.assertTrue(manifest.exists(), str(manifest))
            root = ET.parse(manifest).getroot()
            self.assertEqual(root.get("package"), "org.framemedialab." + package)
            permissions = {p.get(NS + "name") for p in root.findall("uses-permission")}
            self.assertEqual(
                permissions,
                {"android.permission.INTERNET"} if package == "media" else set(),
            )
            activity = root.find("application/activity")
            self.assertEqual(activity.get(NS + "name"), ".MainActivity")
            self.assertEqual(activity.get(NS + "exported"), "true")
            self.assertIsNotNone(
                activity.find(
                    "intent-filter/action[@%s='android.intent.action.MAIN']"
                    % (NS + "name")
                )
            )

    def test_missing_sdk_fails_without_installing_or_creating_artifacts(self):
        script = ROOT / "scripts/build_android.py"
        self.assertTrue(script.exists())
        with tempfile.TemporaryDirectory(
            dir=ROOT / "build", prefix="android-test-"
        ) as directory:
            env = dict(os.environ, ANDROID_HOME=directory, ANDROID_SDK_ROOT=directory)
            result = subprocess.run(
                [sys.executable, str(script), "--sdk", directory, "--check"],
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("platforms;android-35", result.stderr)
            self.assertEqual(list(Path(directory).iterdir()), [])

    @unittest.skipUnless(
        shutil.which("java") and shutil.which("javac"),
        "JDK required for source-policy execution",
    )
    def test_media_source_policy_rejects_non_media_schemes_without_echoing_secrets(
        self,
    ):
        policy = (
            ANDROID
            / "media-test/src/main/java/org/framemedialab/media/SourcePolicy.java"
        )
        self.assertTrue(policy.exists())
        with tempfile.TemporaryDirectory(
            dir=ROOT / "build", prefix="android-java-"
        ) as directory:
            harness = Path(directory) / "PolicyTest.java"
            harness.write_text("""package org.framemedialab.media;
public class PolicyTest {
 public static void main(String[] args) {
  String[][] values = {{"https://user:secret@example.org/video?token=secret", "https"},
   {"http://example.org/file.mp4", "http"}, {"content://provider/private/12", "content"},
   {"file:///data/user/0/test/files/clip.mp4", "file"}, {"/data/private/file name.mp4", "file"}};
  for (String[] v : values) if (!v[1].equals(SourcePolicy.kind(v[0]))) throw new AssertionError();
  for (String bad : new String[]{"", "relative.mp4", "javascript:secret", "ftp://secret", "https://"}) {
   try { SourcePolicy.kind(bad); throw new AssertionError("accepted invalid input"); }
   catch (IllegalArgumentException expected) {
    if (expected.getMessage().contains("secret")) throw new AssertionError("secret leaked");
   }
  }
 }
}""")
            compiled = subprocess.run(
                ["javac", "-d", directory, str(policy), str(harness)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            run = subprocess.run(
                ["java", "-cp", directory, "org.framemedialab.media.PolicyTest"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(run.returncode, 0, run.stderr)

    @unittest.skipUnless(shutil.which("java") and shutil.which("javac"), "JDK required")
    def test_media_gate_never_grants_a_second_owner_before_matching_release(self):
        gate = (
            ANDROID
            / "media-test/src/main/java/org/framemedialab/media/PlaybackGate.java"
        )
        self.assertTrue(gate.exists())
        with tempfile.TemporaryDirectory(
            dir=ROOT / "build", prefix="android-gate-"
        ) as directory:
            harness = Path(directory) / "GateTest.java"
            harness.write_text("""package org.framemedialab.media;
public class GateTest {
 public static void main(String[] args) throws Exception {
  PlaybackGate<Object> gate = new PlaybackGate<>(); Object a = new Object(), b = new Object();
  if (!gate.tryAcquire(a) || gate.tryAcquire(a) || gate.tryAcquire(b)) throw new AssertionError("overlap");
  gate.release(b);
  if (gate.current() != a || gate.tryAcquire(b)) throw new AssertionError("foreign release");
  gate.release(a);
  if (!gate.tryAcquire(b)) throw new AssertionError("never unlocked");
  gate.release(a);
  if (gate.current() != b) throw new AssertionError("late callback unlocked replacement");
  gate.release(b);
  java.util.concurrent.atomic.AtomicInteger successes = new java.util.concurrent.atomic.AtomicInteger();
  java.util.concurrent.CountDownLatch ready = new java.util.concurrent.CountDownLatch(1);
  Thread one = new Thread(() -> { try {ready.await();} catch(Exception e) {} if(gate.tryAcquire(a)) successes.incrementAndGet(); });
  Thread two = new Thread(() -> { try {ready.await();} catch(Exception e) {} if(gate.tryAcquire(b)) successes.incrementAndGet(); });
  one.start(); two.start(); ready.countDown(); one.join(); two.join();
  if (successes.get() != 1) throw new AssertionError("concurrent overlap");
 }
}""")
            compiled = subprocess.run(
                ["javac", "-d", directory, str(gate), str(harness)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            run = subprocess.run(
                ["java", "-cp", directory, "org.framemedialab.media.GateTest"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(run.returncode, 0, run.stderr)

    @unittest.skipUnless(shutil.which("java") and shutil.which("javac"), "JDK required")
    def test_media_launch_record_invalidates_completed_playback_with_a_new_identity(
        self,
    ):
        import json

        record = (
            ANDROID
            / "media-test/src/main/java/org/framemedialab/media/LaunchRecord.java"
        )
        self.assertTrue(record.exists())
        with tempfile.TemporaryDirectory(
            dir=ROOT / "build", prefix="android-launch-"
        ) as directory:
            harness = Path(directory) / "LaunchTest.java"
            harness.write_text("""package org.framemedialab.media;
public class LaunchTest {
 public static void main(String[] args) {
  System.out.println(new LaunchRecord().initialJson());
  System.out.println(new LaunchRecord().initialJson());
 }
}""")
            compiled = subprocess.run(
                ["javac", "-d", directory, str(record), str(harness)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            run = subprocess.run(
                ["java", "-cp", directory, "org.framemedialab.media.LaunchTest"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            records = [json.loads(line) for line in run.stdout.splitlines()]
            self.assertNotEqual(records[0]["launch_id"], records[1]["launch_id"])
            for value in records:
                self.assertEqual(value["schema_version"], 1)
                self.assertIs(value["synthetic"], False)
                self.assertIs(value["complete"], False)
                self.assertEqual(value["state"], "IDLE")
                self.assertNotIn("video_decoder", value)
                self.assertNotIn("frames_submitted_to_surface", value)

    def test_drm_source_boundary_never_requests_identifiers_provisioning_or_keys(self):
        sources = list((ANDROID / "diagnostics").rglob("*.java"))
        self.assertTrue(sources)
        text = "\n".join(p.read_text() for p in sources)
        for forbidden in (
            "getPropertyByteArray(",
            "getProvisionRequest(",
            "provideProvisionResponse(",
            "getKeyRequest(",
            "provideKeyResponse(",
            "getSecureStops(",
            "getDeviceUniqueId(",
        ):
            self.assertNotIn(forbidden, text)
        self.assertIn("getSecurityLevel(sessionId)", text)
        self.assertIn("MediaCodecList.ALL_CODECS", text)


if __name__ == "__main__":
    unittest.main()
