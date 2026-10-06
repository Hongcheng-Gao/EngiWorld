from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).parents[1] / "desktop_env" / "server" / "runtime_media.py"
SPEC = importlib.util.spec_from_file_location("runtime_media", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_windows_recording_uses_gdigrab_without_x11() -> None:
    command = MODULE.recording_command("Windows", Path(r"C:\Temp\recording.mp4"))

    assert "gdigrab" in command
    assert "desktop" in command
    assert "x11grab" not in command
    assert ":0.0" not in command


def test_linux_recording_uses_x11_display_and_size() -> None:
    command = MODULE.recording_command(
        "Linux",
        Path("/tmp/recording.mp4"),
        screen_size=(1920, 1080),
    )

    assert "x11grab" in command
    assert "1920x1080" in command
    assert ":0.0" in command


def test_linux_recording_requires_screen_size() -> None:
    with pytest.raises(ValueError, match="screen_size"):
        MODULE.recording_command("Linux", Path("/tmp/recording.mp4"))


def test_runtime_media_uses_configured_directory(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OSWORLD_RUNTIME_DIR", str(tmp_path / "runtime"))

    screenshot = MODULE.screenshot_path()
    recording = MODULE.recording_path()

    assert screenshot == tmp_path / "runtime" / "screenshots" / "screenshot.png"
    assert screenshot.parent.is_dir()
    assert recording == tmp_path / "runtime" / "recording.mp4"
