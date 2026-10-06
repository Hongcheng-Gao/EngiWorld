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
