"""Exercise the real DRM probe's fault boundaries without Android hardware."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DrmProbeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("javac") and shutil.which("java"), "JDK required")
    def test_failed_advertisement_does_not_block_construction_or_session(self):
        source = (
            ROOT
            / "android/diagnostics/src/main/java/org/framemedialab/diagnostics/MainActivity.java"
        ).read_text()
        methods = "static JSONObject drm(UUID uuid) {" + source.split(
            "static JSONObject drm(UUID uuid) {", 1
        )[1].split("static JSONArray codecs()", 1)[0]
        harness = """import java.util.UUID;
import java.util.LinkedHashMap;
public class DrmTest {
 static class JSONObject extends LinkedHashMap<String,Object> { }
 static void put(JSONObject o,String k,Object v) {o.put(k,v);}
 static String error(Exception e) {return e.getClass().getSimpleName();}
 static final String[] SAFE_PROPERTIES={"securityLevel"};
 static class Build {static class VERSION {static final int SDK_INT=30;}}
 static class UnsupportedSchemeException extends Exception { }
 static class NotProvisionedException extends Exception { }
 static class ResourceBusyException extends Exception { }
 static class MediaDrm {
  static final int SECURITY_LEVEL_SW_SECURE_CRYPTO=1,SECURITY_LEVEL_SW_SECURE_DECODE=2,
   SECURITY_LEVEL_HW_SECURE_CRYPTO=3,SECURITY_LEVEL_HW_SECURE_DECODE=4,SECURITY_LEVEL_HW_SECURE_ALL=5;
  static boolean queryThrows,queryValue,unsupported,needsProvision,closed,released;
  static int constructors,opens;
  static boolean isCryptoSchemeSupported(UUID id) {
   if(queryThrows)throw new IllegalArgumentException();return queryValue;
  }
  MediaDrm(UUID id) throws UnsupportedSchemeException {
   constructors++;if(unsupported)throw new UnsupportedSchemeException();
  }
  String getPropertyString(String name) {return "test";}
  int getConnectedHdcpLevel() {return 0;}
  int getMaxHdcpLevel() {return 0;}
  byte[] openSession() throws NotProvisionedException,ResourceBusyException {
   opens++;if(needsProvision)throw new NotProvisionedException();return new byte[]{1};
  }
  int getSecurityLevel(byte[] id) {return 1;}
  void closeSession(byte[] id) {closed=true;}
  void release() {released=true;}
  static void reset() {
   queryThrows=true;queryValue=false;unsupported=false;needsProvision=false;
   closed=false;released=false;constructors=0;opens=0;
  }
 }
 __METHODS__
 static JSONObject session(JSONObject result) {return (JSONObject)result.get("session");}
 static void expect(Object want,Object got) {
  if(!java.util.Objects.equals(want,got))throw new AssertionError("expected="+want+" actual="+got);
 }
 public static void main(String[] args) {
  UUID uuid=UUID.fromString("edef8ba9-79d6-4ace-a3c8-27dcd51d21ed");
  MediaDrm.reset();JSONObject result=drm(uuid);
  expect("SUCCESS",result.get("construction"));expect("OPENED",session(result).get("status"));
  expect("SW_SECURE_CRYPTO",session(result).get("security_level_name"));
  expect(1,MediaDrm.constructors);expect(1,MediaDrm.opens);
  expect(true,MediaDrm.closed);expect(true,MediaDrm.released);
  expect(null,result.get("supported"));expect("ERROR",result.get("support_query_status"));
  expect("IllegalArgumentException",result.get("support_query_error"));
  MediaDrm.reset();MediaDrm.queryThrows=false;result=drm(uuid);
  expect(false,result.get("supported"));expect("SUCCESS",result.get("support_query_status"));
  expect("OPENED",session(result).get("status"));
  MediaDrm.reset();MediaDrm.unsupported=true;result=drm(uuid);
  expect("UNSUPPORTED_SCHEME",result.get("construction"));
  expect("NOT_TESTED",session(result).get("status"));expect(0,MediaDrm.opens);
  expect(false,MediaDrm.released);
  MediaDrm.reset();MediaDrm.needsProvision=true;result=drm(uuid);
  expect("SUCCESS",result.get("construction"));
  expect("PROVISIONING_REQUIRED",session(result).get("status"));
  expect(false,MediaDrm.closed);expect(true,MediaDrm.released);
 }
}
""".replace("__METHODS__", methods)
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            test = Path(directory) / "DrmTest.java"
            test.write_text(harness)
            compile_result = subprocess.run(
                ["javac", "-d", directory, str(test)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            result = subprocess.run(
                ["java", "-cp", directory, "DrmTest"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
