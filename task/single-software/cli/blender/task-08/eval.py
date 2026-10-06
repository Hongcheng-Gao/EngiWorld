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
INIT_MAP = [('bricks.csv', '/home/user/Desktop/bricks.csv'), ('template.blend', '/home/user/Desktop/template.blend')]


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
