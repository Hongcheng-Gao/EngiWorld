import json, re
from pathlib import Path
R = re.compile(r"\[Software\][^\`]*\`([^\`]+)\`", re.I)
for n in range(1, 21):
    p = Path(f"task/task-c/ansys/task-{n:02d}/task-{n:02d}.json")
    o = json.loads(p.read_text(encoding="utf-8"))
    m = R.search(o["instruction"])
    s = m.group(1) if m else "NONE"
    # show last 100 chars of software block
    print(f"{n:02d}: ...{s[-95:]}")
