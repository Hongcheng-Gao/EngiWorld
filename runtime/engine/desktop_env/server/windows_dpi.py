"""Physical-pixel coordinates for the Windows guest and GUI action processes.

No display settings are changed here. UI Automation, capture and input must use
the same DPI context, including Flask and accessibility traversal pool threads.
"""

import ctypes
from ctypes import wintypes
from contextlib import contextmanager
from functools import lru_cache
import inspect
import sys


class DpiCoordinateError(RuntimeError):
    """The guest cannot guarantee physical-pixel observations."""


def initialize_dpi_awareness():
    """Run before GUI imports; also embedded verbatim in GUI action children.

    Keep this function self-contained: action children do not need the server
    directory on sys.path. A host/manifest may have locked the process default;
    in that case the explicit thread context still guarantees physical pixels.
    """
    import ctypes
    import sys

    if sys.platform != "win32":
        return None
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    set_process = user32.SetProcessDpiAwarenessContext
    set_process.argtypes = [ctypes.c_void_p]
    set_process.restype = ctypes.c_bool
    set_thread = user32.SetThreadDpiAwarenessContext
    set_thread.argtypes = [ctypes.c_void_p]
    set_thread.restype = ctypes.c_void_p
    # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 is a pointer-sized pseudo-handle.
    context = ctypes.c_void_p(-4)
    ctypes.set_last_error(0)
    process_set = bool(set_process(context))
    error = ctypes.get_last_error()
    if not process_set and error != 5:  # ERROR_ACCESS_DENIED: already configured
        raise RuntimeError(f"DpiCoordinateError: process DPI initialization failed ({error})")
    if not set_thread(context):
        raise RuntimeError(
            f"DpiCoordinateError: thread DPI initialization failed ({ctypes.get_last_error()})"
        )
    return {"coordinate_space": "physical_pixels", "process_default_set": process_set}


@lru_cache(maxsize=1)
def action_dpi_bootstrap():
    """Use the same initialization in fresh action interpreters, before imports."""
    return inspect.getsource(initialize_dpi_awareness) + "\ninitialize_dpi_awareness()\n"


@lru_cache(maxsize=1)
def _user32():
    api = ctypes.WinDLL("user32", use_last_error=True)
    api.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    api.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
    api.GetThreadDpiAwarenessContext.argtypes = []
    api.GetThreadDpiAwarenessContext.restype = ctypes.c_void_p
    api.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    api.GetAwarenessFromDpiAwarenessContext.restype = ctypes.c_int
    api.GetPhysicalCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    api.GetPhysicalCursorPos.restype = wintypes.BOOL
    api.GetSystemMetrics.argtypes = [ctypes.c_int]
    api.GetSystemMetrics.restype = ctypes.c_int
    return api


@contextmanager
def physical_pixel_context():
    """Set and restore awareness on *this* request/traversal thread."""
    if sys.platform != "win32":
        yield
        return
    api = _user32()
    previous = api.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
    if not previous:
        raise DpiCoordinateError(f"Cannot set physical-pixel thread context ({ctypes.get_last_error()})")
    try:
        yield
    finally:
        if not api.SetThreadDpiAwarenessContext(ctypes.c_void_p(previous)):
            raise DpiCoordinateError(f"Cannot restore thread DPI context ({ctypes.get_last_error()})")


def physical_cursor_position():
    point = wintypes.POINT()
    if not _user32().GetPhysicalCursorPos(ctypes.byref(point)):
        raise DpiCoordinateError(f"Cannot read physical cursor ({ctypes.get_last_error()})")
    return point.x, point.y


def coordinate_status():
    if sys.platform != "win32":
        return None
    with physical_pixel_context():
        api = _user32()
        awareness = api.GetAwarenessFromDpiAwarenessContext(api.GetThreadDpiAwarenessContext())
        if awareness != 2:  # DPI_AWARENESS_PER_MONITOR_AWARE
            raise DpiCoordinateError(f"Expected per-monitor DPI awareness, got {awareness}")
        return {
            "coordinate_space": "physical_pixels",
            "dpi_awareness": awareness,
            "screen_width": api.GetSystemMetrics(0),
            "screen_height": api.GetSystemMetrics(1),
        }


def validate_screenshot_size(size):
    status = coordinate_status()
    if status is None:
        return
    expected = (status["screen_width"], status["screen_height"])
    if tuple(size) != expected:
        raise DpiCoordinateError(
            f"Screenshot size {tuple(size)} does not match physical desktop {expected}"
        )
