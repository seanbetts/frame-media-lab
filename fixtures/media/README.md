# Generated clear fixtures

All clips are ffmpeg-generated moving test patterns plus a 440 Hz sine wave; no copyrighted film or proprietary APK downloads are involved. Generated outputs are local and ignored by Git. The generation script depends only on an existing ffmpeg/ffprobe installation and never installs one.

```sh
./frame-media-lab generate-media                 # eight clips, 5 seconds each
./frame-media-lab generate-media --codec h264 --size 1080p --seconds 2
```

| Codec | Sizes | Video encoder | Audio / container |
|---|---|---|---|
| H.264 | 1920×1080, 3840×2160 | libx264 | AAC / MP4 |
| HEVC | 1920×1080, 3840×2160 | libx265 (`hvc1`) | AAC / MP4 |
| VP9 | 1920×1080, 3840×2160 | libvpx-vp9 | AAC / MP4 |
| AV1 | 1920×1080, 3840×2160 | libaom-av1, or libsvtav1 when available | AAC / MP4 |

Clips use 24 fps, 8-bit YUV 4:2:0 and fast-start progressive MP4. These are clear decode/load probes, not HDR, provider-quality or sustained battery benchmarks. Android extractor support for VP9/AV1 in MP4 must itself be tested; if extraction fails, record that independently from codec capability and consider a separately generated WebM variant.

Missing encoders produce NOT TESTED. Completed files are not overwritten. Work is written to `.incomplete.mp4` then promoted after ffprobe succeeds; a failed partial remains available for diagnosis and can be removed explicitly before retrying. Each encode has a five-minute ceiling. AV1/4K encoding can be expensive; short clips are intentional. `generation.json` records the most recent invocation; validation outputs are also retained under build/ during project verification.

Use a trusted HTTP server you explicitly start, or the file picker/app-private copy workflow in [ANDROID.md](../../docs/ANDROID.md). The toolkit never opens an HTTP server automatically. A Mac filesystem path is not an Android file path. Do not grant broad device storage access just to play a fixture.
