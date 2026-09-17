I now have the Steam Frame physically here and connected to this Mac.

We previously built this project specifically to investigate whether Steam Frame can become a high-quality standalone media-streaming device, particularly through Android streaming apps running under Valve's Lepton compatibility environment.

This is a fresh session. Before doing ANYTHING to the Frame:

1. Read CONTEXT.md completely.
2. Read ../LEPTON_MEDIA_INVESTIGATION.md, paying particular attention to §§3–8, 12, 13 and 15.
3. Read README.md.
4. Read IMPLEMENTATION_NOTES.md.
5. Read docs/ANDROID_VALIDATION.md.
6. Read docs/SAFETY.md.
7. Inspect the current frame-media-lab CLI/help and relevant implementation where necessary.

Treat those files as the authoritative context for this investigation.

IMPORTANT

The physical shipping Steam Frame is now the authoritative source.

Do not assume that:
- the public Lepton repository exactly matches the shipping runtime;
- components absent from public Lepton are absent from Frame;
- components present on Frame are necessarily active;
- advertised DRM/codec capabilities establish working playback.

Preserve the project's evidence standard throughout:

FACT
INFERENCE
UNKNOWN

And preserve the evidence hierarchy:

ADVERTISED CAPABILITY
→ ACTUAL API/SESSION RESULT
→ ACTUAL DECODER USE
→ HEADSET OBSERVATION
→ ACTUAL STREAM QUALITY

Do not collapse those layers.

GOAL

We want to determine whether this shipping Steam Frame can provide useful standalone streaming for:

- Disney+
- Apple TV
- HBO Max
- Netflix
- YouTube

We already have the prior browser baselines documented in CONTEXT.md.

The particularly important question is whether native Android applications through Lepton can materially improve upon the browser experience for Disney+, Apple TV and HBO Max.

APPROACH

Use the existing frame-media-lab toolkit rather than inventing a new investigation.

Begin by establishing the current state of the Mac, Frame and toolkit.

I expect the starting point to be approximately:

    ./frame-media-lab doctor

followed eventually by:

    ./frame-media-lab first-hour

BUT:

Do not blindly execute those commands based on this prompt.

First inspect the current README, CLI help and implementation so you understand exactly what each command will do.

SAFETY

Start read-only.

Do not:

- modify ../Lepton/
- modify ../LEPTON_MEDIA_INVESTIGATION.md
- modify /usr/share/guestos/android
- disable SteamOS read-only protection
- reset Podman
- make broad system changes
- modify DRM provisioning
- spoof DRM/security identity
- extract DRM keys/keyboxes/device credentials
- circumvent DRM
- dump licence payloads unnecessarily

If a step changes device state — including starting Lepton Development, installing an APK or launching an Activity — explain what you're about to do and use the toolkit's existing explicit state-changing workflow.

Do not make changes merely because they might make something work. First establish the shipping device's unmodified capabilities.

FIRST INVESTIGATION PRIORITIES

We want to establish, approximately in this order:

1. Shipping SteamOS version.
2. Shipping Lepton version/build.
3. Shipping Android image/version.
4. What host/device-specific components complete public Lepton.
5. Contents and role of /usr/share/guestos/android.
6. Which relevant DRM/media/codec/allocator/HWC components are actually loaded.
7. Whether an ordinary 2D Android Activity can be displayed and controlled in the headset.
8. Whether Widevine is supported.
9. Whether an actual Widevine session opens.
10. The security level of THAT SESSION.
11. Android MediaCodec inventory.
12. Hardware decoder availability.
13. Secure decoder availability.
14. Clear 1080p H.264 playback.
15. Clear 4K and HEVC/VP9/AV1 playback where useful.
16. Evidence for/against a protected presentation path.
17. Only then commercial streaming-app testing.

We already have three compiled and validated diagnostic APKs:

- org.framemedialab.flatscreen
- org.framemedialab.diagnostics
- org.framemedialab.media

Use them for their intended purposes.

COMMERCIAL STREAMING TESTS

Do not jump immediately to installing streaming applications.

First understand the underlying Frame/Lepton environment.

When we reach commercial testing, the default priority is:

1. Disney+
2. Apple TV
3. HBO Max
4. Netflix
5. YouTube

But change that order if the evidence suggests another test would answer a more fundamental question.

For every service preserve the boundaries:

INSTALL
→ LAUNCH
→ LOGIN
→ CATALOGUE
→ DRM SESSION
→ LICENCE
→ DECODER
→ VIDEO VISIBLE
→ ACTUAL SOURCE RESOLUTION

Do not summarise an intermediate failure simply as "the app doesn't work".

HUMAN OBSERVATIONS

Some results cannot be determined programmatically.

When you need to know what I can:

- see in the headset;
- hear;
- interact with;
- read from an application's own playback diagnostics;

ask me explicitly and record my observation in the appropriate investigation bundle.

For example, a protected video being visible in-headset while appearing black in screenshots may be important evidence. Do not infer headset visibility from screenshots.

WORKING STYLE

Work through this interactively with me.

Do not race through the entire investigation unattended.

At important evidence boundaries, tell me succinctly:

- what we observed;
- what that establishes;
- what it does NOT establish;
- what the next highest-value test is.

Use the existing resumable result bundle so we preserve evidence and don't accidentally mix tests.

Do not claim success until the corresponding evidence exists.

START NOW

Read the project context and documentation first.

Then inspect the current toolkit state and tell me the first action you recommend taking with the connected Steam Frame.

Do not modify the Frame before completing that review.