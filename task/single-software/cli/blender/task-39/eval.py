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
INIT_MAP = [('scan.obj', '/home/user/Desktop/scan.obj'), ('scene.blend', '/home/user/Desktop/scene.blend')]


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
