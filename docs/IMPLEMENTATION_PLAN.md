# Frame Media Lab implementation plan

The supplied request and ../LEPTON_MEDIA_INVESTIGATION.md are the specification. Read completely on 2026-09-17; implementation must remain within this directory. No commits, repository initialization, host installations, hardware claims or parent modifications.

## Design

Use Python 3.10+ standard library for a local CLI, configuration, bounded SSH/ADB subprocesses, JSON evidence, redaction, reports and a resumable interactive workflow. Use native Java Android Activities and platform media APIs for three independently installable apps. Keep execution, collection, interpretation and user observation separate. Shell-only would make structured reporting and safe error handling harder; a web service would add unnecessary dependencies.

Default host inspection never invokes Lepton: its pre-dispatch code can migrate Podman and start services. Explicit runtime probes and app installation/launch require a named state-changing command or workflow confirmation. Query an explicitly selected ADB serial and validate it is Android. No secret files or DRM payloads are collected. Logs are opt-in and filtered; reports use structured, redacted evidence rather than embedding raw dumps.

## Tasks and validation

1. Core CLI: configuration/environment overrides; dependency doctor; safe transport, explicit target selection, unique private bundles; tests for timeout, failure, quoting and missing targets.
2. Collectors: fixed read-only host queries, Python overlay metadata/hash inventory with sensitive-file exclusions, filtered Podman mount identity, Android properties/packages/services; actual Lepton probes explicitly opt-in. Test parsers and read-only command boundaries using synthetic fixtures.
3. Android apps: ordinary flatscreen Activity/input/lifecycle UI, MediaDrm session + codec enumeration/export, clear MediaCodec/AudioTrack player. Build with installed SDK if available; otherwise leave complete projects and exact prerequisite instructions. No automatic software installation. Agent owns android/, Android build script and app-specific tests/docs only.
4. Evidence: commercial APK manifest/ZIP inspection; explicit single/split installs and Activity resolution; fixture generation; scoped component comparison that distinguishes source absence from shipping-only proof.
5. Reporting/workflow: measured versus advertised distinctions, all five service records, failure classification, browser baseline, resumable first-hour stages with manual headset observations; reject synthetic/real mixing.
6. Validation/docs: automated tests and syntax checks, synthetic CLI run and complete report, redaction adversarial tests, build/preflight attempt, generated media probe, source baseline hash comparison, README/architecture/safety/test/service guides and IMPLEMENTATION_NOTES.md.

## Success coverage

Tasks 1/5 cover doctor and guided workflow. Task 2 covers safe host and overlay investigation. Task 3 covers all APK projects/build attempts. Task 4 covers fixtures, ADB/SSH, APKs and comparison. Tasks 1/5 cover timestamped bundles, summaries and redaction. Task 6 covers mock evidence and unchanged-source verification. All physical Frame criteria remain NOT TESTED until measured.

## Source findings and limits

Report links refer to an older directory name (`lepton-main`); actual archive is ../Lepton. CI files now sit in the parent outside Lepton. Relevant source behavior agrees with the report: command order is `lepton run dev ...`; `start dev` is long-lived; per-file overlays have no explicit duplicate-destination winner; launcher help/ps has side effects; common postinstall directory requires cautious helper sequencing. No source behavior discrepancy identified in checked paths.

## Execution record

- Initial filesystem hashes captured in build/source-baseline.json.
- SDK not detected in standard locations; Java 17 and ffmpeg present. Further bounded SDK discovery belongs to Android task.
