# Safety and privacy

Default inspection reads metadata and public configuration. It does not launch Lepton, change Android properties, install apps, provision DRM or request licences. SSH and ADB may create normal connection/audit activity. ADB can start its normal local server; this is not an Android capability result.

| Command | Effects |
|---|---|
| `doctor`, `discover`, `inspect` | Local result files; read-only configured host queries; no LAN scans |
| `inspect --containers` | Explicit Podman metadata query; Podman may initialise its runtime |
| `runtime-probe --allow-runtime-changes` | Lepton ps/help/version; launcher may migrate/start/restart runtime services before dispatch |
| `android-status`, `drm`, `codecs`, `media-result`, `effective-components` | Android metadata/API-export reads; no app start/installation |
| `collect` / `collect --logs` | Bounded service snapshots / opt-in filtered logcat; no clearing logs |
| `inspect-apk`, `report`, `compare`, `redact`, `record-service` | Local files only |
| `install-apk` | Installs/replaces exactly the provided package/split set; no blanket grants or uninstall |
| `launch`, `play` | Force-stops and starts the named Activity; play fetches only user-supplied clear source |
| `connect-adb` | Explicit local ADB connection state |
| `connection-plan` | Prints commands; executes none |
| `build-android`, `generate-media` | Local build/generated files using existing software; no installations |
| `first-hour` | Guided sequence with explicit confirmations for helper/commercial app changes; no automatic Lepton start |

Never run Valve CI reset/setup scripts on a real desktop/Frame. This toolkit contains no call to sudo, host package installation, SteamOS read-only disable, Podman reset, broad context cleanup, provisioning mutation, DRM identity spoofing, protected credential extraction or licence-payload dumping. No files in Valve's source, installed Lepton or `/usr/share/guestos/android` are modified.

Overlay inspection exports component metadata and hashes, not bytes. Symlinks/special files are not read. Secret-like paths (keybox, credentials, provision, private, secret, token, cookie, accounts, persistent stores and common key/database extensions) are metadata-only. An unknown benign-looking filename can still be sensitive: hash inventories remain private unless reviewed. No generic `/data` traversal, process memory, complete process environments or network traffic capture is implemented.

The DRM probe has no INTERNET permission and uses only allowlisted properties. It opens/closes an ordinary session, records provisioning-required errors and does not initiate provisioning or licence requests. It never calls the device-unique-ID getter or retrieves keyboxes. The media app has network permission solely for the chosen clear source; it does not implement DRM.

## Sharing results

Result directories are created with owner-only permissions. JSON records are redacted before storage. Email addresses, obvious token/password/header/cookie fields, URL strings, MAC addresses, serial/device IDs and known licence/provisioning payload lines are masked. The reporter does not embed full logcat/dumpsys output.

`target.local.json` is **RAW / MAY CONTAIN SENSITIVE DATA**, contains local target addresses/serial history and must remain local. It supports safe resume. No raw-log option is enabled. Existing external raw input passed to `redact` is preserved; output must be a new path.

`report.md` and `report.json` are **REDACTED / REVIEW BEFORE SHARING**. Read their free-text notes and host identity excerpts. Automated filtering cannot honestly promise “safe to share” for every unknown vendor log format, multiline secret or manually entered value. Do not attach whole result bundles. If screenshots are useful, inspect them for accounts and private UI; the toolkit does not automatically capture or share them.

A black screenshot can be normal capture protection. It is neither proof of playback failure nor L1. Observe the actual headset, then correlate clear/protected decode and compositor evidence. Library names, protected flags, registered HALs, package presence and screenshots never substitute for end-to-end authorized playback.
