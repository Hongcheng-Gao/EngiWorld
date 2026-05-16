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
