"""Cross-platform runtime paths and screen-recording commands."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def runtime_directory() -> Path:
    configured = os.environ.get("OSWORLD_RUNTIME_DIR")
    root = (
        Path(configured).expanduser()
        if configured
        else Path(tempfile.gettempdir()) / "osworld-server"
    )
    root.mkdir(parents=True, exist_ok=True)
    return root


def screenshot_path() -> Path:
    path = runtime_directory() / "screenshots" / "screenshot.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def recording_path() -> Path:
    return runtime_directory() / "recording.mp4"


def recording_command(
    platform_name: str,
    output_path: Path,
    *,
    screen_size: tuple[int, int] | None = None,
) -> list[str]:
    common = ["ffmpeg", "-y", "-loglevel", "error"]
    if platform_name == "Windows":
        return [
            *common,
            "-f",
            "gdigrab",
            "-framerate",
            "30",
            "-draw_mouse",
            "1",
            "-i",
            "desktop",
            "-c:v",
            "libx264",
            str(output_path),
        ]
    if platform_name == "Linux":
        if screen_size is None:
            raise ValueError("screen_size is required for Linux recording")
        width, height = screen_size
        return [
            *common,
            "-f",
            "x11grab",
            "-draw_mouse",
            "1",
            "-video_size",
            f"{width}x{height}",
            "-framerate",
            "30",
            "-i",
            ":0.0",
            "-c:v",
            "libx264",
            str(output_path),
        ]
    raise NotImplementedError(f"Screen recording is not supported on {platform_name}")
