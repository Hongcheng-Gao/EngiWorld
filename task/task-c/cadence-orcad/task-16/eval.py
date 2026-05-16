from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': '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', 'ground_truth/class_ab.out': 'eNrNluFvmkAYxr+b+T88yb6oifS4am2b+AEOTHCKlEOzfVqYssqmYAS6pH/97sC2YOkyki3pm4i5l98999zxvoR2qycCZHBBRxf0ClS9HQxu1Rv08rzDD+E6AB0qqkLQoUPM/eN6C0roVTdnYBkfQQpcRLvVbqEHtvOTBJqOQ5Zs+4dst0OS+vcB1sc4SeKH4IgwSg7BOg3jSJGT5DQpJ4NZLltaHgyTM9dyPGthF0jvn0ahKVThbQMk8U7aSrZxttvgmEVIt2GCyE/DhwAGQ3r0o+S7RH4FwQF+tEGS7ff+MXwMBBtIoZftbQJ/g8c4CuAf40ywBCux50OW5ttV5gvDnOGO2lSEBtux0bH4WDX76gD6ZEyJmKBNxioh3Qp+Q0YaHNv5E95urRgD8gsRByrcq1QkTVMk5eWU7MusyFs2IH9PedJuuSpOOV3jJtSfEryTNnPVPGkvlt7zFsRd6SqXr96VjuVsdybU8qxcBtf5OYjV5PJ9YXyP02UvN2xqXFpZCf6rTckcE8s2sOpIgS40b9ynNaBaB9YoCgyvQHJOOXVyNWpOnb/CnuMudFP8m7bRbn1ov8d206ceivpyNFebm57p8v/Zb2Ltajx3QWmcl/kpXk2QZVgOWXjleJ4wM1emrDqoZwpqLS5Lnsu7RCF5iPYavhqXcX0CyN4rx9m4jNuTJmZEQ8u1q+rq2+q622irdiPc4vJkQM7wN824ZjOcNcHZtJH6qsChjIYVvjyuqLNm6qyJ+vwJv7ys4qXxC/75ZOZvHxOb8mbeeRPv+DRp9FS1RvUOlrc1VQa00k8KrcdhFF6vR1XvQ1rCz98404UOtrDZbGmY7/aVLE1yT/Ms7lmMgy/nc8398j9fyoAXp/4OP+JvSMN9gE6WhNE9ePFZpHaFq/HLEZNLcXS/ASNf6nI=', 'ground_truth/class_ab_measure.txt': 'eNoL8w8NifczMvC1UgjT8ANyNG11DfUMzcxMXHUNjRUcQxR0jfQMgMBV18CIlysMrNwQRbmpnpGlEUi5CVi5IbpyZMUKBhBZbQMDkGIED6o2AMVoBVSjMUwOQHG3Aqq7kZ0NAIOfMuU=', 'ground_truth/xover.json': 'eNqr5uVSUFAKyy8tiU8sidc1MsgNU7JS0DXUMzQzM0nVNTTWQVVgCFVgqmdkaQRSYIKqACJtoGeAKgzVhksX1Fp0W1NSE1Piq/LzUuPB0kZwY5OL8ouLU4vjq1KL8uOLK3NzU0uKMpMTc3IqgcpKikpTeblqebkAIIk66g=='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('class_ab.cir', '/home/user/Desktop/class_ab.cir')]


def _decode(payload: str) -> bytes:
    return zlib.decompress(base64.b64decode(payload.encode("ascii")))


def _materialize_bundle(root: Path) -> None:
    for rel, payload in BUNDLE.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_decode(payload))
    for dirname in ("init_file", "ground_truth", "_internal"):
        (root / dirname).mkdir(parents=True, exist_ok=True)
    for rel, desktop_path in INIT_MAP:
        src = Path(desktop_path)
        dst = root / "init_file" / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def _bundle_python_paths(root: Path) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        text = str(path)
        if text not in seen:
            seen.add(text)
            paths.append(text)

    add(root)
    for rel in BUNDLE:
        rel_path = Path(rel)
        if rel_path.suffix == ".py" and rel_path.parent != Path("."):
            add(root / rel_path.parent)
    return paths



def _load_module(root: Path):
    spec = importlib.util.spec_from_file_location("eval_inner", root / "eval_inner.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load eval_inner.py")
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules["eval_inner"] = module
    added_paths = _bundle_python_paths(root)
    for path in reversed(added_paths):
        sys.path.insert(0, path)
    try:
        spec.loader.exec_module(module)
    finally:
        for path in added_paths:
            try:
                sys.path.remove(path)
            except ValueError:
                pass
    return module
def _is_pass(result) -> bool:
    if isinstance(result, bool):
        return result
    if isinstance(result, dict):
        if "pass" in result:
            return bool(result["pass"])
        if "passed" in result:
            return bool(result["passed"])
        score = result.get("score")
        if isinstance(score, (int, float)):
            return float(score) == 1.0
    for attr in ("all_passed", "passed"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if isinstance(value, bool):
                return value
    if hasattr(result, "score"):
        try:
            return float(getattr(result, "score")) == 1.0
        except Exception:
            pass
    return False


def _resolve_arg(spec: str):
    if spec == "__DESKTOP_DIR__":
        return str(DESKTOP)
    return spec


def _run() -> bool:
    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        module = _load_module(root)
        func = getattr(module, CALL_FUNC)
        args = [_resolve_arg(arg) for arg in CALL_ARGS]
        result = func(*args)
        return _is_pass(result)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
