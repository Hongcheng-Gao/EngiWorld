import re
import os
import ast
import json
import time
import math
import httpx
import base64
import backoff
import traceback
from loguru import logger
from typing import Any, Dict, List, Tuple, Optional, Union

from mm_agents._llm_retry import EmptyResponseError, make_llm_retry
from mm_agents._rate_limit import acquire_rpm_slot

def encode_image(image_content):
    return base64.b64encode(image_content).decode("utf-8")

INSTRUCTION_TEMPLATE = "# Task Instruction:\n{instruction}\n\nPlease generate the next move according to the screenshot, task instruction and previous steps (if provided).\n"

STEP_TEMPLATE = "# Step {step_num}:\n"

SYSTEM_PROMPT_THINKING = """
You are a GUI agent. You are given an instruction, a screenshot of the screen and your previous interactions with the computer. You need to perform a series of actions to complete the task. The passoword of the computer is {password}.

For each step, provide your response in this format:
{thought}
## Action:
{action}
## Code:
{code}

In the code section, the code should be either pyautogui code or one of the following functions wrapped in the code block:
- {"name": "computer.wait", "description": "Make the computer wait for 20 seconds for installation, running code, etc.", "parameters": {"type": "object", "properties": {}, "required": []}}
- {"name": "computer.terminate", "description": "Terminate the current task and report its completion status", "parameters": {"type": "object", "properties": {"status": {"type": "string", "enum": ["success", "failure"], "description": "The status of the task"}, "answer": {"type": "string", "description": "The answer of the task"}}, "required": ["status"]}}
""".strip()

SYSTEM_PROMPT_NON_THINKING = """
You are a GUI agent. You are given an instruction, a screenshot of the screen and your previous interactions with the computer. You need to perform a series of actions to complete the task. The passoword of the computer is {password}.

For each step, provide your response in this format:
## Thought
{thought}
## Action:
{action}
## Code:
{code}

In the code section, the code should be either pyautogui code or one of the following functions wrapped in the code block:
- {"name": "computer.wait", "description": "Make the computer wait for 20 seconds for installation, running code, etc.", "parameters": {"type": "object", "properties": {}, "required": []}}
- {"name": "computer.terminate", "description": "Terminate the current task and report its completion status", "parameters": {"type": "object", "properties": {"status": {"type": "string", "enum": ["success", "failure"], "description": "The status of the task"}, "answer": {"type": "string", "description": "The answer of the task"}}, "required": ["status"]}}
""".strip()

# computer_13 模式：保留 ## Thought / ## Action / ## Code 框架，把 code 块换成单个 JSON 字典。
# x/y 是绝对像素坐标，DesktopEnv.controllers.python.execute_action 直接派发到 pyautogui，
# 不再走 project_coordinate_to_absolute_scale。{screen_width}/{screen_height} 在运行时填。
SYSTEM_PROMPT_COMPUTER13_THINKING = """
You are a GUI agent. You are given an instruction, a screenshot of the screen and your previous interactions with the computer. You need to perform a series of actions to complete the task. The password of the computer is {password}.

For each step, provide your response in this format:
{thought}
## Action:
{action}
## Code:
{code}

In the code section, return EXACTLY ONE JSON object describing the next action, wrapped in a ```json fenced block. All x/y are ABSOLUTE PIXEL COORDINATES on a {screen_width}x{screen_height} screen.

Available action_type values and their parameters:
- {"action_type": "MOVE_TO", "parameters": {"x": <int>, "y": <int>}}
- {"action_type": "CLICK", "parameters": {"button": "left"|"middle"|"right", "x": <int>, "y": <int>, "num_clicks": <int, optional, default 1>}}
- {"action_type": "MOUSE_DOWN", "parameters": {"button": "left"|"middle"|"right"}}
- {"action_type": "MOUSE_UP", "parameters": {"button": "left"|"middle"|"right"}}
- {"action_type": "RIGHT_CLICK", "parameters": {"x": <int>, "y": <int>}}
- {"action_type": "DOUBLE_CLICK", "parameters": {"x": <int>, "y": <int>}}
- {"action_type": "DRAG_TO", "parameters": {"x": <int>, "y": <int>}}
- {"action_type": "SCROLL", "parameters": {"dx": <int, optional>, "dy": <int, positive=up, negative=down>}}
- {"action_type": "TYPING", "parameters": {"text": "<string>"}}
- {"action_type": "PRESS", "parameters": {"key": "<keyname>"}}
- {"action_type": "KEY_DOWN", "parameters": {"key": "<keyname>"}}
- {"action_type": "KEY_UP", "parameters": {"key": "<keyname>"}}
- {"action_type": "HOTKEY", "parameters": {"keys": ["ctrl", "c"]}}
- {"action_type": "WAIT"}                       # wait ~20s for installs/loading
- {"action_type": "DONE"}                       # task succeeded
- {"action_type": "FAIL"}                       # task cannot be completed

Output exactly one JSON object. Do not return pyautogui code. Do not return multiple actions in a single step.
""".strip()

