"""Short generated test-pattern clips; ffmpeg is optional and never installed here."""

import json
import shutil
from .core import ROOT, Runner, dump

ENCODERS = {
    "h264": "libx264",
    "hevc": "libx265",
    "vp9": "libvpx-vp9",
    "av1": "libaom-av1",
}


def generate(
    codecs=("h264", "hevc", "vp9", "av1"), sizes=("1080p", "4k"), seconds=5, runner=None
):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise ValueError(
            "Install ffmpeg with ffprobe explicitly; see fixtures/media/README.md"
        )
    if not 1 <= seconds <= 60:
        raise ValueError("Duration must be 1..60 seconds")
    r = runner or Runner()
    inventory = r.run(["ffmpeg", "-hide_banner", "-encoders"])
    available = inventory["stdout"]
    out = ROOT / "fixtures/media/generated"
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for codec in codecs:
        for size in sizes:
            encoder = ENCODERS[codec]
            if codec == "av1" and encoder not in available and "libsvtav1" in available:
                encoder = "libsvtav1"
            name = codec + "-" + size + ".mp4"
            target = out / name
            if encoder not in available:
                results.append(
                    {
                        "file": name,
                        "status": "NOT TESTED",
                        "reason": "Encoder unavailable: " + encoder,
                    }
                )
                continue
            dimensions = "1920x1080" if size == "1080p" else "3840x2160"
            if target.exists():
                results.append(
                    {
                        "file": name,
                        "status": "WARNING",
                        "reason": "Exists; left untouched",
                    }
                )
                continue
            pending = out / (target.stem + ".incomplete.mp4")
            argv = [
                "ffmpeg",
                "-hide_banner",
                "-nostdin",
                "-n",
                "-f",
                "lavfi",
                "-i",
                f"testsrc2=size={dimensions}:rate=24",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=48000",
                "-t",
                str(seconds),
                "-c:v",
                encoder,
                "-threads",
                "4",
                "-pix_fmt",
                "yuv420p",
            ]
            if codec == "h264":
                argv += ["-preset", "fast", "-crf", "23"]
            if codec == "hevc":
                argv += [
                    "-preset",
                    "fast",
                    "-crf",
                    "26",
                    "-tag:v",
                    "hvc1",
                    "-x265-params",
                    "pools=4:frame-threads=2",
                ]
            if codec == "vp9":
                argv += [
                    "-deadline",
                    "realtime",
                    "-cpu-used",
                    "6",
                    "-crf",
                    "32",
                    "-b:v",
                    "0",
                ]
            if codec == "av1":
                argv += (
                    ["-preset", "12", "-crf", "35", "-svtav1-params", "lp=4"]
                    if encoder == "libsvtav1"
                    else ["-cpu-used", "8", "-row-mt", "1", "-crf", "35", "-b:v", "0"]
                )
            argv += [
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-shortest",
                "-movflags",
                "+faststart",
                str(pending),
            ]
            result = r.run(argv, timeout=300)
            entry = {
                "file": name,
                "status": result["status"],
                "stderr": result["stderr"][-2000:],
            }
            if result["status"] == "PASS":
                check = r.run(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-show_streams",
                        "-show_format",
                        "-of",
                        "json",
                        str(pending),
                    ]
                )
                if check["status"] == "PASS":
                    entry["probe"] = json.loads(check["stdout"])
                    pending.replace(target)
                else:
                    entry.update(status="FAIL", stderr=check["stderr"])
            results.append(entry)
            dump(out / "generation.json", results)
    dump(out / "generation.json", results)
    return results
