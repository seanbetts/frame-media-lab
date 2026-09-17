# Implementation notes

Implemented and validated on 17 September 2026 in `frame-media-lab/`. No physical Steam Frame was available. Nothing was committed or pushed; no repository was initialised, the explicitly authorised minimal Android SDK was installed on the follow-up; no parent or shell configuration was changed.

## Architecture decisions

- Python 3.10+ standard library: maintainable modules, structured JSON, bounded subprocesses and explicit transport scopes without a dependency tree.
- Platform-only Java Activities: ordinary flatscreen UI; MediaDrm/codec diagnostics; separate clear MediaCodec/AudioTrack player. Direct existing-SDK build avoids downloading a Gradle/plugin dependency graph.
- Default host inspection never invokes Lepton because its pre-dispatch code can migrate Podman and manage services. Lepton ps/help/version require an explicit runtime flag. Podman container inspection is separately opt-in.
- Read-only Python scripts run via SSH stdin; no script files are written on Frame. Host Python is optional and missing support is recorded, not automatically installed.
- Structured report evidence stays separate from command snapshots, manual headset observations, advertised API capabilities and actual playback.
- Bundle synthetic/live identity and private target binding prevent accidental evidence mixing. Media launch/run IDs prevent stale exports from describing a new test. Declined commercial tests are persisted as skipped.
- Comparison uses exact public-overlay paths. A source archive without built rootfs cannot establish that a missing binary is proprietary/host-only. Such comparisons remain UNKNOWN rather than fabricating certainty.
- Logs are bounded, opt-in and redacted before storage. Reports say REVIEW BEFORE SHARING rather than falsely guaranteeing that arbitrary vendor logs/free text can never contain a secret.

The supplied request already specified scope and authorised planning followed by implementation. No additional design-approval pause was needed. The brainstorming/planning, subagent-development, test-first and verification workflows were used proportionately, with no skill-requested commits because the user explicitly prohibited commits.

## Implemented deliverables

| Area | Implementation |
|---|---|
| Mac CLI | Doctor, discovery, inspect, Android baseline, DRM/codecs/media export, APK inspect/install/resolve/launch, clear play, log snapshots, compare, reports, first-hour, connection plans, build, media generation, redaction, source verification |
| Configuration | JSON plus FML environment overrides; host/user/port, ADB method/serial, context, results and timeout |
| Host inspection | OS/kernel/CPU, tool/package identity, Lepton/rootfs version files, context paths, devices, sockets, auto-install inventory |
| Shipping overlay | Relative paths, type, permissions, owner/group, size, safe SHA-256, package ownership, media/DRM concept flags; no component file copying |
| Mount/component correlation | Scoped Podman fields, guest/process mountinfo, bounded effective library hashes, conservative exact-path comparison |
| Android baseline | Getprop, package/features/libraries, service list, dumpsys service list, lshal, WebView, device and component paths |
| Flatscreen app | Buttons, text, scroll, animation, dimensions, touch/pointer and lifecycle evidence; no OpenXR |
| Diagnostics app | Widevine/ClearKey scheme/creation/session/errors, actual security API level, safe properties, HDCP, ALL_CODECS video capabilities and structured export |
| Clear player | Explicit local/content/HTTP(S) source, actual selected codec/output, frame counters/cadence, audio state, dimensions, errors and JSON; no DRM |
| APK inspector | Text/binary XML, launcher aliases, SDK/version/ABI, permissions/features, splits, native libraries, intent/deep-link and reference hints |
| Reporting | All requested sections, five service rows, browser baseline, failure boundaries, FACT/INFERENCE/UNKNOWN, explicit synthetic labels |
| First-hour | Ten resumable stages, runtime instructions, explicit install/launch confirmations, fresh exports, human observations, evidence-based service priority |
| Fixture/media tooling | Fifteen synthetic scenarios; generated AVC/HEVC/VP9/AV1 clips at 1080p and 4K with AAC |
| Documentation | README, architecture/future UX, safety, service testing, tests, Android build/app guide, fixture guide and implementation plan |

## Dependencies and current build state

The Mac has Python, OpenSSH, JDK 17.0.19, ffmpeg/ffprobe and Ruff. The authorised follow-up installed Google's Command-line Tools 22.0, Platform 35 revision 2, Build-Tools 35.0.0 and Platform-Tools 37.0.1 at `/Users/sean/Library/Android/sdk`. Only `android-sdk-license` was accepted for those packages. No Studio, emulator, system images or global shell edits.

**All three APKs compiled and passed independent artifact verification.** Rebuild with `./frame-media-lab build-android`; outputs and the retained private debug key are in `build/android/`. The build itself still never downloads or installs anything. `lab/android_sdk.py` centralises SDK/ADB lookup and supports `FML_ANDROID_SDK`; stale nonexistent automatic environment paths are skipped. Connection plans print the resolved ADB path.

The initial real javac build failed with `cannot find symbol: metafactory(...)` / `Unable to find method metafactory`. Root cause was the absent compile-only SDK lambda stubs on the Java 8 bootclasspath. `scripts/build_android.py` now includes `core-lambda-stubs.jar` and checks that prerequisite. An executable Android listener-lambda regression test failed before the fix and passes after it. No app Java sources or manifests were changed. AAPT2/apkanalyzer confirm only app and D8-generated classes, with no bundled SDK stubs or OpenXR/native libraries. See [Android validation](docs/ANDROID_VALIDATION.md).

