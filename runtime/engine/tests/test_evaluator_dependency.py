import io
import json
from types import SimpleNamespace

import pytest
import requests

from desktop_env.desktop_env import DesktopEnv
from desktop_env.errors import EvaluationDependencyError, EvaluationExecutionError
from desktop_env.evaluators.getters import general as getter


def environment(metric="exact_match", artifacts=None):
    env = DesktopEnv.__new__(DesktopEnv)
    env.vm_ip, env.server_port = "test", 5000
    env.action_history, env.enable_proxy = [], False
    env.setup_controller = SimpleNamespace(setup=lambda *args: True)
    config = {"func": metric, "result": {"type": "vm_command_line", "command": "python eval.py"}}
    if metric == "exact_match":
        config["expected"] = {"type": "rule", "rules": {"expected": "True\n"}}
    env._set_evaluator_info({"evaluator": config})
    env._attach_quantified_score_artifacts = lambda output: {"stdout": output, **(artifacts or {})}
    return env


def response(payload, status=200):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(payload).encode()
    return result


def run_evaluator(monkeypatch, payload, *, metric="exact_match", status=200, artifacts=None):
    monkeypatch.setattr(getter.requests, "post", lambda *a, **kw: response(payload, status))
    env = environment(metric, artifacts)
    return env, env.evaluate


@pytest.mark.parametrize("output,rc,stderr,score", [
    ("True\n", 0, "", 1), ("False\n", 0, "", 0), ("False\n", 1, "", 0),
    ("False\n", 1, "FAIL: EvaluationError: hole diameter mismatch", 0),
    ("False\n", 1, "missing result.step", 0),
    ("True\r\n", 0, "DeprecationWarning: old API", 1),
])
def test_valid_binary_results_keep_their_scores(monkeypatch, output, rc, stderr, score):
    env, evaluate = run_evaluator(monkeypatch, {"output": output, "error": stderr, "returncode": rc})
    assert evaluate() == score
    assert env.last_evaluation_details["score"] == score


@pytest.mark.parametrize("payload,status", [
    ({"message": "Command timed out after 120 seconds"}, 500),
    ({"status": "error", "output": "True\n", "returncode": 0}, 200),
    ({"output": "", "error": "execution failed", "returncode": 1}, 200),
    ({"output": "False\n", "error": "killed", "returncode": 137}, 200),
    ({"output": "True\n", "returncode": 1}, 200),
    ({"output": "True\n"}, 200),
    ({"output": "True\n", "returncode": "0"}, 200),
    ({"output": None, "returncode": 0}, 200),
    ({"output": "", "returncode": 0}, 200),
    ({"output": "debug output only", "returncode": 0}, 200),
    ({"output": "True", "returncode": 0}, 200),
    ([], 200),
])
def test_service_execution_and_output_failures_never_produce_a_score(monkeypatch, payload, status):
    env, evaluate = run_evaluator(monkeypatch, payload, status=status)
    with pytest.raises(EvaluationExecutionError) as caught:
        evaluate()
    assert caught.value.error_category == "infra"
    assert env.last_evaluation_details["score"] is None


@pytest.mark.parametrize("message", [
    "EVAL_DEPENDENCY_ERROR: FreeCADCmd missing",
    "FAIL: EvaluationError: FreeCADCmd is unavailable to the evaluator",
    "Traceback (most recent call last):\nModuleNotFoundError: No module named 'cadquery'",
    "ImportError: DLL load failed while importing geometry",
])
@pytest.mark.parametrize("rc", [0, 1, 2])
def test_dependency_errors_override_false_output(monkeypatch, message, rc):
    _, evaluate = run_evaluator(monkeypatch, {"output": "False\n", "error": message, "returncode": rc})
    with pytest.raises(EvaluationDependencyError):
        evaluate()


@pytest.mark.parametrize("failure", [requests.Timeout("timed out"), requests.ConnectionError("connection refused"), ValueError("invalid JSON")])
def test_request_and_json_errors_are_infrastructure(monkeypatch, failure):
    def post(*args, **kwargs):
        assert kwargs["timeout"] == (10, 130)
        raise failure
    monkeypatch.setattr(getter.requests, "post", post)
    with pytest.raises(EvaluationExecutionError):
        environment().evaluate()


@pytest.mark.parametrize("output,artifacts,score", [
    ('{"score": 0.0, "error": "missing optimized.obj"}\n', {}, 0),
    ("0.75\n", {}, 0.75),
    ("True\n", {"score_json": '{"score": 1.37}'}, 1.37),
    ("False\n", {"score_json": '{"score": 0.0, "valid": false}'}, 0),
])
def test_valid_continuous_scores_are_preserved(monkeypatch, output, artifacts, score):
    _, evaluate = run_evaluator(monkeypatch, {"output": output, "returncode": 0},
                                metric="quantified_score", artifacts=artifacts)
    assert evaluate() == score


@pytest.mark.parametrize("output", ["", "debug: evaluator failed", "True\n", "False\n", '{"score": false}', '{"score": NaN}', "Infinity"])
def test_missing_or_invalid_quantitative_score_is_not_zero(monkeypatch, output):
    env, evaluate = run_evaluator(monkeypatch, {"output": output, "returncode": 0}, metric="quantified_score")
    with pytest.raises(EvaluationExecutionError):
        evaluate()
    assert env.last_evaluation_details["score"] is None


def test_failed_command_cannot_reuse_old_quantitative_score(monkeypatch):
    _, evaluate = run_evaluator(monkeypatch, {"output": "", "returncode": 1},
                                metric="quantified_score", artifacts={"score_json": '{"score": 1.0}'})
    with pytest.raises(EvaluationExecutionError):
        evaluate()


def test_evaluation_error_is_saved_with_null_score(monkeypatch, tmp_path):
    import lib_run_single as runner
    env, _ = run_evaluator(monkeypatch, {"output": "", "returncode": 1})
    monkeypatch.setattr(runner, "_copy_evaluator_cache", lambda *a: [])
    monkeypatch.setattr(runner, "_collect_declared_vm_artifacts", lambda *a: ([], None))
    with pytest.raises(EvaluationExecutionError):
        runner._evaluate_and_capture(env, {"id": "test"}, str(tmp_path), io.StringIO(), io.StringIO())
    record = json.loads((tmp_path / "evaluation.json").read_text())
    assert record["score"] is None and record["error_category"] == "infra"
    assert record["evaluation_status"] == "infra_incomplete" and record["error"]
    assert not (tmp_path / "result.txt").exists()
