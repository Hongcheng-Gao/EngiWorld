import json, re
from pathlib import Path
R = re.compile(r"\[Software\]([^\`]+)\`([^\`]+)\`")
for n in range(1, 21):
    p = Path(f"task/task-c/ansys/task-{n:02d}/task-{n:02d}.json")
    o = json.loads(p.read_text(encoding="utf-8"))
    m = R.search(o["instruction"])
    if m:
        print(f"{n:02d} | prefix={m.group(1)!r} | path={m.group(2)}")
