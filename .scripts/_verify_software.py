import json, re
from pathlib import Path
R = re.compile(r"\[Software\][^\`]*\`([^\`]+)\`")
for p in [
    "task/task-c/abaqus/task-01/task-01.json",
    "task/task-c/ansys/task-01/task-01.json",
    "task/task-c/ansys/task-09/task-09.json",
    "task/task-c/ansys/task-11/task-11.json",
]:
    o = json.loads(Path(p).read_text(encoding="utf-8"))
    m = R.search(o["instruction"])
    print(p, "->", m.group(1) if m else "MISSING")
