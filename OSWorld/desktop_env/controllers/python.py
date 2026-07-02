import base64
import json
import logging
import random
from typing import Any, Callable, Dict, Optional, TypeVar
import time
import traceback
import requests

from desktop_env.actions import KEYBOARD_KEYS

logger = logging.getLogger("desktopenv.pycontroller")

_T = TypeVar("_T")


class SandboxUnavailableError(RuntimeError):
    """Raised when a controller HTTP endpoint keeps failing past its retry budget.

    Callers should treat this as a fail-fast signal: the sandbox is unreachable or
    repeatedly returning errors, and the task cannot meaningfully continue. Catching
    and continuing is *not* recommended — the on-VM state may be desynced from what
    the agent thinks happened (e.g. a write request that timed out may or may not
    have been applied).
    """


class SandboxExecuteHardTimeoutError(RuntimeError):
    """Raised when a sandbox execution endpoint hits its server-side hard timeout.

    Distinct from ``SandboxUnavailableError``: the sandbox is healthy, but the
    server-side ``subprocess.run`` enforced a timeout. The cap differs per
    endpoint (``/run_bash_script`` per-request ``timeout`` arg, legacy
    ``/execute`` 120s) but the failure mode is the same:
    the child was killed mid-flight and any grandchildren it spawned may still
    be running on the VM.

    Surfacing this as its own exception lets the runner mark the task as an
    *infra* failure instead of either:

    * burning ~20 min retrying every cap fire (default ``retry_timeout = 1200s``),
      or
    * feeding a fake "you timed out" observation back to the model and
      mis-attributing the eventual score to model intelligence.
    """


def _raise_if_execute_hard_timeout(response, op_name: str) -> None:
    """If the 500 body looks like a ``subprocess.TimeoutExpired``, raise
    ``SandboxExecuteHardTimeoutError`` so the caller bails without retry.

    Covers three server handlers with different body shapes:
      * ``/execute``           → ``{"status":"error","message":str(exc)}``
      * ``/run_python``        → ``{"status":"error","message":...,"error":"TimeoutExpired"}``
      * ``/run_bash_script``   → ``{"status":"error","output":"Script execution timed out ..."}``

    We inspect ``message``/``output``/``error`` and match
    ``"timed out after"`` / ``"timeoutexpired"`` case-insensitively. Anything
    else is treated as a transient 500 and goes through the normal retry loop.
    """
    if response.status_code != 500:
        return
    fields: list[str] = []
    try:
        body = response.json()
        if isinstance(body, dict):
            for key in ("message", "output", "error"):
                val = body.get(key)
                if isinstance(val, str) and val:
                    fields.append(val)
    except Exception:
        if response.text:
            fields.append(response.text)
    lowered = " ".join(fields).lower()
    if "timed out after" in lowered or "timeoutexpired" in lowered:
        # Prefer the first non-empty field as the human-readable message.
        msg = next((f for f in fields if f), "")
        raise SandboxExecuteHardTimeoutError(
            f"[{op_name}] sandbox hit server-side hard timeout. "
            f"Server message: {msg!r}. The VM may still be running zombie "
            f"descendants (subprocess.run kills only its immediate child)."
        )