SYSTEM_PROMPT_COMPUTER13_NON_THINKING = """
You are a GUI agent. You are given an instruction, a screenshot of the screen and your previous interactions with the computer. You need to perform a series of actions to complete the task. The password of the computer is {password}.

For each step, provide your response in this format:
## Thought
{thought}
## Action:
{action}
## Code:
{code}

In the code section, return EXACTLY ONE JSON object describing the next action, wrapped in a ```json fenced block. All x/y are ABSOLUTE PIXEL COORDINATES on a {screen_width}x{screen_height} screen.

Available action_type values and their parameters:
- {"action_type": "MOVE_TO", "parameters": {"x": <int>, "y": <int>}}
- {"action_type": "CLICK", "parameters": {"button": "left"|"middle"|"right", "x": <int>, "y": <int>, "num_clicks": <int, optional, default 1>}}
- {"action_type": "MOUSE_DOWN", "parameters": {"button": "left"|"middle"|"right"}}
- {"action_type": "MOUSE_UP", "parameters": {"button": "left"|"middle"|"right"}}
- {"action_type": "RIGHT_CLICK", "parameters": {"x": <int>, "y": <int>}}
- {"action_type": "DOUBLE_CLICK", "parameters": {"x": <int>, "y": <int>}}
- {"action_type": "DRAG_TO", "parameters": {"x": <int>, "y": <int>}}
- {"action_type": "SCROLL", "parameters": {"dx": <int, optional>, "dy": <int, positive=up, negative=down>}}
- {"action_type": "TYPING", "parameters": {"text": "<string>"}}
- {"action_type": "PRESS", "parameters": {"key": "<keyname>"}}
- {"action_type": "KEY_DOWN", "parameters": {"key": "<keyname>"}}
- {"action_type": "KEY_UP", "parameters": {"key": "<keyname>"}}
- {"action_type": "HOTKEY", "parameters": {"keys": ["ctrl", "c"]}}
- {"action_type": "WAIT"}                       # wait ~20s for installs/loading
- {"action_type": "DONE"}                       # task succeeded
- {"action_type": "FAIL"}                       # task cannot be completed

Output exactly one JSON object. Do not return pyautogui code. Do not return multiple actions in a single step.
""".strip()

THOUGHT_HISTORY_TEMPLATE_THINKING = "◁think▷{thought}◁/think▷## Action:\n{action}\n"
THOUGHT_HISTORY_TEMPLATE_NON_THINKING = "## Thought:\n{thought}\n\n## Action:\n{action}\n"


