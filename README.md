# Frame Media Lab

A Mac-side toolkit for investigating Steam Frame's Android/Lepton media capabilities: shipping components, ordinary 2D apps, actual MediaDrm sessions, clear video decoding and authorised streaming-app playback.

The goal is to establish whether Apple TV, Disney+, HBO Max, Netflix and YouTube provide a useful standalone experience. **There are no physical Frame results yet.** All three Android APKs have now compiled against Platform 35 and passed local manifest, DEX, alignment and debug-signature inspection. SDK tooling and ADB are installed; Android execution, DRM sessions and playback remain **NOT TESTED**. The build command checks prerequisites and installs nothing.

## Start here

Read [CONTEXT.md](CONTEXT.md) first for the practical question, prior user-provided browser observations, shipping-component hypothesis and FACT / INFERENCE / UNKNOWN evidence rules. For a fresh investigation once Frame is physically connected, use [START.md](START.md) as the session prompt; its opening statement describes that future session, not a recorded hardware result. Read the current documentation and CLI help before acting on the device.

Run from this directory with Python 3.10 or newer:

```sh
./frame-media-lab doctor
make check
./frame-media-lab --synthetic l1 first-hour
./frame-media-lab build-android
```

The synthetic command creates a clearly labelled demonstration report. An L1-like fixture proves report behavior only. A missing-SDK build exits with exact instructions; see [Android build and app guide](docs/ANDROID.md). No pip packages are required for the CLI. On 17 September 2026, Java 17 and ffmpeg are available, and the SDK is installed at `~/Library/Android/sdk`: Command-line Tools 22.0, Platform 35 revision 2, Build-Tools 35.0.0 and Platform-Tools 37.0.1. Project-local discovery handles the stale global `ANDROID_HOME` without editing shell profiles. See [compiled APK validation](docs/ANDROID_VALIDATION.md) for artifact hashes, API audit and remaining runtime checks.

## When Frame arrives

Enable developer access through Valve's supported UI. Establish SSH trust yourself in a terminal first; the toolkit requires an already-known host key and noninteractive SSH authentication. It never disables host-key verification.

```sh
cp config/example.json config/local.json
# Edit host, port, context and eventually the explicit Android guest serial.
./frame-media-lab --config config/local.json doctor
./frame-media-lab --config config/local.json first-hour
```

Global options precede the command. Configuration is loaded only with `--config`; environment overrides are `FML_HOST`, `FML_SSH_USER`, `FML_SSH_PORT`, `FML_ADB_METHOD`, `FML_SERIAL`, `FML_CONTEXT`, `FML_RESULTS_DIR`, `FML_TIMEOUT`. CLI `--host`, `--serial` and `--results` override those. Relative results paths are relative to your current directory. There is no hard-coded address or network scan.

The workflow saves after every stage and observation. It pauses if Android is unavailable; completed stages are retained. Open **Lepton Development** manually or use the printed command in a separate SSH terminal. Confirm its actual port with the explicit runtime probe if necessary:

```sh
./frame-media-lab --config config/local.json runtime-probe --allow-runtime-changes
# Substitute the OBSERVED guest port; this only prints commands:
./frame-media-lab --config config/local.json connection-plan --method ssh --guest-port 5556
```

The plan prints an SSH tunnel, `adb connect`, and an Android identity check. Direct LAN and USB-host forwarding are also supported. USB ADB may initially target SteamOS, not Android. Set the resulting guest serial in configuration before resuming. When a serial changes, `--rebind-adb` is an explicit assertion that it is still the same Frame/context; other target changes require a new bundle.

```sh
# Use the exact directory printed by the previous command:
./frame-media-lab --config config/local.json --bundle results/YOUR-RUN --rebind-adb first-hour
# Deliberately repeat a completed/failed observation stage:
./frame-media-lab --config config/local.json --bundle results/YOUR-RUN first-hour --retry-stage 06-flatscreen
```

The workflow confirms helper installation and Activity launches, asks what you see/hear in the headset, tests clear H.264 before more demanding clips, summarises DRM evidence, and offers an optional commercial-app test. Account credentials are entered only in the app. Declining that decision skips the commercial stage. Each helper should initially be tested in its own Development session because Lepton's postinstall handling uses a common APK directory. No session is automatically stopped or reset.

## Individual commands

Each collecting command creates a unique private bundle unless `--bundle` is supplied. Use the same bundle for related evidence:

```sh
./frame-media-lab --config config/local.json inspect
# Set RUN to the exact printed bundle directory:
RUN=results/YOUR-RUN
./frame-media-lab --config config/local.json --bundle "$RUN" android-status
./frame-media-lab --config config/local.json --bundle "$RUN" drm
./frame-media-lab --config config/local.json --bundle "$RUN" codecs
./frame-media-lab --config config/local.json --bundle "$RUN" effective-components
./frame-media-lab --bundle "$RUN" compare
./frame-media-lab report "$RUN"
```

