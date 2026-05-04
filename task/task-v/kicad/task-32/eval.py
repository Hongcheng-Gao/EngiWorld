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
INIT_MAP = [('footprints.pretty/LQFP-100_14x14mm_P0.5mm.kicad_mod', '/home/user/Desktop/footprints.pretty/LQFP-100_14x14mm_P0.5mm.kicad_mod'), ('footprints.pretty/LQFP-144_20x20mm_P0.5mm.kicad_mod', '/home/user/Desktop/footprints.pretty/LQFP-144_20x20mm_P0.5mm.kicad_mod'), ('footprints.pretty/QFP-32_7x7mm_P0.8mm.kicad_mod', '/home/user/Desktop/footprints.pretty/QFP-32_7x7mm_P0.8mm.kicad_mod'), ('footprints.pretty/QFP-44_10x10mm_P0.8mm.kicad_mod', '/home/user/Desktop/footprints.pretty/QFP-44_10x10mm_P0.8mm.kicad_mod'), ('footprints.pretty/QFP-48_7x7mm_P0.5mm.kicad_mod', '/home/user/Desktop/footprints.pretty/QFP-48_7x7mm_P0.5mm.kicad_mod'), ('footprints.pretty/QFP-64_10x10mm_P0.5mm.kicad_mod', '/home/user/Desktop/footprints.pretty/QFP-64_10x10mm_P0.5mm.kicad_mod'), ('footprints.pretty/SOIC-14_3.9x8.7mm_P1.27mm.kicad_mod', '/home/user/Desktop/footprints.pretty/SOIC-14_3.9x8.7mm_P1.27mm.kicad_mod'), ('footprints.pretty/SOIC-16_3.9x9.9mm_P1.27mm.kicad_mod', '/home/user/Desktop/footprints.pretty/SOIC-16_3.9x9.9mm_P1.27mm.kicad_mod'), ('footprints.pretty/SOIC-20_7.5x12.8mm_P1.27mm_Wide.kicad_mod', '/home/user/Desktop/footprints.pretty/SOIC-20_7.5x12.8mm_P1.27mm_Wide.kicad_mod'), ('footprints.pretty/SOIC-24_7.5x15.4mm_P1.27mm_Wide.kicad_mod', '/home/user/Desktop/footprints.pretty/SOIC-24_7.5x15.4mm_P1.27mm_Wide.kicad_mod'), ('footprints.pretty/SOIC-28_7.5x18.0mm_P1.27mm_Wide.kicad_mod', '/home/user/Desktop/footprints.pretty/SOIC-28_7.5x18.0mm_P1.27mm_Wide.kicad_mod'), ('footprints.pretty/SOIC-8_3.9x4.9mm_P1.27mm.kicad_mod', '/home/user/Desktop/footprints.pretty/SOIC-8_3.9x4.9mm_P1.27mm.kicad_mod'), ('models/LQFP100_14x14.wrl', '/home/user/Desktop/models/LQFP100_14x14.wrl'), ('models/LQFP144_20x20.wrl', '/home/user/Desktop/models/LQFP144_20x20.wrl'), ('models/QFP32_7x7.wrl', '/home/user/Desktop/models/QFP32_7x7.wrl'), ('models/QFP44_10x10.wrl', '/home/user/Desktop/models/QFP44_10x10.wrl'), ('models/QFP48_7x7.wrl', '/home/user/Desktop/models/QFP48_7x7.wrl'), ('models/QFP64_10x10.wrl', '/home/user/Desktop/models/QFP64_10x10.wrl'), ('models/SO14_3.9x8.7.wrl', '/home/user/Desktop/models/SO14_3.9x8.7.wrl'), ('models/SO16_3.9x9.9.wrl', '/home/user/Desktop/models/SO16_3.9x9.9.wrl'), ('models/SO20_wide.wrl', '/home/user/Desktop/models/SO20_wide.wrl'), ('models/SO24_wide.wrl', '/home/user/Desktop/models/SO24_wide.wrl'), ('models/SO28_wide.wrl', '/home/user/Desktop/models/SO28_wide.wrl'), ('models/SO8_3.9x4.9.wrl', '/home/user/Desktop/models/SO8_3.9x4.9.wrl'), ('packages.csv', '/home/user/Desktop/packages.csv')]


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
    print("True" if _run() else "False")
