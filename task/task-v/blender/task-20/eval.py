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
