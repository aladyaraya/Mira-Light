#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pipeline
import rokid_render_pipeline


DEFAULT_HOST = "192.168.0.183"
DEFAULT_USER = "root"
DEFAULT_PORT = 22
DEFAULT_DEVICE = "auto"
DEFAULT_VIDEO_SIZE = "1280x720"
DEFAULT_INPUT_FORMAT = "mjpeg"
DEFAULT_CONNECT_TIMEOUT = 10
DEFAULT_SSH_RETRIES = 3
DEFAULT_SSH_RETRY_DELAY_SECONDS = 3.0
DEFAULT_KNOWN_HOSTS_PATH = Path("/tmp/javis-digua-known-hosts")
DEFAULT_CAPTURE_DIR = pipeline.DEFAULT_OUTPUT_DIR / "digua-remote" / "source"
DEFAULT_OUTPUT_DIR = pipeline.DEFAULT_OUTPUT_DIR / "digua-remote"
DEFAULT_STYLE_SLUG = "digua-anime"
DEFAULT_STYLE_PROMPT = (
    "现代高清的吉卜力动画风格插画，保留开发板摄像头拍到的真实构图和主体，"
    "画面干净明亮，有电影感"
)
BEGIN_MARKER = "__JAVIS_DIGUA_IMAGE_BEGIN__"
END_MARKER = "__JAVIS_DIGUA_IMAGE_END__"
CAMERA_CONTROLS_PATTERN = re.compile(r"^[A-Za-z0-9_,=.+:-]+$")
MIN_CAPTURE_IMAGE_BYTES = 512
REMOTE_CAMERA_ERROR_PATTERNS = (
    "No /dev/video* camera devices found",
    "No remote camera device produced a JPEG frame",
    "remote camera device not found",
    "Cannot open video device",
)


def normalize_camera_controls(camera_controls: str) -> str:
    controls = ",".join(part.strip() for part in str(camera_controls or "").split(",") if part.strip())
    if controls and not CAMERA_CONTROLS_PATTERN.fullmatch(controls):
        raise ValueError(
            "camera controls must be a comma-separated v4l2 control list, "
            "for example brightness=96,gamma=105"
        )
    return controls


def tcl_braced(value: str) -> str:
    return "{" + value.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}") + "}"


def build_remote_capture_script(
    *,
    remote_device: str,
    input_format: str,
    video_size: str,
    remote_temp_path: str,
    camera_controls: str = "",
) -> str:
    controls = normalize_camera_controls(camera_controls)
    ffmpeg_common = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "v4l2",
        "-input_format",
        sh_quote(input_format),
        "-video_size",
        sh_quote(video_size),
    ]
    lines = [
        "set -eu",
        f"rm -f {sh_quote(remote_temp_path)}",
    ]
    if str(remote_device or "").strip().lower() in {"", "auto", "detect"}:
        lines.extend(
            [
                "devices=$(ls /dev/video* 2>/dev/null || true)",
                "if [ -z \"$devices\" ]; then",
                "  echo \"No /dev/video* camera devices found on remote board. Check that the USB/UVC camera is plugged in and visible to Linux.\" >&2",
                "  exit 66",
                "fi",
                "capture_ok=0",
                "for device in $devices; do",
                "  echo \"trying remote camera device: $device\" >&2",
            ]
        )
        if controls:
            lines.append(
                "  "
                + " ".join(["v4l2-ctl", "-d", "\"$device\"", "--set-ctrl", sh_quote(controls)])
                + " || continue"
            )
        lines.extend(
            [
                "  if "
                + " ".join(
                    [
                        *ffmpeg_common,
                        "-i",
                        "\"$device\"",
                        "-frames:v",
                        "1",
                        "-y",
                        sh_quote(remote_temp_path),
                    ]
                )
                + "; then",
                "    capture_ok=1",
                "    break",
                "  fi",
                "done",
                "if [ \"$capture_ok\" -ne 1 ]; then",
                "  echo \"No remote camera device produced a JPEG frame. Tried: $devices\" >&2",
                "  exit 67",
                "fi",
            ]
        )
    else:
        lines.extend(
            [
                f"capture_device={sh_quote(remote_device)}",
                "if [ ! -e \"$capture_device\" ]; then",
                "  echo \"remote camera device not found: $capture_device\" >&2",
                "  exit 66",
                "fi",
            ]
        )
        if controls:
            lines.append(" ".join(["v4l2-ctl", "-d", "\"$capture_device\"", "--set-ctrl", sh_quote(controls)]))
        lines.append(
            " ".join(
                [
                    *ffmpeg_common,
                    "-i",
                    "\"$capture_device\"",
                    "-frames:v",
                    "1",
                    "-y",
                    sh_quote(remote_temp_path),
                ]
            )
        )
    lines.extend(
        [
            f"echo {sh_quote(BEGIN_MARKER)}",
            f"base64 {sh_quote(remote_temp_path)}",
            f"echo {sh_quote(END_MARKER)}",
        ]
    )
    return "\n".join(lines)


def sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def build_ssh_command(
    *,
    host: str,
    user: str,
    port: int,
    bind_address: str,
    known_hosts_path: Path,
    connect_timeout: int,
    remote_script: str,
    batch_mode: bool,
    identity_file: str | None = None,
) -> list[str]:
    command = [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        f"UserKnownHostsFile={known_hosts_path}",
        "-o",
        f"ConnectTimeout={connect_timeout}",
    ]
    if batch_mode:
        command.extend(["-o", "BatchMode=yes"])
    if bind_address:
        command.extend(["-b", bind_address])
    # 添加 IdentityFile（如果提供）
    if identity_file:
        command.extend(["-i", identity_file])
    command.extend(["-p", str(port), f"{user}@{host}", "sh", "-lc", sh_quote(remote_script)])
    return command


DEFAULT_PLINK_HOSTKEYS = {
    ("192.168.0.183", 22): "SHA256:K8oyEoddaZ4keNu39exAqMJLDEcncgoQGcRPQ898Bb4",
}


def _resolve_plink_hostkey(*, host: str, port: int) -> str:
    configured = os.environ.get("MIRA_SHENZHEN_PLINK_HOSTKEY", "").strip() or os.environ.get("MIRA_PLINK_HOSTKEY", "").strip()
    if configured:
        return configured
    return DEFAULT_PLINK_HOSTKEYS.get((host, port), "")


def _build_plink_command(
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    remote_script: str,
) -> list[str]:
    plink_bin = shutil.which("plink") or shutil.which("plink.exe")
    if not plink_bin:
        raise RuntimeError("plink is required for password SSH on Windows. Install PuTTY or configure SSH key auth.")
    command = [
        plink_bin,
        "-batch",
        "-ssh",
        "-P",
        str(port),
    ]
    hostkey = _resolve_plink_hostkey(host=host, port=port)
    if hostkey:
        command.extend(["-hostkey", hostkey])
    command.extend([
        "-pw",
        password,
        f"{user}@{host}",
        "sh",
        "-lc",
        sh_quote(remote_script),
    ])
    return command


def run_ssh_with_password(
    *,
    command: list[str],
    password: str,
    timeout: int,
    host: str = "",
    port: int = 22,
    user: str = "",
    remote_script: str = "",
) -> subprocess.CompletedProcess[bytes]:
    expect_bin = shutil.which("expect")
    if not expect_bin:
        # Fallback to plink on Windows
        if os.name == "nt" and host and user and remote_script:
            plink_command = _build_plink_command(
                host=host,
                port=port,
                user=user,
                password=password,
                remote_script=remote_script,
            )
            return subprocess.run(
                plink_command,
                capture_output=True,
                timeout=timeout + 5,
            )
        raise RuntimeError("expect is required for password SSH. Install expect or configure SSH key auth.")
    command_items = " ".join(tcl_braced(item) for item in command)
    expect_script = "\n".join(
        [
            f"set timeout {int(timeout)}",
            f"set password {tcl_braced(password)}",
            f"set command [list {command_items}]",
            "spawn {*}$command",
            "expect {",
            '  -re "(?i)yes/no" { send "yes\\r"; exp_continue }',
            '  -re "(?i)password:" { send -- "$password\\r"; exp_continue }',
            "  eof {}",
            "  timeout { exit 124 }",
            "}",
            "catch wait result",
            "exit [lindex $result 3]",
            "",
        ]
    )
    return subprocess.run(
        [expect_bin],
        input=expect_script.encode("utf-8"),
        capture_output=True,
        timeout=timeout + 5,
    )


def summarize_remote_capture_failure(stderr: str, stdout: str) -> str:
    combined_lines = [line.strip() for line in f"{stderr}\n{stdout}".splitlines() if line.strip()]
    for pattern in REMOTE_CAMERA_ERROR_PATTERNS:
        for line in reversed(combined_lines):
            if pattern in line:
                summary = line[line.index(pattern) :]
                return re.sub(r"""["']?\s*>\s*&2\s*$""", "", summary).strip("\"'")
    for line in reversed(combined_lines):
        if line.startswith("spawn ssh ") or "password:" in line:
            continue
        return line
    return ""


