import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest


RUNTIME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNTIME / "engine"))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bootstrap = load_module("open_ended_bootstrap", RUNTIME.parent / "task/open-environment-engineering/prepare_evaluator.py")
getter = load_module("open_ended_getter", RUNTIME / "engine/desktop_env/evaluators/getters/general.py")


def test_existing_checker_does_not_install_packages():
    with patch.object(bootstrap.shutil, "which", return_value="/usr/bin/freecadcmd"), \
         patch.object(bootstrap.Path, "is_file", return_value=True), \
         patch.object(bootstrap.os, "access", return_value=True), \
         patch.object(bootstrap.subprocess, "run") as run:
        bootstrap.prepare()
    run.assert_not_called()


def test_blank_vm_prepares_checker_with_bounded_package_operations():
    with patch.object(bootstrap.shutil, "which", side_effect=lambda name: "/usr/bin/" + name if name in {"sudo", "apt-get"} else None), \
         patch.object(bootstrap.Path, "is_file", return_value=False), \
         patch.object(bootstrap.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as run:
        bootstrap.prepare()
    assert run.call_count == 2
    assert run.call_args_list[0].args[0][-1] == "update"
    assert run.call_args_list[1].args[0][-1] == "freecad"
    assert [call.kwargs["timeout"] for call in run.call_args_list] == [300, 600]


def test_package_failure_is_reported():
    with patch.object(bootstrap.shutil, "which", side_effect=lambda name: name if name in {"sudo", "apt-get"} else None), \
         patch.object(bootstrap.Path, "is_file", return_value=False), \
         patch.object(bootstrap.subprocess, "run", return_value=SimpleNamespace(returncode=1, stderr="repository unavailable", stdout="")):
        with pytest.raises(RuntimeError, match="repository unavailable"):
            bootstrap.prepare()


@pytest.mark.parametrize("status", ["0", "2"])
def test_dependency_setup_uses_background_polling_and_reports_infrastructure_failure(status):
    responses = iter(["", "pending", status, "sudo unavailable"])
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs["json"])
        return SimpleNamespace(raise_for_status=lambda: None,
                               json=lambda: {"returncode": 0, "output": next(responses)})

    env = SimpleNamespace(vm_ip="127.0.0.1", server_port=5000)
    with patch.object(getter.requests, "post", side_effect=post), patch.object(getter.time, "sleep"):
        if status == "0":
            getter._prepare_evaluator_dependency(env, {"prepare_command": "python3 prepare.py"})
        else:
            with pytest.raises(getter.EvaluationDependencyError, match="sudo unavailable") as error:
                getter._prepare_evaluator_dependency(env, {"prepare_command": "python3 prepare.py"})
            assert error.value.error_category == "infra"
    assert calls[0]["command"][-1].endswith("&")
    assert "printf pending" in calls[1]["command"][-1]


def test_regular_tasks_do_not_prepare_open_ended_dependencies():
    with patch.object(getter.requests, "post") as post:
        getter._prepare_evaluator_dependency(SimpleNamespace(), {"command": "python3 eval.py"})
    post.assert_not_called()


@pytest.mark.parametrize("payload", [[], {"status": "error", "returncode": 0, "output": ""},
                                    {"returncode": False, "output": ""}, {"returncode": 0, "output": None}])
def test_invalid_preparation_response_is_infrastructure_failure(payload):
    response = SimpleNamespace(raise_for_status=lambda: None, json=lambda: payload)
    env = SimpleNamespace(vm_ip="127.0.0.1", server_port=5000)
    with patch.object(getter.requests, "post", return_value=response):
        with pytest.raises(getter.EvaluationDependencyError) as error:
            getter._prepare_evaluator_dependency(env, {"prepare_command": "python3 prepare.py"})
    assert error.value.error_category == "infra"
