"""Configuration, privacy, evidence storage and bounded command execution."""

from __future__ import annotations
import dataclasses
import datetime as dt
import json
import os
import platform
import re
import shlex
import signal
import subprocess
import uuid
from pathlib import Path
from typing import Any
from .android_sdk import SDK_TOOLS, tool_path

ROOT = Path(__file__).resolve().parent.parent
VERSION = "0.1.0"
STATUSES = ("PASS", "FAIL", "PARTIAL", "UNKNOWN", "NOT TESTED")
SENSITIVE = re.compile(
    r"(?i)(token|cookie|authorization|password|passwd|credential|secret|keybox|unique.?id|device.?id|advertising.?id|serial(?:no|number)?|android.?id|imei|imsi|email|license.?payload|licence.?payload|provision.*(?:data|request|response))"
)


def redact(value: Any) -> Any:
    """Conservative best-effort filtering; never a guarantee for arbitrary free text."""
    if isinstance(value, dict):
        return {
            str(k): "[REDACTED]" if SENSITIVE.search(str(k)) else redact(v)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if not isinstance(value, str):
        return value
    value = re.sub(
        r"(?is)-----BEGIN [^-]*(?:PRIVATE KEY|CERTIFICATE)-----.*?-----END [^-]+-----",
        "[REDACTED MATERIAL]",
        value,
    )
    value = re.sub(
        r"(?im)^.*(?:authorization\s*[:=]|cookie\s*[:=]|(?:licen[cs]e|provisioning)\s*(?:request|response|payload)|keybox|deviceUniqueId|ro\.serialno|ro\.boot\.serialno|android_id|\bIMEI\b|\bIMSI\b).*$",
        "[REDACTED SENSITIVE LINE]",
        value,
    )
    value = re.sub(r'https?://[^\s<>"\']+', "[REDACTED URL]", value)
    value = re.sub(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "[REDACTED EMAIL]",
        value,
        flags=re.I,
    )
    value = re.sub(
        r'(?i)\b(token|password|passwd|secret|credential|serial(?:no|number)?)\b\s*[:=]\s*(?:"[^"]*"|\S+)',
        r"\1=[REDACTED]",
        value,
    )
    value = re.sub(
        r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b",
        "[REDACTED JWT]",
        value,
    )
    value = re.sub(r"(?i)\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b", "[REDACTED MAC]", value)
    return value


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )
    tmp.chmod(0o600)
    tmp.replace(path)


@dataclasses.dataclass
class Config:
    host: str = ""
    ssh_user: str = "steamos"
    ssh_port: int = 22
    adb_method: str = "existing"
    serial: str = ""
    context: str = "dev"
    results_dir: str = str(ROOT / "results")
    timeout: int = 25

    def validate(self) -> Config:
        if self.host and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.:%_-]*", self.host):
            raise ValueError("host must be a hostname or IP, not SSH options")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", self.ssh_user):
            raise ValueError("invalid SSH username")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", self.context):
            raise ValueError("invalid Lepton context")
        if not 1 <= int(self.ssh_port) <= 65535:
            raise ValueError("SSH port must be 1..65535")
        if self.adb_method not in ("existing", "direct", "ssh", "usb"):
            raise ValueError("adb_method must be existing/direct/ssh/usb")
        if self.serial.startswith("-") or any(c.isspace() for c in self.serial):
            raise ValueError("invalid ADB serial")
        if not 1 <= int(self.timeout) <= 300:
            raise ValueError("timeout must be 1..300 seconds")
        return self

    @classmethod
    def load(cls, path: Path | None = None, overrides: dict | None = None) -> Config:
        values = {}
        if path:
            values = json.loads(path.read_text())
            unknown = set(values) - {f.name for f in dataclasses.fields(cls)}
            if unknown:
                raise ValueError(
                    "unknown configuration fields: " + ", ".join(sorted(unknown))
                )
        for f in dataclasses.fields(cls):
            key = "FML_" + f.name.upper()
            if key in os.environ:
                values[f.name] = os.environ[key]
        values.update({k: v for k, v in (overrides or {}).items() if v is not None})
        for k in ("ssh_port", "timeout"):
            if k in values:
                values[k] = int(values[k])
        return cls(**values).validate()

    def public(self) -> dict:
        data = dataclasses.asdict(self)
        for k in ("host", "serial", "results_dir"):
            data[k] = "[LOCAL CONFIG OMITTED]" if data[k] else ""
        return data


