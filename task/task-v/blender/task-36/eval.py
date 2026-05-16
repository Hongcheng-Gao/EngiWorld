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
