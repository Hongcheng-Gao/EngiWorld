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
