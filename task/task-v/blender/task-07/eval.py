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
