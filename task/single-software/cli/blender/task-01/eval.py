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
