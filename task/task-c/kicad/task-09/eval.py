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
INIT_MAP = [('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb'), ('pad_rules.csv', '/home/user/Desktop/pad_rules.csv')]


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
    print("True" if _run() else "False")
