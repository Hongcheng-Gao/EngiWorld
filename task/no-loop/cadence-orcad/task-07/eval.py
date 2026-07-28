from __future__ import annotations

import ast
import os
import re
from pathlib import Path

ANSWER_NAME = 'answer.cir'
LANGUAGE = 'spice'
REQUIRED_TOKENS = ['Silicon diode room-temperature I-V', '.MODEL DSI D', '.END']
MIN_LINES = 6

def _resolve(candidate=None):
    if candidate:
        path = Path(candidate)
        return path / ANSWER_NAME if path.is_dir() else path
    env_path = os.environ.get("ENGIWORLD_ANSWER_PATH")
    if env_path:
        return Path(env_path)
    choices = [
        Path("/home/user/Desktop") / ANSWER_NAME,
        Path(r"C:\Users\user\Desktop") / ANSWER_NAME,
        Path.cwd() / ANSWER_NAME,
    ]
    return next((path for path in choices if path.is_file()), choices[0])

def _strip_comments(text):
    if LANGUAGE == "python":
        return "\n".join(line.split("#", 1)[0] for line in text.splitlines())
    if LANGUAGE == "spice":
        return "\n".join(line.split("$", 1)[0] for line in text.splitlines()
                         if not line.lstrip().startswith("*"))
    if LANGUAGE == "apdl":
        return "\n".join(line.split("!", 1)[0] for line in text.splitlines())
    if LANGUAGE == "calculix":
        return "\n".join(line for line in text.splitlines()
                         if not line.lstrip().startswith("**"))
    if LANGUAGE == "scad":
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        return "\n".join(line.split("//", 1)[0] for line in text.splitlines())
    return text

def _balanced(text):
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for char in text:
        if char in "([{":
            stack.append(char)
        elif char in pairs:
            if not stack or stack.pop() != pairs[char]:
                return False
    return not stack

def _language_valid(text, active):
    try:
        if LANGUAGE == "python":
            tree = ast.parse(text)
            nodes = [n for n in ast.walk(tree)
                     if isinstance(n, (ast.Call, ast.Assign, ast.AnnAssign))]
            return len(nodes) >= 8
        lines = [line.strip() for line in active.splitlines() if line.strip()]
        if LANGUAGE == "spice":
            return bool(lines) and lines[-1].upper() == ".END" and any(
                line[0].upper() in "RCLVIEQMGD" for line in lines
                if not line.startswith("."))
        if LANGUAGE == "apdl":
            upper = active.upper()
            return ("/PREP7" in upper and "/SOLU" in upper and
                    "SOLVE" in upper and upper.count("FINISH") >= 2)
        if LANGUAGE == "calculix":
            upper = active.upper()
            return all(x in upper for x in
                       ("*NODE", "*ELEMENT", "*MATERIAL", "*STEP", "*END STEP"))
        if LANGUAGE == "scad":
            return _balanced(active) and ";" in active
    except (SyntaxError, ValueError):
        return False
    return False

def eval_outputs(candidate, expected=None, postconfig=None):
    path = _resolve(candidate)
    if not path.is_file() or path.name.lower() != ANSWER_NAME.lower():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    if chr(96) * 3 in text or "\x00" in text:
        return False
    active = _strip_comments(text)
    if len([line for line in active.splitlines() if line.strip()]) < MIN_LINES:
        return False
    lowered = active.lower()
    if any(x in lowered for x in ("todo", "notimplemented", "your code here")):
        return False
    if not _language_valid(text, active):
        return False
    return all(token.lower() in lowered for token in REQUIRED_TOKENS)

def main():
    passed = eval_outputs(_resolve())
    print("True" if passed else "False")
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())
