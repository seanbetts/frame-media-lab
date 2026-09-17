# Test plan

## Reproduce the Mac checks

```sh
make check
RUFF_CACHE_DIR=build/ruff-cache ruff check lab scripts tests   # optional installed development tool
./frame-media-lab doctor
./frame-media-lab --synthetic l1 first-hour
./frame-media-lab --synthetic provisioning-required first-hour
./frame-media-lab --synthetic protected-black first-hour
./frame-media-lab build-android
./frame-media-lab generate-media --seconds 2
./frame-media-lab verify-source
```

`make check` uses standard-library unittest, Python AST validation and installed JDK checks in Android contract tests. Tests need no Frame/network. Ruff is optional and is never installed by the project. Android source/Java ownership-policy tests do not substitute for Android compilation or device execution. SDK build failure is expected on the current Mac until the documented prerequisites are installed explicitly.

Fixtures in `fixtures/mock/baseline.json` are invented. All derived bundles and reports carry `synthetic:true`; fixture injection into a live bundle is rejected. All five service rows remain NOT TESTED unless a scenario explicitly simulates an observation. A synthetic L1-like session never marks actual protected playback successful.

## Automated coverage

- CLI dispatch/configuration, explicit target selection, SSH shell quoting, missing executable and command timeouts.
- Unique private bundles, path containment, synthetic/live mismatch rejection, local target binding and explicit endpoint rebinding.
- Getprop and Lepton endpoint parsers; GMS presence without invented certification.
- Overlay hashing without following symlinks or reading secret-like files; public/effective hash comparison and unknown-source boundaries.
- APK metadata/aliases/ABI/GMS hints; binary XML validation. All six supplied Lepton manifest fixtures were separately parsed without modifying them.
- Redaction of structured secrets, URLs, headers, email, identifiers and representative licence payload lines.
- Report defaults, all synthetic scenarios, real Android HDCP schema, actual session versus advertised property, diagnostic and per-service failures, decoded resolution evidence.
- Resume without repeating completed actions, durable failed-stage retry, explicitly clearing only relevant observations, declined commercial-stage skip.
- Media launch identity and playback ownership policy; old completed media is excluded when a fresh launch is expected.

Synthetic scenarios: unreachable Frame; missing Lepton; no dev context; unavailable ADB; unsupported Widevine; provisioning required; L3; L1-like API session; software-only codecs; hardware decoder without secure support; rendered Activity without host panel; clear playback with black protected video; commercial login failure; low-resolution service playback.

## First-hour hardware acceptance

1. **Preflight:** supported developer access, verified host key, host identification, discovered Lepton installation and actual ADB endpoint. No assumptions about default port or USB reaching Android.
2. **Host:** inventory shipping overlay/components, package owners, versions, devices and sockets. Opt into Podman mount metadata if needed. Read errors remain unknowns.
3. **Development:** review auto-install directory, open only one intended context, wait for Android boot. Record actual OS/fingerprint/ABI/graphics selection and package/HAL inventories.
4. **Diagnostics:** install our debug APK in a suitable Development session; launch; wait for a fresh completed JSON; verify unsupported/provisioning/resource errors and actual security level. No provisioning or licence requests from the probe.
5. **2D:** observe headset panel, pointer/buttons, text input, scrolling, animation, resize, Home/Back, lifecycle log and relaunch. Android pixels alone are insufficient.
6. **Clear AVC:** play generated H.264 1080p/AAC; record source/output/surface dimensions, actual codec name, submitted/render callbacks, audible tone and headset smoothness. Only then try the seven other clips. Use separate bundles for separate performance runs.
7. **Protected service:** select one authorised APK/set after DRM assessment. Record installation, launch, login, catalog, actual DRM/licence/decoder evidence, video in headset, audio, independently measured source resolution and HDR. Missing internal service diagnostics stay UNKNOWN.
8. **Correlation:** collect bounded post-playback codec/compositor evidence. If appropriate, specify the media service PID for library paths and its mount namespace. A black screenshot is not equivalent to black headset video.
9. **Repeatability:** resume a deliberately paused stage, restart app/context without losing prior exported evidence, then test account persistence and callback behavior separately.
10. **Sustained tests:** longer playback, A/V sync, drop/thermal/CPU/power behavior, suspend/resume, audio route changes, HDR and comfort. Short fixture success is insufficient for an efficiency claim.

## Failure interpretation

| Boundary | Next evidence |
|---|---|
| Install failure | SDK/ABI/splits/signatures/package-manager stderr |
| Launch or absent panel | Resolved alias, exported state, flatscreen/headless, HWC/Wayland and direct headset observation |
| Login failure | ACTION_VIEW host interception, callback scheme, WebView/GMS/provider requirements |
| Widevine unsupported | Guest HAL registration/UUID, component packaging |
| Provisioning required | Report required state; use only supported vendor/provider paths outside this probe |
| Licence rejected | Service-authorised error and entitlement/device policy; never capture payloads |
| Secure decode/configure fails | Actual decoder and format/security requirements |
| Clear works, protected headset video black | Protected allocation/import/compositor path; no bypass |
| Visible headset video, black screenshot | Possible intended capture protection; does not prove L1 |
| Low quality | Provider/stream diagnostics, account tier/settings and actual output format |

The final decision is per-service authorised end-to-end playback at measured acceptable quality. No mock, Mac build, generic emulator or source-only observation can meet that criterion.
