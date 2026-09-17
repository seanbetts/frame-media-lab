# Android probe applications

Three platform-only Java projects, each with `MainActivity`, minimum API 26, target API 34, compiled against API 35. No native libraries or OpenXR dependencies are included. Their DEX bytecode has no native ABI restriction; ARM64 installation/execution still needs a device test. API 28/29/30 calls are guarded. These are debuggable local diagnostic tools, not production distribution builds; `run-as` retrieval is intentional. Backups are disabled.

| Project / APK basename | Package | Purpose |
|---|---|---|
| `flatscreen-test` | `org.framemedialab.flatscreen` | Ordinary Activity, animation, pointer/touch, keyboard, scrolling, dimensions, lifecycle |
| `diagnostics` | `org.framemedialab.diagnostics` | Widevine + ClearKey session probes and advertised video codecs |
| `media-test` | `org.framemedialab.media` | Actual clear MediaCodec video and PCM AudioTrack playback |

## Build on the Mac

Run from `frame-media-lab/`:

```sh
python3 scripts/build_android.py --check
python3 scripts/build_android.py
# Equivalent CLI entry, when using the toolkit:
./frame-media-lab build-android
```

The complete build configuration is `scripts/build_android.py` plus each manifest and Java source tree. It invokes the existing Android SDK directly: javac → D8 → AAPT2 → zipalign → apksigner. This avoids Gradle, Android Gradle Plugin and Maven dependency downloads. No wrapper binary or network bootstrap is needed. The build never installs software or accepts SDK licenses.

Prerequisites (installed on this Mac on 17 September 2026):

1. JDK 17 on `PATH`, including `java`, `javac`, `jar` and `keytool`.
2. Android SDK platform **Android 15 / API 35**, package `platforms;android-35`.
3. Android SDK Build-Tools **35.0.0**, package `build-tools;35.0.0`, containing `aapt`, `aapt2`, `d8`, `zipalign`, `apksigner` and compile-only `core-lambda-stubs.jar`.
4. Android SDK Platform-Tools for subsequent ADB operations, not for the build itself.

Google's official Mac ARM command-line archive was SHA-256 checked, then installed at `/Users/sean/Library/Android/sdk/cmdline-tools/latest`. The installed versions are Command-line Tools **22.0**, Platform 35 **revision 2**, Build-Tools **35.0.0**, Platform-Tools **37.0.1** (ADB **1.0.41**, build **15733141**). Existing Homebrew JDK **17.0.19** is used. Only the required `android-sdk-license` was accepted for the three explicitly requested packages. No Android Studio, emulator, system image, Gradle or additional JDK was installed.

`lab/android_sdk.py` supplies shared SDK discovery for the builder, doctor, local ADB calls and printed connection plans: explicit build `--sdk`, then `FML_ANDROID_SDK`, otherwise existing `ANDROID_HOME`, `ANDROID_SDK_ROOT`, `~/Library/Android/sdk`, `~/Android/Sdk`. Missing automatic candidate directories are skipped. An explicit `--sdk`/`FML_ANDROID_SDK` override never silently selects another SDK. SDK binaries take precedence over PATH where present; PATH is a fallback. No global environment or shell profile was changed. The old `ANDROID_HOME=/opt/homebrew/share/android-commandlinetools` remains untouched and is skipped because it does not exist.

```sh
# Normal rebuild and verification; no environment changes needed on this Mac:
./frame-media-lab build-android
./frame-media-lab doctor
./frame-media-lab discover  # adb devices -l; starts the local ADB server if needed
# Optional SDK override scoped to this invocation:
FML_ANDROID_SDK=/absolute/path/to/sdk ./frame-media-lab doctor
./frame-media-lab build-android --sdk /absolute/path/to/sdk
# Only for explicitly installing missing packages on another machine:
"$HOME/Library/Android/sdk/cmdline-tools/latest/bin/sdkmanager" \
  --sdk_root="$HOME/Library/Android/sdk" \
  'platforms;android-35' 'build-tools;35.0.0' 'platform-tools'
```

The installed sdkmanager works with Java 17, although Google now prints a deprecation notice recommending the bundled `android sdk` command. No migration is needed for this build.

Outputs: `build/android/flatscreen-test-debug.apk`, `diagnostics-debug.apk`, `media-test-debug.apk`. The local signing identity is retained under `build/android/private/debug.keystore` so subsequent `adb install -r` works. It is a debug key with standard debug passwords and must never be used for release signing. Build temporary files, Java preferences and Android user files are directed beneath `build/android/`; nothing writes a global Gradle cache. Deleting that private key changes APK identity and may require explicitly uninstalling older builds before installation.

**All three APKs compiled successfully on 17 September 2026.** The first real build exposed missing lambda bootstrap stubs in javac's bootclasspath. Adding the SDK's `core-lambda-stubs.jar` fixed it; D8 desugars the lambdas and the stub classes are not packaged. No Java app code, API guards, manifests or intended functionality changed. A regression test compiles an Android listener lambda through the same bootclasspath helper. The diagnostics build emits a deprecation note for `MediaDrm.release()`; the method remains supported on the target API range.

