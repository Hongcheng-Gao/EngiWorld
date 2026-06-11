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
