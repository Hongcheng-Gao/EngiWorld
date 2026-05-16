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
