import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from errors import AppError

ALLOWED_FORMAT_TOKENS = {"webm", "matroska"}
ALLOWED_AUDIO_CODECS = {"opus"}
PROBE_TIMEOUT_SECONDS = 8


@dataclass
class AudioProbeResult:
    format_name: str
    codec_name: str
    duration_seconds: float
    duration_source: str


def _raise_unsupported() -> None:
    raise AppError(
        415,
        "UNSUPPORTED_MEDIA_TYPE",
        "当前录音格式不受支持，请使用可录制 WebM/Opus 的浏览器。",
        "upload",
    )


def _raise_invalid_duration(message: str) -> None:
    raise AppError(422, "INVALID_AUDIO_DURATION", message, "upload")


def _run_ffprobe(args: list[str]) -> subprocess.CompletedProcess[str]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise AppError(
            502,
            "AUDIO_PROBE_UNAVAILABLE",
            "服务器缺少音频探测工具 ffprobe，请先安装 FFmpeg 后再试。",
            "upload",
        )
    try:
        return subprocess.run(
            [ffprobe, *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise AppError(
            504,
            "AUDIO_PROBE_TIMEOUT",
            "音频校验超时，请重新上传较短的录音。",
            "upload",
        ) from exc


def _parse_duration(value: object) -> float | None:
    if value in (None, "", "N/A", "n/a"):
        return None
    try:
        duration = float(value)
    except (TypeError, ValueError):
        return None
    if duration <= 0:
        return None
    return duration


def _duration_from_packets(path: Path) -> float | None:
    completed = _run_ffprobe(
        [
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "packet=pts_time,dts_time,duration_time",
            "-of",
            "csv=p=0",
            str(path),
        ]
    )
    if completed.returncode != 0:
        return None

    first_ts: float | None = None
    last_ts: float | None = None
    last_packet_duration = 0.0

    for raw_line in completed.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split(",")]
        timestamp = None
        packet_duration = 0.0
        for index, part in enumerate(parts):
            parsed = _parse_duration(part)
            if parsed is None:
                continue
            if index < 2 and timestamp is None:
                timestamp = parsed
            elif index >= 2:
                packet_duration = parsed
        if timestamp is None:
            continue
        if first_ts is None:
            first_ts = timestamp
        last_ts = timestamp
        last_packet_duration = packet_duration

    if first_ts is None or last_ts is None:
        return None
    duration = last_ts + last_packet_duration - first_ts
    if duration <= 0 and last_packet_duration > 0:
        duration = last_packet_duration
    return duration if duration > 0 else None


def probe_audio(path: Path) -> AudioProbeResult:
    completed = _run_ffprobe(
        [
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
    )
    if completed.returncode != 0:
        _raise_unsupported()

    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        _raise_unsupported()

    format_info = payload.get("format") or {}
    format_name = str(format_info.get("format_name") or "")
    format_tokens = {token.strip() for token in format_name.split(",") if token.strip()}
    if not format_tokens.intersection(ALLOWED_FORMAT_TOKENS):
        _raise_unsupported()

    audio_stream = None
    for stream in payload.get("streams") or []:
        if stream.get("codec_type") == "audio":
            audio_stream = stream
            break
    if audio_stream is None:
        _raise_unsupported()

    codec_name = str(audio_stream.get("codec_name") or "").lower()
    if codec_name not in ALLOWED_AUDIO_CODECS:
        _raise_unsupported()

    duration = _parse_duration(format_info.get("duration"))
    duration_source = "format"
    if duration is None:
        duration = _parse_duration(audio_stream.get("duration"))
        duration_source = "stream"
    if duration is None:
        duration = _duration_from_packets(path)
        duration_source = "packets"
    if duration is None:
        _raise_invalid_duration("无法读取录音时长，请重新录制。")

    return AudioProbeResult(
        format_name=format_name,
        codec_name=codec_name,
        duration_seconds=duration,
        duration_source=duration_source,
    )


def validate_uploaded_audio(path: Path) -> AudioProbeResult:
    result = probe_audio(path)
    if result.duration_seconds < 1.0 or result.duration_seconds > 60.0:
        _raise_invalid_duration("录音时长需在1到60秒之间，请重新录制。")
    return result
