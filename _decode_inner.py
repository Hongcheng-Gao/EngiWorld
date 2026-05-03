"""Decode the embedded eval_inner from a sketchup/kicad/altium/eagle eval.py."""

import base64
import re
import sys
import zlib
from pathlib import Path


def decode_inner(eval_path: Path) -> str:
    src = eval_path.read_text(encoding="utf-8")
    # Execute just the BUNDLE assignment in a restricted namespace.
    ns: dict = {}
    # Find the line range of BUNDLE = { ... }
    start = src.find("BUNDLE = {")
    if start < 0:
        return "(no BUNDLE)"
    # Find matching closing brace
    depth = 0
    end = start
    for i in range(start, len(src)):
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    chunk = src[start:end]
    exec(chunk, ns)
    bundle = ns["BUNDLE"]
    inner = bundle.get("eval_inner.py")
    if not inner:
        return "(no eval_inner.py)"
    return zlib.decompress(base64.b64decode(inner)).decode("utf-8", errors="replace")


if __name__ == "__main__":
    p = Path(sys.argv[1])
    out = decode_inner(p)
    print(out)
