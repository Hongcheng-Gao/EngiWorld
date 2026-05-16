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
        score = result.get("score")
        if isinstance(score, (int, float)):
            return float(score) == 1.0
    for attr in ("all_passed", "passed"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if isinstance(value, bool):
                return value
    if hasattr(result, "score"):
        try:
            return float(getattr(result, "score")) == 1.0
        except Exception:
            pass
    return False


def _resolve_arg(spec: str):
    if spec == "__DESKTOP_DIR__":
        return str(DESKTOP)
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
        score = result.get("score")
        if isinstance(score, (int, float)):
            return float(score) == 1.0
    for attr in ("all_passed", "passed"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if isinstance(value, bool):
                return value
    if hasattr(result, "score"):
        try:
            return float(getattr(result, "score")) == 1.0
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
