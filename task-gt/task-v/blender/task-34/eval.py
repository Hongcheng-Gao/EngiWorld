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
INIT_MAP = [('scene.blend', 'C:\\Users\\Administrator\\Desktop\\scene.blend'), ('textures\\blue.png', 'C:\\Users\\Administrator\\Desktop\\textures\\blue.png'), ('textures\\green.png', 'C:\\Users\\Administrator\\Desktop\\textures\\green.png'), ('textures\\red.png', 'C:\\Users\\Administrator\\Desktop\\textures\\red.png')]


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
