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
