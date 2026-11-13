"""Execute the player's real input-feeding branch against Android boundary doubles."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MediaInputTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("javac") and shutil.which("java"), "JDK required")
    def test_clear_sample_and_eof_are_queued_but_encrypted_samples_are_rejected(self):
        source = (
            ROOT
            / "android/media-test/src/main/java/org/framemedialab/media/ClearPlayer.java"
        ).read_text()
        # Compile the actual feeding branch, not a copied version of its logic.
        branch = "if(!inputEnd) {" + source.split("if(!inputEnd) {", 1)[1].split(
            "int slot=decoder.dequeueOutputBuffer", 1
        )[0]
        harness = """import java.nio.ByteBuffer;
public class InputTest {
 static class MediaExtractor {
  static final int SAMPLE_FLAG_ENCRYPTED=2;
  int size, flags; boolean advanced;
  MediaExtractor(int size,int flags) {this.size=size;this.flags=flags;}
  int getSampleFlags() {return flags;}
  int readSampleData(ByteBuffer b,int offset) {if(size>0)b.put((byte)42);return size;}
  long getSampleTime() {return 123;}
  void advance() {advanced=true;size=-1;flags=-1;}
 }
 static class MediaCodec {
  static final int BUFFER_FLAG_END_OF_STREAM=4;
  final ByteBuffer buffer=ByteBuffer.allocate(16);
  int calls, bytes, lastFlags; long lastTime;
  int dequeueInputBuffer(int timeout) {return 0;}
  ByteBuffer getInputBuffer(int slot) {buffer.clear();return buffer;}
  void queueInputBuffer(int slot,int offset,int size,long time,int flags) {
   calls++;bytes+=size;lastFlags=flags;lastTime=time;
   if(size>0 && buffer.get(0)!=42)throw new AssertionError("payload lost");
  }
 }
 static boolean feed(MediaExtractor input,MediaCodec decoder) {
  boolean inputEnd=false,progress=false;
  __BRANCH__
  return inputEnd;
 }
 public static void main(String[] args) {
  MediaExtractor input=new MediaExtractor(1,1);MediaCodec decoder=new MediaCodec();
  if(feed(input,decoder) || !input.advanced || decoder.calls!=1 || decoder.bytes!=1
    || decoder.lastTime!=123 || decoder.lastFlags!=0)throw new AssertionError("clear sample not queued");
  try {
   if(!feed(input,decoder))throw new AssertionError("EOF not signalled");
  } catch(SecurityException e) {throw new AssertionError("EOF mistaken for encrypted content",e);}
  if(decoder.calls!=2 || decoder.bytes!=1 || decoder.lastFlags!=4)throw new AssertionError("EOS not queued");
  for(int flags:new int[]{2,3}) {
   MediaCodec protectedDecoder=new MediaCodec();
   try {feed(new MediaExtractor(1,flags),protectedDecoder);throw new AssertionError("encrypted sample accepted");}
   catch(SecurityException expected) { }
   if(protectedDecoder.calls!=0)throw new AssertionError("encrypted bytes queued");
  }
  MediaCodec empty=new MediaCodec();
  if(!feed(new MediaExtractor(-1,-1),empty) || empty.lastFlags!=4)throw new AssertionError("empty stream not ended");
 }
}
""".replace("__BRANCH__", branch)
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            test = Path(directory) / "InputTest.java"
            test.write_text(harness)
            compiled = subprocess.run(
                ["javac", "-d", directory, str(test)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            run = subprocess.run(
                ["java", "-cp", directory, "InputTest"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