class Runner:
    def __init__(self, config: Config | None = None):
        self.config = config or Config()

    def run(
        self,
        argv: list[str],
        timeout: float | None = None,
        input_text: str | None = None,
        scope: str = "LOCAL MAC COMMAND",
    ) -> dict:
        if argv and argv[0] in SDK_TOOLS:
            argv = [tool_path(argv[0]) or argv[0], *argv[1:]]
        result = {
            "scope": scope,
            "argv": redact(argv),
            "status": "FAIL",
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "timed_out": False,
        }
        try:
            p = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
                start_new_session=True,
            )
            try:
                out, err = p.communicate(
                    input_text, timeout=timeout or self.config.timeout
                )
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                out, err = p.communicate()
                result["timed_out"] = True
            result.update(
                returncode=p.returncode,
                stdout=out[:4_000_000],
                stderr=err[:200_000],
                truncated=len(out) > 4_000_000 or len(err) > 200_000,
            )
            result["status"] = (
                "PASS"
                if p.returncode == 0
                and not result["timed_out"]
                and not result["truncated"]
                else "FAIL"
            )
        except OSError as exc:
            result.update(returncode=127, stderr=str(exc))
        return result

    def ssh_argv(self, argv: list[str]) -> list[str]:
        self.config.validate()
        if not self.config.host:
            raise ValueError("Set FML_HOST or --host; no Frame target configured")
        return [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            "ConnectTimeout=8",
            "-p",
            str(self.config.ssh_port),
            f"{self.config.ssh_user}@{self.config.host}",
            shlex.join(argv),
        ]

    def ssh(self, argv: list[str], **kwargs) -> dict:
        return self.run(self.ssh_argv(argv), scope="REMOTE FRAME COMMAND", **kwargs)

    def adb(self, argv: list[str], **kwargs) -> dict:
        if not self.config.serial:
            raise ValueError(
                "Set FML_SERIAL or --serial to the Android guest endpoint; USB may target SteamOS"
            )
        return self.run(
            ["adb", "-s", self.config.serial] + argv,
            scope="ANDROID GUEST COMMAND",
            **kwargs,
        )

    def shell(self, argv: list[str], **kwargs) -> dict:
        # ADB shell passes through a remote shell, even though the local call is argv-based.
        return self.adb(["shell", shlex.join(argv)], **kwargs)

    def require_android(self) -> dict:
        r = self.shell(["getprop", "ro.build.version.sdk"])
        if r["status"] != "PASS" or not r["stdout"].strip().isdigit():
            raise ValueError(
                "Selected ADB endpoint did not return an Android SDK level. Check guest serial/forwarding; "
                + str(redact(r["stderr"]))
            )
        return r


