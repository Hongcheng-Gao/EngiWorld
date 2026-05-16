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
CALL_ARGS = ['/home/user/Desktop/normal_bake.png']
INIT_MAP = [('hi_low.blend', '/home/user/Desktop/hi_low.blend'), ('stub_black.png', '/home/user/Desktop/stub_black.png')]


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
