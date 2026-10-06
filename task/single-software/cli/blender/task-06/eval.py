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
