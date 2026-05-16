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
INIT_MAP = [('lib\\characters.blend', 'C:\\Users\\Administrator\\Desktop\\lib\\characters.blend'), ('lib\\characters.blend.sha256', 'C:\\Users\\Administrator\\Desktop\\lib\\characters.blend.sha256'), ('scene.blend', 'C:\\Users\\Administrator\\Desktop\\scene.blend')]


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
