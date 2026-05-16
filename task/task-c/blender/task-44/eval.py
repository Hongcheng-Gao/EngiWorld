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
CALL_ARGS = ['/home/user/Desktop/output/city.usda']
INIT_MAP = [('scene.blend', '/home/user/Desktop/scene.blend')]


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
