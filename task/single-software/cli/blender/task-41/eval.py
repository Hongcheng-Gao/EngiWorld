from __future__ import annotations

import base64
import importlib.util
import json
import subprocess
import shutil
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BLENDER_PATH = "blender"

BUNDLE = {'eval_inner.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['/home/user/Desktop/answer.blend']
INIT_MAP = [('character.blend', '/home/user/Desktop/character.blend'), ('walk.bvh', '/home/user/Desktop/walk.bvh')]


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
        if "all_passed" in result:
            return bool(result["all_passed"])
        score = result.get("score", result.get("total_score"))
        if isinstance(score, (int, float)):
            return float(score) == 1.0
    for attr in ("all_passed", "passed"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if isinstance(value, bool):
                return value
    for attr in ("score", "total_score"):
        if hasattr(result, attr):
            try:
                return float(getattr(result, attr)) == 1.0
            except Exception:
                pass
    return False


def _resolve_arg(spec: str):
    if spec == "__DESKTOP_DIR__":
        return str(DESKTOP)
    desktop_prefix = "/home/user/Desktop"
    if spec.startswith(desktop_prefix):
        rel = spec[len(desktop_prefix):].lstrip("/")
        return str(DESKTOP / rel) if rel else str(DESKTOP)
    return spec


def _call_inner(root: Path):
    module = _load_module(root)
    func = getattr(module, CALL_FUNC)
    args = [_resolve_arg(arg) for arg in CALL_ARGS]
    return func(*args)


def _have_bpy() -> bool:
    try:
        import bpy  # noqa: F401
        return True
    except Exception:
        return False


def _run_via_blender(root: Path) -> bool:
    result_path = root / "_blender_result.json"
    runner_path = root / "_blender_runner.py"
    added_paths = _bundle_python_paths(root)
    args = [_resolve_arg(arg) for arg in CALL_ARGS]
    runner_code = f"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path({str(root)!r})
RESULT_PATH = Path({str(result_path)!r})
CALL_FUNC = {CALL_FUNC!r}
CALL_ARGS = {args!r}
ADDED_PATHS = {added_paths!r}


def _is_pass(result):
    if isinstance(result, bool):
        return result
    if isinstance(result, dict):
        if "pass" in result:
            return bool(result["pass"])
        if "passed" in result:
            return bool(result["passed"])
        if "all_passed" in result:
            return bool(result["all_passed"])
        score = result.get("score", result.get("total_score"))
        if isinstance(score, (int, float)):
            return float(score) == 1.0
    for attr in ("all_passed", "passed"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if isinstance(value, bool):
                return value
    for attr in ("score", "total_score"):
        if hasattr(result, attr):
            try:
                return float(getattr(result, attr)) == 1.0
            except Exception:
                pass
    return False


spec = importlib.util.spec_from_file_location("eval_inner", ROOT / "eval_inner.py")
if spec is None or spec.loader is None:
    raise RuntimeError("unable to load eval_inner.py")
module = importlib.util.module_from_spec(spec)
sys.modules["eval_inner"] = module
for path in reversed(ADDED_PATHS):
    sys.path.insert(0, path)
try:
    spec.loader.exec_module(module)
    func = getattr(module, CALL_FUNC)
    value = func(*CALL_ARGS)
    RESULT_PATH.write_text(json.dumps({{"pass": _is_pass(value)}}), encoding="utf-8")
finally:
    for path in ADDED_PATHS:
        try:
            sys.path.remove(path)
        except ValueError:
            pass
"""
    runner_path.write_text(runner_code, encoding="utf-8")
    try:
        proc = subprocess.run(
            [BLENDER_PATH, "--background", "--factory-startup", "--python", str(runner_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
    except Exception:
        return False
    if result_path.exists():
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            return bool(payload.get("pass"))
        except Exception:
            return False
    return proc.returncode == 0


def _run() -> bool:
    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        if _have_bpy():
            return _is_pass(_call_inner(root))
        return _run_via_blender(root)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    print("True" if _run() else "False")
