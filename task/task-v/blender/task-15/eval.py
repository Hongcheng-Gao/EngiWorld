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



def _has_generated_python_file() -> bool:
    if not DESKTOP.exists():
        return False
    initial_python_names = {Path(rel).name for rel, _ in INIT_MAP if Path(rel).suffix.lower() == ".py"}
    allowed_names = {"eval.py"}
    allowed_names.update(initial_python_names)
    try:
        items = list(DESKTOP.iterdir())
    except Exception:
        return False
    for path in items:
        if path.name in allowed_names or path.name == "_runtime":
            continue
        try:
            if path.is_file() and path.suffix.lower() == ".py":
                return True
        except Exception:
            continue
    return False

def _run() -> bool:
    if _has_generated_python_file():
        return False

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
