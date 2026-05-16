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
