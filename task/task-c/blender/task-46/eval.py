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
