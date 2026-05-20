"""Revert external _gui_bypass imports and inline Revit-style checks in each eval.py."""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TASK_V = REPO / "task" / "task-v"

APPS = (
    "ansys",
    "autocad",
    "freecad",
    "freecad-path",
    "librecad",
    "openscad",
    "solidcam",
    "solidworks",
    "solvespace",
)

IMPORT_RE = re.compile(
    r"\nimport sys\n\n_TASK_V_ROOT = Path\(__file__\)\.resolve\(\)\.parents\[2\]\n"
    r"if str\(_TASK_V_ROOT\) not in sys\.path:\n"
    r"    sys\.path\.insert\(0, str\(_TASK_V_ROOT\)\)\n"
    r"from _gui_bypass import check_no_gui_bypass\n\n",
    re.MULTILINE,
)

BYPASS_CHECK_RE = re.compile(
    r"    if not check_no_gui_bypass\([^)]+\):\n        return False\n",
    re.MULTILINE,
)

MAIN_BYPASS_RE = re.compile(
    r"        if not check_no_gui_bypass\([^)]+\):\n            ok = False\n        else:\n            ",
    re.MULTILINE,
)

# Revit-style block + CAE/CAD tokens (inlined, no external module).
INLINE_BLOCK = '''
GUI_BYPASS_FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".psm1", ".psd1", ".vbs", ".js", ".mjs", ".ts", ".rb",
    ".lua", ".tcl", ".ahk", ".scr",
}
GUI_BYPASS_ALLOWED_FILENAMES = {"eval.py"}
GUI_BYPASS_OUTPUT_TOKENS = (
    "result.ifc", "result.pdf", "result.osm", "workflow.osw", "summary.txt",
    "report.csv", "result.csv",
    ".dxf", ".dwg", ".step", ".stp", ".fcstd", ".scad", ".stl", ".obj",
    ".db", ".rst", ".rth", ".wbpj", ".odb", ".cae", ".inp",
    ".nc", ".gcode", ".slb", ".ipt", ".sldprt", ".sldasm",
    "autocad_result", "apdl_", "wb_",
)
GUI_BYPASS_COMMAND_TOKENS = (
    "python", "python3", "py ", "powershell", "pwsh", "cmd.exe", "cmd /c",
    "bash", " sh ", "zsh", "node", "ruby", "perl",
    "ifcopenshell", "openstudio", "energyplus",
    "blender --background", "revitbatchprocessor",
    "ansys", "mapdl", "fluent", "abaqus", "cae noGUI",
    "freecad", "freecadcmd", "openscad", "librecad",
    "ezdxf", "cadquery", "accoreconsole", "autolisp",
    "solidworks", "solvespace",
)


def _read_text_safe(path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _desktop_script_artifacts(root):
    if not root.exists() or not root.is_dir():
        return True
    try:
        candidates = list(root.iterdir())
        for directory in list(candidates):
            if directory.is_dir() and directory.name not in {"__pycache__", "_runtime"}:
                try:
                    candidates.extend(directory.iterdir())
                except Exception:
                    pass
        for path in candidates:
            if not path.is_file():
                continue
            if path.name in GUI_BYPASS_ALLOWED_FILENAMES:
                continue
            if path.suffix.lower() in GUI_BYPASS_FORBIDDEN_EXTENSIONS:
                return True
    except Exception:
        return True
    return False


def _history_paths(root):
    home = Path.home()
    return [
        home / ".bash_history",
        home / ".zsh_history",
        home / ".python_history",
        home / ".local/share/fish/fish_history",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/Visual Studio Code Host_history.txt",
        root / ".bash_history",
        root / ".zsh_history",
    ]


def _history_contains_bypass(root):
    for path in _history_paths(root):
        if not path.is_file():
            continue
        text = _read_text_safe(path).lower()
        if not text:
            continue
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or "eval.py" in line:
                continue
            touches_output = any(token in line for token in GUI_BYPASS_OUTPUT_TOKENS)
            runs_command = any(token in line for token in GUI_BYPASS_COMMAND_TOKENS)
            writes_file = any(
                token in line for token in (">", "tee ", "cat ", "set-content", "out-file", "new-item")
            )
            if touches_output and (runs_command or writes_file):
                return True
            if ("/desktop/" in line or "\\desktop\\" in line) and any(
                ext in line for ext in GUI_BYPASS_FORBIDDEN_EXTENSIONS
            ) and runs_command:
                return True
    return False


def check_no_gui_bypass(root):
    root = Path(root)
    if _desktop_script_artifacts(root):
        return False
    if _history_contains_bypass(root):
        return False
    return True

'''

