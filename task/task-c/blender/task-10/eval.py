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