def parse_response_to_cot_and_action(
    response,
    screen_size,
    coordinate_type,
    thinking: bool,
    action_space: str = "pyautogui",
) -> Tuple[str, List[Union[str, dict]], dict]:
    """Parse response including Observation, Thought, Action and code block.

    Returns: (action_natural_language, [action_payload], sections)
      - pyautogui 路径下 action_payload 是 str（pyautogui 代码或 'WAIT'/'DONE'/'FAIL'）。
      - computer_13 路径下 action_payload 是 dict（含 action_type/parameters）或字符串 sentinel。
    """
    logger.warning(f"Response: {response}")
    input_string = response['content'].lstrip()

    sections = {}
    try:
        if thinking:
            thought = response.get('reasoning_content', '').strip()
            sections['thought'] = thought
            logger.info(f"Extracted thought (thinking): {sections['thought']}")
            m = re.search(r"^##\s*Action\b", input_string, flags=re.MULTILINE) # remove extra content before ## Action
            if m:
                input_string = input_string[m.start():]
        else:
            thought = re.search(r'^##\s*Thought\s*:?[\n\r]+(.*?)(?=^##\s*Action:|^##|\Z)', input_string, re.DOTALL | re.MULTILINE)
            if thought:
                sections['thought'] = thought.group(1).strip()
            else:
                sections['thought'] = ""

            logger.info(f"Extracted thought (non-thinking): {sections['thought']}")

        action_match = re.search(
            r'^\s*##\s*Action\s*:?\s*[\n\r]+(.*?)(?=^\s*##|\Z)',
            input_string, re.DOTALL | re.MULTILINE
        )
        if action_match:
            action = action_match.group(1).strip()
            sections['action'] = action.strip()

        code_blocks = re.findall(r'```(?:code|python|json)?\s*(.*?)\s*```', input_string, re.DOTALL | re.IGNORECASE)
        if not code_blocks:
            logger.error("No code blocks found in the input string")
            return f"<Error>: no code blocks found in the input string: {input_string}", ["FAIL"], sections

        code_block = code_blocks[-1].strip()
        sections['original_code'] = code_block

        if action_space == "computer_13":
            return _parse_computer13_block(code_block, sections, input_string)

        # ---- pyautogui 路径（原行为）----
        if "computer.wait" in code_block.lower():
            sections["code"] = "WAIT"
            return sections['action'], ["WAIT"], sections
        elif "computer.terminate" in code_block.lower():
            lower_block = code_block.lower()
            if ("failure" in lower_block) or ("fail" in lower_block):
                sections['code'] = "FAIL"
                return code_block, ["FAIL"], sections
            elif "success" in lower_block:
                sections['code'] = "DONE"
                return code_block, ["DONE"], sections
            else:
                logger.error("Terminate action found but no specific status provided in code block")
                return f"<Error>: terminate action found but no specific status provided in code block: {input_string}", ["FAIL"], sections

        corrected_code = code_block
        sections['code'] = corrected_code
        sections['code'] = project_coordinate_to_absolute_scale(corrected_code, screen_width=screen_size[0], screen_height=screen_size[1], coordinate_type=coordinate_type)

        if ('code' not in sections or sections['code'] is None or sections['code'] == "") or ('action' not in sections or sections['action'] is None or sections['action'] == ""):
            logger.error("Missing required action or code section")
            return f"<Error>: no code parsed: {input_string}", ["FAIL"], sections

        return sections['action'], [sections['code']], sections

    except Exception as e:
        error_message = f"<Error>: parsing response: {str(e)}\nTraceback:\n{traceback.format_exc()}\nInput string: {input_string}"
        logger.exception(error_message)
        return error_message, ['FAIL'], sections


def _parse_computer13_block(code_block: str, sections: dict, input_string: str
                            ) -> Tuple[str, List[Union[str, dict]], dict]:
    """从 ```json 块中抽出 computer_13 action dict，并把 WAIT/DONE/FAIL 映射成字符串 sentinel。"""
    try:
        action_obj = json.loads(code_block)
    except json.JSONDecodeError as e:
        logger.error(f"computer_13 JSON parse failed: {e}; block: {code_block}")
        return f"<Error>: computer_13 JSON parse failed: {e}; block: {code_block}", ["FAIL"], sections

    if not isinstance(action_obj, dict) or "action_type" not in action_obj:
        logger.error(f"computer_13 expected dict with action_type, got: {action_obj}")
        return f"<Error>: computer_13 expected dict with action_type, got: {action_obj}", ["FAIL"], sections

    action_type = action_obj.get("action_type")
    sections['code'] = action_obj

    # WAIT/DONE/FAIL 走字符串 sentinel，与 lib_run_single 早退/记录路径兼容（runner 期望字符串判断）。
    if action_type == "WAIT":
        sections['code'] = "WAIT"
        return sections.get('action', 'wait'), ["WAIT"], sections
    if action_type == "DONE":
        sections['code'] = "DONE"
        return sections.get('action', 'done'), ["DONE"], sections
    if action_type == "FAIL":
        sections['code'] = "FAIL"
        return sections.get('action', 'fail'), ["FAIL"], sections

    if 'action' not in sections or not sections.get('action'):
        # action 是给 traj.jsonl 的自然语言摘要，缺失时退化为 action_type
        sections['action'] = action_type

    return sections['action'], [action_obj], sections


