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
