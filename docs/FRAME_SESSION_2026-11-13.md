# First physical Frame session — 13 November 2026

These are first-hand results from Sean's Frame, combining recorded API results with his direct headset observations. **FACT** applies only to the named configuration/test. No result below establishes provider certification or a hardware-secure video path.

## Shipping baseline and connection

- **FACT — host inspection:** SteamOS `0.4.5`, build `20261022.6150929`; installed Lepton launcher label `v3.0.5`, Android image label `v3.0.3`, Steam Lepton build `25772114`.
- **FACT — runtime:** Android 11 / API 30, ARM64. The image label is not the Android OS version.
- Developer Mode and USB ADB provide access without a user password. USB initially reaches SteamOS; forwarding the observed guest listener on port 5555 provides the separate Android endpoint. The first cable did not enumerate; a replacement did. That does not prove the first cable is charge-only.
- Lepton was installed but Lepton Development was not visible in the library. Sean installed/launched Valve's separate free tool (Steam app `3056000`); an Android launcher window appeared.
- **FACT — headset:** the ordinary, non-OpenXR flatscreen helper displayed, its click counter responded and its animation ran. Keyboard, scrolling, resizing and lifecycle recovery were not tested.

The host overlay was inventoried read-only. Its presence does not establish operational DRM or effective component loading.

## Local Chromium baseline

Sean confirmed Chromium runs directly on Frame. All five services gave a satisfactory initial experience. No matched-title or sustained benchmark was performed.

| Service | Observed evidence | Actual source resolution |
|---|---|---|
| YouTube | Stats screenshot: VP9, 8 dropped of 818 frames at capture; Sean confirms sound and smooth motion | Current/optimal both 3840×2160 at 24 fps |
| Disney+ | Login/catalogue, visible video, sound, smooth motion; Sean says it does not look soft | UNKNOWN |
| Apple TV | Sean reports it works comparably to Disney+ | UNKNOWN |
| HBO Max | Sean reports a similar experience | UNKNOWN |
| Netflix | Sean confirms good picture, smooth playback and audio | UNKNOWN |

Subjective sharpness is not an HD/4K measurement. The YouTube frame counter is one cumulative sample, not a sustained drop-rate benchmark. Browser hardware decoding and CDM/session security remain unmeasured.

## Android diagnostics

The diagnostics helper produced a fresh, complete, non-synthetic API export.

- **FACT:** six video decoder entries: Google OMX AVC, H.263, HEVC, MPEG-4, VP8 and VP9. None reports hardware acceleration or secure playback; AV1 is absent.
- The API also returns `software_only=false` for these entries. Preserve the exact flags. **INFERENCE:** the Google OMX identities suggest software implementations; they do not establish a Frame-wide absence of hardware decoding.
- **FACT — initial probe:** both Widevine and ClearKey capability queries raise `IllegalArgumentException`. The original helper's outer catch labels this `construction=ERROR`, but the query failed before construction. That initial run could not establish constructor/session behavior.
- **FACT — corrected probe in a fresh Development session:** the capability query still raises `IllegalArgumentException`, but construction is now attempted independently. Both Widevine and ClearKey constructors throw `UnsupportedSchemeException` (exported as `UNSUPPORTED_SCHEME`). No MediaDrm object or session is obtained, so there is no L1/L3 session result. This demonstrates rejection through the tested Android API route, not absence of every DRM file, alternate runtime or host integration.
- The query/constructor separation and report handling have regressions that failed before the fix and pass afterward. The full current check passes **55 tests**, syntax checks in **28 Python files** and Ruff. The corrected diagnostic APK was rebuilt, signature-verified and run on Frame without provisioning or licence requests.

## Actual clear-media tests

Each clip is a two-second generated 24 fps, 8-bit test pattern with a tone. Files were hash-verified after copying into the media helper's private directory. Successful video runs selected/configured/used the named decoder, produced the listed dimensions and submitted all 48 frames at approximately 24 fps. Submission/render callbacks are not final-headset frame counts.

