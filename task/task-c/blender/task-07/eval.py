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
INIT_MAP = [('height.png', '/home/user/Desktop/height.png'), ('template.blend', '/home/user/Desktop/template.blend')]


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
