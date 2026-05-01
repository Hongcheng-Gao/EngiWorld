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
