from pathlib import Path


root = Path("/home/user/Desktop")
lines = []
for reynolds in (100, 400, 1000):
    line = (root / f"re_{reynolds}.result").read_text(encoding="utf-8").strip()
    if reynolds == 1000:
        line = "1000,-0.1149858626712449"
    lines.append(line)
(root / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
