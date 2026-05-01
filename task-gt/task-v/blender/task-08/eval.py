from __future__ import annotations

import base64
import importlib.util
import json
import subprocess
import shutil
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\Administrator\Desktop')
BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender5.1\blender.exe"

BUNDLE = {'eval_inner.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['C:\\Users\\Administrator\\Desktop\\answer.blend']
INIT_MAP = [('scene.blend', 'C:\\Users\\Administrator\\Desktop\\scene.blend')]


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
    print("true" if _run() else "false")