## Verification results

- **52 automated tests passed** via `make check`.
- **Python syntax: 26 files passed.** Ruff lint and formatter checks passed; no third-party type checker was installed or required.
- **15 synthetic CLI first-hour scenarios passed**, each with synthetic provenance and a generated report. Validation bundles are under `build/validation-results/`.
- **6 real binary-manifest fixtures** in the supplied Lepton archive parsed successfully, yielding package, minimum SDK and launcher Activity, without modifying the archive.
- **7 Java sources passed syntax parsing.** Seven Android contract/pure-Java/preflight/SDK tests pass, including source URI restrictions, launch-evidence identity and decoder ownership.
- **8 real generated clips passed ffprobe:** H.264, HEVC, VP9 and AV1; each 1920×1080 and 3840×2160 at 24 fps with AAC. Short two-second validation clips occupy about 27 MiB. The installed ffmpeg lacks libaom-av1, so AV1 generation used its available libsvtav1 encoder.
- Doctor passes all local prerequisites including working ADB; Frame SSH and Android endpoint remain NOT TESTED. ADB 37.0.1 returns an empty device list, as expected. SSH/direct/USB connection plans were checked against installed ADB syntax without connecting to a target.
- The existing CLI build produced three signed APKs. Own inspector and official AAPT2/apkanalyzer agree on package, version 0.1.0 (1), minSDK 26, targetSDK 34 and MAIN/LAUNCHER activities. ZIP integrity, DEX inventory, alignment, permissions and debug certificate verification pass; APK SHA-256 hashes are recorded. No app installation/launch, emulator or physical Frame test occurred.
- Read-only/default command definitions were checked against prohibited operations. Actual tests cover target/quoting failures, timeout handling, secret masking, non-followed symlinks, skipped collection, absent packages remaining UNKNOWN and stale/mixed evidence rejection.
- **361 protected files** (the current `Lepton/` archive plus `LEPTON_MEDIA_INVESTIGATION.md`) matched their initial SHA-256 snapshot. No changes detected. Archive layout differs from the earlier report's old absolute directory name and original file-count scope; the baseline covers the actual protected paths supplied here.

Evidence: `build/check-validation.txt`, `build/verification.json`, `build/android-build-status.json`, `build/source-baseline.json`. Follow-up installation/build/ADB/API evidence is in `build/sdk-setup/`; APK independent inspections and hashes are in `build/android/validation/`. The follow-up reran the `l1` first-hour scenario and regenerated its report with synthetic provenance intact. A complete current example is `results/2026-09-17T21-04-56-14ff013a-SYNTHETIC/report.md` and its JSON companion. Generated/build/result evidence is intentionally ignored by Git.

Independent review caught and prompted fixes for HDCP schema mismatch, missing service/DRM failure classification, stale media exports, retained answers on explicit retry, a declined-commercial-stage bug, target mixing on resume and overlapping decoder ownership. Regression tests cover these. The scoped re-review found one remaining stale-report path; that was reproduced, fixed and tested so old completed video results are excluded when a new launch is expected.

## Known limitations and intentional deferrals

- Android API compilation and a source/compiled-bytecode/API-metadata guard audit passed. Actual API 30 and API 34/35 execution, Android error handling and media lifecycle still require device/runtime testing.
- The player is a progressive clear-file diagnostic, not an adaptive/HLS/DASH/DRM production player. No subtitles, seeking, background playback, surround/HDR or long-term A/V clock correction. Dropped frames are explicitly unavailable; callbacks/submissions are not final-display counts. Native network/extractor stalls may require explicitly force-stopping our app; no replacement decoder starts while resources remain owned.
- Remote Python, pacman, Podman metadata fields and Android shell APIs depend on shipping availability. Permission-denied/missing tools remain recorded unknowns. No fallback package installation occurs.
- Effective component hashes use the ADB-shell namespace. APEX and consuming-media-service namespaces need targeted live correlation; no automatic secure allocation test or protected-content capture is performed.
- Source/built-rootfs and proprietary-overlay equivalence cannot be completely resolved from this source archive. No automatic rootfs extraction, arbitrary file copying or binary reverse engineering is included.
- APK resource references and signature relationships are not resolved by the lightweight parser. Android performs signature/split installation checks; install-multiple accepts only explicitly selected files.
- First-hour starts Lepton through supported manual UI/separate-terminal instructions. This avoids owning/killing a long-lived launcher or implicitly applying its setup side effects. Endpoint changes require an explicit rebind; different host/context requires a new bundle.
- Each standalone collector makes a new bundle unless `--bundle` is supplied. Use a shared bundle for a single investigation and separate bundles for independent media performance runs. There is no multi-run database or automatic provider benchmarking.
- Redaction is conservative best effort, not a guarantee for unknown free-text formats. `target.local.json` must never be shared. Raw logs are not retained by default or offered as a bulk export.
- Polished Steam per-service launch wrappers are documented but deferred until actual app compatibility is known.

## Requires a physical Steam Frame

Shipping proprietary/component identities and package ownership; effective overlay/APEX precedence; actual Android version/ABI/GMS configuration; legitimate Widevine support/provisioning/session security; real hardware and secure decoding; enforced protected buffers/import/composition; ordinary panel visibility and controller/text interaction; clear-video smoothness/audio/sync; service install/login/licence/visible playback and measured quality; persistence/callback behavior; HDR, thermals, power and comfort. Every such result remains NOT TESTED or UNKNOWN here.
