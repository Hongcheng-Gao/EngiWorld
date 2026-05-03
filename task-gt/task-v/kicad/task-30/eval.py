from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


def _push_utf8_text_io():
    import builtins
    import pathlib

    orig_open = builtins.open
    orig_read_text = pathlib.Path.read_text

    def patched_open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        if 'b' not in mode and encoding is None:
            encoding = 'utf-8'
        return orig_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

    def patched_read_text(self, encoding=None, errors=None):
        if encoding is None:
            encoding = 'utf-8'
        return orig_read_text(self, encoding=encoding, errors=errors)

    builtins.open = patched_open
    pathlib.Path.read_text = patched_read_text
    return orig_open, orig_read_text


def _pop_utf8_text_io(state):
    import builtins
    import pathlib

    orig_open, orig_read_text = state
    builtins.open = orig_open
    pathlib.Path.read_text = orig_read_text


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': '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', 'schema.py': 'eNqNVG1u00AQ/R8pdxjMH0eAW/HTUlAjFCQkBFXafyWyFnuWmm52rd0NIgqWOAQX6RU4Cidh9sOx06ShjiXH4zdv3ozfOEmS8Wj+nYkFmrWwYMpbXDH4++s32FsEY5msmK5Ao11rCXbTIHClgQkBSGlrZjFrNpSn68aabDxKHCPXagUVs6wUzBg0UK8apW0fegm8RlFFJNHW8msHmsnNeOR+Fzv4eOQv8PYWy7sgNR+PgA7JVpiTTh1uG1euyuGLUiJE8EeDpXUx4oUpfFQSwxNW2jUTh3GrBGomS+LlQjELP/3DPYxUNpSlqGs4RCvkUBQULYrUoOCTKNIdNEq7Ng5+Obu6SqDm4CBZUAwoDELybvb+Q9LnNExbl3LDk5ttIGiXsPV5rvE2WfbgjrBrGGrjZHrRAx073ow1Dcoq5UmXMd3uEbTJ5JA9DO3p3AEfmcPNM32UeTf2p5NTyvTP/XY//Si5f18nudLtDthOhhTR+gnQ+cJfsm+qlqnPnzzm1H6nYlnLzF1RVwOvGotNwWsx9G/pDG5yELWxNwO3L8kFfmNS8hijQMFpmEpvpg4Z1aLWSgdX7lkW4DlNwbphXF3PL4EzKlqRz4HsXXXmvWi0alDbTe/l4M1gZXj1Bmpp84PBmPUqLTsbu29DSbgw9dDN5EQFqywT/ykgUKZPpDOl0tjT+fXNj6yIGxTQGZ1DGmA6hfMHDon1z7Pzw6YHq3s2oBl+CWgwK6Y3vRx6MYMKopYYl/uavBHXOtqkzeN9qNGebfsabXRJfD0AqW877pj/n2evObl4+UjrD/r0SvpNAJgvFp8WnQKfsbdUx17yKUrqOy0nR1bqs4y75OEE+AcnCfRs'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('design.kicad_sch', '/home/user/Desktop/design.kicad_sch'), ('legacy.kicad_sym', '/home/user/Desktop/legacy.kicad_sym'), ('sym-lib-table', '/home/user/Desktop/sym-lib-table')]


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
    io_state = _push_utf8_text_io()
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
        _pop_utf8_text_io(io_state)
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("true" if _run() else "false")
