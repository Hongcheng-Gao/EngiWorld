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
