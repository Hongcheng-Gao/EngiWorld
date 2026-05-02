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
INIT_MAP = [('hotswap.kicad_sch', '/home/user/Desktop/hotswap.kicad_sch'), ('hotswap_spec.csv', '/home/user/Desktop/hotswap_spec.csv'), ('mosfet_soa.csv', '/home/user/Desktop/mosfet_soa.csv')]


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
