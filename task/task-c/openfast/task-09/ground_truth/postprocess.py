from pathlib import Path
import math
import sys


def power_statistics(path):
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    header_index = next(
        index for index, line in enumerate(lines)
        if line.split() and line.split()[0] == "Time"
    )
    names = lines[header_index].split()
    power_index = names.index("GenPwr")
    values = []
    for line in lines[header_index + 2:]:
        fields = line.split()
        if not fields:
            continue
        row = [float(field) for field in fields]
        if len(row) != len(names) or not all(math.isfinite(value) for value in row):
            raise ValueError("malformed OpenFAST output row")
        values.append(row[power_index])
    if not values:
        raise ValueError("no OpenFAST output rows")
    return sum(values) / len(values), max(values)


input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("fixed.out")
output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("fixed_summary.txt")
mean_power, max_power = power_statistics(input_path)
output_path.write_text(f"{mean_power:.12f}, {max_power:.12f}\n", encoding="utf-8")
