from __future__ import annotations

import base64
import importlib.util
import os
import shutil
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
KICAD_CLI_PATH = "/usr/bin/kicad-cli"

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
