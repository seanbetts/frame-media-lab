# Steam Frame media investigation: decision context

Prepared 17 September 2026, before hardware arrival. **No Steam Frame has been connected or tested. All Frame runtime, DRM, decoder, headset and service-quality results remain UNKNOWN / NOT TESTED.** Local builds and synthetic reports are preparation, not device evidence.

This is a reasoning handoff for a fresh coding agent. The detailed source authority is [LEPTON_MEDIA_INVESTIGATION.md](../LEPTON_MEDIA_INVESTIGATION.md), especially §§3–8 and 15. Use the current [README](README.md), [implementation notes](IMPLEMENTATION_NOTES.md) and [Android validation record](docs/ANDROID_VALIDATION.md) for toolkit behavior and the dated preparation baseline.

## The practical question

Sean is considering/obtaining a Steam Frame and wants a genuinely useful **standalone media-streaming device** for Apple TV, Disney+, HBO Max, Netflix and YouTube. This is not primarily generic Lepton research.

Can Frame provide good-quality standalone streaming through its browser or through those services' Android apps running under Lepton? The Android route matters because prior browser testing exposed substantial service-specific limitations. Installation or an attractive virtual screen alone does not answer the question; actual service playback and source quality do.

## Evidence rules — read before interpreting any result

Keep these evidence layers separate:

**ADVERTISED CAPABILITY → ACTUAL API/SESSION RESULT → ACTUAL DECODER USE → HEADSET OBSERVATION → ACTUAL STREAM QUALITY.**

An observation in one layer does not establish the next. Record the precise test, provenance and boundary of each claim.

| Observation | Does **not** establish |
|---|---|
| A Widevine filename | Working Widevine |
| `MediaDrm.isCryptoSchemeSupported(Widevine)` | A successful Widevine session |
| `securityLevel="L1"` property | An actual L1 session |
| An actual `HW_SECURE_ALL` / L1-like session | Working end-to-end protected video |
| A secure decoder advertised | That decoder successfully configured or used |
| A hardware decoder advertised | Actual hardware decoding |
| A decoder advertising 4K | 4K playback |
| A 4K Android window | A 4K video stream |
| A 4K SteamVR panel | A 4K source stream |
| APK installation | Activity launch |
| Activity launch | Working login |
| Login | Catalogue access |
| Catalogue access | DRM licence success |
| DRM licence success | Secure decoding |
| Secure decoding | Visible protected video |
| Visible video | HD/4K video |
| A black screenshot | Failed playback |

If protected video is visible in the headset but black in screenshots/capture, that **may be successful capture protection**. Conversely, a non-black screenshot of protected content may indicate an unprotected path. Neither capture outcome alone proves the security of the complete pipeline; correlate it with direct headset observation and API/decoder evidence.

Continue using these labels:

- **FACT:** Directly observed in source, shipping-device inspection, an actual API result, actual playback, documented primary-source material or a narrowly defined test. State which: a source FACT is not a shipping Frame FACT, and a user report is not an independently repeated measurement.
- **INFERENCE:** Strongly suggested by architecture or observed behavior but not directly established.
- **UNKNOWN:** Missing runtime, device or provider evidence is required. Unavailable or permission-denied evidence is not evidence of absence.

Never upgrade an inference to fact merely because it seems technically likely. Keep synthetic evidence explicitly labelled and separate from live runs. Query security for the **opened session**; `MediaDrm.getMaxSecurityLevel()` is a request constant, not a device measurement.

## Prior browser observations and why Android matters

**USER-PROVIDED OBSERVATIONS — prior tests, not Frame results, not independently retested here.**

| Service | Bazzite Chrome | macOS Chrome | macOS Safari |
|---|---|---|---|
| Netflix | 1920×1080 | 1920×1080 | 1920×1080 |
| Disney+ | 854×480 | 854×480 | 1920×1080 |
| HBO Max | 1024×576 | 1024×576 | 1920×1080 |
| Apple TV | Playback fails | Playback fails | ~3840×1920 |
| YouTube | 3840×2160 | Not tested | Not tested |

Chrome reported Widevine as **Software Secure on both Bazzite and macOS**. Bazzite used an **RTX 5090**; GPU acceleration and hardware video decoding were successfully enabled. This did not change Chrome's Software Secure status, and Disney+ remained 854×480. Spoofing a Windows Chrome user agent also did not improve Disney+. Safari dramatically improved Apple TV, Disney+ and HBO Max compared with Chrome.

