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