def project_coordinate_to_absolute_scale(pyautogui_code_relative_coordinates, screen_width, screen_height, coordinate_type="relative"):
    """
    Convert the relative coordinates in the pyautogui code to absolute coordinates based on the logical screen size.
    """
    def _coordinate_projection(x, y, screen_width, screen_height, coordinate_type):
        if x<=1.0 and y<=1.0:
            return int(round(x * screen_width)), int(round(y * screen_height))
        else:
            return int(round(x)), int(round(y))
            
    pattern = r'(pyautogui\.\w+\([^\)]*\))'
    matches = re.findall(pattern, pyautogui_code_relative_coordinates)

    new_code = pyautogui_code_relative_coordinates

    for full_call in matches:
        func_name_pattern = r'(pyautogui\.\w+)\((.*)\)'
        func_match = re.match(func_name_pattern, full_call, re.DOTALL)
        if not func_match:
            continue

        func_name = func_match.group(1)
        args_str = func_match.group(2)

        try:
            parsed = ast.parse(f"func({args_str})").body[0].value
            parsed_args = parsed.args
            parsed_keywords = parsed.keywords

        except SyntaxError:
            return pyautogui_code_relative_coordinates

        function_parameters = {
            'click': ['x', 'y', 'clicks', 'interval', 'button', 'duration', 'pause'],
            'rightClick':  ['x', 'y', 'duration', 'tween', 'pause'],
            'middleClick': ['x', 'y', 'duration', 'tween', 'pause'],
            'doubleClick': ['x', 'y', 'interval', 'button', 'duration', 'pause'],
            'tripleClick': ['x', 'y', 'interval', 'button', 'duration', 'pause'],
            'moveTo': ['x', 'y', 'duration', 'tween', 'pause'],
            'dragTo': ['x', 'y', 'duration', 'button', 'mouseDownUp', 'pause'],
        }

        func_base_name = func_name.split('.')[-1]

        param_names = function_parameters.get(func_base_name, [])

        args = {}
        for idx, arg in enumerate(parsed_args):
            if idx < len(param_names):
                param_name = param_names[idx]
                arg_value = ast.literal_eval(arg)
                args[param_name] = arg_value

        try:
            for kw in parsed_keywords:
                param_name = kw.arg
                arg_value = ast.literal_eval(kw.value)
                args[param_name] = arg_value
        except Exception as e:
            logger.error(f"Error parsing keyword arguments: {e}")
            return pyautogui_code_relative_coordinates

        updated = False
        if 'x' in args and 'y' in args:
            try:
                x_rel = float(args['x'])
                y_rel = float(args['y'])
                x_abs, y_abs = _coordinate_projection(x_rel, y_rel, screen_width, screen_height, coordinate_type)
                args['x'] = x_abs
                args['y'] = y_abs
                updated = True
            except ValueError:
                pass

        if updated:
            reconstructed_args = []
            for idx, param_name in enumerate(param_names):
                if param_name in args:
                    arg_value = args[param_name]
                    if isinstance(arg_value, str):
                        arg_repr = f"'{arg_value}'"
                    else:
                        arg_repr = str(arg_value)
                    reconstructed_args.append(arg_repr)
                else:
                    break

            used_params = set(param_names[:len(reconstructed_args)])
            for kw in parsed_keywords:
                if kw.arg not in used_params:
                    arg_value = args[kw.arg]
                    if isinstance(arg_value, str):
                        arg_repr = f"{kw.arg}='{arg_value}'"
                    else:
                        arg_repr = f"{kw.arg}={arg_value}"
                    reconstructed_args.append(arg_repr)

            new_args_str = ', '.join(reconstructed_args)
            new_full_call = f"{func_name}({new_args_str})"
            new_code = new_code.replace(full_call, new_full_call)

    return new_code

