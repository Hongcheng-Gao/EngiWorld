"""DPI regressions without requiring a Windows desktop on the test runner."""
import ast
import ctypes
import importlib.util
from pathlib import Path
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("windows_dpi_under_test", ROOT / "desktop_env/server/windows_dpi.py")
dpi = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dpi)


class Function:
    def __init__(self, fn):
        self.fn = fn

    def __call__(self, *args):
        return self.fn(*args)


class Windows:
    def __init__(self, scale=1.5, locked=False, process_error=5, thread_failure=False):
        self.scale = scale
        self.local = threading.local()
        self.locked = locked
        self.error = 0
        self.process_error = process_error
        self.thread_failure = thread_failure
        self.SetProcessDpiAwarenessContext = Function(self.set_process)
        self.SetThreadDpiAwarenessContext = Function(self.set_thread)
        self.GetThreadDpiAwarenessContext = Function(lambda: self.context)
        self.GetAwarenessFromDpiAwarenessContext = Function(lambda value: 2 if self.context == -4 else 0)
        self.GetPhysicalCursorPos = Function(self.cursor)
        self.GetSystemMetrics = Function(lambda index: int((1920, 1080)[index] / (1 if self.context == -4 else self.scale)))

    @property
    def context(self):
        return getattr(self.local, "context", -1)

    def set_process(self, context):
        self.error = self.process_error if self.locked else 0
        return not self.locked

    def set_thread(self, context):
        if self.thread_failure:
            self.error = 87
            return None
        previous = self.context
        self.local.context = ctypes.c_ssize_t(context.value).value
        return previous

    def cursor(self, ptr):
        ptr._obj.x, ptr._obj.y = 1015, 1065
        return True


@pytest.fixture
def windows(monkeypatch):
    fake = Windows()
    monkeypatch.setattr(ctypes, "WinDLL", lambda *a, **k: fake, raising=False)
    monkeypatch.setattr(ctypes, "set_last_error", lambda value: setattr(fake, "error", value), raising=False)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: fake.error, raising=False)
    dpi._user32.cache_clear()
    yield fake
    dpi._user32.cache_clear()


@pytest.mark.parametrize("scale", [1.0, 1.25, 1.5])
def test_capture_size_uses_physical_pixels_at_each_scale(windows, scale):
    windows.scale = scale
    with patch.object(sys, "platform", "win32"):
        assert dpi.coordinate_status()["screen_width"] == 1920
        dpi.validate_screenshot_size((1920, 1080))
        assert dpi.physical_cursor_position() == (1015, 1065)
    assert windows.context == -1


def test_wrong_capture_size_fails_instead_of_returning_misaligned_observation(windows):
    with patch.object(sys, "platform", "win32"):
        with pytest.raises(dpi.DpiCoordinateError, match="does not match physical desktop"):
            dpi.validate_screenshot_size((1280, 720))


def test_locked_process_default_still_initializes_current_thread(windows):
    windows.locked = True
    with patch.object(sys, "platform", "win32"):
        result = dpi.initialize_dpi_awareness()
    assert result["process_default_set"] is False
    assert windows.context == -4


def test_unexpected_initialization_error_is_not_silenced(windows):
    windows.locked = True
    windows.process_error = 87
    with patch.object(sys, "platform", "win32"):
        with pytest.raises(RuntimeError, match="process DPI initialization failed"):
            dpi.initialize_dpi_awareness()


def test_thread_failure_is_not_silenced(windows):
    windows.thread_failure = True
    with patch.object(sys, "platform", "win32"):
        with pytest.raises(dpi.DpiCoordinateError, match="Cannot set"):
            with dpi.physical_pixel_context():
                pytest.fail("must not collect a tree with the wrong context")


def test_context_is_applied_in_pool_threads_and_restored_after_exceptions(windows):
    def collect():
        before = windows.context
        try:
            with dpi.physical_pixel_context():
                assert windows.context == -4
                with dpi.physical_pixel_context():
                    assert windows.context == -4
                assert windows.context == -4
                raise ValueError("provider error")
        except ValueError:
            return before, windows.context

    with patch.object(sys, "platform", "win32"):
        with ThreadPoolExecutor(max_workers=3) as pool:
            assert list(pool.map(lambda _: collect(), range(9))) == [(-1, -1)] * 9


def test_gui_action_bootstrap_works_without_importing_the_server_package(windows):
    with patch.object(sys, "platform", "win32"):
        exec(dpi.action_dpi_bootstrap(), {})
    assert windows.context == -4


def test_non_windows_is_a_noop(monkeypatch):
    monkeypatch.setattr(dpi, "_user32", lambda: pytest.fail("Windows API used on Linux"))
    with patch.object(sys, "platform", "linux"):
        assert dpi.initialize_dpi_awareness() is None
        assert dpi.coordinate_status() is None
        dpi.validate_screenshot_size((384, 216))
        with dpi.physical_pixel_context():
            pass
        exec(dpi.action_dpi_bootstrap(), {})


def test_guest_initializes_before_gui_imports_and_wraps_every_capture_thread():
    module = ast.parse((ROOT / "desktop_env/server/main.py").read_text(encoding="utf-8"))
    initialized = next(n.lineno for n in module.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and getattr(n.value.func, "id", None) == "initialize_dpi_awareness")
    imported = [n.lineno for n in ast.walk(module) if isinstance(n, ast.Import) and any(a.name in {"pyautogui", "pywinauto.application"} for a in n.names)]
    assert all(initialized < line for line in imported)
    functions = {n.name: n for n in module.body if isinstance(n, ast.FunctionDef)}
    for name in ["capture_screen_with_cursor", "get_accessibility_tree", "_create_pywinauto_node", "get_screen_size", "get_cursor_position"]:
        assert any(isinstance(d, ast.Call) and getattr(d.func, "id", None) == "physical_pixel_context" for d in functions[name].decorator_list), name


def test_gui_controller_prepends_bootstrap_before_action_imports():
    module = ast.parse((ROOT / "desktop_env/controllers/python.py").read_text(encoding="utf-8"))
    cls = next(n for n in module.body if isinstance(n, ast.ClassDef) and n.name == "PythonController")
    fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "execute_python_command")
    ns = {"Dict": dict, "Any": object, "action_dpi_bootstrap": lambda: "DPI_BOOTSTRAP\n", "logger": type("Log", (), {"info": lambda *a: None})()}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "controller-test", "exec"), ns)
    codes = []
    class Controller:
        pkgs_prefix = "import pyautogui; {command}"
        def _build_python_bash_script(self, code):
            codes.append(code)
            return code
        def run_bash_script(self, code, timeout):
            return {"returncode": 0}
        def _python_result_from_bash(self, result):
            return result
    ns["execute_python_command"](Controller(), "pyautogui.click(900, 600)")
    assert codes == ["DPI_BOOTSTRAP\nimport pyautogui; pyautogui.click(900, 600)"]
