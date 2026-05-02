from __future__ import annotations

import base64
import importlib.util
import os
import shutil
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
KICAD_CLI_PATH = r"D:\kicad\bin\kicad-cli.exe"

BUNDLE = {'common/__init__.py': 'eNoDAAAAAAE=', 'common/native_kicad.py': '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', 'common/sexp.py': 'eNqtV0tv4zYQvhvwf5hqD5JaR9nt0akXKIpsD213F92iQBEHMi1RazYSpZJUEqPtf+8MSUcP27GzaA6OxHl9881wSAVB8IuQomIl6Av+2CiutaglNExprqCoFfwkfmA5FKLkGqLkTmQsT3W2gUvwL022hsvpxL/lqu1EVZ13L3pbxcl0Mp38qFhVMQVCA4OfhW5At2vNzXw6AfzTiAP/zRfATF3BPxBGoV38GsI4dDpWYnW0UUJ+Ri10v65LfJBtteaKAn2yMoyiOOR1uy75xV9tbXgOD8JsYLUMVsBkjg/LFXCdsYbrBD5ZR85qjT/TianvuETJe+vZSRQ3rZLoimkoypqZSyFNQumYfYWPW7Op5XRSWunDptYcGVXaAC95xaUhLsy2QZ7KcousuGSQrSAIppNCYbZpWrTokacpiKqplUHosjbMYL201yEXSIaXfy+3xMJ0kvPCVTQy/NHMibMYLt4CwfGkY5yPpIFOh53g+L3y6YDZcDB1c1Hye15aB4mFSD4aWEBqvSgbKPbLib4TTfqgI7/gXTWJxZRSMBINkKZIxDloScpZBXXRg9VPQJ/EV7cGBTe3R9A+bLD1cVnAd1ByGaFC7GF464Q1DZd5NEwo7nSOMYC2XdqFkLnNWtY5n8GGs9zl3uX8h+BlDpii2lo2jnYSFslvhxX5Wc0wYtYqLZCdbUeIKFBbSG2YzLiPS377+aEOCew+GSnfvL6dueqQ0K/AYuGwdy7ob2uhk063TtMlQ3bRsbSigza2sZ/IsfqOnbjPHTIwJm4GKGJtiS2EOwFL/L6WvMfmr11HOwZzgSwZD8nyi8kqQzvKzQvL5YA+3ICnKfTV9mjc+nO5D8viM7ZOLdHO7OnpOOc+rtUa9N0Tkh1/96xs+Uv5e4cprCJSh/vYtph1fn+FrYhd6Y07uiS6GBcq7pikxqUIgG5pn8kYN9y3J2j0a/Lmza3LJiuZ1rtd7o0pwzTFY86kaaR5Wcygmyy9ACRKNKIk6WhZ4PJrCrBzuNvRJO07cePC27iJ4fzGo+pk6NFJbpz27VCOnGSJ0Lph2ARj4x6ubxbwZijkJdlSU4RX4RzgFTYP8prVlR0QkbInG049zQoe7zs+noLtuiFo+ArDLGV4AOAJkJofsFnjNL/r89wbqWOqHZDhZPXM+bBvF88UQDGBbfo7tf61UrWKglZiHBwBeGhff3gX9Fw+V6wnsqPw8Aa0FqlLhLbxCKszDs4wdmdx3/yAEl2N3HH61Pu90GMOcbdwvCqMauqy2dsCwyoOz82ucX5T7biyxyr1gmodq5jhqhKSUc0oweCI92FucfiS/TQ+sfvrvePf2o9uAHtF8CU8vwzBqTKs2+JgGf6nEWRBLJcvJkw+mhPePfgdfX+HOETsKJlBaOyjoceAHgN6IhT299/kM8dT5NHMKEwcf9lsDL60CcIw+bMWMkLw8XlDrcsyOxfsiV53fRQcajE7APZmJd1kdgUR5/SKv9SNm7I7kmC5n8qB88FekZC0KN4j/GDi9mOr1zoEfL7XQK9wzGzpU48rkfWM1Xa+18NhEhIC5xhvFyEfvV937/OjVbcfeZFVig9Oavz+2xPzx4w3plfGw0PeQcGk6HvTX92nk/8AqENGEw==', 'eval_inner.py': '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', 'schema.py': 'eNqNVG1u00AQ/R8pdxjMH0eAW/HTUlAjFCQkBFXafyWyFnuWmm52rd0NIgqWOAQX6RU4Cidh9sOx06ShjiXH4zdv3ozfOEmS8Wj+nYkFmrWwYMpbXDH4++s32FsEY5msmK5Ao11rCXbTIHClgQkBSGlrZjFrNpSn68aabDxKHCPXagUVs6wUzBg0UK8apW0fegm8RlFFJNHW8msHmsnNeOR+Fzv4eOQv8PYWy7sgNR+PgA7JVpiTTh1uG1euyuGLUiJE8EeDpXUx4oUpfFQSwxNW2jUTh3GrBGomS+LlQjELP/3DPYxUNpSlqGs4RCvkUBQULYrUoOCTKNIdNEq7Ng5+Obu6SqDm4CBZUAwoDELybvb+Q9LnNExbl3LDk5ttIGiXsPV5rvE2WfbgjrBrGGrjZHrRAx073ow1Dcoq5UmXMd3uEbTJ5JA9DO3p3AEfmcPNM32UeTf2p5NTyvTP/XY//Si5f18nudLtDthOhhTR+gnQ+cJfsm+qlqnPnzzm1H6nYlnLzF1RVwOvGotNwWsx9G/pDG5yELWxNwO3L8kFfmNS8hijQMFpmEpvpg4Z1aLWSgdX7lkW4DlNwbphXF3PL4EzKlqRz4HsXXXmvWi0alDbTe/l4M1gZXj1Bmpp84PBmPUqLTsbu29DSbgw9dDN5EQFqywT/ykgUKZPpDOl0tjT+fXNj6yIGxTQGZ1DGmA6hfMHDon1z7Pzw6YHq3s2oBl+CWgwK6Y3vRx6MYMKopYYl/uavBHXOtqkzeN9qNGebfsabXRJfD0AqW877pj/n2evObl4+UjrD/r0SvpNAJgvFp8WnQKfsbdUx17yKUrqOy0nR1bqs4y75OEE+AcnCfRs'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb')]


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


def _apply_runtime_env() -> None:
    os.environ["KICAD_CLI"] = KICAD_CLI_PATH


def _run() -> bool:
    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        _apply_runtime_env()
        return _is_pass(_call_inner(root))
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    print("true" if _run() else "false")