def transform_action_to_code_block(action):
    if any(keyword in action for keyword in ["computer.terminate", "computer.wait", "browser.select_option", "browser.clear"]):
        return f"```code\n{action}\n```"
    else:
        return f"```python\n{action}\n```"

class KimiAgent:
    """
    KimiAgent: a desktop-automation agent powered by Kimi K2.5.

    This agent observes a desktop environment via screenshots and generates
    executable actions (e.g., mouse/keyboard operations) that can be applied
    through a GUI executor (such as PyAutoGUI) to complete automation tasks.

    Notes:
        - This is a beta feature of Kimi K2.5. APIs, prompt formats, and runtime
          behaviors may change, and occasional instability is expected.
    """
    def __init__(
            self,
            model: str, # Kimi model name, e.g. "kimi-k2.5"
            max_steps: int, # The max number of steps to finish the task
            max_image_history_length: int = 3, # The max number of images in the history
            platform: str = "ubuntu", # The platform of the computer
            max_tokens: int = 4096, # The max number of tokens in the response
            top_p: float = 0.95, # The top p value in the response
            temperature: float = 1, # The temperature value in the response
            action_space: str = "pyautogui", # The action space: pyautogui
            observation_type: str = "screenshot", # The observation type: screenshot
            screen_size: Tuple[int, int] = (1920, 1080), # The screen size
            coordinate_type: str = "relative", # The coordinate type: relative, absolute, qwen25
            password="osworld-public-evaluation", # The password for the ubuntu platform
            thinking: bool = True, # Whether to use thinking mode
            max_retries: int = 10, # Max attempts for the LLM call retry policy
            **kwargs
    ):
        assert coordinate_type in ["relative", "absolute", "qwen25"]
        assert action_space in ["pyautogui", "computer_13"], "Invalid action space"
        assert observation_type in [
            "screenshot", "a11y_tree", "screenshot_a11y_tree"
        ], "Invalid observation type (som not supported by Kimi)"
        assert model is not None, "Model cannot be None"

        self.model = model
        self.platform = platform
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.temperature = temperature
        self.action_space = action_space
        self.observation_type = observation_type
        self.coordinate_type = coordinate_type
        self.screen_size = screen_size
        self.max_image_history_length = max_image_history_length
        self.max_steps = max_steps
        self.max_retries = max_retries
        self.password = password
        self.thinking = thinking

        if self.action_space == "computer_13":
            base = (SYSTEM_PROMPT_COMPUTER13_THINKING if self.thinking
                    else SYSTEM_PROMPT_COMPUTER13_NON_THINKING)
            self.system_prompt = (
                base
                .replace("{password}", self.password)
                .replace("{screen_width}", str(self.screen_size[0]))
                .replace("{screen_height}", str(self.screen_size[1]))
            )
        else:
            base = SYSTEM_PROMPT_THINKING if self.thinking else SYSTEM_PROMPT_NON_THINKING
            self.system_prompt = base.replace("{password}", self.password)
        self.history_template = (
            THOUGHT_HISTORY_TEMPLATE_THINKING if self.thinking
            else THOUGHT_HISTORY_TEMPLATE_NON_THINKING
        )

        self.actions = []
        self.observations = []
        self.cots = []

    def reset(self, _logger=None):
        global logger
        logger = _logger if _logger is not None else logging.getLogger("desktopenv.agent")
        
        self.observations = []
        self.cots = []
        self.actions = []
    
    def _scale_scroll_for_windows(self, code, factor: int = 50):
        """ pyautogui.scroll 在 Ubuntu / Windows 上 scale 不同；只对 str 代码做正则替换。
        computer_13 路径下 code 是 dict，直接放过（DesktopEnv 端不接 hscroll/vscroll，
        Windows scroll 缩放对 computer_13 暂不支持，需要时由 DesktopEnv 的 SCROLL 分发处理）。"""
        if not isinstance(code, str):
            return code
        if self.platform.lower() != "windows":
            return code

        pattern_pos = re.compile(r'(pyautogui\.scroll\()\s*([-+]?\d+)\s*\)')
        code = pattern_pos.sub(lambda m: f"{m.group(1)}{int(m.group(2))*factor})", code)
        return code

    def _build_user_content(self, obs: Dict, text: str, include_image: bool, include_a11y: bool):
        """按 observation_type 拼当前 turn 的 user content。
        - screenshot:           image + text
        - a11y_tree:            a11y_text + text （无图）
        - screenshot_a11y_tree: image + a11y_text + text
        a11y 文本只在当前 turn 加，历史保持纯图（避免 token 雪崩）。"""
        parts = []
        if include_image:
            parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{encode_image(obs['screenshot'])}"},
            })
        if include_a11y:
            a11y = obs.get("accessibility_tree") or ""
            if not a11y:
                logger.warning("observation_type 要求 a11y_tree 但 obs 中无 accessibility_tree，已用空串代替。")
            parts.append({
                "type": "text",
                "text": "## Accessibility Tree:\n" + a11y,
            })
        parts.append({"type": "text", "text": text})
        return parts

    def predict(self, instruction: str, obs: Dict, **kwargs) -> Tuple[Any, List[Union[str, dict]], Dict]:
        """
        Predict the next action(s) based on the current observation.
        """
        if "step_idx" in kwargs:
            logger.info(f"========= {self.model} Step {kwargs['step_idx']} =======")
        else:
            logger.info(f"========================== {self.model} ===================================")
        logger.info(f"Instruction: \n{instruction}")

        # 历史是否携带过去截图：observation_type=a11y_tree（纯文本）时不带，免无意义图开销。
        history_carries_image = self.observation_type in ("screenshot", "screenshot_a11y_tree")
        # 当前 turn 是否带图 / 带 a11y 文本
        current_has_image = self.observation_type in ("screenshot", "screenshot_a11y_tree")
        current_has_a11y = self.observation_type in ("a11y_tree", "screenshot_a11y_tree")

        messages = []
        messages.append({
                "role": "system",
                "content": self.system_prompt
            })
        instruction_prompt = INSTRUCTION_TEMPLATE.format(instruction=instruction)

        history_step_texts = []
        for i in range(len(self.actions)):
            if i > len(self.actions) - self.max_image_history_length:
                if history_carries_image:
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{encode_image(self.observations[i]['screenshot'])}"}
                            }
                        ]
                    })

                history_content = STEP_TEMPLATE.format(step_num=i+1) + self.history_template.format(
                    thought=self.cots[i].get('thought'),
                    action=self.cots[i]['action']
                )

                messages.append({
                    "role": "assistant",
                    "content": history_content
                })
            else:
                history_content = STEP_TEMPLATE.format(step_num=i+1) + self.history_template.format(
                    thought=self.cots[i].get('thought'),
                    action=self.cots[i].get('action')
                )
                history_step_texts.append(history_content)
                if i == len(self.actions) - self.max_image_history_length:
                    messages.append({
                        "role":"assistant",
                        "content": "\n".join(history_step_texts)
                    })

        messages.append({
            "role": "user",
            "content": self._build_user_content(
                obs,
                text=instruction_prompt,
                include_image=current_has_image,
                include_a11y=current_has_a11y,
            ),
        })

        max_retry = 5
        retry_count = 0
        low_level_instruction = None
        pyautogui_actions = None
        other_cot = {}

        while retry_count < max_retry:
            try:
                response = self.call_llm({
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "top_p": self.top_p,
                    "temperature": self.temperature if retry_count==0 else max(0.2, self.temperature)
                }, self.model)

                logger.info(f"Model Output: \n{response}")
                if not response:
                    logger.error("No response found in the response.")
                    raise ValueError(f"No response found in the response:\n{response}.")

                low_level_instruction, pyautogui_actions, other_cot = parse_response_to_cot_and_action(
                    response,
                    self.screen_size,
                    self.coordinate_type,
                    thinking=self.thinking,
                    action_space=self.action_space,
                )
                if "<Error>" in low_level_instruction or not pyautogui_actions:
                    logger.error(f"Error parsing response: {low_level_instruction}")
                    raise ValueError(f"Error parsing response: {low_level_instruction}")
                break

            except EmptyResponseError as e:
                # Inner call_llm already retried 20× with exponential backoff;
                # retrying again here would amplify the same upstream issue.
                logger.error(f"Kimi LLM exhausted inner retries: {e}")
                return str(e), ['FAIL'], other_cot
            except Exception as e:
                logger.error(f"Error during message preparation: {e}")
                retry_count += 1
                if retry_count == max_retry:
                    logger.error("Maximum retries reached. Exiting.")
                    return str(e), ['FAIL'], other_cot

        pyautogui_actions = [
            self._scale_scroll_for_windows(code) for code in pyautogui_actions
        ]
        logger.info(f"Action: \n{low_level_instruction}")
        logger.info(f"Code: \n{pyautogui_actions}")

        self.observations.append(obs)
        self.actions.append(low_level_instruction)
        self.cots.append(other_cot)

        # 是否已经是终止动作？pyautogui 路径靠 "computer.terminate" 字符串识别；
        # computer_13 路径已经被 _parse_computer13_block 把 DONE/FAIL 收敛成字符串 sentinel。
        first = pyautogui_actions[0]
        if isinstance(first, str):
            already_terminating = first in ("DONE", "FAIL") or "computer.terminate" in first.lower()
        else:
            already_terminating = False  # dict 类型只可能是真实动作（非 sentinel）

        current_step = len(self.actions)
        if current_step >= self.max_steps and not already_terminating:
            logger.warning(f"Reached maximum steps {self.max_steps}. Forcing termination.")
            low_level_instruction = 'Fail the task because reaching the maximum step limit.'
            pyautogui_actions = ['FAIL']
            other_cot['code'] = 'FAIL'

        return response, pyautogui_actions, other_cot
            
    
    def call_llm(self, payload, model):
        """Call the Kimi LLM API. Retries on transport errors, non-200 status,
        non-stop finish_reason, or empty message content."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['KIMI_API_KEY']}"
        }
        base_url = os.environ.get("KIMI_BASE_URL", "https://api.moonshot.ai/v1").rstrip("/")
        api_url = base_url + "/chat/completions"

        for attempt in make_llm_retry(
            exceptions=(EmptyResponseError, httpx.HTTPError),
            max_attempts=self.max_retries,
            max_wait=60.0,
        ):
            with attempt:
                # Account-level RPM gate (no-op when --rpm is unset).
                acquire_rpm_slot()
                response = httpx.post(
                    api_url,
                    headers=headers,
                    json=payload,
                    timeout=1200,
                    verify=False,
                )

                if response.status_code != 200:
                    request_id = (
                        response.headers.get("x-request-id")
                        or response.headers.get("msh-request-id")
                    )
                    raise EmptyResponseError(
                        f"Kimi HTTP {response.status_code} (request_id={request_id}, "
                        f"model={model}, body={response.text!r})"
                    )

                body = response.json()
                finish_reason = body["choices"][0].get("finish_reason")
                message = body["choices"][0].get("message") or {}
                content = message.get("content")
                tool_calls = message.get("tool_calls")
                is_empty_content = (
                    not isinstance(content, str) or not content.strip()
                ) and not tool_calls
                if finish_reason == "stop" and not is_empty_content:
                    return message
                raise EmptyResponseError(
                    f"Kimi {model} non-stop or empty: finish_reason={finish_reason!r}, "
                    f"empty_content={is_empty_content}"
                )