Each APK was checked using `inspect-apk`, AAPT2 badging, apkanalyzer manifest/DEX inspection, ZIP CRC checks, zipalign and apksigner. Full results, APK SHA-256 hashes and API-level reasoning are in [Android validation](ANDROID_VALIDATION.md). ADB version and empty device enumeration passed. `doctor` recognises the SDK, sdkmanager, aapt/aapt2 and working ADB; Frame SSH/Android connectivity remain **NOT TESTED**. No Android app was installed or run.

## Installation and launcher resolution

Select the Android guest serial, not Frame's Linux USB endpoint. Install helpers one at a time in a fresh development session initially: Lepton's postinstall code uses a common application directory. These commands change the Android guest and are explicit test actions. For the raw commands below, first set the terminal-local variable `ADB="$HOME/Library/Android/sdk/platform-tools/adb"` (adjust for a custom SDK). The toolkit itself needs no PATH changes, and `connection-plan` prints the discovered executable path.

```sh
"$ADB" -s "$SERIAL" install -r build/android/diagnostics-debug.apk
"$ADB" -s "$SERIAL" shell cmd package resolve-activity --brief \
  -a android.intent.action.MAIN -c android.intent.category.LAUNCHER \
  -p org.framemedialab.diagnostics
"$ADB" -s "$SERIAL" shell am start -S -W -n org.framemedialab.diagnostics/.MainActivity
"$ADB" -s "$SERIAL" exec-out run-as org.framemedialab.diagnostics cat files/diagnostics.json
```

Wait until `complete` is true and check `run_id`/`timestamp` changed before importing the result. `am start -W` proves Activity launch, not probe completion. A fresh launch writes `complete:false` before querying. A per-property or session failure is evidence and still permits `complete:true`; a top-level probe/export failure does not. The UI offers **Run DRM + codec probe** and a Storage Access Framework export action. On Lepton the file picker may be absent; ADB export remains available.

For the flatscreen probe substitute `flatscreen-test-debug.apk` and `org.framemedialab.flatscreen/.MainActivity`. A successful Android screenshot is not a headset observation. Record headset visibility, pointer/button/keyboard behavior, scrolling, resize, Home/Back and relaunch independently. The lifecycle list is in-memory for the current Activity; destruction followed by relaunch starts a new list.

With a built APK copied to Frame, this source-supported host command explicitly requests the ordinary panel:

```sh
# REMOTE FRAME COMMAND; starts a runtime context and may install the APK
APP_WANTS_FLATSCREEN=true lepton start /absolute/path/flatscreen-test-debug.apk
```

For an already running development context, use resolved `am start` via ADB or `lepton run dev am start -n ...`. Do not assume automatic launcher selection or create a second dev context over an existing one.

## Diagnostic evidence contract

`files/diagnostics.json` has `schema_version:1`, `synthetic:false`, `run_id`, UTC `timestamp`, `finished_at`, `complete`, `device`, `widevine`, `clearkey`, and `codecs`.

A scheme result contains `supported` (boolean or unknown/null), `construction`, `properties`, and `session`. Construction is `SUCCESS`, `UNSUPPORTED_SCHEME`, `ERROR`, or `NOT_TESTED`. Session `status` is `OPENED`, `PROVISIONING_REQUIRED`, `RESOURCE_BUSY`, `ERROR`, or `NOT_TESTED`; `security_level` is the integer returned by `getSecurityLevel(sessionId)` and `security_level_name` is its Android API constant name. A property called `securityLevel` is separately reported and is never substituted for an actual session measurement. API-level limitations and exceptions remain explicit.

The only plugin string properties queried are `vendor`, `version`, `description`, `algorithms`, and `securityLevel`. Connected and maximum HDCP are API enum integers, not resolution or secure-output proof. The app has **no network permission**, requests no device identifiers, retrieves no credentials, makes no license/provisioning requests, and changes no security-level properties. Exception classes are exported; vendor exception messages are suppressed to avoid accidental sensitive payload disclosure. Widevine and ClearKey sessions are closed and objects released.

`MediaCodecList.ALL_CODECS` covers every video decoder, including AVC, HEVC, VP9 and AV1 when exposed. Records include MIME/name, hardware/software/vendor flags, alias/canonical identity, profiles/levels, ranges/alignment, 1080p/4K size-rate support and adaptive/secure/tunneled/low-latency features. `null` means API unavailable/unknown. These records say `evidence:ADVERTISED`, `configured:false`, `actually_used:false`; they are not a playback test or proof of protected composition.

## Clear media operation

Install `media-test-debug.apk`, then use **Choose file** (SAF) or an explicit source:

```sh
"$ADB" -s "$SERIAL" shell am start -S -W -n org.framemedialab.media/.MainActivity \
  --es source 'https://YOUR-CONTROLLED-SERVER/clear-fixture.mp4'
"$ADB" -s "$SERIAL" exec-out run-as org.framemedialab.media cat files/media.json
```

