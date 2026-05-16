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
INIT_MAP = [('bricks.csv', '/home/user/Desktop/bricks.csv'), ('scene.blend', '/home/user/Desktop/scene.blend')]


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
