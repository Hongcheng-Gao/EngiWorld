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
INIT_MAP = [('character.blend', '/home/user/Desktop/character.blend')]


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
