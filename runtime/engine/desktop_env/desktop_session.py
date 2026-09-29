"""Trusted desktop preparation executed in the sandbox before model actions."""

import json
import platform
import re
import subprocess
import time


def _linux_resolution(width, height):
    listing = subprocess.check_output(["xrandr", "--query"], text=True, timeout=15)
    outputs = re.findall(r"^(\S+) connected\b", listing, re.MULTILINE)
    if len(outputs) != 1:
        raise RuntimeError(f"Expected one connected display, found {outputs}")
    subprocess.run(
        ["xrandr", "--output", outputs[0], "--mode", f"{width}x{height}"],
        check=True, capture_output=True, text=True, timeout=15,
    )


def _windows_resolution(width, height):
    import ctypes
    import win32api

    ctypes.windll.user32.SetProcessDPIAware()
    mode = win32api.EnumDisplaySettings(None, -1)
    if (mode.PelsWidth, mode.PelsHeight) != (width, height):
        mode.PelsWidth, mode.PelsHeight = width, height
        mode.Fields = 0x00080000 | 0x00100000  # DM_PELSWIDTH | DM_PELSHEIGHT
        result = win32api.ChangeDisplaySettings(mode, 0)
        if result != 0:
            supported = set()
            index = 0
            while True:
                try:
                    candidate = win32api.EnumDisplaySettings(None, index)
                except Exception:
                    break
                supported.add((candidate.PelsWidth, candidate.PelsHeight))
                index += 1
            raise RuntimeError(
                f"Windows rejected {width}x{height}: display status {result}; "
                f"supported desktop sizes: {sorted(supported)}. "
                "Configure the image display driver to support the requested size."
            )


def _hide_server_console(server_port):
    """Hide only the console attached to the process listening on the server port."""
    import ctypes
    from ctypes import wintypes

    command = (
        f"Get-NetTCPConnection -LocalPort {int(server_port)} -State Listen "
        "| Select-Object -ExpandProperty OwningProcess -Unique"
    )
    pids = subprocess.check_output(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        stdin=subprocess.DEVNULL, stderr=subprocess.PIPE,
        creationflags=0x08000000, text=True, timeout=20,
    ).split()
    if len(pids) != 1:
        raise RuntimeError(f"Expected one server process on port {server_port}, found {pids}")
    kernel = ctypes.windll.kernel32
    user = ctypes.windll.user32
    kernel.GetConsoleWindow.restype = wintypes.HWND
    kernel.GetStdHandle.restype = wintypes.HANDLE
    user.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    kernel.FreeConsole()
    if not kernel.AttachConsole(int(pids[0])):
        error = kernel.GetLastError()
        if error == 6:  # The server already runs without a console.
            return "consoleless"
        raise RuntimeError(f"Cannot attach to server console: Windows error {error}")
    try:
        hwnd = kernel.GetConsoleWindow()
        if hwnd:
            user.ShowWindow(hwnd, 0)
            if user.IsWindowVisible(hwnd):
                raise RuntimeError("Server console remained visible")
        return "hidden" if hwnd else "consoleless"
    finally:
        kernel.FreeConsole()


def _check_windows_startup_dialogs():
    import win32gui

    blocked = []
    def inspect(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).strip()
            if title.casefold() == "solidworks license agreement":
                blocked.append(title)
    win32gui.EnumWindows(inspect, None)
    if blocked:
        raise RuntimeError(
            "Image setup is incomplete: SOLIDWORKS License Agreement is open. "
            "Complete the application license setup in the image before evaluation."
        )


def prepare_desktop(width, height, server_port=5000, check_startup_dialogs=False):
    width, height = int(width), int(height)
    if width <= 0 or height <= 0:
        raise ValueError("Desktop dimensions must be positive")
    system = platform.system()
    console = "not applicable"
    if system == "Windows":
        console = _hide_server_console(server_port)
        _windows_resolution(width, height)
        if check_startup_dialogs:
            _check_windows_startup_dialogs()
    elif system == "Linux":
        _linux_resolution(width, height)
    else:
        raise RuntimeError(f"Desktop preparation is not implemented for {system}")
    import pyautogui
    actual = None
    for _ in range(10):
        actual = tuple(pyautogui.screenshot().size)
        if actual == (width, height):
            return {"width": width, "height": height, "server_console": console}
        time.sleep(0.2)
    raise RuntimeError(f"Requested desktop {width}x{height}, screenshot is {actual}")
