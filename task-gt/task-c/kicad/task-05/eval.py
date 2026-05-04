from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': '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', 'schema.py': 'eNqNVG1u00AQ/R8pdxjMH0eAW/HTUlAjFCQkBFXafyWyFnuWmm52rd0NIgqWOAQX6RU4Cidh9sOx06ShjiXH4zdv3ozfOEmS8Wj+nYkFmrWwYMpbXDH4++s32FsEY5msmK5Ao11rCXbTIHClgQkBSGlrZjFrNpSn68aabDxKHCPXagUVs6wUzBg0UK8apW0fegm8RlFFJNHW8msHmsnNeOR+Fzv4eOQv8PYWy7sgNR+PgA7JVpiTTh1uG1euyuGLUiJE8EeDpXUx4oUpfFQSwxNW2jUTh3GrBGomS+LlQjELP/3DPYxUNpSlqGs4RCvkUBQULYrUoOCTKNIdNEq7Ng5+Obu6SqDm4CBZUAwoDELybvb+Q9LnNExbl3LDk5ttIGiXsPV5rvE2WfbgjrBrGGrjZHrRAx073ow1Dcoq5UmXMd3uEbTJ5JA9DO3p3AEfmcPNM32UeTf2p5NTyvTP/XY//Si5f18nudLtDthOhhTR+gnQ+cJfsm+qlqnPnzzm1H6nYlnLzF1RVwOvGotNwWsx9G/pDG5yELWxNwO3L8kFfmNS8hijQMFpmEpvpg4Z1aLWSgdX7lkW4DlNwbphXF3PL4EzKlqRz4HsXXXmvWi0alDbTe/l4M1gZXj1Bmpp84PBmPUqLTsbu29DSbgw9dDN5EQFqywT/ykgUKZPpDOl0tjT+fXNj6yIGxTQGZ1DGmA6hfMHDon1z7Pzw6YHq3s2oBl+CWgwK6Y3vRx6MYMKopYYl/uavBHXOtqkzeN9qNGebfsabXRJfD0AqW877pj/n2evObl4+UjrD/r0SvpNAJgvFp8WnQKfsbdUx17yKUrqOy0nR1bqs4y75OEE+AcnCfRs'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb'), ('layers.txt', '/home/user/Desktop/layers.txt')]


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


def _run() -> bool:
    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        module = _load_module(root)
        func = getattr(module, CALL_FUNC)
        args = [_resolve_arg(arg) for arg in CALL_ARGS]
        result = func(*args)
        return _is_pass(result)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