`drm` and `codecs` retrieve JSON from our already-installed/running diagnostics app; they do not install it. `media-result` retrieves the clear-player export. `inspect --containers` additionally permits Podman metadata queries, which can initialise its runtime. Default inspection does not invoke Lepton or Podman's container-management queries.

```sh
./frame-media-lab inspect-apk /path/to/authorised.apk
./frame-media-lab inspect-apk /path/to/authorised.apks
./frame-media-lab --config config/local.json install-apk /path/to/base.apk /path/to/matching-split.apk
./frame-media-lab --config config/local.json resolve com.example.app
./frame-media-lab --config config/local.json launch com.example.app/.ActualLauncher
./frame-media-lab --config config/local.json play https://YOUR-TRUSTED-SERVER/h264-1080p.mp4
./frame-media-lab --config config/local.json --bundle "$RUN" collect --logs
./frame-media-lab --bundle "$RUN" record-service disney
```

APK ZIP/manifest inspection is local and does not execute APK code. `.apks`/`.xapk` members can be inspected but are not automatically extracted or selected for installation. Supply an explicit authorised base/split set. The inspector supports binary Android XML and Activity aliases without SDK dependencies. It does not resolve resource-backed manifest values or certify signatures.

## What we know

The primary specification is [the existing investigation](../LEPTON_MEDIA_INVESTIGATION.md), particularly §§3–8, 10–13 and 15. Public Lepton supports normal Activities, ADB/APK installation and an explicit flatscreen request. OpenXR is not required. The host `/usr/share/guestos/android` can supply guest components absent from the public source. The public default media/allocator/HWC implementations do not establish a complete protected-video path; shipping replacements are possible and unmeasured.

Even `lepton ps` and `lepton help` can trigger Podman migration/service setup before command dispatch. The toolkit therefore treats them as explicit runtime operations. Overlay file order does not prove precedence: duplicate destinations may fail, and APEX/service namespaces matter. Public source absence is not proof that a binary is proprietary or missing on Frame.

User-provided browser baseline, not retested here:

| Service | Bazzite Chrome | macOS Chrome | macOS Safari |
|---|---|---|---|
| Netflix | 1920×1080 | 1920×1080 | 1920×1080 |
| Disney+ | 854×480 | 854×480 | 1920×1080 |
| HBO Max | 1024×576 | 1024×576 | 1920×1080 |
| Apple TV | Playback fails | Playback fails | ~3840×1920 |
| YouTube | 3840×2160 | Not tested | Not tested |

Chrome reported Software Secure. Bazzite GPU acceleration/hardware decoding and a Windows user-agent spoof did not improve Disney+. Android/native testing is therefore most valuable for Disney+, Apple TV and HBO Max. Netflix Android may do worse than browser 1080p if only software-secure sessions are available.

## Safety and evidence

Read [SAFETY.md](docs/SAFETY.md) before hardware use. The toolkit never installs host packages, disables SteamOS read-only protection, resets Podman, modifies Valve's installation/overlay, provisions DRM, requests licences, extracts credentials or spoofs identities. Explicit `install-apk`, `launch`, `play` and `connect-adb` change only the named app/connection state. The guided workflow confirms those actions.

Results contain structured JSON, filtered/redacted command output and concise Markdown/JSON reports. `target.local.json` is **RAW / MAY CONTAIN SENSITIVE DATA**, retained only to bind a bundle to its target. Share only reviewed `report.md`/`report.json`, not entire bundles. Automated redaction cannot promise arbitrary free text is secret-free. No raw log retention is enabled; logcat is opt-in, bounded and tag-filtered.

An actual MediaDrm session security result is kept separate from plugin properties and secure-codec advertisements. Headset visibility requires your observation. Actual source/decoder resolution is kept separate from Android window and SteamVR panel size. No successful provisioning, protected playback, service quality, HDR or efficiency is inferred from a filename or feature flag.

## More detail

- [Architecture and future launcher path](docs/ARCHITECTURE.md)
- [Test plan and acceptance boundaries](docs/TEST_PLAN.md)
- [Service testing](docs/SERVICE_TESTING.md)
- [Fixture generation](fixtures/media/README.md)
- [Implementation notes and verified limitations](IMPLEMENTATION_NOTES.md)
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)

## Repository scope

Git is initialised on `main` inside `frame-media-lab/`, with initial commit `fe54a6d` (`Initial commit of Frame Media Lab`). The parent directory, `../Lepton/` and `../LEPTON_MEDIA_INVESTIGATION.md` are outside this repository. Keep those sibling resources alongside the toolkit for source investigation; cloning this repository alone will not include them.

Source, documentation, tests and synthetic fixture definitions are tracked. Builds, local device configuration, generated videos, signing keys and result-bundle contents are excluded by `.gitignore`; `results/.gitkeep` preserves the empty results directory.
