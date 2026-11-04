# Steam Frame media investigation: decision context

Prepared 17 September 2026; external evidence updated 22 October 2026, before our hardware arrival. **We have not connected or tested a Steam Frame. All of our Frame runtime, DRM, decoder, headset and service-quality results remain UNKNOWN / NOT TESTED.** Local builds and synthetic reports are preparation, not device evidence. The external source findings and third-party physical-device reports below are separately attributed.

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

### External physical-device evidence before our Frame arrived

**FACT — third-party physical-device observation:** In the [immerGallery release discussion](https://www.reddit.com/r/SteamFrame/comments/1wkxkf8/vr_media_player_app_immergallery_now_available_on/), independently opened and read on 20 September 2026, developer **immerVR** reports that their shipping Android/Lepton VR/media application plays video on physical Steam Frame hardware but cannot currently access hardware video decoding through Lepton; their tested 6K/8K videos consequently did not play smoothly. This is the developer's reported observation, **not our Frame result or an independently repeated measurement**.

**INFERENCE:** This independently corroborates the public-source evidence that the visible/default Lepton media configuration does not currently establish a hardware MediaCodec decoding path. It strengthens concern about the normal/default Android media path without establishing a Frame-wide limitation.

**UNKNOWN:** Whether another shipping Lepton configuration, Valve-supplied component, future software version or different Android media integration exposes hardware decoding. The report does not establish that Frame has no hardware decoder anywhere, that Valve cannot enable one, that our diagnostics will see the same inventory, or that clear 1080p/4K playback performs poorly.

The exercised path is **Android/Lepton media application → video decode/playback → Frame presentation**. immerGallery is a VR/media app; this does not prove ordinary non-OpenXR 2D Activity presentation. That remains **UNKNOWN** until our flatscreen APK is tested on Frame.

**Hardware video decoding and hardware-secure DRM/protected video are related but separate.** This report establishes nothing directly about Widevine, L1/L3, OEMCrypto, TEE, provisioning, secure MediaCodec, protected buffers/composition or provider certification. Frame's actual Widevine availability/security level, secure decoding and commercial-service playback remain **UNKNOWN**; Reddit L3 speculation is not adopted as evidence. The shipping-component hypothesis below remains an architectural possibility, not shipping evidence; `/usr/share/guestos/android` and the effective shipping runtime still require inspection.

#### Browser streaming reports — reviewed 6 October 2026

**FACT — third-party owner reports, not our measurements:** In the independently read [Streaming video thread](https://www.reddit.com/r/SteamFrame/comments/1wyqzto/streaming_video/), **Chip_Lamonica** reports visible YouTube video but audio without video for HBO Max, Netflix and Amazon, identifying their browser as Chrome. **CaseFace5** separately reports Firefox failing and the included Chromium working, without naming tested services or quality. No owner follow-up confirming the suggested browser switch was visible when reviewed.

**INFERENCE:** Browser choice and presentation route warrant comparison; the failure alone does not identify DRM, decoding or capture/composition as its cause. This is separate from immerGallery's Android/Lepton result.

**UNKNOWN:** The original Chrome execution route (local versus PC-streamed), versions, failing stage, actual resolution, decoder and CDM/session security. The Chromium comment is a playback lead, not service-by-service HD/4K verification. Neither report establishes Android Widevine, secure MediaCodec or ordinary Android 2D presentation. Commenters' DRM diagnoses remain speculation.

#### Whirligig and alternative decode paths — reviewed 15 October 2026

**FACT — third-party physical-device/developer reports:** Whirligig developer **Phil / phileday** reports testing on a Valve-supplied Frame. The [Steam announcements](https://steamcommunity.com/app/451650/allnews/) introduce an Android/Lepton beta on 27 September and describe both on-device Proton and Lepton builds in the 4 October v5.8004 release, warning that hardware video decoding is unavailable in those paths. In a [13 October v5.8005 discussion](https://steamcommunity.com/app/451650/discussions/0/583936729654912155/), an owner reports working SBS 3D playback but difficulty with 4K-and-above files; the developer reiterates the decoding limitation. These are attributed reports, not our measurements or a codec/bitrate-controlled benchmark.

**INFERENCE:** This adds a second developer's corroboration of the default Lepton decoding concern. Keep Proton, Android/Lepton and native Linux results separate. The developer's [Reddit post](https://www.reddit.com/r/SteamFrame/comments/1ww3ddj/whirligig_vr_media_player_steam_frame_updates/) suggests HD/UHD may work and that enabling decoding might be simple; neither is a measured 1080p/4K guarantee or proof that changing one setting completes MediaCodec integration.

**FACT — separate native/custom-path reports:** Following the developer's pointer, [MatineeVR](https://embedding-shapes.itch.io/matineevr) advertises standalone hardware-decoded local playback with a Linux ARM64 build (8-bit H.264/HEVC/VP9; no HDR/10-bit support claimed there). More specifically, [ijingo's 12 October report](https://github.com/ValveSoftware/steam-for-linux/issues/13727) says `/dev/video-dec0` was accessible on the host but absent from their stock Lepton container; exposing it in a **custom container**, together with their **direct V4L2 implementation**, reportedly enabled HEVC Main/Main10 hardware decoding. This does not establish a stock Android MediaCodec backend, protected decoding or a generally supported modification.

**FACT — tracker status:** Valve's **kisak-valve** closed that GitHub issue as a duplicate of [Lepton work item #1](https://gitlab.steamos.cloud/frame-public/lepton/-/work_items/1). Its public API, checked on 15 October, identifies **phileday** as the author, creation on 30 September and state **opened**, with no description. This establishes tracking, not a delivered fix or release commitment.

**UNKNOWN:** Our stock runtime's codec inventory/actual selection and practical 1080p/4K performance remain untested. These reports support path-specific hardware access, not a Frame-wide absence of decoding. They establish nothing about Widevine/security level, secure buffers/composition, provider certification, commercial-service quality or ordinary non-OpenXR Android 2D presentation. The shipping secure-media hypothesis remains an architectural possibility.

#### Frame Cinema browser/service reports — reviewed 15 October 2026

**FACT — third-party developer report, not our Frame result:** [Frame Cinema](https://sframelab.itch.io/frame-cinema) is offered as a Linux app for standalone Netflix, HBO Max and Disney+ viewing. Developer **eyfeldb** [identifies Google Chrome inside the cinema](https://www.reddit.com/r/SteamFrame/comments/1x6rxxm/comment/pgxyfn9/) and describes its DRM as software-only Widevine L3. They [report Netflix 1080p, HBO Max 720p and Disney+ 480p](https://www.reddit.com/r/SteamFrame/comments/1x6rxxm/comment/pgxyuar/). These are physical-Frame developer claims with no published session diagnostics or resolution-measurement method in the reviewed replies; their generalisation to all Linux browsers is not adopted.

**INFERENCE:** This supplies a specific browser-based standalone service-playback comparison, rather than another Lepton decoder result. Reported Netflix/Disney+ quality resembles our prior computer-browser baseline; the HBO Max figure differs, but unmatched titles/settings prevent attributing an improvement to Frame Cinema.

**UNKNOWN:** Exact browser/build/CPU execution path, hardware decoder use, measured CDM/session security, title-dependent source quality and sustained performance. Browser L3 reporting does not resolve Android MediaDrm availability/security level, secure MediaCodec, protected composition or provider certification. Apple TV is not established by this report. No installer or application was executed here; our three APKs remain runtime NOT TESTED.

#### FramePlayerX native source evidence — reviewed 22 October 2026

**FACT — inspected third-party source, not our hardware execution:** [FramePlayerX](https://github.com/remotesojourner/frameplayerx/tree/3732b89b37cca8f1e9ec4624a218dc46ac7713af), a fork of yellkell's FramePlayer, releases v0.12.4 at commit `3732b89b37cca8f1e9ec4624a218dc46ac7713af`. It builds for **Linux ARM64**, with OpenXR/Vulkan presentation rather than Android/Lepton. Its [V4L2 implementation](https://github.com/remotesojourner/frameplayerx/blob/3732b89b37cca8f1e9ec4624a218dc46ac7713af/crates/fp-media/src/v4l2.rs) opens `/dev/video-dec0` or a suitable alternative and implements H.264/HEVC decoding; 10-bit HEVC uses Qualcomm Q10C output. [Decoder selection](https://github.com/remotesojourner/frameplayerx/blob/3732b89b37cca8f1e9ec4624a218dc46ac7713af/crates/fp-media/src/decode.rs) tries native V4L2, applicable FFmpeg V4L2 wrappers (including VP9), then software; AV1 selects software dav1d. Candidate selection is not a measured successful decode.

**FACT — documented capabilities/limits:** The project advertises local/removable-media and Jellyfin/Emby/network playback. Its [user guide](https://github.com/remotesojourner/frameplayerx/blob/3732b89b37cca8f1e9ec4624a218dc46ac7713af/docs/USER-GUIDE.md) describes an HW/SW indicator, HDR tone mapping and contention for the decoder shared with Steam streaming. These are developer claims, not independently repeated performance results; HDR tone mapping does not establish HDR headset output or protected buffers.

**INFERENCE:** This provides a concrete, auditable native clear-media comparison for our practical 1080p/4K goal, strengthening the case for path-specific integration limits. It does not establish stock Lepton MediaCodec availability. **UNKNOWN:** Actual performance on our Frame, secure decoding, Widevine/session security, ordinary non-OpenXR Android 2D presentation and commercial-service quality. All three of our APKs remain runtime NOT TESTED; the shipping secure-media hypothesis remains an architectural possibility. No external app, installer or probe was run here.

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

The latest recorded automated verification passes: **52 tests, syntax checks for 26 Python files and Ruff**. The documentation also records 15 synthetic first-hour scenarios. These are dated local results, not a promise about future checkouts. **All three of our APKs remain runtime NOT TESTED; none has been installed or executed by us on Frame.** See the Android validation record for exact artifacts, API guards and retained evidence.

## The three Android test apps

| App | Purpose and evidence boundary |
|---|---|
| **Flatscreen** — `org.framemedialab.flatscreen` | Prove that an ordinary non-OpenXR Activity can install, launch, display in the headset and receive interaction. Includes buttons, text, scrolling, animation and lifecycle/input evidence. Headset visibility requires human observation. |
| **Diagnostics** — `org.framemedialab.diagnostics` | Use legitimate Android APIs to inspect Widevine and ClearKey, actual MediaDrm session outcome/security, HDCP where available, and MediaCodec inventory: hardware/software/vendor classification, secure-playback flags and AVC/HEVC/VP9/AV1 when advertised. Capability records are not decoder-use results. |
| **Clear media** — `org.framemedialab.media` | Exercise **MediaExtractor → MediaCodec → Surface** without DRM, with audio via AudioTrack. Record actual selected decoder/output and source dimensions separately from Surface dimensions, plus frame/audio/error evidence. |

Diagnostics opens and closes sessions; it deliberately does **not** bypass DRM, request arbitrary licences, extract credentials, expose keyboxes, modify security level or perform provisioning. The clear player configures without MediaCrypto and rejects encrypted samples; it is not a protected/adaptive streaming player.

Eight short generated fixtures exist: **H.264 1080p, H.264 4K, HEVC 1080p, HEVC 4K, VP9 1080p, VP9 4K, AV1 1080p and AV1 4K**. All are two-second, 24 fps MP4 test clips with AAC audio. Local ffprobe validation does not prove Android extraction or playback. Start with H.264 1080p: clear testing separates “Frame/Lepton cannot decode this video” from “protected DRM playback is failing.” Short clips do not establish sustained performance, thermals or viewing comfort.

## First questions when Frame arrives

**Hardware MediaCodec investigation now has equal importance to Widevine investigation.** Investigate approximately in this order, recording unavailable evidence explicitly; the ordering does not make either question secondary:

1. What SteamOS, Lepton and Android versions actually ship?
2. What is present in `/usr/share/guestos/android` and other shipping host integrations?
3. Which guest components are actually loaded, rather than merely present?
4. Does ordinary 2D Android presentation work?
5. What video decoders does Android advertise through MediaCodec?
6. Which are classified as hardware accelerated, and which as software? Keep advertisements separate from actual use.
7. Which advertise secure playback? This does not establish working secure decoding.
8. Which decoder is **actually selected** for clear H.264 1080p, and is that selected decoder actually hardware accelerated? Correlate its identity/classification with runtime evidence; record uncertainty rather than treating an advertised flag as proof.
9. Does that clip decode and display smoothly? Record actual playback performance and headset observation alongside decoder/output evidence.
10. Repeat decoder selection, hardware/software assessment and performance observation progressively with **H.264 4K → HEVC 1080p/4K → VP9 1080p/4K → AV1 1080p/4K**. The existing generated fixtures are suitable initial probes; prioritise practical high-quality 1080p/4K streaming, not an immediate jump to 6K/8K. Their short duration still cannot establish sustained performance.
11. Is Widevine supported, and can an actual Widevine session be opened?
12. What security level does **that session** obtain?
13. Can protected video traverse the complete presentation path? Resolve this through legitimate playback; the clear player cannot answer it.
14. Can a commercial streaming APK install and launch?
15. Can it log in?
16. Can it obtain a legitimate licence?
17. Does protected video appear in the headset?
18. What **actual source resolution** does the service provide?

Compare immerGallery's reported hardware-decoding unavailability through its Lepton path with **our advertised decoder inventory + actual selected decoder + actual 1080p/4K playback**. Finding a hardware decoder would be materially different and should trigger investigation of why the environments/paths differ, while retaining the advertised-versus-used distinction. Software-only inventory and actual decoding would independently reproduce/corroborate the developer's finding for our tested configuration, without resolving DRM or generalising to every Lepton configuration.

Include Whirligig as a second external comparison, recording the exact app build, selected compatibility tool and video backend. Inspect host versus guest decoder-device visibility read-only alongside the effective shipping components. Native Linux and custom V4L2 reports are separate comparison evidence; preserve the **unmodified shipping baseline** and do not apply their patches during initial investigation. Hardware MediaCodec and Widevine remain equal priorities, starting with our existing 1080p/4K fixtures.

FramePlayerX is an optional later **native clear-media comparison** using the same fixtures: record its exact version, actual HW/SW selection, performance and any competing decoder sessions. Its documented `--decode-bench FILE [--sw]` measures decoding without display; keep that separate from headset-visible playback. Do not substitute its native decoder inventory or results for our Android diagnostics.

Establish a separate **Frame built-in browser baseline** early: record browser/version and whether execution is local or PC-streamed, then test YouTube and legitimate service playback in the headset. Compare the same service/title through another browser where available, recording visible video, audio and actual source resolution. Keep browser CDM/decoder evidence separate from Android MediaDrm/MediaCodec evidence; neither an audio-only failure nor visible browser playback resolves the Lepton questions.

Use Frame Cinema's reported service resolutions as comparison targets, not acceptance results. If tested later, compare the same titles/accounts/settings with direct browser playback and verify actual source dimensions; a cinema environment alone does not establish improved stream quality. Preserve the separate Android MediaCodec/Widevine investigation.

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
