from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\Administrator\Desktop')
BUNDLE = {'eval_inner.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('old.PrjPcb', 'C:\\Users\\Administrator\\Desktop\\old.PrjPcb'), ('old.PrjPcbStructure', 'C:\\Users\\Administrator\\Desktop\\old.PrjPcbStructure'), ('old_Analog.SchDoc', 'C:\\Users\\Administrator\\Desktop\\old_Analog.SchDoc'), ('old_Debug.SchDoc', 'C:\\Users\\Administrator\\Desktop\\old_Debug.SchDoc'), ('old_IO.SchDoc', 'C:\\Users\\Administrator\\Desktop\\old_IO.SchDoc'), ('old_MCU.SchDoc', 'C:\\Users\\Administrator\\Desktop\\old_MCU.SchDoc'), ('old_Power.SchDoc', 'C:\\Users\\Administrator\\Desktop\\old_Power.SchDoc'), ('old_Storage.SchDoc', 'C:\\Users\\Administrator\\Desktop\\old_Storage.SchDoc'), ('old_Top.SchDoc', 'C:\\Users\\Administrator\\Desktop\\old_Top.SchDoc')]


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


def _materialize_output_view(root: Path) -> Path:
    stage = root / "_output_view"
    stage.mkdir(parents=True, exist_ok=True)
    init_names = {Path(rel).name for rel, _ in INIT_MAP}
    if DESKTOP.exists():
        for item in DESKTOP.iterdir():
            if item.name in {"eval.py", "_runtime"} or item.name in init_names:
                continue
            dst = stage / item.name
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            elif item.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst)
    return stage


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


def _resolve_arg(spec: str, output_view: Path):
    if spec == "__DESKTOP_DIR__":
        return str(output_view)
    desktop_prefix = str(DESKTOP)
    if spec.startswith(desktop_prefix):
        rel = spec[len(desktop_prefix):].lstrip("\\/")
        return str(output_view / Path(rel)) if rel else str(output_view)
    return spec


def _run() -> bool:
    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        output_view = _materialize_output_view(root)
        module = _load_module(root)
        func = getattr(module, CALL_FUNC)
        args = [_resolve_arg(arg, output_view) for arg in CALL_ARGS]
        result = func(*args)
        return _is_pass(result)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
