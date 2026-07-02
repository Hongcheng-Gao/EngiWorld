from __future__ import annotations

import logging
import os
import time
import re
from typing import Callable, Any, Optional, Tuple
from typing import List, Dict, Union

import gymnasium as gym

from desktop_env.controllers.python import PythonController
from desktop_env.controllers.setup import SetupController
from desktop_env.evaluators import metrics, getters
from desktop_env.providers import create_vm_manager_and_provider

logger = logging.getLogger("desktopenv.env")

Metric = Callable[[Any, Any], float]
Getter = Callable[[gym.Env, Dict[str, Any]], Any]

MAX_RETRIES = 5 # Maximum retries for environment setup
DEFAULT_WAIT_SECONDS = 120.0


def _coerce_wait_seconds(value: Any, default: float = DEFAULT_WAIT_SECONDS) -> float:
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return default
            


def _fix_pyautogui_less_than_bug(command: str) -> str:
    """
    Fix PyAutoGUI '<' character bug by converting it to hotkey("shift", ',') calls.
    
    This fixes the known PyAutoGUI issue where typing '<' produces '>' instead.
    References:
    - https://github.com/asweigart/pyautogui/issues/198
    - https://github.com/xlang-ai/OSWorld/issues/257
    
    Args:
        command (str): The original pyautogui command
        
    Returns:
        str: The fixed command with '<' characters handled properly
    """
    # Pattern to match press('<') or press('\u003c') calls  
    press_pattern = r'pyautogui\.press\(["\'](?:<|\\u003c)["\']\)'

    # Handle press('<') calls
    def replace_press_less_than(match):
        return 'pyautogui.hotkey("shift", ",")'
    
    # First handle press('<') calls
    command = re.sub(press_pattern, replace_press_less_than, command)

    # Pattern to match typewrite calls with quoted strings
    typewrite_pattern = r'pyautogui\.typewrite\((["\'])(.*?)\1\)'
    
    # Then handle typewrite calls
    def process_typewrite_match(match):
        quote_char = match.group(1)
        content = match.group(2)
        
        # Preprocess: Try to decode Unicode escapes like \u003c to actual '<'
        # This handles cases where '<' is represented as escaped Unicode
        try:
            # Attempt to decode unicode escapes
            decoded_content = content.encode('utf-8').decode('unicode_escape')
            content = decoded_content
        except UnicodeDecodeError:
            # If decoding fails, proceed with original content to avoid breaking existing logic
            pass  # English comment: Graceful degradation - fall back to original content if decoding fails
        
        # Check if content contains '<'
        if '<' not in content:
            return match.group(0)
        
        # Split by '<' and rebuild
        parts = content.split('<')
        result_parts = []
        
        for i, part in enumerate(parts):
            if i == 0:
                # First part
                if part:
                    result_parts.append(f"pyautogui.typewrite({quote_char}{part}{quote_char})")
            else:
                # Add hotkey for '<' and then typewrite for the rest
                result_parts.append('pyautogui.hotkey("shift", ",")')
                if part:
                    result_parts.append(f"pyautogui.typewrite({quote_char}{part}{quote_char})")
        
        return '; '.join(result_parts)
    
    command = re.sub(typewrite_pattern, process_typewrite_match, command)
    
    return command


