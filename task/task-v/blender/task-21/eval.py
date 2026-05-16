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
