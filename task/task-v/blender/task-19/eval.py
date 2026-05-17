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