**INFERENCE:** Browser/DRM/service policy matters. Chrome behaved remarkably similarly on Linux/x86 and macOS/ARM; “Linux is bad for streaming” does not adequately explain the observations. Hardware video decoding and DRM security are distinct. Desktop Chrome's CDM status does not establish Android MediaDrm's status.

For the intended Frame use case, the observed Netflix browser 1080p is acceptable and YouTube browser 4K is strong; Disney+ 480p and HBO Max ~576p are poor, and Apple TV browser playback is questionable/non-functional in Chrome. These are comparison targets and potential fallbacks, **not verified Frame browser capabilities**.

**FACT — documented provider policy in the investigation:** Netflix's Android phone/tablet app requires Widevine L1 for HD; L3 is limited to SD. See the investigation's §8.2 and its [Netflix Android support source](https://help.netflix.com/en/node/23939?fromApp=true&netflixsource=android). Thus an L3 Android installation could be **worse** than the observed 1080p browser route. This is not a universal L3 resolution rule for all services; recheck current provider policy when testing.

## What public Lepton establishes

**FACT — inspected implementation, not hardware execution:**

- Lepton runs modified Android userspace in a rootless Podman container on the SteamOS host kernel.
- Ordinary Android ARM64 Activities have an implemented execution path. APK installation and Activity launching are supported; OpenXR is not required to launch an ordinary app.
- An explicit flatscreen/2D mechanism exists. Android content can travel through **SurfaceFlinger → Waydroid HWC → host Wayland**. Ordinary APK flatscreen presentation is normally hidden by default but can be requested; Android rendering alone does not establish headset visibility.
- `/usr/share/guestos/android` is an important host-supplied overlay. Public Lepton is not a completely self-contained runtime: graphics drivers/layers, Android Steam libraries and the SteamVR Android runtime include explicit external integration mechanisms.

**UNKNOWN from public source:** Operational Widevine, L3, L1, hardware MediaCodec decoding, secure MediaCodec decoding, protected allocation, protected composition, commercial-app compatibility, provider certification and HD/4K playback. None is established merely by the ordinary-app path.

The public defaults contain concrete concerns: software-oriented codec configuration, normal Codec2 selection disabled, protected-buffer handling that does not establish secure allocation, and no demonstrated complete protected HWC-to-host presentation route. These remain meaningful evidence about the inspected implementations; they are not immutable limits on shipping replacements.

## The shipping-component hypothesis

**INFERENCE / architectural possibility:** Public Lepton may contain only the open-source/redistributable portion of the shipping Android environment. Proprietary, licensed, device-specific or provisioned components may legitimately live elsewhere. Potential examples are a Widevine CDM, MediaDrm vendor implementation, OEMCrypto, Qualcomm DRM/media libraries, TEE/TrustZone integration, secure hardware codec services, protected allocators, device provisioning, host DRM/media brokers and protected compositor integration.

The focused source follow-up (§15) established concrete extension and replacement boundaries:

- The host overlay can inject regular files into important guest filesystem locations **before Android init**, including potential DRM HAL/service/configuration and hardware codec payloads.
- The identified insecure allocator implementations and Waydroid HWC are replaceable userspace libraries/HALs.
- An authorized host-side TEE/secure-media broker is technically possible. Protected presentation could combine guest replacements with separately shipped SteamOS, SteamVR, Gamescope and driver components.
- No unconditional architectural reason was found that makes Widevine L1 impossible in Lepton.

**THIS DOES NOT ESTABLISH THAT VALVE SHIPS ANY OF THESE DRM/SECURE-MEDIA COMPONENTS.** The physical Frame is required to determine that. Known external graphics/runtime dependencies do not imply hidden DRM; shipping could add little or nothing to the public media defaults.

The counterargument is essential: **dropping a Widevine `.so` into the overlay is not sufficient for L1.** A complete hardware-secure implementation potentially requires coordinated:

**CDM → provisioning → TEE/OEMCrypto → secure decoder → protected allocator → protected buffer transport → trusted compositor → display path → provider/device acceptance.**

The overlay is per-file read-only bind mounts, not an unconditional “host overlay wins” merge. Duplicate destinations can fail; Android APEX activation and consuming-service namespaces can change effective visibility. ABI, HAL registration, startup, codec/allocator selection and compatible host drivers/firmware must agree. Regular-file injection does not itself supply sockets/devices, trusted firmware or secure provisioning. The unchanged public clear-copy path cannot be made protected merely by a hidden host component.

## Why source absence is insufficient

Do **not** conclude “no Widevine source in the public repository → Frame has no Widevine,” or “public minigbm mishandles protected buffers → shipping Frame cannot support protected buffers.” External host/device completion and replaceable allocator/HWC implementations are established architectural facts.

The arrival question is: **WHAT ACTUALLY COMPLETES THE PUBLIC LEPTON GUEST ON SHIPPING STEAMOS?**

Inspect `/usr/share/guestos/android` as a high-priority target, plus other host integrations. A non-empty overlay proves nothing about DRM. Identify what is **actually loaded and used**, correlating package/version identity, effective paths/hashes, mounts, service registration and loaded components. File presence, source absence and “proprietary” are different claims; the public archive is not a complete built-rootfs inventory.

## What is already prepared

**Dated pre-hardware baseline, supported by README, IMPLEMENTATION_NOTES.md and docs/ANDROID_VALIDATION.md:** Frame Media Lab was built specifically to answer the questions above. Implemented preparation includes:

- Mac-side CLI and a guided, resumable first-hour workflow.
- Read-only shipping inspection, host-overlay inspection, Android baseline inspection and conservative public-versus-shipping component comparison.
- DRM/codec diagnostics, ordinary flatscreen and clear-media Android apps.
- APK inspection/install/launch tooling and service-result recording.
- Report generation/redaction, synthetic fixtures and automated tests.

The Android development environment is ready at `~/Library/Android/sdk`: Command-line Tools **22.0**, Platform **35 revision 2**, Build-Tools **35.0.0**, Platform-Tools **37.0.1**, ADB **1.0.41**, and JDK **17**. All three APKs compiled and passed independent manifest, DEX, alignment, integrity and signature validation. Packages are `org.framemedialab.flatscreen`, `org.framemedialab.diagnostics` and `org.framemedialab.media`.

The latest recorded automated verification passes: **52 tests, syntax checks for 26 Python files and Ruff**. The documentation also records 15 synthetic first-hour scenarios. These are dated local results, not a promise about future checkouts. **All apps remain runtime UNTESTED; no APK has been installed or executed on Frame.** See the Android validation record for exact artifacts, API guards and retained evidence.

## The three Android test apps

| App | Purpose and evidence boundary |
|---|---|
| **Flatscreen** — `org.framemedialab.flatscreen` | Prove that an ordinary non-OpenXR Activity can install, launch, display in the headset and receive interaction. Includes buttons, text, scrolling, animation and lifecycle/input evidence. Headset visibility requires human observation. |
| **Diagnostics** — `org.framemedialab.diagnostics` | Use legitimate Android APIs to inspect Widevine and ClearKey, actual MediaDrm session outcome/security, HDCP where available, and MediaCodec inventory: hardware/software/vendor classification, secure-playback flags and AVC/HEVC/VP9/AV1 when advertised. Capability records are not decoder-use results. |
| **Clear media** — `org.framemedialab.media` | Exercise **MediaExtractor → MediaCodec → Surface** without DRM, with audio via AudioTrack. Record actual selected decoder/output and source dimensions separately from Surface dimensions, plus frame/audio/error evidence. |

Diagnostics opens and closes sessions; it deliberately does **not** bypass DRM, request arbitrary licences, extract credentials, expose keyboxes, modify security level or perform provisioning. The clear player configures without MediaCrypto and rejects encrypted samples; it is not a protected/adaptive streaming player.

Eight short generated fixtures exist: **H.264 1080p, H.264 4K, HEVC 1080p, HEVC 4K, VP9 1080p, VP9 4K, AV1 1080p and AV1 4K**. All are two-second, 24 fps MP4 test clips with AAC audio. Local ffprobe validation does not prove Android extraction or playback. Start with H.264 1080p: clear testing separates “Frame/Lepton cannot decode this video” from “protected DRM playback is failing.” Short clips do not establish sustained performance, thermals or viewing comfort.

## First questions when Frame arrives

Investigate approximately in this order, recording unavailable evidence explicitly:

1. What SteamOS, Lepton and Android versions actually ship?
2. What is present in `/usr/share/guestos/android` and other shipping host integrations?
3. Which guest components are actually loaded, rather than merely present?
4. Does ordinary 2D Android presentation work?
5. Is Widevine supported?
6. Can an actual Widevine session be opened?
7. What security level does **that session** obtain?
8. What MediaCodec decoders are advertised?
9. Which are reported hardware accelerated? Keep actual use separate.
10. Which advertise secure playback?
11. Can clear 1080p H.264 actually decode and display?
12. Can clear 4K and other codecs actually decode and display?
13. Can protected video traverse the complete presentation path? Resolve this through legitimate playback; the clear player cannot answer it.
14. Can a commercial streaming APK install and launch?
15. Can it log in?
16. Can it obtain a legitimate licence?
17. Does protected video appear in the headset?
18. What **actual source resolution** does the service provide?

## Service priority and success criteria

Default commercial-test priority: **Disney+ → Apple TV → HBO Max → Netflix → YouTube**. The first three have the largest deficits in the prior Chrome route; Netflix already showed 1080p and YouTube 4K on the tested computers. Change the order if diagnostics or another service would answer a more fundamental question first. Ordinary YouTube uploads and protected rentals/purchases are separate tests.

An especially useful **hypothetical outcome, not a result**, would be: Widevine supported; an actual hardware-secure/L1 session; hardware AVC/HEVC/VP9/AV1 decoders present; a secure decoder present and used where required; protected video visible in the headset; Disney+ and HBO Max at 1080p+; and working high-quality Apple TV playback.

Actual end-to-end service results like those would demonstrate a material improvement over the observed Chromium baseline. Enumerating the individual capabilities does not demonstrate that outcome. A comparison specifically against Frame's browser also requires measuring that browser on Frame.

## Preserve failure boundaries

Record these separately rather than collapsing them into “the app doesn't work”:

- APK installation failure; Activity launch failure; Activity visible in an Android screenshot but absent from the headset.
- Login callback failure; Widevine unsupported; plugin present but provisioning unavailable; L3-only session; licence rejection.
- Secure decoder unavailable; protected allocator/import failure; audio with black headset video.
- Headset video visible but capture black — **potential capture protection, not necessarily a failure**.
- Playback succeeds but actual source resolution is low.

These describe different stages and may have different causes or remedies. L3 or low-resolution playback may miss the practical goal without constituting a broken app. Capture blackness and headset blackness must never be conflated.

## Safety and scope

This is legitimate compatibility testing of owned hardware and legitimately used streaming accounts/services. Initial investigation is observational and minimally invasive. Use the existing toolkit; add functionality only if a concrete investigation need requires it.

Do not circumvent DRM, extract DRM keys or device keyboxes, dump licence payloads unnecessarily, spoof security levels, defeat provider access controls, modify device provisioning, disable security mechanisms or make destructive SteamOS changes. Do not modify Valve's `../Lepton/` source unless explicitly asked later; preserve `../LEPTON_MEDIA_INVESTIGATION.md`. Do not modify `/usr/share/guestos/android` during initial investigation.

Read [SAFETY.md](docs/SAFETY.md) before hardware use. Even `lepton help`/`ps` can trigger setup before command dispatch; use the toolkit's explicit runtime boundaries. Helper installation, launches and connection changes are separate from read-only inspection. Enter account credentials only in legitimate app flows. Preserve synthetic/live provenance and target binding; review redacted reports before sharing and never share `target.local.json` or entire raw bundles.

## Starting a fresh investigation session

Suggested fresh-agent instruction:

> Read CONTEXT.md, ../LEPTON_MEDIA_INVESTIGATION.md, README.md and IMPLEMENTATION_NOTES.md. I now have the Steam Frame connected to this Mac. Use frame-media-lab to guide me through the investigation. Treat the physical shipping device as the authoritative source and preserve the project's FACT / INFERENCE / UNKNOWN evidence standard.

The expected starting commands, from `frame-media-lab/`, are approximately:

```sh
./frame-media-lab doctor
./frame-media-lab first-hour
```

Before executing anything, read the current README and CLI help: the toolkit may have changed since this context was written. Follow its supported developer-access, SSH-trust, configuration and explicit Android-endpoint steps; the current README uses `--config config/local.json` before each command for a configured target. Resume the appropriate saved bundle rather than silently mixing devices or restarting completed observations.