| Format | API result | Sean's headset observation |
|---|---|---|
| H.264 MP4, 1920×1080 | `OMX.google.h264.decoder`; 1080p output; clean EOS on corrected helper | Picture, tone, smooth motion on initial run |
| H.264 MP4, 3840×2160 | Same decoder; 4K output; clean EOS | Picture, tone, smooth motion |
| HEVC MP4, 1920×1080 | `OMX.google.hevc.decoder`; 1080p output; clean EOS | Picture, tone, smooth motion |
| HEVC MP4, 3840×2160 | Video track extracted; no video decoder selected; zero frames; audio completes | Tone, black picture |
| VP9 MP4, 1920×1080 | Failure before video metadata/decoder selection | Not separately observed |
| VP9 WebM, 1920×1080 | `OMX.google.vp9.decoder`; 1080p output; clean EOS | Picture, tone, smooth motion |
| VP9 WebM, 3840×2160 | Video track extracted; no video decoder selected; zero frames; audio completes | Tone, blank picture |
| AV1 WebM, 1920×1080 | `video/av01` track extracted; no video decoder selected; zero frames; audio completes | Tone, black picture |
| AV1, 3840×2160 | NOT TESTED after 1080p decoder selection failed | NOT TESTED |

WebM variants preserve the original VP9/AV1 video bitstream (hash-checked) and transcode the generated AAC tone to Opus. VP9's successful WebM run distinguishes the earlier MP4 preparation failure from a general VP9 decoding failure. HEVC's advertised 4K rate ceiling of approximately 15.43 fps may explain rejection of the 24 fps fixture; the precise rejection reason has not been captured. All used video decoders report `hardware_accelerated=false` and `software_only=false`.

These results do not establish sustained playback, Main10/HDR, thermals, battery life, protected playback or the capabilities of native Linux players. Chromium's successful VP9 4K source playback is a separate path from Android MediaCodec.

## Necessary helper correction

The original media helper threw its own `SecurityException` near the end of the first clear clip. An independent extractor probe on this Android runtime reproduced flags `-1` and sample size `-1` at EOF for both tracks. The original bitmask mistook that sentinel for encrypted data.

The fix handles EOF before checking encryption for an actual sample; encrypted samples remain rejected. An executable regression failed before the fix and passed afterward. `make check` passes 53 tests plus Python syntax and Ruff checks. The rebuilt, signature-verified media APK has SHA-256 `83215a20620e3e09e4d85edf54cf99626c65767b73fcb44edc4fe256697db748`. The repeated H.264 1080p test then reached audio/video EOS and released resources without those errors. Original and corrected run exports are preserved. Earlier APK hashes in ANDROID_VALIDATION.md describe the original preparation artifacts.

## Native Jellyfin viewing and practical outcome

**FACT — installation:** FramePlayerX v0.18.0 was downloaded from its official GitHub release. Archive and installer SHA-256 digests matched the release metadata; the installed AArch64 binary matched the archive and its Steam entry was read back. The isolated installation appears as **FramePlayerX (evaluation)**; no Steam restart was required.

**FACT — connection and viewing:** the Frame could not resolve Sean's Tailscale Jellyfin hostname and had no Tailscale client installed. Jellyfin's advertised LAN endpoint was reachable from the Frame and returned the same server ID as the Mac's Tailscale connection. Sean connected in FramePlayerX and saw his library. He played a film, explicitly observed **4K@24 in the player**, and reported initial streaming stutter followed by smooth, sharp playback once buffered. He subsequently confirmed the viewing experience was fine. This is user-observed player-reported 4K24; the native decoder, hardware acceleration, bitrate and delivery mode were not independently measured. No fixed viewing duration was recorded.

Sean considers Direct Play verification and resume/reporting checks low priority for this practical goal. Direct Play remains his inference; those checks are deferred, not passed. VideoFrameVR was not installed or evaluated. This is a practical acceptance observation, not completion of every formal E0 benchmark or native performance gate.

**Recommendation:** use local Chromium for the five streaming services and the existing FramePlayerX client for Jellyfin. The observed experience meets Sean's current viewing needs; no concrete gap has been identified that justifies adapting or building another Jellyfin client. Further investigation should respond to an actual viewing problem or a specific quality question. This does not authorise new application development or waive evidence standards for later hardware/HDR/performance claims.

## Evidence and follow-up

Private local browser notes and screenshot: `results/2026-11-13-browser-baseline/`. Target-bound Android bundle: `results/2026-11-13T17-37-58-6911c2ac/`, including raw per-run exports under `media/runs/` and the EOF reproduction/fix evidence. These ignored directories are not included in a clone. Review individual reports before sharing; never publish entire bundles or `target.local.json`.

The original and corrected DRM exports are retained under `drm/runs/`; `drm/query-fix-build.json` records the corrected diagnostic APK hash. Current normal Android API construction rejects both tested DRM schemes. No Android commercial streaming APK has been tested in this session.

Private native-player installation, connectivity and user observations are recorded in `results/2026-11-13-native-players/`. That ignored directory contains local server details and must remain private. The successful native clear-media result is independent of Android DRM; it does not repair or certify protected streaming. Preserve the current results and use the working setup before adding further investigation scope.
