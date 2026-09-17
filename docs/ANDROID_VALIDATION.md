# Android build and pre-hardware validation — 17 September 2026

All three APKs built through `./frame-media-lab build-android`. This is Mac-side compilation and artifact validation, **not Android runtime or Frame evidence**.

## Installed tooling

SDK: `/Users/sean/Library/Android/sdk`. Existing JDK: Homebrew 17.0.19. Mac: macOS 27.0, arm64. Initial inventory found no usable SDK, adb, sdkmanager or Android Studio; the existing `ANDROID_HOME` pointed to a nonexistent Homebrew directory.

| Component | Installed version |
|---|---|
| Google Command-line Tools, Mac ARM | 22.0 / archive 15859902 |
| `platforms;android-35` | API 35, revision 2, extension level 13 |
| `build-tools;35.0.0` | 35.0.0 |
| `platform-tools` | 37.0.1; ADB 1.0.41, build 15733141 |

The [official Google command-line archive](https://developer.android.com/studio#command-tools) matched published SHA-256 `835b62a26162b229b441d1f6d4680383815a270809eb33522c0d480fa5002c4e`. sdkmanager installed only the three requested packages and accepted only their `android-sdk-license`; the command-line archive carries the Android SDK licence too. No Studio, emulator, system images, additional JDK or shell-profile changes. The SDK's native AAPT2 supports arm64 directly.

## APKs

All have version **0.1.0 (code 1)**, **minSDK 26**, **targetSDK 34**, **compileSDK 35**, and exported MAIN/LAUNCHER Activity `<package>/.MainActivity`.

| APK under `build/android/` | Package | Bytes |
|---|---|---|
| `flatscreen-test-debug.apk` | `org.framemedialab.flatscreen` | 16787 |
| `diagnostics-debug.apk` | `org.framemedialab.diagnostics` | 24979 |
| `media-test-debug.apk` | `org.framemedialab.media` | 37267 |

SHA-256 (also in `build/android/validation/SHA256SUMS`):

- `flatscreen-test-debug.apk`: `a3bbfa2a67832eb5baf1d0f60b7e40b942889f9940ad61980e40c9bec7d3cff3`
- `diagnostics-debug.apk`: `86bb4f519fd909a500d8236498b2817accc9d5775300da07a0bcd7a2971abd82`
- `media-test-debug.apk`: `0b93a77667a0d5692b3a79f42794b58692f4a56d2832a0bfa2018acd5d8a31b3`

Each passed ZIP CRC/integrity checks; the toolkit's binary-manifest `inspect-apk`; official AAPT2 badging; apkanalyzer manifest and defined DEX class inspection; `zipalign -c -v 4`; and `apksigner verify --verbose --print-certs`. Signature verification also passed with API 30–35 bounds. No native libraries, ABI-specific payload, OpenXR dependency, split APK requirement or bundled SDK/lambda-stub classes. Defined classes belong to the app packages, including D8-generated lambda helpers.

All are debuggable, backups disabled, signed by the same local RSA-2048 **CN=Frame Media Lab Debug** certificate. Certificate SHA-256: `b88c9f41e05f4aa56e6a6dfb12a957ee3e6752013b399b967648705442c554db`. APK v2 and v3 signatures verify; v1/v3.1/v4 and SourceStamp are absent. These are local diagnostic debug builds. The retained private keystore enables repeat installations; it is not a release signing identity.

Diagnostics and flatscreen declare no permissions. Media declares only `android.permission.INTERNET`, and permits cleartext for trusted clear HTTP fixtures. No explicit feature declarations; AAPT2 reports Android's implicit `android.hardware.faketouch` default. These are structurally ordinary installable APKs; actual installer/PackageManager resolution awaits a target.

## API and behavior audit

Compared Java source, compiled diagnostics bytecode (`javap -p -c`) and Platform 35 `data/api-versions.xml`, cross-checked against the official [MediaDrm](https://developer.android.com/reference/android/media/MediaDrm), [MediaCodecInfo](https://developer.android.com/reference/android/media/MediaCodecInfo) and [CodecCapabilities](https://developer.android.com/reference/android/media/MediaCodecInfo.CodecCapabilities) documentation.

| Diagnostics API | Introduced | Source/compiled guard |
|---|---|---|
| MediaDrm construction, scheme query, safe string properties, openSession(), closeSession(), release() | 18 | Below minSDK 26 |
| getSecurityLevel(sessionId), connected/max HDCP | 28 | SDK_INT >= 28; unavailable/error stays explicit |
| ALL_CODECS constructor/enumeration, video capabilities | 21 | Below minSDK 26 |
| Hardware/software/vendor classification, alias/canonical name | 29 | SDK_INT >= 29; null on older APIs |
| Secure-playback support and required flag | 21 | Below minSDK 26 |
| Low-latency feature | 30 | SDK_INT >= 30; null on older APIs |

Widevine UUID is `edef8ba9-79d6-4ace-a3c8-27dcd51d21ed`; ClearKey is separately queried with `e2719d58-a985-b3c9-781a-b030af78d30e`. Sessions are actually opened by the implementation and queried by session ID, then closed. The code distinguishes support advertisement, construction and session outcome; it does not substitute the `securityLevel` string property for a session measurement. No provisioning, licence/key requests, device identifiers or security-level modification. Plugin absence and provisioning/resource failures remain explicit outcomes.

The `ALL_CODECS` loop enumerates every advertised video MIME, including `video/avc`, `video/hevc`, `video/x-vnd.on2.vp9` and `video/av01` when present, with profile/level, dimensions/rates and secure-playback flags. No named codec is assumed to exist. Every codec record starts ADVERTISED/configured=false/actually_used=false.

These guards and API introductions support API 30 and API 34/35 at the API-contract level; compileSDK 35 does not impose an Android 15 runtime requirement. This is not execution testing on those versions, and does not establish plugin provisioning, L1, HDCP enforcement or hardware/protected decoding.

Flatscreen extends ordinary Activity, with no XR dependencies: animation, button count, text entry, scrolling, pointer/touch coordinates, layout/display dimensions and lifecycle events remain present. Manifest and DEX agree on its Activity. Headset panel visibility and input are untested.

Media uses normal MediaExtractor → MediaCodec → Surface and AudioTrack APIs, configures without MediaCrypto and rejects encrypted samples. Its tested source policy accepts absolute paths, file/content URIs and HTTP(S); content grants and storage access depend on Android. It reports selected/instantiated decoder, output format, source dimensions separately from Surface dimensions, submitted/render-callback counters, audio state and structured launch/run evidence. Surface size is not a measurement of final headset display resolution. No DRM circumvention or protected playback path exists.

All eight existing two-second MP4 fixtures were re-probed: AVC/HEVC/VP9/AV1 at 1920×1080 and 3840×2160, 24 fps, AAC audio. Use the documented app-private `run-as` copy or trusted HTTP source and start with H.264 1080p before testing the other seven. Compare requested source dimensions/MIME with diagnostics advertisements and the actual media result. No Android extractor, codec or playback success was inferred from ffprobe.

## Verification and evidence

- `make check`: **52 tests**, Python syntax in **26 files**, Ruff pass. Includes five new SDK-discovery regressions and a real javac Android-lambda test.
- `doctor`: all local tooling PASS; Frame SSH/Android endpoint NOT TESTED.
- Project Runner's `adb version` and `adb devices -l`: PASS, empty device list. Enumeration started the local ADB server. No connection, install or runtime action was sent to a device.
- SSH, direct and USB-host `connection-plan` output uses the same discovered ADB path. Installed help confirms connect/forward/tcp/shell/serial syntax. Hidden exec-in/exec-out dispatch was confirmed against a deliberately nonexistent serial, returning device-not-found rather than unknown-command. Actual forwarding/connectivity is untested.
- Synthetic `l1 first-hour` and explicit report regeneration passed, retaining synthetic provenance and NOT TESTED protected playback. Earlier 15-scenario verification remains recorded separately.
- Protected-source check: **361 files**, PASS, no changes to `../Lepton/` or `../LEPTON_MEDIA_INVESTIGATION.md`.

Evidence index:

- `build/sdk-setup/installation.json`, Google archive/checksum, `sdkmanager-install.log`: inventory, versions and scoped licence/install evidence.
- `build/sdk-setup/android-build-initial-failure.log`, `lambda-regression-before.txt`, `lambda-regression-after.txt`, `android-build.log`: exact failure, regression and successful CLI build.
- `build/android/validation/`: own/official manifests, DEX inventory, signature/alignment outputs, `apks.json`, `SHA256SUMS`.
- `build/sdk-setup/diagnostics-api-levels.json`, `diagnostics-bytecode.txt`: API metadata and compiled guards.
- `build/sdk-setup/adb-validation.json`, `connection-plan-*.txt`, `doctor-after-install.txt`: tooling/command checks.
- `build/sdk-setup/media-validation.json`, `synthetic-validation.json`, `protected-source-validation.json`; `build/check-validation.txt`.

No APK has been installed or executed. Actual API 30/34/35 runtime behavior, input/lifecycle/teardown, DRM sessions, clear decoding/audio/sync, headset visibility and commercial service playback remain NOT TESTED. No commits or pushes.
