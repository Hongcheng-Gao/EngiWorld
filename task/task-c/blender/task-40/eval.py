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
