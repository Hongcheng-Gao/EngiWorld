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
