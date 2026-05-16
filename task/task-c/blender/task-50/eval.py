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
