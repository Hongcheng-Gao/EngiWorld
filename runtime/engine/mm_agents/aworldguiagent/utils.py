"""
This code is adapted from AgentS2 (https://github.com/simular-ai/Agent-S)
with modifications to suit specific requirements.
"""
import re
import base64
from aworld.core.common import Observation, ActionModel
from aworld.models.model_response import ModelResponse
from aworld.core.agent.base import AgentResult
from aworld.memory.main import InMemoryMemoryStore

def encode_image(image_content):
    # if image_content is a path to an image file, check type of the image_content to verify
    if isinstance(image_content, str):
        with open(image_content, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    else:
        return base64.b64encode(image_content).decode("utf-8")


def extract_first_agent_function(code_string):
    # Regular expression pattern to match 'agent' functions with any arguments, including nested parentheses
    pattern = r'agent\.[a-zA-Z_]+\((?:[^()\'"]|\'[^\']*\'|"[^"]*")*\)'

    # Find all matches in the string
    matches = re.findall(pattern, code_string)

    # Return the first match if found, otherwise return None
    return matches[0] if matches else None


def parse_single_code_from_string(input_string):
    input_string = input_string.strip()
    if input_string.strip() in ["WAIT", "DONE", "FAIL"]:
        return input_string.strip()

    # This regular expression will match both ```code``` and ```python code```
    # and capture the `code` part. It uses a non-greedy match for the content inside.
    pattern = r"```(?:\w+\s+)?(.*?)```"
    # Find all non-overlapping matches in the string
    matches = re.findall(pattern, input_string, re.DOTALL)

    # The regex above captures the content inside the triple backticks.
    # The `re.DOTALL` flag allows the dot `.` to match newline characters as well,
    # so the code inside backticks can span multiple lines.

    # matches now contains all the captured code snippets

    codes = []

    for match in matches:
        match = match.strip()
        commands = [
            "WAIT",
            "DONE",
            "FAIL",
        ]  # fixme: updates this part when we have more commands

        if match in commands:
            codes.append(match.strip())
        elif match.split("\n")[-1] in commands:
            if len(match.split("\n")) > 1:
                codes.append("\n".join(match.split("\n")[:-1]))
            codes.append(match.split("\n")[-1])
        else:
            codes.append(match)

    if len(codes) <= 0:
        return "fail"
    return codes[0]


def sanitize_code(code):
    # This pattern captures the outermost double-quoted text
    if "\n" in code:
        pattern = r'(".*?")'
        # Find all matches in the text
        matches = re.findall(pattern, code, flags=re.DOTALL)
        if matches:
            # Replace the first occurrence only
            first_match = matches[0]
            code = code.replace(first_match, f'"""{first_match[1:-1]}"""', 1)
    return code

def prune_image_messages(memory_store: InMemoryMemoryStore, max_trajectory_length: int):
    """
    Inspect memory_store and retain images only in the latest max_trajectory_length image-bearing messages.
    Remove image content from older messages.

    Args:
        memory_store (InMemoryMemoryStore): The in-memory store instance.
        max_trajectory_length (int): Maximum number of image-bearing messages to retain.
    """
    # Step 1: Get all messages with memory_store.get_all().
    all_items = memory_store.get_all()

    # Step 2: Select messages containing images.
    image_messages = []
    for item in all_items:
        if isinstance(item.content, list):
            if any(isinstance(part, dict) and part.get('type') == 'image_url' for part in item.content):
                image_messages.append(item)

    # Step 3: Check whether the image-message count exceeds the limit.
    if len(image_messages) <= max_trajectory_length:
        print("Number of image messages does not exceed the limit. No pruning needed.")
        return

    # Step 4: Identify older messages whose images should be removed.
    # get_all() returns insertion order, so the first entries are the oldest.
    num_to_prune = len(image_messages) - max_trajectory_length
    messages_to_prune = image_messages[:num_to_prune]

    print(f"Found {len(image_messages)} image messages. Pruning the oldest {num_to_prune}.")

    # Step 5: Update each affected message and persist it with store.update().
    for item_to_prune in messages_to_prune:

        # Build new content containing only nonimage parts.
        new_content = [
            part for part in item_to_prune.content
            if not (isinstance(part, dict) and part.get('type') == 'image_url')
        ]

        # Optionally simplify new_content to a string if only one text element remains.
        if len(new_content) == 1 and new_content[0].get('type') == 'text':
            final_content = new_content[0].get('text', '')
        else:
            final_content = new_content

        # Update the message content attribute.
        item_to_prune.content = final_content

        # Persist the changes with memory_store.update().
        memory_store.update(item_to_prune)

        print(f"Pruned image from message with ID: {item_to_prune.id}")

def reps_action_result(resp: ModelResponse) -> AgentResult:
    try:
        full_response = resp.content
        # Extract thoughts section
        thoughts_match = re.search(
            r"<thoughts>(.*?)</thoughts>", full_response, re.DOTALL
        )
        thoughts = thoughts_match.group(1).strip()
        # Extract answer section
        answer_match = re.search(r"<answer>(.*?)</answer>", full_response, re.DOTALL)
        answer = answer_match.group(1).strip()
        action = ActionModel(action_name=answer, policy_info=thoughts)
        return AgentResult(actions=[action], current_state=None)
    except Exception as e:
        action = ActionModel(action_name=resp.content, policy_info="")
        return AgentResult(actions=[action], current_state=None)

def parse_single_code_from_string(input_string):
    input_string = input_string.strip()
    if input_string.strip() in ["WAIT", "DONE", "FAIL"]:
        return input_string.strip()

    # This regular expression will match both ```code``` and ```python code```
    # and capture the `code` part. It uses a non-greedy match for the content inside.
    pattern = r"```(?:\w+\s+)?(.*?)```"
    # Find all non-overlapping matches in the string
    matches = re.findall(pattern, input_string, re.DOTALL)

    # The regex above captures the content inside the triple backticks.
    # The `re.DOTALL` flag allows the dot `.` to match newline characters as well,
    # so the code inside backticks can span multiple lines.

    # matches now contains all the captured code snippets

    codes = []

    for match in matches:
        match = match.strip()
        commands = [
            "WAIT",
            "DONE",
            "FAIL",
        ]  # fixme: updates this part when we have more commands

        if match in commands:
            codes.append(match.strip())
        elif match.split("\n")[-1] in commands:
            if len(match.split("\n")) > 1:
                codes.append("\n".join(match.split("\n")[:-1]))
            codes.append(match.split("\n")[-1])
        else:
            codes.append(match)

    if len(codes) <= 0:
        return "fail"
    return codes[0]