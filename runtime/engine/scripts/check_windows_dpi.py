"""Check guest capture/UIA coordinates; optional click only in an idle test VM.

Does not change Windows scaling, resolution, or any application document.
"""
import argparse
import concurrent.futures
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--click-test", action="store_true", help="Create and click a temporary button in an idle VM")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(args.server_dir.resolve()))
    # Loading the actual guest entry point also checks initialization ordering.
    spec = importlib.util.spec_from_file_location("dpi_validation_guest", args.server_dir / "main.py")
    guest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guest)
    import windows_dpi as dpi
    import ctypes
    from PIL import ImageGrab
    from pywinauto import Desktop
    import win32con
    import win32gui
    import win32api

    cp = "{https://accessibility.windows.example.org/ns/component}"
    report = {"status": dpi.coordinate_status(), "screenshot_size": list(ImageGrab.grab().size)}
    dpi.validate_screenshot_size(report["screenshot_size"])
    taskbar = Desktop(backend="uia").window(class_name="Shell_TrayWnd").wrapper_object()
    import ast
    report["taskbar_physical_rect"] = list(win32gui.GetWindowRect(taskbar.handle))
    get_dpi = dpi._user32().GetDpiForWindow
    get_dpi.argtypes = [ctypes.c_void_p]
    get_dpi.restype = ctypes.c_uint
    report["taskbar_dpi"] = get_dpi(ctypes.c_void_p(taskbar.handle))

    def collect_in_unaware_thread():
        api = dpi._user32()
        old = api.SetThreadDpiAwarenessContext(ctypes.c_void_p(-1))
        try:
            before = api.GetAwarenessFromDpiAwarenessContext(api.GetThreadDpiAwarenessContext())
            tree = guest._create_pywinauto_node(taskbar, {}, 1)
            after = api.GetAwarenessFromDpiAwarenessContext(api.GetThreadDpiAwarenessContext())
            return {"before_awareness": before, "after_awareness": after,
                    "taskbar_position": tree.get(cp + "screencoord"), "taskbar_size": tree.get(cp + "size")}
        finally:
            api.SetThreadDpiAwarenessContext(ctypes.c_void_p(old))

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        report["pool_trees"] = list(pool.map(lambda _: collect_in_unaware_thread(), range(2)))
    for row in report["pool_trees"]:
        x, y = ast.literal_eval(row["taskbar_position"])
        w, h = ast.literal_eval(row["taskbar_size"])
        assert [x, y, x+w, y+h] == report["taskbar_physical_rect"], row
        assert row["before_awareness"] == row["after_awareness"] == 0, row
    # Exercise /accessibility without traversing unrelated application windows.
    class TaskbarDesktop:
        def __init__(self, **kwargs):
            pass
        def windows(self):
            return [taskbar]
    real_desktop = guest.Desktop
    guest.Desktop = TaskbarDesktop
    try:
        client = guest.app.test_client()
        health = client.get("/health")
        response = client.get("/accessibility")
        assert health.status_code == response.status_code == 200, response.data.decode()
        payload = response.get_json()
        report["endpoint_coordinates"] = payload["coordinates"]
        (args.output / "taskbar.xml").write_text(payload["AT"], encoding="utf-8")
    finally:
        guest.Desktop = real_desktop

    child = dpi.action_dpi_bootstrap() + "\nimport pyautogui,json; print(json.dumps({'screen':list(pyautogui.size()),'cursor':list(pyautogui.position())}))"
    process = subprocess.run([sys.executable, "-c", child], capture_output=True, text=True, timeout=30)
    assert process.returncode == 0, process.stderr
    report["action_process"] = json.loads(process.stdout)
    assert report["action_process"]["screen"] == report["screenshot_size"]

    if args.click_test:
        clicked = []
        def procedure(hwnd, message, wparam, lparam):
            if message == win32con.WM_COMMAND and (wparam & 0xFFFF) == 701:
                clicked.append(True)
                return 0
            return win32gui.DefWindowProc(hwnd, message, wparam, lparam)
        klass = win32gui.WNDCLASS()
        klass.hInstance = win32api.GetModuleHandle(None)
        klass.lpszClassName = "OSWorldDpiValidation"
        klass.lpfnWndProc = procedure
        klass.hbrBackground = win32con.COLOR_WINDOW + 1
        atom = win32gui.RegisterClass(klass)
        window = None
        saved_cursor = dpi.physical_cursor_position()
        try:
            window = win32gui.CreateWindowEx(
                win32con.WS_EX_TOPMOST | win32con.WS_EX_TOOLWINDOW, atom,
                "OSWorld coordinate validation", win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE,
                240, 180, 520, 260, 0, 0, klass.hInstance, None,
            )
            button = win32gui.CreateWindowEx(0, "BUTTON", "DPI coordinate check",
                win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.BS_PUSHBUTTON,
                80, 60, 260, 55, window, 701, klass.hInstance, None)
            win32gui.UpdateWindow(window)
            win32gui.PumpWaitingMessages()
            wrapper = Desktop(backend="uia").window(handle=button).wrapper_object()
            node = guest._create_pywinauto_node(wrapper, {}, 1)
            x, y = ast.literal_eval(node.get(cp + "screencoord"))
            w, h = ast.literal_eval(node.get(cp + "size"))
            rectangle = list(win32gui.GetWindowRect(button))
            assert [x, y, x+w, y+h] == rectangle, (node.attrib, rectangle)
            center = (x+w//2, y+h//2)
            report["button"] = {"physical_rect": rectangle, "tree_position": [x,y], "tree_size": [w,h], "click": center}
            guest.runtime_screenshot_path = lambda: args.output / "screenshot.png"
            response = guest.app.test_client().get("/screenshot")
            assert response.status_code == 200, response.data.decode()
            response.close()
            action = dpi.action_dpi_bootstrap() + f"\nimport pyautogui; pyautogui.click({center[0]}, {center[1]})"
            process = subprocess.Popen([sys.executable, "-c", action], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            deadline = time.monotonic()+30
            while time.monotonic() < deadline and (process.poll() is None or not clicked):
                win32gui.PumpWaitingMessages()
                time.sleep(0.02)
            if process.poll() is None:
                process.kill()
            stdout, stderr = process.communicate(timeout=5)
            report["button"]["click_events"] = len(clicked)
            assert process.returncode == 0 and len(clicked) == 1, (stdout, stderr, report["button"])
        finally:
            if window:
                win32gui.DestroyWindow(window)
            win32gui.UnregisterClass(atom, klass.hInstance)
            win32api.SetCursorPos(saved_cursor)
    report["passed"] = True
    (args.output / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
