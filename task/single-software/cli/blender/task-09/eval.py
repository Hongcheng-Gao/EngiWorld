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
INIT_MAP = [('parts.blend', '/home/user/Desktop/parts.blend')]


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
