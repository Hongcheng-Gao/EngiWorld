from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'common/schema.py': 'eNqNVG1u00AQ/R8pdxjMH0eAW/HTUlAjFCQkBFXafyWyFnuWmm52rd0NIgqWOAQX6RU4Cidh9sOx06ShjiXH4zdv3ozfOEmS8Wj+nYkFmrWwYMpbXDH4++s32FsEY5msmK5Ao11rCXbTIHClgQkBSGlrZjFrNpSn68aabDxKHCPXagUVs6wUzBg0UK8apW0fegm8RlFFJNHW8msHmsnNeOR+Fzv4eOQv8PYWy7sgNR+PgA7JVpiTTh1uG1euyuGLUiJE8EeDpXUx4oUpfFQSwxNW2jUTh3GrBGomS+LlQjELP/3DPYxUNpSlqGs4RCvkUBQULYrUoOCTKNIdNEq7Ng5+Obu6SqDm4CBZUAwoDELybvb+Q9LnNExbl3LDk5ttIGiXsPV5rvE2WfbgjrBrGGrjZHrRAx073ow1Dcoq5UmXMd3uEbTJ5JA9DO3p3AEfmcPNM32UeTf2p5NTyvTP/XY//Si5f18nudLtDthOhhTR+gnQ+cJfsm+qlqnPnzzm1H6nYlnLzF1RVwOvGotNwWsx9G/pDG5yELWxNwO3L8kFfmNS8hijQMFpmEpvpg4Z1aLWSgdX7lkW4DlNwbphXF3PL4EzKlqRz4HsXXXmvWi0alDbTe/l4M1gZXj1Bmpp84PBmPUqLTsbu29DSbgw9dDN5EQFqywT/ykgUKZPpDOl0tjT+fXNj6yIGxTQGZ1DGmA6hfMHDon1z7Pzw6YHq3s2oBl+CWgwK6Y3vRx6MYMKopYYl/uavBHXOtqkzeN9qNGebfsabXRJfD0AqW877pj/n2evObl4+UjrD/r0SvpNAJgvFp8WnQKfsbdUx17yKUrqOy0nR1bqs4y75OEE+AcnCfRs', 'eval_inner.py': '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'}
CALL_FUNC = 'evaluate'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('assembled.brd', '/home/user/Desktop/assembled.brd')]
REQUIRED_OUTPUTS = ('pnp_top.csv', 'pnp_bottom.csv')


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
    if not all((DESKTOP / rel).is_file() for rel in REQUIRED_OUTPUTS):
        return False
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