class DesktopEnv(gym.Env):
    """
    DesktopEnv with OpenAI Gym interface. It provides a desktop environment for setting and evaluating desktop automation tasks.
    """
    def __init__(
            self,
            provider_name: str = "msh-sandbox",
            region: str = None,
            action_space: str = "pyautogui",
            cache_dir: str = "cache",
            screen_size: Tuple[int] = (int(os.environ.get("SCREEN_WIDTH", 1920)), int(os.environ.get("SCREEN_HEIGHT", 1080))),
            headless: bool = False,
            require_a11y_tree: bool = True,
            require_terminal: bool = False,
            os_type: str = "Ubuntu",
            enable_proxy: bool = False,
            client_password: str = "",
            spec: Optional[str] = None,
    ):
        """
        Args:
            provider_name (str): virtualization provider name, default to "msh-sandbox"
            region (str): region for cloud-backed providers (ignored by msh-sandbox)
            action_space (str): legacy paradigm name ("computer_13" / "claude_computer_use" /
                "autoglm_computer_use" / "cli+readimg") OR a "+"-joined PromptAgent
                typed-action set drawn from {pyautogui, python, bash}. The env itself
                only reads ``self.action_space`` for the legacy dispatch branches; typed
                actions are self-describing via tuple shape ``(kind, payload)`` in ``step()``.
            cache_dir (str): cache directory for task artifacts (downloads, evaluator references)
            screen_size (Tuple[int]): screen size of the VM
            headless (bool): whether to run the VM in headless mode
            require_a11y_tree (bool): whether to require accessibility tree in observations
            require_terminal (bool): whether to require terminal output in observations
            os_type (str): operating system type, used as a hint for image resolution
            enable_proxy (bool): whether to enable proxy support
            client_password (str): VM user password (defaults to "password")
            spec (str): sandbox session spec name (msh-sandbox only; None = provider default)
        """
        _legacy_paradigms = {"computer_13", "claude_computer_use", "autoglm_computer_use", "cli+readimg"}
        if action_space not in _legacy_paradigms:
            _parts = action_space.split("+")
            if not _parts or any(not p for p in _parts) or set(_parts) - {"pyautogui", "python", "bash"}:
                raise ValueError(
                    f"action_space {action_space!r} is not a legacy paradigm and is not a "
                    f"'+'-joined typed-action subset of {{pyautogui, python, bash}}."
                )

        self.region = region
        self.provider_name = provider_name
        self.enable_proxy = enable_proxy
        self.client_password = client_password if client_password else "password"
        self.screen_width = screen_size[0]
        self.screen_height = screen_size[1]
        self.os_type = os_type
        self.headless = headless
        self.require_a11y_tree = require_a11y_tree
        self.require_terminal = require_terminal
        self.cache_dir_base: str = cache_dir
        self.action_space = action_space
        self.spec = spec

        self.current_use_proxy = False
        self.manager, self.provider = create_vm_manager_and_provider(
            provider_name, region, use_proxy=False, spec=spec
        )

        # Lazy-start: emulator and controllers are bound on the first reset(), once we know
        # the task's snapshot. Anything that touches self.controller / self.setup_controller
        # before reset() will hit AttributeError and that is intentional.
        self.current_snapshot: Optional[str] = None
        self.controller: Optional[PythonController] = None
        self.setup_controller: Optional[SetupController] = None
        self.vm_ip: Optional[str] = None
        self.server_port: Optional[int] = None
        self.chromium_port: Optional[int] = None
        self.vnc_port: Optional[int] = None
        self.vlc_port: Optional[int] = None

        self.instruction = None
        self._traj_no: int = -1
        self._step_no: int = 0
        self.action_history: List[Dict[str, any]] = []

    def _bind_controllers(self) -> None:
        endpoint = self.provider.get_ip_address().split(':')
        if len(endpoint) != 5:
            raise RuntimeError(
                f"provider.get_ip_address() must return 'host:server_port:chromium_port:vnc_port:vlc_port', "
                f"got {endpoint!r}"
            )
        self.vm_ip = endpoint[0]
        self.server_port = int(endpoint[1])
        self.chromium_port = int(endpoint[2])
        self.vnc_port = int(endpoint[3])
        self.vlc_port = int(endpoint[4])
        self.controller = PythonController(vm_ip=self.vm_ip, server_port=self.server_port)
        self.setup_controller = SetupController(
            vm_ip=self.vm_ip,
            server_port=self.server_port,
            chromium_port=self.chromium_port,
            vlc_port=self.vlc_port,
            cache_dir=self.cache_dir_base,
            client_password=self.client_password,
            screen_width=self.screen_width,
            screen_height=self.screen_height,
        )

    def _start_with_snapshot(self, snapshot: str) -> None:
        resolved = self.manager.resolve_image(snapshot, os_type=self.os_type)
        try:
            self.provider.start_emulator(resolved, self.headless, self.os_type)
            self.current_snapshot = snapshot
            self._bind_controllers()
        except Exception:
            try:
                self.provider.stop_emulator()
            except Exception as stop_err:
                logger.warning(f"Cleanup after start failure: {stop_err}")
            self.current_snapshot = None
            raise

    def close(self):
        if self.current_snapshot is not None:
            self.provider.stop_emulator()
            self.current_snapshot = None
        self.controller = None
        self.setup_controller = None

    def reset(self, task_config: Optional[Dict[str, Any]] = None, seed=None, options=None) -> Dict[str, Any]:
        logger.info("Resetting environment...")
        if task_config is None:
            raise ValueError("DesktopEnv.reset() requires a task_config")
        if "snapshot" not in task_config:
            raise KeyError(
                f"task {task_config.get('id', '<unknown>')!r} is missing required 'snapshot' field. "
                "Per-task snapshot is now mandatory; provider-specific image resolution happens in VMManager.resolve_image."
            )
        new_snapshot = task_config["snapshot"]

        tid = task_config.get("id", "")
        if tid.endswith("-windows"):
            self.os_type = "Windows"
        elif tid.endswith("-ubuntu"):
            self.os_type = "Ubuntu"

        task_use_proxy = task_config.get("proxy", False) and self.enable_proxy
        if not self.enable_proxy and task_config.get("proxy", False):
            logger.info("Task requires proxy but proxy is disabled at system level, ignoring proxy requirement.")
        self.current_use_proxy = task_use_proxy

        self._traj_no += 1
        self._step_no = 0
        self.action_history.clear()

        for attempt in range(MAX_RETRIES):
            if self.current_snapshot is None:
                logger.info(f"Starting emulator with snapshot {new_snapshot!r}...")
                self._start_with_snapshot(new_snapshot)
            elif self.current_snapshot != new_snapshot:
                logger.info(f"Snapshot changed {self.current_snapshot!r} -> {new_snapshot!r}, restarting emulator...")
                self.provider.stop_emulator()
                self.current_snapshot = None
                self._start_with_snapshot(new_snapshot)
            else:
                logger.info(f"Resetting emulator to clean state (snapshot {new_snapshot!r})...")
                self.provider.reset_to_clean()
                self._bind_controllers()

            if task_use_proxy:
                self.setup_controller._proxy_setup(self.client_password)
            self._set_task_info(task_config)
            self.setup_controller.reset_cache_dir(self.cache_dir)
            logger.info("Setting up environment...")
            success = self.setup_controller.setup(self.config, task_use_proxy)
            if success:
                break
            logger.error("Environment setup failed, retrying (%d/%d)...", attempt + 1, MAX_RETRIES)
            time.sleep(5)

        logger.info("Environment setup complete.")
        return self._get_obs()

    def _get_obs(self):
        # We provide screenshot, accessibility_tree (optional), terminal (optional), and instruction.
        # can be customized and scaled
        return {
            "screenshot": self.controller.get_screenshot(),
            "accessibility_tree": self.controller.get_accessibility_tree() if self.require_a11y_tree else None,
            "terminal": self.controller.get_terminal_output() if self.require_terminal else None,
            "instruction": self.instruction
        }

    @property
    def vm_platform(self):
        return self.controller.get_vm_platform()

    @property
    def vm_machine(self):
        return self.controller.get_vm_machine()

    @property
    def vm_screen_size(self):
        return self.controller.get_vm_screen_size()

    def _set_task_info(self, task_config: Dict[str, Any]):
        """Set task info (proxy logic is handled in reset method)"""
        self.task_id: str = task_config["id"]
        self.cache_dir: str = os.path.join(self.cache_dir_base, self.task_id)
        os.makedirs(self.cache_dir, exist_ok=True)
        self.instruction = task_config["instruction"]
        self.config = task_config["config"] if "config" in task_config else []
        
        self._set_evaluator_info(task_config)

    def _set_evaluator_info(self, task_config: Dict[str, Any]):
        """Set evaluator information from task config"""
        # evaluator dict
        # func -> metric function string, or list of metric function strings
        # conj -> conjunction of multiple metrics if func is a list with length > 1, "and"/"or"
        # result -> result getter config, or list of result getter configs
        # expected (optional) -> expected getter config, or list of expected getter configs
        # options (optional) -> metric options, or list of metric options
        # if func is a str list, then result, expected (if exists), options (if exists) should also be lists of the same length
        # even if one of the metrics does not need expected or options field, it should be included in the list with None
        self.evaluator = task_config["evaluator"]
        self.metric: Metric = [getattr(metrics, func) for func in self.evaluator["func"]] \
            if isinstance(self.evaluator["func"], list) \
            else getattr(metrics, self.evaluator["func"])
        self.metric_conj: str = self.evaluator.get("conj", "and")  # take conjunction of multiple metrics
        if "result" in self.evaluator and len(self.evaluator["result"]) > 0:
            self.result_getter: Getter = [getattr(getters, "get_{:}".format(res["type"])) for res in
                                          self.evaluator["result"]] \
                if isinstance(self.evaluator["result"], list) \
                else getattr(getters, "get_{:}".format(self.evaluator["result"]["type"]))
        else:
            self.result_getter = [None] * len(self.metric) \
                if isinstance(self.metric, list) \
                else None

        if "expected" in self.evaluator and len(self.evaluator["expected"]) > 0:
            self.expected_getter: Getter = [getattr(getters, "get_{:}".format(exp["type"])) if exp else None for exp in
                                            self.evaluator["expected"]] \
                if isinstance(self.evaluator["expected"], list) \
                else getattr(getters, "get_{:}".format(self.evaluator["expected"]["type"]))
        else:
            self.expected_getter = [None] * len(self.metric) \
                if isinstance(self.metric, list) \
                else None
        self.metric_options: Union[List[Dict[str, Any]], Dict[str, Any]] = [opt if opt else {} for opt in
                                                                            self.evaluator["options"]] \
            if isinstance(self.evaluator.get("options", {}), list) \
            else self.evaluator["options"] \
            if "options" in self.evaluator \
            else [{}] * len(self.metric) \
            if isinstance(self.metric, list) \
            else {}

        assert (not isinstance(self.evaluator["func"], list)
                or (len(self.metric) == len(self.result_getter) == len(self.expected_getter) == len(
                    self.metric_options)))

    def step(self, action, pause=2, bash_timeout=120):
        self._step_no += 1
        self.action_history.append(action)

        reward = 0  # todo: Define reward calculation for each example
        done = False  # todo: Define episode termination condition for each example
        info = {}
        logger.info(f"Step {self._step_no} in trajectory {self._traj_no} with action: {action}")

        # PromptAgent typed-action protocol: action is (kind, payload).
        #   kind ∈ {"pyautogui","python","computer13","bash","WAIT","DONE","FAIL"}
        #   payload is the code/script for the first three; "" for signals.
        #   bash_timeout (seconds) is forwarded to run_bash_script for bash and
        #   to execute_python_command for pyautogui/python. The latter is also
        #   transported via /run_bash_script so old /run_python's 30s server cap
        #   does not apply.
        if isinstance(action, tuple) and len(action) == 2 and isinstance(action[0], str):
            kind, payload = action
            if kind == "WAIT":
                time.sleep(_coerce_wait_seconds(payload))
                return self._get_obs(), reward, done, info
            elif kind == "FAIL":
                done = True
                info = {"fail": True}
            elif kind == "DONE":
                done = True
                info = {"done": True}
            elif kind in ("pyautogui", "python"):
                self.controller.execute_python_command(
                    _fix_pyautogui_less_than_bug(payload),
                    timeout=bash_timeout,
                )
            elif kind == "computer13":
                if not isinstance(payload, dict):
                    raise ValueError("computer13 typed-action payload must be a dict")
                self.controller.execute_action(payload)
            elif kind == "bash":
                self.controller.run_bash_script(payload, timeout=bash_timeout)
            else:
                raise ValueError(f"Unknown typed-action kind: {kind!r}")
            time.sleep(pause)
            return self._get_obs(), reward, done, info

        # Legacy paradigms (computer_13 dict, claude_computer_use str/dict).
        # Untouched by the PromptAgent action-type refactor.
        if action in ['WAIT', 'FAIL', 'DONE'] or (type(action) == dict and action['action_type'] in ['WAIT', 'FAIL', 'DONE']):
            if action == 'WAIT' or (type(action) == dict and action.get('action_type') == 'WAIT'):
                time.sleep(pause)
            elif action == 'FAIL' or (type(action) == dict and action.get('action_type') == 'FAIL'):
                done = True
                info = {"fail": True}
            elif action == 'DONE' or (type(action) == dict and action.get('action_type') == 'DONE'):
                done = True
                info = {"done": True}

        if self.action_space == "computer_13":
            self.controller.execute_action(action)
        elif self.action_space == "claude_computer_use":
            if action in ['WAIT', 'FAIL', 'DONE'] or (type(action) == dict and action.get('action_type') in ['WAIT', 'FAIL', 'DONE']):
                self.controller.execute_action(action)
            else:
                if type(action) == str:
                    self.controller.execute_python_command(_fix_pyautogui_less_than_bug(action))
                elif type(action) == dict:
                    self.controller.execute_python_command(_fix_pyautogui_less_than_bug(action['command']))

        time.sleep(pause)
        observation = self._get_obs()

        return observation, reward, done, info

    def evaluate(self):
        """
        Evaluate whether the task is successfully completed.
        """

        postconfig = self.evaluator.get("postconfig", [])
        self.setup_controller.setup(postconfig, self.enable_proxy)

        if self.evaluator['func'] == "infeasible":
            if len(self.action_history) > 0:
                last_action = self.action_history[-1]
                if (
                    last_action == "FAIL"
                    or (type(last_action) == dict and last_action.get('action_type') == 'FAIL')
                    or (isinstance(last_action, tuple) and len(last_action) == 2 and last_action[0] == "FAIL")
                ):
                    return 1
            return 0
        else:
            if len(self.action_history) > 0:
                last_action = self.action_history[-1]
                if (
                    last_action == "FAIL"
                    or (type(last_action) == dict and last_action.get('action_type') == 'FAIL')
                    or (isinstance(last_action, tuple) and len(last_action) == 2 and last_action[0] == "FAIL")
                ):
                    return 0

        if type(self.metric) == list:
            # Multiple metrics to evaluate whether the task is successfully completed
            results = []
            assert len(self.metric) == len(self.result_getter), "The number of metrics and result getters must be the same"
            if "expected" in self.evaluator:
                assert len(self.metric) == len(self.expected_getter), "The number of metrics and expected getters must be the same"
            for idx, metric in enumerate(self.metric):
                try:
                    config = self.evaluator["result"][idx]
                    result_state = self.result_getter[idx](self, config)
                except FileNotFoundError:
                    logger.error("File not found!")
                    if self.metric_conj == 'and':
                        return 0

                if "expected" in self.evaluator and self.expected_getter and self.evaluator["expected"]:
                    expected_state = self.expected_getter[idx](self, self.evaluator["expected"][idx])
                    metric: int = metric(result_state, expected_state, **self.metric_options[idx])
                else:
                    metric: int = metric(result_state, **self.metric_options[idx])

                if self.metric_conj == 'and' and float(metric) == 0.0:
                    return 0
                elif self.metric_conj == 'or' and float(metric) == 1.0:
                    return 1
                else:
                    results.append(metric)

            return sum(results) / len(results) if self.metric_conj == 'and' else max(results)
        else:
            # Single metric to evaluate whether the task is successfully completed
            try:
                result_state = self.result_getter(self, self.evaluator["result"])
            except FileNotFoundError:
                logger.error("File not found!")
                return 0

            if "expected" in self.evaluator and self.expected_getter and self.evaluator["expected"]:
                expected_state = self.expected_getter(self, self.evaluator["expected"])
                metric: float = self.metric(result_state, expected_state, **self.metric_options)
            else:
                metric: float = self.metric(result_state, **self.metric_options)

        return metric

    def render(self, mode='rgb_array'):
        if mode == 'rgb_array':
            return self.controller.get_screenshot()
        else:
            raise ValueError('Unsupported render mode: {}'.format(mode))