def run_ssh_capture(
    *,
    host: str,
    user: str,
    port: int,
    password: str,
    bind_address: str,
    known_hosts_path: Path,
    connect_timeout: int,
    remote_script: str,
    timeout: int,
) -> bytes:
    # DEBUG: 打印 password 参数
    import sys
    print(f"[DEBUG run_ssh_capture] password={repr(password)}, type={type(password).__name__}, bool={bool(password)}", file=sys.stderr)

    # 尝试使用标准 SSH 密钥位置
    identity_file = None
    if not password:
        from pathlib import Path as _Path
        home = _Path.home()
        for key_path in [
            home / ".ssh" / "id_ed25519_mira",
            home / ".ssh" / "id_ed25519",
            home / ".ssh" / "id_rsa",
        ]:
            if key_path.exists():
                identity_file = str(key_path)
                break

    command = build_ssh_command(
        host=host,
        user=user,
        port=port,
        bind_address=bind_address,
        known_hosts_path=known_hosts_path,
        connect_timeout=connect_timeout,
        remote_script=remote_script,
        batch_mode=not password,
        identity_file=identity_file,
    )
    if password:
        result = run_ssh_with_password(
            command=command,
            password=password,
            timeout=timeout,
            host=host,
            port=port,
            user=user,
            remote_script=remote_script,
        )
    else:
        result = subprocess.run(command, capture_output=True, timeout=timeout)
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        stdout_tail = result.stdout.decode("utf-8", errors="replace").strip()[-1200:]
        summary = summarize_remote_capture_failure(stderr, stdout_tail)
        raise RuntimeError(f"remote camera capture failed with exit code {result.returncode}: {summary or stderr or stdout_tail}")
    return result.stdout


def extract_marked_base64_payload(raw_output: bytes | str) -> bytes:
    text = raw_output.decode("utf-8", errors="replace") if isinstance(raw_output, bytes) else raw_output
    end_index = text.rfind(END_MARKER)
    begin_index = text.rfind(BEGIN_MARKER, 0, end_index)
    if begin_index < 0 or end_index < 0 or end_index <= begin_index:
        tail = text[-1600:]
        raise ValueError(f"missing captured image markers in SSH output: {tail}")
    payload = text[begin_index + len(BEGIN_MARKER) : end_index]
    payload_lines = []
    for line in payload.splitlines():
        candidate = line.strip()
        if candidate and re.fullmatch(r"[A-Za-z0-9+/=]+", candidate):
            payload_lines.append(candidate)
    compact = "".join(payload_lines)
    if not compact:
        raise ValueError("captured image payload is empty")
    return base64.b64decode(compact, validate=True)


def validate_capture_image(image_bytes: bytes) -> None:
    if len(image_bytes) < MIN_CAPTURE_IMAGE_BYTES:
        raise ValueError(f"captured image is too small to be a valid camera frame: {len(image_bytes)} bytes")
    if not image_bytes.startswith(b"\xff\xd8"):
        raise ValueError("captured image does not look like a JPEG frame")


def write_capture_image(image_bytes: bytes, capture_dir: Path, timestamp: str) -> Path:
    validate_capture_image(image_bytes)
    capture_dir.mkdir(parents=True, exist_ok=True)
    output_path = capture_dir / f"digua-camera-{timestamp}.jpg"
    output_path.write_bytes(image_bytes)
    return output_path


