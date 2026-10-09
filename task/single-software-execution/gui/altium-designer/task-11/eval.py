from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DEFAULT_DESKTOP = Path(r"C:\Users\user\Desktop")
FORBIDDEN_SCRIPT_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".psm1", ".psd1", ".vbs", ".js", ".mjs", ".ts", ".rb",
    ".lua", ".tcl", ".ahk", ".scr",
}


def _has_unexpected_script(root: Path) -> bool:
    try:
        for path in root.rglob("*"):
            if not path.is_file() or path.name.lower() == "eval.py":
                continue
            if path.suffix.lower() in FORBIDDEN_SCRIPT_EXTENSIONS:
                return True
    except OSError:
        return True
    return False


def _parse_sections(text: str) -> dict[str, list[tuple[str, str]]]:
    sections: dict[str, list[tuple[str, str]]] = {}
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            sections.setdefault(current, [])
            continue
        if current is not None and "=" in line:
            key, value = line.split("=", 1)
            sections[current].append((key.strip(), value.strip()))
    return sections


def _numbered_outputs(fields: list[tuple[str, str]]) -> dict[int, dict[str, str]]:
    outputs: dict[int, dict[str, str]] = {}
    pattern = re.compile(r"^([A-Za-z][A-Za-z0-9_]*?)(\d+)$")
    for key, value in fields:
        match = pattern.match(key)
        if match:
            outputs.setdefault(int(match.group(2)), {})[match.group(1)] = value
    return outputs


def _expected_plot_layers(stackup: dict) -> list[str]:
    layers = stackup["layers"]
    signal_positions = [i for i, layer in enumerate(layers) if layer["type"] == "Signal"]
    first_signal = signal_positions[0]
    last_signal = signal_positions[-1]
    intermediate_number = 0
    expected = []
    for index, layer in enumerate(layers):
        if layer["type"] != "Signal":
            expected.append("Mechanical15")
        elif index == first_signal:
            expected.append("TopLayer")
        elif index == last_signal:
            expected.append("BottomLayer")
        else:
            intermediate_number += 1
            expected.append(f"MidLayer{intermediate_number}")
    return expected


def eval_outputs(output_dir: Path) -> bool:
    output_dir = Path(output_dir).resolve()
    if _has_unexpected_script(output_dir):
        return False

    stackup_path = output_dir / "stackup.json"
    answer_path = output_dir / "layered.OutJob"
    if not stackup_path.is_file() or not answer_path.is_file():
        return False

    try:
        stackup = json.loads(stackup_path.read_text(encoding="utf-8"))
        text = answer_path.read_text(encoding="utf-8", errors="replace")
        expected = _expected_plot_layers(stackup)
    except (OSError, ValueError, KeyError, IndexError):
        return False

    sections = _parse_sections(text)
    group = sections.get("OutputGroup1")
    if group is None:
        return False
    outputs = _numbered_outputs(group)
    if sorted(outputs) != list(range(1, len(expected) + 1)):
        return False

    for number, plot_layer in enumerate(expected, start=1):
        output = outputs[number]
        if output.get("OutputType", "").lower() != "gerber":
            return False
        if output.get("PlotLayer") != plot_layer:
            return False
        if output.get("OutputEnabled", "").lower() not in {"1", "true", "yes"}:
            return False
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", nargs="?", default=str(DEFAULT_DESKTOP))
    args = parser.parse_args()
    print("True" if eval_outputs(Path(args.output_dir)) else "False")
