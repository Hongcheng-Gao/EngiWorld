from pathlib import Path


root = Path("/home/user/Desktop")
lines = []
for reynolds in (100, 400, 1000):
    lines.append((root / f"re_{reynolds}.result").read_text(encoding="utf-8").strip())
(root / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
