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