DESKTOP_LINE_RE = re.compile(
    r"^((?:DESKTOP|OUTPUT_ROOT|TARGET)\s*=\s*.+)$",
    re.MULTILINE,
)


def revert_external_import(text: str) -> str:
    text = IMPORT_RE.sub("\n", text)
    text = BYPASS_CHECK_RE.sub("", text)
    text = MAIN_BYPASS_RE.sub("        ", text)
    # Drop import sys if now unused
    if "import sys" in text and "sys." not in text.replace("import sys", ""):
        text = re.sub(r"\nimport sys\n", "\n", text)
    return text


def detect_root_var(text: str) -> str | None:
    for name in ("DESKTOP", "OUTPUT_ROOT", "TARGET"):
        if re.search(rf"^{name}\s*=", text, re.M):
            return name
    if re.search(r"/home/user/Desktop", text):
        return "DESKTOP"
    return None


def ensure_desktop_const(text: str) -> tuple[str, str]:
    root = detect_root_var(text)
    if root:
        return text, root
    if re.search(r"/home/user/Desktop", text):
        const = 'DESKTOP = Path("/home/user/Desktop")\n\n'
        # after imports / future
        m = re.search(r"(^from __future__.*\n\n|^import .+\n\n)", text, re.M)
        if m:
            pos = text.find("\n\n", m.end() - 2) + 2
            text = text[:pos] + const + text[pos:]
        else:
            text = const + text
        return text, "DESKTOP"
    return text, ""


def has_inline_block(text: str) -> bool:
    return "GUI_BYPASS_FORBIDDEN_EXTENSIONS" in text and "def check_no_gui_bypass" in text


def insert_inline_block(text: str, root_var: str) -> str:
    if has_inline_block(text):
        return text
    m = DESKTOP_LINE_RE.search(text)
    if not m:
        return text
    insert_pos = m.end()
    # after desktop line, skip blank lines
    while insert_pos < len(text) and text[insert_pos] in "\r\n":
        insert_pos += 1
    text = text[:insert_pos] + "\n" + INLINE_BLOCK + text[insert_pos:]

    bypass = f"    if not check_no_gui_bypass({root_var}):\n        return False\n"
    for pat in (
        r"(def evaluate\([^)]*\)\s*(?:->\s*bool)?\s*:\n)",
        r"(def main\(\)\s*->\s*bool:\n)",
    ):
        m2 = re.search(pat, text)
        if m2:
            return text[: m2.end()] + bypass + text[m2.end() :]

    # solidcam: only __main__
    pat = r'(if __name__ == ["\']__main__["\']:\n\s+try:\n)'
    m3 = re.search(pat, text)
    if m3:
        inner = (
            f"        if not check_no_gui_bypass({root_var}):\n"
            "            ok = False\n"
            "        else:\n"
            "            "
        )
        return text[: m3.end()] + inner + text[m3.end() :].lstrip()
    return text


def process(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = revert_external_import(text)
    text, root = ensure_desktop_const(text)
    if not root:
        return "no_root"
    text = insert_inline_block(text, root)
    path.write_text(text, encoding="utf-8")
    return "ok"


def main() -> None:
    stats: dict[str, int] = {}
    for app in APPS:
        for p in sorted((TASK_V / app).glob("task-*/eval.py")):
            stats[process(p)] = stats.get(process(p), 0) + 1
    helper = TASK_V / "_gui_bypass.py"
    if helper.exists():
        helper.unlink()
        stats["deleted_helper"] = 1
    print(stats)


if __name__ == "__main__":
    main()
