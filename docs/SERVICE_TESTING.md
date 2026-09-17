# Authorised service testing

No APK downloads or repository scraping are performed. Obtain the correct app and matching base/splits from an authorised distribution route. Inspect them locally before installation. `.apks`/`.xapk` archives may contain multiple device variants; the toolkit intentionally requires explicit split selection rather than installing every member.

```sh
./frame-media-lab inspect-apk /path/to/base.apk /path/to/config.arm64_v8a.apk
./frame-media-lab --config config/local.json install-apk /path/to/base.apk /path/to/config.arm64_v8a.apk
./frame-media-lab --config config/local.json resolve com.example.actualpackage
./frame-media-lab --config config/local.json launch com.example.actualpackage/.ActualAlias
```

The resolver supports MAIN/LAUNCHER and MAIN/LEANBACK; inspect aliases/exported state if neither resolves. `install-multiple -r` handles explicit APK sets. Package and version-code consistency are checked before installation; Android enforces signatures and completeness. No broad `-g` grant is passed. Lepton's guest package wrapper can still perform its own postinstall actions, described in the investigation.

Use one target/helper per initial Development session because current public Lepton relocates installed code into a common directory. Preserve exports first. Context resets, uninstalling and stopping are manual, scoped decisions; the toolkit never performs broad cleanup. Test login persistence only after basic functionality is established.

## Test record

Use `--bundle RUN record-service disney` (or apple/hbo/netflix/youtube). Record PASS, FAIL, PARTIAL, UNKNOWN or NOT TESTED for install, launch, login, catalog, DRM session, licence, decoder, visible video, audio and HDR. Record package version, title, subscription tier, region, quality setting, duration/notes and resolution evidence. Do not mark licence/session PASS solely because the catalog opened; if the app does not expose that internal boundary, use UNKNOWN.

Keep these independent:

- **Actual source resolution:** provider diagnostics or a decoder format tied to the playing video and timestamp.
- **Android window/surface resolution:** a composition/UI size, not a stream measurement.
- **SteamVR panel resolution:** presentation size, not a source measurement.

A maximum supported resolution is not the current resolution. Allow adaptive playback to settle; record duration, bandwidth and any quality changes. “Looks sharp” is an observation, not a pixel count. Never place account credentials, licence URLs or debug payloads into notes.

## Test priority

The existing measured browser gap makes Disney+, Apple TV and HBO Max high-value candidates. If Widevine is unavailable, use clear YouTube uploads or our fixture player first to establish native decode/input; protected-service rejection tests then identify boundaries. If hardware decoding is absent, establish clear performance first. Netflix and YouTube already have acceptable browser baselines (1080p and 4K respectively); the Android route must show a concrete benefit.

## Netflix

Netflix's current Android help says HD requires Widevine L1 and L3 is limited to SD. In the app, open **My Netflix → Menu → App Settings → Diagnostics → Playback Specification**. Record its Widevine result and advertised maximum playback capability separately from the actual playing title's resolution. An L1 indication by itself does not show that this Frame actually plays HD. [Netflix Android help](https://help.netflix.com/en/node/23939) (checked 17 September 2026).

## YouTube

For the Android app, enable Stats for nerds under account **Settings → General**, then play a video and open **More → Stats**. Record current/optimal resolution, selected codec, dropped frames and the observation time where exposed; keep viewport size separate. Omit video/session identifiers from shared notes. Ordinary user uploads test clear media; rentals/purchases need a separate protected-content test. [YouTube Android instructions](https://support.google.com/youtube/answer/7519898?co=GENIE.Platform%3DAndroid&hl=en) (checked 17 September 2026).

## Disney+, Apple TV and HBO Max

Record the chosen app variant and exact version; phone/tablet, TV and VR builds may differ. Do not assume a mobile APK supplies TV/4K behavior. Prefer app-supported playback diagnostics; otherwise tie any decoder-size evidence to the active service/process and record uncertainty. The toolkit does not intercept TLS, licence requests or protected media, and it does not reverse engineer authentication.

Inspect login separately from DRM. The public Lepton patch intercepts ACTION_VIEW URIs and forwards them to the Steam host; browser/custom-scheme callback failures may explain login issues. Device-code/QR login may be informative where officially supported. Package presence does not establish GMS certification or a provider's device allowlist.

## Protected playback evidence

```sh
./frame-media-lab --config config/local.json --bundle RUN collect --logs
# If you have identified an authorised, readable media-service PID:
./frame-media-lab --config config/local.json --bundle RUN collect --pid 1234
./frame-media-lab --bundle RUN report
```

Correct final report syntax is also `./frame-media-lab report RUN`; `--bundle RUN report` selects the same bundle. Snapshot collection does not capture network traffic, licence payloads, keys, memory or app-private data. If permissions deny maps/mountinfo, leave that boundary UNKNOWN. A protected screenshot may be black while the headset is playing normally; direct observation is required.
