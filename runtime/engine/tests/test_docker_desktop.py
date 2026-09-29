from types import SimpleNamespace

import pytest

from desktop_env.desktop_env import DesktopEnv
from desktop_env import desktop_env as desktop_module
from desktop_env.errors import DesktopPreparationError


def environment(provider, fail_on=None):
    env = DesktopEnv.__new__(DesktopEnv)
    events = []
    env.provider_name = provider
    env.screen_width, env.screen_height = 1920, 1080
    env._traj_no, env.action_history = 0, []
    env.is_environment_used = False
    env.enable_proxy = env.current_use_proxy = False
    env.cache_dir, env.config = "unused", [{}]

    def prepare(width, height, check_startup_dialogs=False):
        assert (width, height) == (1920, 1080)
        events.append("prepare_after" if check_startup_dialogs else "prepare_before")
        if events[-1] == fail_on:
            raise DesktopPreparationError("Server screenshot is (1280, 720); requested (1920, 1080)")

    env.controller = SimpleNamespace(prepare_desktop=prepare)
    env.setup_controller = SimpleNamespace(
        setup=lambda *a: events.append("task_setup") or True,
        reset_cache_dir=lambda *a: None,
    )
    env._set_task_info = lambda *a: None
    env._get_obs = lambda: events.append("observation") or {"screenshot": b"verified"}
    return env, events


@pytest.mark.parametrize("provider", ["docker", "volcengine"])
def test_reset_calibrates_before_and_after_task_setup(provider):
    env, events = environment(provider)
    assert env.reset({"config": []})["screenshot"] == b"verified"
    assert events == ["prepare_before", "task_setup", "prepare_after", "observation"]


@pytest.mark.parametrize("phase", ["prepare_before", "prepare_after"])
def test_docker_never_returns_ready_observation_if_calibration_fails(phase):
    env, events = environment("docker", fail_on=phase)
    with pytest.raises(DesktopPreparationError) as caught:
        env.reset({"config": []})
    assert caught.value.error_category == "infra"
    assert "observation" not in events
    if phase == "prepare_before":
        assert "task_setup" not in events


@pytest.mark.parametrize("provider,guest_port", [("docker", 5000), ("volcengine", 5012)])
def test_environment_distinguishes_guest_and_forwarded_server_ports(monkeypatch, provider, guest_port):
    env = DesktopEnv.__new__(DesktopEnv)
    env.provider_name, env.path_to_vm, env.headless, env.os_type = provider, "disk", True, "Windows"
    env.server_port, env.chromium_port, env.vnc_port, env.vlc_port = 5000, 9222, 8006, 8080
    env.cache_dir_base, env.client_password = "cache", "password"
    env.screen_width, env.screen_height = 1920, 1080
    env.provider = SimpleNamespace(start_emulator=lambda *a: None,
                                   get_ip_address=lambda *a: "localhost:5012:9234:8018:8092")
    env._inject_vm_secret_mounts = lambda: None
    monkeypatch.setattr(desktop_module, "SetupController", lambda **kw: SimpleNamespace())
    env._start_emulator()
    assert env.controller.http_server == "http://localhost:5012"
    assert env.controller.guest_server_port == guest_port
