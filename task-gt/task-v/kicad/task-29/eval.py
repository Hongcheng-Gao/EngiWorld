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
INIT_MAP = [('mipi.kicad_sch', '/home/user/Desktop/mipi.kicad_sch')]


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
    print("true" if _run() else "false")
