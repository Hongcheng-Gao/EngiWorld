import logging
import re
import shlex
import time
import uuid
from typing import Dict
import requests

from desktop_env.errors import EvaluationDependencyError, EvaluationExecutionError

logger = logging.getLogger("desktopenv.getters.general")


def _prepare_evaluator_dependency(env, config):
    """Prepare scoring tools only after the agent stops, on older VM servers too."""
    command = config.get("prepare_command")
    if not command:
        return
    url = f"http://{env.vm_ip}:{env.server_port}/execute"
    stem = f"/tmp/engiworld-evaluator-{uuid.uuid4().hex}"
    log, status = stem + ".log", stem + ".exit"

    def execute(script):
        try:
            response = requests.post(url, json={"command": ["bash", "-c", script], "shell": False}, timeout=130)
            response.raise_for_status()
            result = response.json()
        except Exception as exc:
            raise EvaluationDependencyError(f"Evaluator preparation request failed: {exc}") from exc
        if not isinstance(result, dict) or result.get("status", "success") != "success":
            raise EvaluationDependencyError(f"Invalid evaluator preparation response: {str(result)[:2000]}")
        returncode = result.get("returncode", result.get("return_code"))
        if type(returncode) is not int or returncode != 0:
            raise EvaluationDependencyError(f"Evaluator preparation command failed: {result.get('error', result)}")
        if not isinstance(result.get("output"), str):
            raise EvaluationDependencyError("Evaluator preparation response is missing valid output")
        return result["output"].strip()

    # The legacy /execute endpoint has a 120-second process limit. Run setup in
    # the background and poll with short requests instead of timing out mid-apt.
    execute(f"( {command}; printf '%s' $? > {shlex.quote(status)} ) > {shlex.quote(log)} 2>&1 < /dev/null &")
    deadline = time.monotonic() + float(config.get("prepare_timeout", 960))
    while time.monotonic() < deadline:
        result = execute(f"if test -f {shlex.quote(status)}; then cat {shlex.quote(status)}; else printf pending; fi")
        if result == "0":
            return
        if result != "pending":
            details = execute(f"tail -c 3000 {shlex.quote(log)}")
            raise EvaluationDependencyError(f"EVAL_DEPENDENCY_ERROR: {details}")
        time.sleep(2)
    raise EvaluationDependencyError("Evaluator dependency preparation timed out")


def get_vm_command_line(env, config: Dict[str, str]):
    _prepare_evaluator_dependency(env, config)
    result = _execute_evaluator_command(env, config)
    output = result["output"]
    evaluator = getattr(env, "evaluator", {})
    funcs = evaluator.get("func", [])
    configs = evaluator.get("result", [])
    expected = evaluator.get("expected", [])
    if not isinstance(funcs, list):
        funcs, configs, expected = [funcs], [configs], [expected]
    for index, (func, result_config) in enumerate(zip(funcs, configs)):
        if result_config != config:
            continue
        if func == "quantified_score" and not output.strip():
            raise EvaluationExecutionError("Evaluator returned empty score output")
        if func == "exact_match":
            rule = expected[index] if index < len(expected) else None
            target = (rule or {}).get("rules", {}).get("expected")
            if isinstance(target, str) and target.strip() in {"True", "False"}:
                # Preserve the boolean scoring contract, including negative rc=1.
                # Normalize Windows line endings, never arbitrary debug output.
                output = output.replace("\r\n", "\n")
                accepted = {target.replace(target.strip(), value) for value in ("True", "False")}
                if output not in accepted:
                    raise EvaluationExecutionError(f"Evaluator returned invalid boolean output: {output[:1000]!r}")
    return output


def _execute_evaluator_command(env, config):
    shell = config.get("shell", False)
    if isinstance(shell, str):
        shell = shell.lower() == "true"
    try:
        response = requests.post(
            f"http://{env.vm_ip}:{env.server_port}/execute",
            json={"command": config["command"], "shell": shell},
            timeout=(10, 130),  # Guest /execute has a 120-second subprocess limit.
        )
        if response.status_code != 200:
            raise EvaluationExecutionError(
                f"Evaluator service returned HTTP {response.status_code}: {response.text[:2000]}"
            )
        result = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise EvaluationExecutionError(f"Evaluator request failed: {exc}") from exc
    if not isinstance(result, dict) or result.get("status", "success") != "success":
        raise EvaluationExecutionError(f"Invalid evaluator response: {str(result)[:2000]}")
    print(result)
    output, error = result.get("output"), result.get("error", "")
    returncode = result.get("returncode", result.get("return_code"))
    if not isinstance(output, str) or not isinstance(error, str) or type(returncode) is not int:
        raise EvaluationExecutionError("Evaluator response is missing valid output/error/returncode fields")
    diagnostics = output + "\n" + error
    if ("EVAL_DEPENDENCY_ERROR:" in diagnostics
            or "FreeCADCmd is unavailable to the evaluator" in diagnostics
            or re.search(r"(?:^|\n)\s*(?:ModuleNotFoundError|ImportError):", diagnostics)):
        raise EvaluationDependencyError(diagnostics.strip()[-3000:])
    # Some released binary evaluators deliberately use rc=1 with False for a
    # missing/invalid model artifact. All other nonzero exits are execution errors.
    valid_negative = returncode == 1 and output.strip() == "False" and "Traceback (most recent call last):" not in error
    if returncode != 0 and not valid_negative:
        raise EvaluationExecutionError(f"Evaluator exited with code {returncode}: {error[-2000:]}")
    return result

def get_vm_command_error(env, config: Dict[str, str]):
    return _execute_evaluator_command(env, config).get("error", "")


def get_vm_terminal_output(env, config: Dict[str, str]):
    return env.controller.get_terminal_output()
