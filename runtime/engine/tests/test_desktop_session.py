import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest


spec = importlib.util.spec_from_file_location(
    "desktop_session", Path(__file__).resolve().parents[1] / "desktop_env" / "desktop_session.py"
)
session = importlib.util.module_from_spec(spec)
spec.loader.exec_module(session)


def test_linux_sets_connected_output(monkeypatch):
    monkeypatch.setattr(session.subprocess, "check_output", lambda *a, **kw: "Screen 0\nDUMMY0 connected primary 1024x768\nDUMMY1 disconnected\n")
    commands = []
    monkeypatch.setattr(session.subprocess, "run", lambda command, **kw: commands.append(command))
    session._linux_resolution(1920, 1080)
    assert commands == [["xrandr", "--output", "DUMMY0", "--mode", "1920x1080"]]


def test_linux_rejects_ambiguous_display_layout(monkeypatch):
    monkeypatch.setattr(session.subprocess, "check_output", lambda *a, **kw: "A connected\nB connected\n")
    with pytest.raises(RuntimeError, match="one connected"):
        session._linux_resolution(1920, 1080)


def test_desktop_verifies_actual_screenshot(monkeypatch):
    monkeypatch.setattr(session.platform, "system", lambda: "Linux")
    monkeypatch.setattr(session, "_linux_resolution", lambda *a: None)
    monkeypatch.setattr(session.time, "sleep", lambda _: None)
    monkeypatch.setitem(sys.modules, "pyautogui", SimpleNamespace(screenshot=lambda: SimpleNamespace(size=(1024, 768))))
    with pytest.raises(RuntimeError, match="screenshot is"):
        session.prepare_desktop(1920, 1080)


def test_desktop_accepts_matching_screenshot(monkeypatch):
    monkeypatch.setattr(session.platform, "system", lambda: "Linux")
    monkeypatch.setattr(session, "_linux_resolution", lambda *a: None)
    monkeypatch.setitem(sys.modules, "pyautogui", SimpleNamespace(screenshot=lambda: SimpleNamespace(size=(1920, 1080))))
    assert session.prepare_desktop(1920, 1080)["width"] == 1920


def test_solidworks_license_is_reported_as_image_setup(monkeypatch):
    monkeypatch.setitem(sys.modules, "win32gui", SimpleNamespace(
        EnumWindows=lambda fn, arg: fn(42, arg),
        IsWindowVisible=lambda hwnd: True,
        GetWindowText=lambda hwnd: "SOLIDWORKS License Agreement",
    ))
    with pytest.raises(RuntimeError, match="Image setup is incomplete"):
        session._check_windows_startup_dialogs()