class Bundle:
    def __init__(self, path: Path, metadata: dict):
        self.path = path
        self.metadata = metadata

    @classmethod
    def create(cls, root: Path, config: Config, synthetic: bool = False) -> Bundle:
        path = root / (
            dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
            + "-"
            + uuid.uuid4().hex[:8]
            + ("-SYNTHETIC" if synthetic else "")
        )
        path.mkdir(parents=True, mode=0o700)
        commit = Runner().run(["git", "-C", str(ROOT), "rev-parse", "HEAD"])
        b = cls(
            path,
            {
                "schema_version": 1,
                "toolkit_version": VERSION,
                "git_commit": commit["stdout"].strip()
                if commit["status"] == "PASS"
                else "UNVERSIONED",
                "created_at": now(),
                "synthetic": synthetic,
                "evidence_origin": "SYNTHETIC FIXTURE"
                if synthetic
                else "LIVE COLLECTION",
                "control_machine": {
                    "os": platform.system(),
                    "release": platform.release(),
                    "architecture": platform.machine(),
                },
                "configuration": config.public(),
                "frame": {},
                "stages": {},
                "errors": [],
                "privacy": "REDACTED / REVIEW BEFORE SHARING; arbitrary logs cannot be guaranteed secret-free",
            },
        )
        for name in (
            "host",
            "lepton",
            "android",
            "drm",
            "codecs",
            "media",
            "services",
            "logs",
        ):
            (path / name).mkdir(mode=0o700)
        dump(
            path / "target.local.json",
            {
                "privacy": "RAW / MAY CONTAIN SENSITIVE DATA — local transport binding; never share",
                "target": b.target_fields(config),
                "endpoint_history": [config.serial] if config.serial else [],
            },
        )
        b.save()
        return b

    @classmethod
    def open(cls, path: Path, synthetic: bool | None = None) -> Bundle:
        data = json.loads((path / "metadata.json").read_text())
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported bundle schema")
        if synthetic is not None and data["synthetic"] != synthetic:
            raise ValueError("Synthetic and real evidence must never be mixed")
        return cls(path, data)

    @staticmethod
    def target_fields(config):
        return {
            k: getattr(config, k)
            for k in ("host", "ssh_user", "ssh_port", "context", "serial")
        }

    def check_target(self, config, rebind_adb=False):
        if self.metadata["synthetic"]:
            return
        p = self.path / "target.local.json"
        if not p.exists():
            raise ValueError(
                "Private target binding missing; create a new bundle before collecting live evidence"
            )
        binding = json.loads(p.read_text())
        previous = binding["target"]
        current = self.target_fields(config)
        if any(previous.get(k) != current[k] for k in current if k != "serial"):
            raise ValueError(
                "Host/user/port/context differs from this bundle. Use original configuration or create a new bundle"
            )
        if previous.get("serial") != current["serial"]:
            if not rebind_adb:
                raise ValueError(
                    "ADB endpoint changed. Verify it is the same Frame/context, then explicitly use --rebind-adb"
                )
            binding["target"] = current
            binding["endpoint_history"].append(current["serial"])
            dump(p, binding)
            self.metadata["stages"]["endpoint-rebind"] = {
                "status": "PASS",
                "at": now(),
                "notes": "User explicitly asserted same Frame/context at changed Android endpoint",
            }
            self.save()

    def save(self):
        dump(self.path / "metadata.json", redact(self.metadata))

    def write(self, name: str, value: Any):
        path = (self.path / name).resolve()
        if not path.is_relative_to(self.path.resolve()):
            raise ValueError("Bundle path escape")
        dump(path, redact(value))

    def read(self, name: str, default=None):
        p = self.path / name
        return json.loads(p.read_text()) if p.exists() else default

    def record(self, name: str, result: dict):
        self.write(name + ".json", result)
        if result.get("status") == "FAIL":
            self.metadata["errors"].append(
                {
                    "evidence": name + ".json",
                    "stderr": redact(result.get("stderr", "")),
                    "timed_out": result.get("timed_out", False),
                }
            )
            self.save()

    def stage(self, name: str, status: str, notes: str = ""):
        self.metadata["stages"][name] = {"status": status, "at": now(), "notes": notes}
        self.save()


def parse_properties(text: str) -> dict:
    return dict(re.findall(r"^\[([^\]]+)\]: \[(.*)\]$", text, re.M))


def parse_lepton_ps(text: str) -> list[dict]:
    return [
        {"context": m[0], "adb_port": int(m[1])}
        for m in re.findall(r"^([^\s]+) \([^\n]*?adb on (\d+)", text, re.M)
    ]
