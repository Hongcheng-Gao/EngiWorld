# -*- coding: utf-8 -*-
# Infeasible verdict check. Stdout must be exactly True\n or False\n.
import sys

VERDICT_FILE = r"C:\Users\Administrator\Desktop\engiworld_infeasible_verdict.txt"

def main() -> None:
    try:
        raw = open(VERDICT_FILE, encoding="utf-8", errors="replace").read()
    except OSError:
        raw = ""
    ok = raw.strip().lower() == "false"
    sys.stdout.write("True\n" if ok else "False\n")

if __name__ == "__main__":
    main()
