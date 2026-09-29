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
