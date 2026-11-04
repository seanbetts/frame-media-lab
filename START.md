# Steam Frame arrival checklist

Use this with Sean when the Frame arrives. Answer two questions: **Which standalone route works best for each streaming service? Is an existing native player good enough for Jellyfin?**

## Before arrival

- [ ] Pick one repeatable title per streaming service. For Jellyfin, choose a test user, a familiar 1080p title and a representative high-bitrate 4K HEVC Main10 title. Note the FramePlayerX and VideoFrameVR releases to compare.
- [ ] Before touching the device, read [CONTEXT](CONTEXT.md), the [source investigation](../LEPTON_MEDIA_INVESTIGATION.md) (§§3–8, 12–13, 15), [README](README.md), [implementation notes](IMPLEMENTATION_NOTES.md), [APK validation](docs/ANDROID_VALIDATION.md) and [safety guide](docs/SAFETY.md). Check current CLI help.

## 1. Stock browser — which services already work?

- [ ] Record SteamOS and browser versions. Use the headset’s built-in browser running locally; exclude PC-streamed playback. Start with YouTube as a control, then Disney+, Apple TV, HBO Max and Netflix.
- [ ] For each title, record visible video, audio, control comfort and **actual source resolution** from playback diagnostics if available. Otherwise record **UNKNOWN**. Window size and headset panel size are not stream measurements. Pick the service whose browser result most needs improving.

## 2. Lepton — does Android improve that result?

- [ ] Follow the README’s developer-access and SSH setup. From this folder run `./frame-media-lab --config config/local.json doctor`, then `./frame-media-lab --config config/local.json first-hour`. Start with read-only inspection; record shipping Lepton/Android versions, the host overlay and which components actually load. Confirm the Android guest endpoint before using ADB. Resume the same live bundle for this Frame and context.
- [ ] Explain each device change before starting Lepton, installing or launching helpers. Keep stock Lepton, its overlay and DRM provisioning intact. Use the flatscreen app to check ordinary 2D display and input; diagnostics to record the **opened Widevine session’s level or error** and advertised hardware/secure codecs; the clear player to identify the **decoder actually used** for H.264 1080p. Ask Sean about picture, sound and smoothness before stepping up to 4K and other codecs.
- [ ] Try an authorised Android app, starting with Disney+ if its browser result is poor. Match the browser title, account and settings. Record install → launch → login → catalogue → DRM session/licence → decoder → visible video → source resolution. Mark unobserved stages unknown. A black capture does not tell you what Sean sees.

## 3. Native Jellyfin — use, adapt or build?

- [ ] In **FramePlayerX**, browse → resume → watch → stop. Check the saved position from another client and whether the server direct-played, remuxed or transcoded. Record any friction with the controls.
- [ ] Compare **VideoFrameVR** on the same file under matched network and render settings. Use short clips to identify the decoder; watch a longer segment to judge sync, stutter and comfort. Native clear playback does not establish Android DRM capability.
- [ ] Apply the [Jellyfin decision criteria](docs/SPATIAL_JELLYFIN_TECHNICAL_DESIGN.md): use an existing player if it meets the viewing goal; consider adapting it for specific observed gaps; consider a new client only if those gaps justify the work.

**After each session:** record what Sean saw or heard separately from API results. Label conclusions **FACT / INFERENCE / UNKNOWN**, note the next useful test, and keep private bundles local.
