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
