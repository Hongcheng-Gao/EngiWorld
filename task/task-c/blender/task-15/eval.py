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