Only absolute local paths and `file:`, `content:`, `http:`, `https:` URIs are accepted. A content URI needs a grant from the picker/provider; passing an arbitrary content URI through ADB does not grant read access. ADB-pushed shared storage can be inaccessible under scoped storage. A deterministic local alternative is copying into this debug app's private directory:

```sh
"$ADB" -s "$SERIAL" shell run-as org.framemedialab.media mkdir -p files
# This writes only the explicitly selected app-private fixture.
"$ADB" -s "$SERIAL" exec-in run-as org.framemedialab.media tee files/clip.mp4 < /absolute/path/to/generated-1080p.mp4 > /dev/null
"$ADB" -s "$SERIAL" shell run-as org.framemedialab.media pwd
# Substitute the returned app directory if different:
"$ADB" -s "$SERIAL" shell am start -S -W -n org.framemedialab.media/.MainActivity \
  --es source /data/user/0/org.framemedialab.media/files/clip.mp4
```

The URI appears in the input field but is never put into the JSON. Only `source_kind` is exported. The app makes the requested media fetch and Android itself may log network errors; keep platform logs private and redact before sharing. HTTP is enabled explicitly for generated clear fixtures on a trusted LAN. No credentials UI, custom auth headers or adaptive manifest player is provided. The platform extractor's supported progressive containers/codecs apply; use the generated MP4/WebM fixtures, not protected streams, DASH or HLS manifests.

Every Activity launch immediately replaces `files/media.json` with a fresh `schema_version:1`, `synthetic:false`, `complete:false`, `state:IDLE`, UTC `timestamp`, and UUID `launch_id`. This happens before creating the UI or starting playback, including after `install -r` retained old app data. This initial record has no playback `run_id`, decoder or frame measurements. Every subsequent playback snapshot carries this same `launch_id` and its own new `run_id`; collectors should first capture the launch identity, then require matching identity for playback evidence. Callbacks from an older Activity cannot overwrite a newer launch's export. If invalidation fails, the old export is deleted rather than left available as apparent current evidence.

The player configures a decoder selected for the actual source format, records `video_selected_decoder`, instantiated `video_decoder`, hardware/software flags, configured/started/actually-used states, source dimensions/rate, decoder output dimensions/crop, surface size, EOS/errors, PCM byte count, AudioTrack playback-head frames and underruns. Source size, decoded output size, Android surface size and headset visibility are distinct fields. Codec output format is never dumped wholesale.

Frames submitted to the Surface and `OnFrameRenderedListener` callbacks are counted separately. `observed_submission_fps` measures submission cadence, not final-headset frames. There is no portable public dropped-frame counter in this probe: `dropped_frames:null` and an explanatory availability string are deliberate. It does not infer drops by subtracting callbacks, which may arrive late. The player paces output to source timestamps using a shared monotonic clock. It is a diagnostic player, not a production A/V sync implementation: long-term audio clock drift, surround, HDR, subtitle tracks, seeking, adaptive streaming and background playback are not implemented. Mono/stereo 16-bit or float PCM is supported. Audio errors do not erase a successful video decode result.

Stop, leaving the Activity, or losing the Surface cancels playback and releases decoder/AudioTrack resources from their owning workers. Decoder and audio-write stalls are bounded; native extractor/network setup follows Android's own network behavior and may not stop immediately. Restart uses an independent evidence object. A process-wide ownership gate prevents a second player from taking the Surface/decoder path until the old video and audio workers have actually released their resources. A replacement request stays pending with Play disabled while cancellation completes. After five seconds without release, the Activity writes `complete:false`, `state:NEEDS_FORCE_STOP`, `teardown_status:CANCELLATION_TIMEOUT` using its current `launch_id`, clears the request and starts no replacement. Explicitly force-stop and relaunch the app to recover; cleanup failures also retain ownership. The timeout never pretends that a stuck native worker released resources. A run's `complete` means the probe finished, not that video was visible or sound audible. Export updates once per second while visible, on stop/pause, and after worker completion. A stopped app does not intentionally continue media playback. If a native call delays teardown, `complete:false` remains explicit; force-stop the diagnostic package if needed and record that failure.

## Required device checks

When an Android test runtime is available, install on a disposable device or optional separately installed emulator first: launch all three apps; verify UI input/resize; re-probe and retrieve a new completed diagnostics JSON; exercise unsupported/provisioning outcomes where available; compare codec enumeration to actual clear playback; test AVC/AAC, each additional fixture, missing/invalid URI, audio-less content, stop/restart/Home and surface recreation. Then repeat on Frame and separately observe its headset/audio. Emulator results are not Frame evidence.

API references: [MediaDrm](https://developer.android.com/reference/android/media/MediaDrm), [MediaCodec](https://developer.android.com/reference/android/media/MediaCodec), [VideoCapabilities](https://developer.android.com/reference/android/media/MediaCodecInfo.VideoCapabilities), [MediaExtractor](https://developer.android.com/reference/android/media/MediaExtractor), [AudioTrack](https://developer.android.com/reference/android/media/AudioTrack).