class PythonController:
    def __init__(self, vm_ip: str,
                 server_port: int,
                 pkgs_prefix: str = "import pyautogui; import time; pyautogui.FAILSAFE = False; {command}"):
        self.vm_ip = vm_ip
        self.http_server = f"http://{vm_ip}:{server_port}"
        self.pkgs_prefix = pkgs_prefix  # fixme: this is a hacky way to execute python commands. fix it and combine it with installation of packages
        # Legacy fields kept for backward compatibility with any external callers.
        self.retry_times = 3
        self.retry_interval = 5
        # New retry budget: long for normal endpoints (sandbox 502 storms can last
        # 30~60s but occasionally minutes; 20min covers VM/sandbox restarts).
        self.retry_timeout = 20 * 60
        # Recording endpoints (start_recording / end_recording) use a much shorter
        # budget — they are often called from cleanup/teardown paths where blocking
        # 20min would stall the worker pool, and the recording is not the core data.
        self.retry_recording_timeout = 60
        self.retry_initial_interval = 5
        self.retry_max_interval = 60
        # Sticky "sandbox is dead right now" window. After any endpoint exhausts its
        # budget we set this so subsequent endpoint calls fast-fail instead of each
        # spending another full budget on the same outage. Short window (30s) only —
        # we want to recover quickly once the sandbox comes back.
        self._unavailable_until: float = 0.0
        self._unavailable_sticky_seconds: float = 30.0

    def _retry_request(
        self,
        op_name: str,
        fn: Callable[[], _T],
        *,
        retry_on_timeout: bool = True,
        timeout_override: Optional[float] = None,
    ) -> _T:
        """Run ``fn`` with exponential backoff until success or the deadline expires.

        ``fn`` performs one HTTP attempt and either returns the success value or raises.
        Any non-``SandboxUnavailableError`` exception is treated as transient and triggers
        a retry — *except* ``requests.exceptions.ReadTimeout`` when ``retry_on_timeout``
        is ``False`` (set this for write/side-effecting endpoints; the request may have
        been received and partially executed on the server, so replaying is unsafe).

        Raises ``SandboxUnavailableError`` once the budget is exhausted, and arms the
        sticky unavailability window so cascading callers fail fast.
        """
        timeout = (
            timeout_override if timeout_override is not None else self.retry_timeout
        )

        now = time.time()
        if self._unavailable_until > now:
            raise SandboxUnavailableError(
                f"[{op_name}] sandbox marked unavailable for "
                f"{self._unavailable_until - now:.1f}s, fast-failing"
            )

        deadline = now + timeout
        interval = self.retry_initial_interval
        last_error: Optional[str] = None
        attempt = 0

        while True:
            attempt += 1
            try:
                return fn()
            except SandboxUnavailableError:
                raise
            except SandboxExecuteHardTimeoutError:
                # Server-side subprocess.run timeout fired — sandbox is fine,
                # retrying would just re-trigger the same cap and burn another
                # subprocess invocation on the VM. Bubble straight to the
                # caller so the task can be marked as an infra failure.
                raise
            except NotImplementedError:
                # Server returned an explicit 501 not_implemented (e.g.
                # /terminal on Windows). The endpoint is structurally absent
                # on this platform; retrying for 20min only to wrap it as
                # SandboxUnavailableError mislabels a feature gap as a VM
                # outage and pollutes the sticky-unavailability window for
                # unrelated subsequent ops. Bubble straight up.
                raise
            except requests.exceptions.ReadTimeout as e:
                if not retry_on_timeout:
                    raise SandboxUnavailableError(
                        f"[{op_name}] ReadTimeout after {e}; refusing to retry "
                        f"because the request may have already side-effected on the server"
                    ) from e
                last_error = f"ReadTimeout: {e}"
            except Exception as e:  # noqa: BLE001 - everything else is transient
                last_error = f"{type(e).__name__}: {e}"

            remaining = deadline - time.time()
            if remaining <= 0:
                break
            sleep_for = min(interval, remaining)
            log_fn = logger.warning if attempt == 1 else logger.debug
            log_fn(
                "[%s] attempt %d failed (%s); retrying in %.1fs (deadline in %.0fs)",
                op_name, attempt, last_error, sleep_for, remaining,
            )
            time.sleep(sleep_for)
            interval = min(interval * 2, self.retry_max_interval)

        self._unavailable_until = time.time() + self._unavailable_sticky_seconds
        logger.error(
            "[%s] giving up after %d attempts in %.0fs. Last error: %s",
            op_name, attempt, timeout, last_error,
        )
        raise SandboxUnavailableError(
            f"[{op_name}] still failing after {timeout:.0f}s "
            f"({attempt} attempts). Last error: {last_error}"
        )

    @staticmethod
    def _is_valid_image_response(content_type: str, data: Optional[bytes]) -> bool:
        """Quick validation for PNG/JPEG payload using magic bytes; Content-Type is advisory.
        Returns True only when bytes look like a real PNG or JPEG.
        """
        if not isinstance(data, (bytes, bytearray)) or not data:
            return False
        # PNG magic
        if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
            return True
        # JPEG magic
        if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
            return True
        # If server explicitly marks as image, accept as a weak fallback (some environments strip magic)
        if content_type and ("image/png" in content_type or "image/jpeg" in content_type or "image/jpg" in content_type):
            return True
        return False

    def get_screenshot(self) -> bytes:
        """Gets a screenshot from the server (with the cursor).

        Raises ``SandboxUnavailableError`` if the sandbox cannot be reached after
        the retry budget is exhausted. Never returns ``None``.
        """
        def _do() -> bytes:
            response = requests.get(self.http_server + "/screenshot", timeout=10)
            if response.status_code != 200:
                raise RuntimeError(
                    f"HTTP {response.status_code}: {response.text}"
                )
            content_type = response.headers.get("Content-Type", "")
            content = response.content
            if not self._is_valid_image_response(content_type, content):
                raise RuntimeError(
                    f"invalid screenshot payload (content-type={content_type!r}, "
                    f"size={len(content)} bytes)"
                )
            return content

        result = self._retry_request("get_screenshot", _do)
        logger.info("Got screenshot successfully")
        return result

    def get_accessibility_tree(self) -> str:
        """Gets the accessibility tree from the server.

        Raises ``SandboxUnavailableError`` once the retry budget is exhausted.
        """
        def _do() -> str:
            response = requests.get(self.http_server + "/accessibility")
            if response.status_code != 200:
                raise RuntimeError(
                    f"HTTP {response.status_code}: {response.text}"
                )
            return response.json()["AT"]

        result = self._retry_request("get_accessibility_tree", _do)
        logger.info("Got accessibility tree successfully")
        return result

    def get_terminal_output(self) -> str:
        """Gets the terminal output from the server.

        Raises ``NotImplementedError`` if the server returns 501 with
        ``status == "not_implemented"`` (e.g. on the Windows image, where
        screen-scraping conhost / Windows Terminal is a known TODO). This
        signals a platform feature gap, not a sandbox outage — fail-fast
        instead of burning the retry budget then mislabeling the failure.

        Raises ``SandboxUnavailableError`` once the retry budget is exhausted.
        """
        def _do() -> str:
            response = requests.get(self.http_server + "/terminal")
            if response.status_code == 501:
                try:
                    body = response.json()
                except ValueError:
                    body = {}
                if body.get("status") == "not_implemented":
                    raise NotImplementedError(
                        f"/terminal not implemented on platform "
                        f"{body.get('platform')!r}: {body.get('message', '')}"
                    )
            if response.status_code != 200:
                raise RuntimeError(
                    f"HTTP {response.status_code}: {response.text}"
                )
            return response.json()["output"]

        result = self._retry_request("get_terminal_output", _do)
        logger.info("Got terminal output successfully")
        return result

    def get_file(self, file_path: str) -> bytes:
        """Gets a file from the server.

        Raises ``SandboxUnavailableError`` once the retry budget is exhausted.
        """
        def _do() -> bytes:
            response = requests.post(self.http_server + "/file", data={"file_path": file_path})
            if response.status_code != 200:
                raise RuntimeError(
                    f"HTTP {response.status_code}: {response.text}"
                )
            return response.content

        result = self._retry_request("get_file", _do)
        logger.info("File downloaded successfully")
        return result

    def _build_python_bash_script(self, code: str) -> str:
        """Wrap Python code in a bash script so /run_bash_script owns timeout.

        This deliberately avoids /run_python because old sandbox images have a
        server-side 30s hard cap there. Git Bash on Windows can usually invoke
        ``python`` or the ``py`` launcher; Linux images usually expose
        ``python3``. We test each candidate for Python 3 instead of assuming one
        name.
        """
        encoded = base64.b64encode(code.encode("utf-8")).decode("ascii")
        return f"""#!/bin/bash
set -u

if python - <<'PY_CHECK' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info[0] == 3 else 1)
PY_CHECK
then
  _OSWORLD_PY=(python)
elif python3 - <<'PY_CHECK' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info[0] == 3 else 1)
PY_CHECK
then
  _OSWORLD_PY=(python3)
elif py -3 - <<'PY_CHECK' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info[0] == 3 else 1)
PY_CHECK
then
  _OSWORLD_PY=(py -3)
elif py - <<'PY_CHECK' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info[0] == 3 else 1)
PY_CHECK
then
  _OSWORLD_PY=(py)
else
  echo "No usable Python 3 interpreter found. Tried: python, python3, py -3, py." >&2
  exit 127
fi

"${{_OSWORLD_PY[@]}}" - <<'PY_ACTION'
import base64

_code = base64.b64decode({encoded!r}).decode("utf-8")
exec(compile(_code, "<osworld-python-action>", "exec"))
PY_ACTION
"""

    @staticmethod
    def _python_result_from_bash(result: Dict[str, Any]) -> Dict[str, Any]:
        output = result.get("output") or ""
        returncode = result.get("returncode", result.get("return_code", -1))
        status = result.get("status") or ("success" if returncode == 0 else "error")
        return {
            "status": status,
            "message": output,
            "need_more": False,
            "output": output,
            # /run_bash_script merges stderr into output on the VM server.
            "error": result.get("error") or "",
            "return_code": returncode,
            "returncode": returncode,
        }

    def execute_python_command(self, command: str, timeout: int = 120) -> Dict[str, Any]:
        """Executes a python command on the server (used for pyautogui actions).

        Routes through ``/run_bash_script`` instead of ``/run_python`` so the
        caller can control the per-action timeout without changing or restarting
        the sandbox server. The agent's pyautogui snippet is wrapped with
        ``pkgs_prefix`` (provides ``pyautogui``/``time`` imports + disables
        FAILSAFE), base64-encoded, decoded inside a bash heredoc, then executed
        by whichever Python executable is available in the VM.

        ``retry_on_timeout=False`` because this is a write/side-effecting endpoint:
        a ``ReadTimeout`` means the request reached the server and the command may
        already be executing on the VM. Replaying it (e.g. ``pyautogui.typewrite``,
        ``click``) would double-apply the action.

        Hard-timeout handling: ``/run_bash_script`` enforces the request
        ``timeout`` server-side; if it fires, raise
        ``SandboxExecuteHardTimeoutError`` rather than burning ~20 min on
        retries.

        Raises ``SandboxUnavailableError`` once the retry budget is exhausted, or
        ``SandboxExecuteHardTimeoutError`` on the first hard-cap hit.
        """
        script = self._build_python_bash_script(
            self.pkgs_prefix.format(command=command)
        )
        result = self._python_result_from_bash(
            self.run_bash_script(script, timeout=timeout)
        )
        logger.info("Command executed successfully: %s", result)
        return result
    
    def run_python_script(self, script: str, timeout: int = 120) -> Dict[str, Any]:
        """Executes a python script on the server.

        Write/side-effecting endpoint — see ``execute_python_command`` for the
        ``retry_on_timeout=False`` rationale. Note that an HTTP 200 with a script
        error inside (e.g. SyntaxError) is *not* a sandbox failure: that response
        is returned as-is so the caller can inspect ``error``/``output``. Only
        transport-level failures (non-200, connection error) trigger retries; only
        a budget-exhausted outage raises ``SandboxUnavailableError``.
        """
        return self._python_result_from_bash(
            self.run_bash_script(
                self._build_python_bash_script(script),
                timeout=timeout,
            )
        )
    
    def run_bash_script(self, script: str, timeout: int = 120, working_dir: Optional[str] = None) -> Dict[str, Any]:
        """Executes a bash script on the server via ``/run_bash_script``.

        The server writes the script to a temp ``.sh`` (prepending ``#!/bin/bash``
        if missing), chmods it executable, runs it under ``/bin/bash`` with
        ``stderr`` merged into ``stdout``, and returns
        ``{status, output, error="", returncode}``.

        :param script: The bash script content (can be multi-line).
        :param timeout: Per-script execution timeout in seconds (default: 120),
            forwarded to the server. A ``ReadTimeout`` means the script ran
            longer than this on the VM; we *cannot* safely retry (it may still
            be running and side-effecting), so the budget loop bails out with
            ``SandboxUnavailableError``. Callers that want to recover from
            script timeouts should catch this and decide.
        :param working_dir: Working directory for script execution (optional);
            forwarded as ``working_dir`` and applied via ``subprocess.run(cwd=...)``.
        :return: Dictionary with status, output, error, and returncode.

        Raises ``SandboxUnavailableError`` once the retry budget is exhausted, or
        ``SandboxExecuteHardTimeoutError`` if the server-side ``timeout`` fires.
        """
        payload = json.dumps({
            "script": script,
            "timeout": timeout,
            "working_dir": working_dir,
        })

        def _do() -> Dict[str, Any]:
            response = requests.post(
                self.http_server + "/run_bash_script",
                headers={'Content-Type': 'application/json'},
                data=payload,
                timeout=timeout + 100,  # HTTP buffer over the script-side timeout
            )
            _raise_if_execute_hard_timeout(response, "run_bash_script")
            if response.status_code != 200:
                raise RuntimeError(
                    f"HTTP {response.status_code}: {response.text}"
                )
            return response.json()

        result = self._retry_request(
            "run_bash_script", _do, retry_on_timeout=False
        )
        logger.info(
            "Bash script executed successfully with return code: %d",
            result.get("returncode", -1),
        )
        return result

    def execute_action(self, action):
        """
        Executes an action on the server computer.
        """
        # Handle string actions
        if action in ['WAIT', 'FAIL', 'DONE']:
            return
        
        # Handle dictionary actions
        if type(action) == dict and action.get('action_type') in ['WAIT', 'FAIL', 'DONE']:
            return

        action_type = action["action_type"]
        parameters = action["parameters"] if "parameters" in action else {param: action[param] for param in action if param != 'action_type'}
        move_mode = random.choice(
            ["pyautogui.easeInQuad", "pyautogui.easeOutQuad", "pyautogui.easeInOutQuad", "pyautogui.easeInBounce",
             "pyautogui.easeInElastic"])
        duration = random.uniform(0.5, 1)

        if action_type == "MOVE_TO":
            if parameters == {} or None:
                self.execute_python_command("pyautogui.moveTo()")
            elif "x" in parameters and "y" in parameters:
                x = parameters["x"]
                y = parameters["y"]
                self.execute_python_command(f"pyautogui.moveTo({x}, {y}, {duration}, {move_mode})")
            else:
                raise Exception(f"Unknown parameters: {parameters}")

        elif action_type == "CLICK":
            if parameters == {} or None:
                self.execute_python_command("pyautogui.click()")
            elif "button" in parameters and "x" in parameters and "y" in parameters:
                button = parameters["button"]
                x = parameters["x"]
                y = parameters["y"]
                if "num_clicks" in parameters:
                    num_clicks = parameters["num_clicks"]
                    self.execute_python_command(
                        f"pyautogui.click(button='{button}', x={x}, y={y}, clicks={num_clicks})")
                else:
                    self.execute_python_command(f"pyautogui.click(button='{button}', x={x}, y={y})")
            elif "button" in parameters and "x" not in parameters and "y" not in parameters:
                button = parameters["button"]
                if "num_clicks" in parameters:
                    num_clicks = parameters["num_clicks"]
                    self.execute_python_command(f"pyautogui.click(button='{button}', clicks={num_clicks})")
                else:
                    self.execute_python_command(f"pyautogui.click(button='{button}')")
            elif "button" not in parameters and "x" in parameters and "y" in parameters:
                x = parameters["x"]
                y = parameters["y"]
                if "num_clicks" in parameters:
                    num_clicks = parameters["num_clicks"]
                    self.execute_python_command(f"pyautogui.click(x={x}, y={y}, clicks={num_clicks})")
                else:
                    self.execute_python_command(f"pyautogui.click(x={x}, y={y})")
            else:
                raise Exception(f"Unknown parameters: {parameters}")

        elif action_type == "MOUSE_DOWN":
            if parameters == {} or None:
                self.execute_python_command("pyautogui.mouseDown()")
            elif "button" in parameters:
                button = parameters["button"]
                self.execute_python_command(f"pyautogui.mouseDown(button='{button}')")
            else:
                raise Exception(f"Unknown parameters: {parameters}")

        elif action_type == "MOUSE_UP":
            if parameters == {} or None:
                self.execute_python_command("pyautogui.mouseUp()")
            elif "button" in parameters:
                button = parameters["button"]
                self.execute_python_command(f"pyautogui.mouseUp(button='{button}')")
            else:
                raise Exception(f"Unknown parameters: {parameters}")

        elif action_type == "RIGHT_CLICK":
            if parameters == {} or None:
                self.execute_python_command("pyautogui.rightClick()")
            elif "x" in parameters and "y" in parameters:
                x = parameters["x"]
                y = parameters["y"]
                self.execute_python_command(f"pyautogui.rightClick(x={x}, y={y})")
            else:
                raise Exception(f"Unknown parameters: {parameters}")

        elif action_type == "DOUBLE_CLICK":
            if parameters == {} or None:
                self.execute_python_command("pyautogui.doubleClick()")
            elif "x" in parameters and "y" in parameters:
                x = parameters["x"]
                y = parameters["y"]
                self.execute_python_command(f"pyautogui.doubleClick(x={x}, y={y})")
            else:
                raise Exception(f"Unknown parameters: {parameters}")

        elif action_type == "DRAG_TO":
            if "x" in parameters and "y" in parameters:
                x = parameters["x"]
                y = parameters["y"]
                self.execute_python_command(
                    f"pyautogui.dragTo({x}, {y}, duration=1.0, button='left', mouseDownUp=True)")

        elif action_type == "SCROLL":
            # todo: check if it is related to the operating system, as https://github.com/TheDuckAI/DuckTrack/blob/main/ducktrack/playback.py pointed out
            if "dx" in parameters and "dy" in parameters:
                dx = parameters["dx"]
                dy = parameters["dy"]
                self.execute_python_command(f"pyautogui.hscroll({dx})")
                self.execute_python_command(f"pyautogui.vscroll({dy})")
            elif "dx" in parameters and "dy" not in parameters:
                dx = parameters["dx"]
                self.execute_python_command(f"pyautogui.hscroll({dx})")
            elif "dx" not in parameters and "dy" in parameters:
                dy = parameters["dy"]
                self.execute_python_command(f"pyautogui.vscroll({dy})")
            else:
                raise Exception(f"Unknown parameters: {parameters}")

        elif action_type == "TYPING":
            if "text" not in parameters:
                raise Exception(f"Unknown parameters: {parameters}")
            # deal with special ' and \ characters
            # text = parameters["text"].replace("\\", "\\\\").replace("'", "\\'")
            # self.execute_python_command(f"pyautogui.typewrite('{text}')")
            text = parameters["text"]
            self.execute_python_command("pyautogui.typewrite({:})".format(repr(text)))

        elif action_type == "PRESS":
            if "key" not in parameters:
                raise Exception(f"Unknown parameters: {parameters}")
            key = parameters["key"]
            if key.lower() not in KEYBOARD_KEYS:
                raise Exception(f"Key must be one of {KEYBOARD_KEYS}")
            self.execute_python_command(f"pyautogui.press('{key}')")

        elif action_type == "KEY_DOWN":
            if "key" not in parameters:
                raise Exception(f"Unknown parameters: {parameters}")
            key = parameters["key"]
            if key.lower() not in KEYBOARD_KEYS:
                raise Exception(f"Key must be one of {KEYBOARD_KEYS}")
            self.execute_python_command(f"pyautogui.keyDown('{key}')")

        elif action_type == "KEY_UP":
            if "key" not in parameters:
                raise Exception(f"Unknown parameters: {parameters}")
            key = parameters["key"]
            if key.lower() not in KEYBOARD_KEYS:
                raise Exception(f"Key must be one of {KEYBOARD_KEYS}")
            self.execute_python_command(f"pyautogui.keyUp('{key}')")

        elif action_type == "HOTKEY":
            if "keys" not in parameters:
                raise Exception(f"Unknown parameters: {parameters}")
            keys = parameters["keys"]
            if not isinstance(keys, list):
                raise Exception("Keys must be a list of keys")
            for key in keys:
                if key.lower() not in KEYBOARD_KEYS:
                    raise Exception(f"Key must be one of {KEYBOARD_KEYS}")

            keys_para_rep = "', '".join(keys)
            self.execute_python_command(f"pyautogui.hotkey('{keys_para_rep}')")

        elif action_type in ['WAIT', 'FAIL', 'DONE']:
            pass

        else:
            raise Exception(f"Unknown action type: {action_type}")

    # Record video — these endpoints use a *short* retry budget
    # (``retry_recording_timeout``, default 60s) instead of the normal 20-minute
    # budget. They are commonly invoked from cleanup/teardown paths where a long
    # block would stall the worker pool, and the recording is auxiliary data, not
    # the trajectory itself.
    def start_recording(self):
        """Starts recording the screen.

        Raises ``SandboxUnavailableError`` once the (short) retry budget is exhausted.
        """
        def _do() -> bool:
            response = requests.post(self.http_server + "/start_recording")
            if response.status_code != 200:
                raise RuntimeError(
                    f"HTTP {response.status_code}: {response.text}"
                )
            return True

        self._retry_request(
            "start_recording", _do,
            timeout_override=self.retry_recording_timeout,
        )
        logger.info("Recording started successfully")

    def end_recording(self, dest: str):
        """Ends recording the screen and writes the video to ``dest``.

        Raises ``SandboxUnavailableError`` once the (short) retry budget is exhausted.
        """
        def _do() -> bool:
            response = requests.post(self.http_server + "/end_recording")
            if response.status_code != 200:
                raise RuntimeError(
                    f"HTTP {response.status_code}: {response.text}"
                )
            with open(dest, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True

        self._retry_request(
            "end_recording", _do,
            timeout_override=self.retry_recording_timeout,
        )
        logger.info("Recording stopped successfully")

    # Additional info
    def get_vm_platform(self):
        """
        Gets the size of the vm screen.
        """
        return self.execute_python_command("import platform; print(platform.system())")['output'].strip()
    
    def get_vm_machine(self):
        """
        Gets the machine of the vm.
        """
        return self.execute_python_command("import platform; print(platform.machine())")['output'].strip()


    def get_vm_screen_size(self) -> Dict[str, Any]:
        """Gets the size of the vm screen.

        Raises ``SandboxUnavailableError`` once the retry budget is exhausted.
        """
        def _do() -> Dict[str, Any]:
            response = requests.post(self.http_server + "/screen_size")
            if response.status_code != 200:
                raise RuntimeError(
                    f"HTTP {response.status_code}: {response.text}"
                )
            return response.json()

        result = self._retry_request("get_vm_screen_size", _do)
        logger.info("Got screen size successfully")
        return result

    def get_vm_window_size(self, app_class_name: str) -> Dict[str, Any]:
        """Gets the size of the vm app window.

        Raises ``SandboxUnavailableError`` once the retry budget is exhausted.
        """
        def _do() -> Dict[str, Any]:
            response = requests.post(
                self.http_server + "/window_size",
                data={"app_class_name": app_class_name},
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"HTTP {response.status_code}: {response.text}"
                )
            return response.json()

        result = self._retry_request("get_vm_window_size", _do)
        logger.info("Got window size successfully")
        return result

    def get_vm_wallpaper(self) -> bytes:
        """Gets the wallpaper of the vm.

        Raises ``SandboxUnavailableError`` once the retry budget is exhausted.
        """
        def _do() -> bytes:
            response = requests.post(self.http_server + "/wallpaper")
            if response.status_code != 200:
                raise RuntimeError(
                    f"HTTP {response.status_code}: {response.text}"
                )
            return response.content

        result = self._retry_request("get_vm_wallpaper", _do)
        logger.info("Got wallpaper successfully")
        return result

    def get_vm_desktop_path(self) -> str:
        """Gets the desktop path of the vm.

        Raises ``SandboxUnavailableError`` once the retry budget is exhausted.
        """
        def _do() -> str:
            response = requests.post(self.http_server + "/desktop_path")
            if response.status_code != 200:
                raise RuntimeError(
                    f"HTTP {response.status_code}: {response.text}"
                )
            return response.json()["desktop_path"]

        result = self._retry_request("get_vm_desktop_path", _do)
        logger.info("Got desktop path successfully")
        return result

    def get_vm_directory_tree(self, path) -> Dict[str, Any]:
        """Gets the directory tree of the vm.

        Raises ``SandboxUnavailableError`` once the retry budget is exhausted.
        """
        payload = json.dumps({"path": path})

        def _do() -> Dict[str, Any]:
            response = requests.post(
                self.http_server + "/list_directory",
                headers={'Content-Type': 'application/json'},
                data=payload,
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"HTTP {response.status_code}: {response.text}"
                )
            return response.json()["directory_tree"]

        result = self._retry_request("get_vm_directory_tree", _do)
        logger.info("Got directory tree successfully")
        return result
