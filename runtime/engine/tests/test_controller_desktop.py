from io import BytesIO

from PIL import Image
import pytest

from desktop_env.controllers.python import PythonController
from desktop_env.errors import DesktopPreparationError


def png(size):
    buffer = BytesIO()
    Image.new("RGB", size).save(buffer, format="PNG")
    return buffer.getvalue()


def test_controller_checks_server_screenshot_independently(monkeypatch):
    controller = PythonController("127.0.0.1", 5000)
    monkeypatch.setattr(controller, "run_python_script", lambda *a, **kw: {"returncode": 0})
    monkeypatch.setattr(controller, "get_screenshot", lambda: png((1024, 768)))
    with pytest.raises(DesktopPreparationError, match="Server screenshot") as error:
        controller.prepare_desktop(1920, 1080)
    assert error.value.error_category == "infra"


def test_controller_stops_when_display_setup_fails(monkeypatch):
    controller = PythonController("127.0.0.1", 5000)
    monkeypatch.setattr(controller, "run_python_script", lambda *a, **kw: {"returncode": 1, "output": "unsupported mode"})
    with pytest.raises(DesktopPreparationError, match="unsupported mode"):
        controller.prepare_desktop(1920, 1080)


def test_controller_accepts_actual_matching_screenshot(monkeypatch):
    controller = PythonController("127.0.0.1", 5000)
    scripts = []
    monkeypatch.setattr(controller, "run_python_script", lambda script, **kw: scripts.append(script) or {"returncode": 0})
    monkeypatch.setattr(controller, "get_screenshot", lambda: png((1920, 1080)))
    assert controller.prepare_desktop(1920, 1080)["returncode"] == 0
    assert "prepare_desktop(1920, 1080, 5000, False)" in scripts[0]


def test_malformed_screenshot_is_infrastructure_failure(monkeypatch):
    controller = PythonController("127.0.0.1", 5000)
    monkeypatch.setattr(controller, "run_python_script", lambda *a, **kw: {"returncode": 0})
    monkeypatch.setattr(controller, "get_screenshot", lambda: b"not a PNG")
    with pytest.raises(DesktopPreparationError):
        controller.prepare_desktop(1920, 1080)


def test_desktop_preparation_uses_guest_port_behind_docker_mapping(monkeypatch):
    controller = PythonController("localhost", 5012, os_type="Windows", guest_server_port=5000)
    scripts = []
    monkeypatch.setattr(controller, "run_python_script", lambda script, **kw: scripts.append(script) or {"returncode": 0})
    monkeypatch.setattr(controller, "get_screenshot", lambda: png((1920, 1080)))
    controller.prepare_desktop(1920, 1080)
    assert controller.http_server == "http://localhost:5012"
    assert "prepare_desktop(1920, 1080, 5000, False)" in scripts[0]