def capture_remote_image(
    *,
    host: str,
    user: str,
    port: int,
    password: str,
    bind_address: str,
    known_hosts_path: Path,
    connect_timeout: int,
    remote_device: str,
    input_format: str,
    video_size: str,
    remote_temp_path: str,
    capture_dir: Path,
    timestamp: str,
    timeout: int,
    ssh_retries: int,
    ssh_retry_delay_seconds: float,
    camera_controls: str = "",
) -> Path:
    remote_script = build_remote_capture_script(
        remote_device=remote_device,
        input_format=input_format,
        video_size=video_size,
        remote_temp_path=remote_temp_path,
        camera_controls=camera_controls,
    )
    attempts = max(1, ssh_retries)
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            raw_output = run_ssh_capture(
                host=host,
                user=user,
                port=port,
                password=password,
                bind_address=bind_address,
                known_hosts_path=known_hosts_path,
                connect_timeout=connect_timeout,
                remote_script=remote_script,
                timeout=timeout,
            )
            break
        except Exception as exc:
            last_error = exc
            if attempt >= attempts:
                raise
            time.sleep(ssh_retry_delay_seconds)
    else:
        if last_error is not None:
            raise last_error
        raise RuntimeError("remote camera capture retry loop exited unexpectedly")
    return write_capture_image(extract_marked_base64_payload(raw_output), capture_dir, timestamp)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture one frame from the Digua board camera over SSH and render it with Seedream anime styling."
    )
    parser.add_argument("--host", default=os.environ.get("DIGUA_CAMERA_HOST", DEFAULT_HOST))
    parser.add_argument("--user", default=os.environ.get("DIGUA_SSH_USER", DEFAULT_USER))
    parser.add_argument("--port", type=int, default=int(os.environ.get("DIGUA_SSH_PORT", DEFAULT_PORT)))
    parser.add_argument("--password", default=os.environ.get("DIGUA_SSH_PASSWORD", ""))
    parser.add_argument("--bind-address", default=os.environ.get("DIGUA_SSH_BIND_ADDRESS", ""))
    parser.add_argument("--known-hosts-path", type=Path, default=DEFAULT_KNOWN_HOSTS_PATH)
    parser.add_argument("--connect-timeout", type=int, default=DEFAULT_CONNECT_TIMEOUT)
    parser.add_argument("--remote-device", default=os.environ.get("DIGUA_CAMERA_DEVICE", DEFAULT_DEVICE))
    parser.add_argument("--input-format", default=DEFAULT_INPUT_FORMAT)
    parser.add_argument("--video-size", default=DEFAULT_VIDEO_SIZE)
    parser.add_argument("--remote-temp-path", default="/tmp/digua-camera-capture.jpg")
    parser.add_argument("--camera-controls", default=os.environ.get("DIGUA_CAMERA_V4L2_CTRLS", ""))
    parser.add_argument("--capture-dir", type=Path, default=DEFAULT_CAPTURE_DIR)
    parser.add_argument("--capture-timeout", type=int, default=90)
    parser.add_argument("--ssh-retries", type=int, default=DEFAULT_SSH_RETRIES)
    parser.add_argument("--ssh-retry-delay-seconds", type=float, default=DEFAULT_SSH_RETRY_DELAY_SECONDS)
    parser.add_argument("--capture-only", action="store_true")
    parser.add_argument("--api-key", default=os.environ.get("ARK_API_KEY", ""))
    parser.add_argument("--api-url", default=pipeline.DEFAULT_API_URL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model", default=pipeline.DEFAULT_MODEL)
    parser.add_argument("--size", default=pipeline.DEFAULT_SIZE)
    parser.add_argument("--response-format", default=pipeline.DEFAULT_RESPONSE_FORMAT)
    parser.add_argument("--timeout", type=int, default=pipeline.DEFAULT_TIMEOUT)
    parser.add_argument("--style-slug", default=DEFAULT_STYLE_SLUG)
    parser.add_argument("--style-prompt", default=DEFAULT_STYLE_PROMPT)
    parser.add_argument("--timestamp")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    timestamp = args.timestamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        source_image_path = capture_remote_image(
            host=args.host,
            user=args.user,
            port=args.port,
            password=args.password,
            bind_address=args.bind_address,
            known_hosts_path=args.known_hosts_path,
            connect_timeout=args.connect_timeout,
            remote_device=args.remote_device,
            input_format=args.input_format,
            video_size=args.video_size,
            remote_temp_path=args.remote_temp_path,
            camera_controls=args.camera_controls,
            capture_dir=args.capture_dir,
            timestamp=timestamp,
            timeout=args.capture_timeout,
            ssh_retries=args.ssh_retries,
            ssh_retry_delay_seconds=args.ssh_retry_delay_seconds,
        )
        result: dict[str, object] = {
            "ok": True,
            "capture": {
                "host": args.host,
                "port": args.port,
                "user": args.user,
                "bind_address": args.bind_address,
                "remote_device": args.remote_device,
                "input_format": args.input_format,
                "video_size": args.video_size,
                "camera_controls": normalize_camera_controls(args.camera_controls),
                "source_image_path": str(source_image_path),
            },
        }
        if not args.capture_only:
            if not args.api_key:
                raise RuntimeError("Provide --api-key or set ARK_API_KEY before rendering.")
            generation = rokid_render_pipeline.generate_from_image_path(
                api_key=args.api_key,
                image_path=source_image_path,
                output_dir=args.output_dir,
                model=args.model,
                size=args.size,
                response_format=args.response_format,
                api_url=args.api_url,
                timeout=args.timeout,
                style_slug=args.style_slug,
                style_prompt=args.style_prompt,
                timestamp=timestamp,
            )
            result["generation"] = generation
            result["output_path"] = generation["output_path"]
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
