"""Fix check_no_gui_bypass(...) calls missing ')' or using inline Path(os.environ...)."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APPS = (
    "ansys", "autocad", "freecad", "freecad-path", "librecad",
    "openscad", "solidcam", "solidworks", "solvespace",
)
FIXES = [
    (
        'check_no_gui_bypass(Path(os.environ.get("OUTPUT_ROOT", r"C:\\Users\\user\\Desktop")):',
        "check_no_gui_bypass(OUTPUT_ROOT):",
    ),
    (
        'check_no_gui_bypass(Path(os.environ.get("EVAL_TARGET_DIR", r"C:\\Users\\User\\Desktop")):',
        "check_no_gui_bypass(TARGET):",
    ),
    (
        'check_no_gui_bypass(Path(os.environ.get("EVAL_OUTPUT_ROOT", "/home/user/Desktop"))):',
        "check_no_gui_bypass(OUTPUT_ROOT):",
    ),
    (
        'check_no_gui_bypass(Path("/home/user/Desktop")):',
        "check_no_gui_bypass(DESKTOP):",
    ),
]

n = 0
for app in APPS:
    for path in (REPO / "task" / "task-v" / app).glob("task-*/eval.py"):
        text = path.read_text(encoding="utf-8")
        orig = text
        for old, new in FIXES:
            text = text.replace(old, new)
        if text != orig:
            path.write_text(text, encoding="utf-8")
            n += 1
print(f"fixed {n} files")
