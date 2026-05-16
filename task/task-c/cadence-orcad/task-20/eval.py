from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': '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', 'ground_truth/diode_answer.json': 'eNqr5uVSUFAKi/f0i08siTc1KC1WslIw1TMw0IFKpGTmp6QiyRnoWRqYQiQ9sUgamBhYQqVLQCYZpOqaQbhBxfH5GbkgVYYGQHUQwVyg/hygkJKLc2hwiL+vEpJwfEFiUSJYQ7WSZzBIX6quoYmOgpIfiK1nBGQFBYMtNazl5QIiAFmFMWg=', 'ground_truth/pulse.out': 'eNqtkU9rwzAMxe+FfAfRU9tRTzHNsgZ28ByxeeQfsT0YY/RQMgh0tDRsn392mpIcdtzDN/2k9yQHM1g5AVT61O4bCGO2YQiL4vgDHDlfwlAfxcMEowQ5AG5uuXt3wSzwY6A6Hz/bQ5PAXMtnyoVRMlxXNtM0h3c4fR+6hnXtF3z4hmBwlqqWVhlISctaVUaVRV90WnRNM7Tt2/Ny2mVqUWhFhQFRiOxNKz0GNJRXVAtja4IHHzhmiOgMnkBeZqz+VdNcTjkJ7axzH64mbTOjBwLUTphdhHbM6vO5g28jRFoj99Drn1Dkd3DQDeIFSlWZ0gT10JZhhP2kcLB8KR9BloXMbErp9a79kUojsr5sVE7T/wVk8X0w+wU/XmpH'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('custom.stl', '/home/user/Desktop/custom.stl'), ('diode.lib', '/home/user/Desktop/diode.lib'), ('pulse.cir', '/home/user/Desktop/pulse.cir')]


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
    print("true" if _run() else "false")
