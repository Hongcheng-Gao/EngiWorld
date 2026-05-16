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
