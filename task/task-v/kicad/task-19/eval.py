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
BUNDLE = {'common/__init__.py': 'eNoDAAAAAAE=', 'common/sexp.py': 'eNqtV0tv4zYQvhvwf5hqD5JaR9nt0akXKIpsD213F92iQBEHMi1RazYSpZJUEqPtf+8MSUcP27GzaA6OxHl9881wSAVB8IuQomIl6Av+2CiutaglNExprqCoFfwkfmA5FKLkGqLkTmQsT3W2gUvwL022hsvpxL/lqu1EVZ13L3pbxcl0Mp38qFhVMQVCA4OfhW5At2vNzXw6AfzTiAP/zRfATF3BPxBGoV38GsI4dDpWYnW0UUJ+Ri10v65LfJBtteaKAn2yMoyiOOR1uy75xV9tbXgOD8JsYLUMVsBkjg/LFXCdsYbrBD5ZR85qjT/TianvuETJe+vZSRQ3rZLoimkoypqZSyFNQumYfYWPW7Op5XRSWunDptYcGVXaAC95xaUhLsy2QZ7KcousuGSQrSAIppNCYbZpWrTokacpiKqplUHosjbMYL201yEXSIaXfy+3xMJ0kvPCVTQy/NHMibMYLt4CwfGkY5yPpIFOh53g+L3y6YDZcDB1c1Hye15aB4mFSD4aWEBqvSgbKPbLib4TTfqgI7/gXTWJxZRSMBINkKZIxDloScpZBXXRg9VPQJ/EV7cGBTe3R9A+bLD1cVnAd1ByGaFC7GF464Q1DZd5NEwo7nSOMYC2XdqFkLnNWtY5n8GGs9zl3uX8h+BlDpii2lo2jnYSFslvhxX5Wc0wYtYqLZCdbUeIKFBbSG2YzLiPS377+aEOCew+GSnfvL6dueqQ0K/AYuGwdy7ob2uhk063TtMlQ3bRsbSigza2sZ/IsfqOnbjPHTIwJm4GKGJtiS2EOwFL/L6WvMfmr11HOwZzgSwZD8nyi8kqQzvKzQvL5YA+3ICnKfTV9mjc+nO5D8viM7ZOLdHO7OnpOOc+rtUa9N0Tkh1/96xs+Uv5e4cprCJSh/vYtph1fn+FrYhd6Y07uiS6GBcq7pikxqUIgG5pn8kYN9y3J2j0a/Lmza3LJiuZ1rtd7o0pwzTFY86kaaR5Wcygmyy9ACRKNKIk6WhZ4PJrCrBzuNvRJO07cePC27iJ4fzGo+pk6NFJbpz27VCOnGSJ0Lph2ARj4x6ubxbwZijkJdlSU4RX4RzgFTYP8prVlR0QkbInG049zQoe7zs+noLtuiFo+ArDLGV4AOAJkJofsFnjNL/r89wbqWOqHZDhZPXM+bBvF88UQDGBbfo7tf61UrWKglZiHBwBeGhff3gX9Fw+V6wnsqPw8Aa0FqlLhLbxCKszDs4wdmdx3/yAEl2N3HH61Pu90GMOcbdwvCqMauqy2dsCwyoOz82ucX5T7biyxyr1gmodq5jhqhKSUc0oweCI92FucfiS/TQ+sfvrvePf2o9uAHtF8CU8vwzBqTKs2+JgGf6nEWRBLJcvJkw+mhPePfgdfX+HOETsKJlBaOyjoceAHgN6IhT299/kM8dT5NHMKEwcf9lsDL60CcIw+bMWMkLw8XlDrcsyOxfsiV53fRQcajE7APZmJd1kdgUR5/SKv9SNm7I7kmC5n8qB88FekZC0KN4j/GDi9mOr1zoEfL7XQK9wzGzpU48rkfWM1Xa+18NhEhIC5xhvFyEfvV937/OjVbcfeZFVig9Oavz+2xPzx4w3plfGw0PeQcGk6HvTX92nk/8AqENGEw==', 'eval_inner.py': 'eNrNGV1v4zbyPUD+A0/3ImEVw7LTa8+oFzjspneLtodDunkKAkGR6FiNTAoivbUR5L93ZkhKlCK13gR3OC+yJofD+ebMkA6C4OpLVu0zLRu2gb/HMs+Ki8tvWPjLp3/OE3ZxwT5UMn9kuslyzrSsZSUfjgw2lUWmSyliVmSlOl7k26wU0SwIgvOzTSN3LE03e71veJqyclfLRrNMCKlpkzo/s7BdprftRHZwdYTx+Rl8zWpAmZVC8UaH8xiQDORXWYrQTYqyEdmOh8C0rIBlFLNgNguiyAqj8i3fZU6QD1ueP15zta90zNAAZmxxc7nbSTFT/FC7DXXWKB6zTSmKNKsqHDVKo4Cf//HLj+mnj2zNAmc7MMC/rq6vADQpHe48Pyv4hqWKP6Sl2MgQBtHq/IzBR8Fe4oBA0ETprNFBZBb5YJGLwi0dElyrZAZrt8ldxMoN0MpEwSouQhWx92u2ZLxSnM1nc7Pn6O9ZnLbnsGj3cMeHt3v4OB9/z+K0PWKgquCtFWAIi6XQoXASiJaaIGoLS81saDgEo2BhI/eiCA9JzJYQJGZ27M0Oi96anQFD320wTdGnqZZpWYS64RAfCHA+xNMkQMA2aCyOUcIi4Qck72Rekg6lgnDXmcg5aLe4i5nSTUQrOGXrNXHyaHgKtibpqf1vKfgg6IDpg96GLv6cSGgZtAdagXzmEG7nKIibJP5k4U+Wdz3OeMBn22MtNRiWXRj6ODgmvj132SEVsuBpwR/ATiiWciJBTrl2xA5M7Hf3vGFygyx3XGjF1DZrSvEAFmJwGmpIDJqFBdc8x0U4PKCGoQs2XtokRU4y572qABPTkjvvIFIGCaEoc20Qc6GJRgsOgUfUeVqhp1Fmzymw5xbOFJkNHXLH3q1Z8mKdjAdW6623xjuEgDbDHM1VGFGcoywust0/suGmThu+CTe1H4P5tqwKisO6H3RekBFOzKpSaRNmBBjEF3JGMCiEERgAK95w2B60547WzdkbbPZ0glg2iF2QTrGoG1lD1j+OcVh2ggIhQr9uJTqF++LPuIM5NT/oE5k3r2NuVzAgrRfrrMDsAm6MGY0p3r2z8EOJiQDyX1ngKciYqnlebsoc0d3xAIdn4H+pazgZ2ot4CAlE8xMTcgoAOJaWAGyTKWqMCgCEMi4obacDEd2ny96A08/eHpMXWXvafKekNm7aGR5i4V2ZxHnx3ivyljymhA4Y6kw9Qh5f23KOGZfXVK3XSMhyRHGlbss6P8CBUcTJ172Z8aaRyGATyL2u95ohIdq6wZrCMs2ecNdz4O0y2jSoCM51c/Ro/lbqLYPDIAw3lim2GRgKYxV5zhqeFaFnaKw7sEA9TIhYrpE45LzW7Iq+IPshUT6hB21mNF+xJ/5Hgv8VKGK3qClGP31UNoNWaGAgNl46gw8//eiiA1FraBz/BD39z/VVEHVsqatjyYrBGvE2/rH+nuW4rGZZDVYsQq8FDDtdkM+aaCNXsz+Iu/U6U4oX69AqUypyKkZg5GFB4wj1BPAw5IlmgTL5hMA8+6xaGzoWHr3QZUG6oJ5v1gdonKCTtfrX6UV+GNfN0HuhH2ba1oLIhWGh6vFH6Go6yCBtYRODjfKt10JHXTEetl22WQiiuy7IHAXVbWsJYxt8e0m53ch61w/Or9hrtLobendpInULxw4SQsUzpSHNtk1NSDcqWt6BV8u64tHrfA8kUkd2zPNU26w5TA4e9zqVARR5jJj1eo/WZGBfdoHdUz9xpF8f5Kcq63xICieTCietoC6ApnVuSU7q/c2KfcTbMjO+vYBjZvrTX/eCOlAWUosLjbBrWAGGJv8evWKIYasMi5gbh11za/lXJj2ZojSpk2bMfo7795NhMtQAMW00x5RXkEc0YkdLetJ6f1ux6/Tz1fXPXWND4YP9TJAE1lTkLOwpCLxwYGsRaOmaHXTKYD3TOLimCEAjWaNlNOyNvGbb9J4k2LD389lt6v7aPdTpRy8jdrgj6e8kR3bONNJgK6lSKVJVV6XG9N87EZ5Xf8jgPjFY6hz6wujUxQxJWScGbZvjI0Su5wA+nl51kpqLfNv1tlaI0aVeF1Mv/gh14aOioql8BNzQMgDP2podexnZ3HUs4QmUl80oqorbDOW/rC2B6H/nLavflL+wWysSdwQWGP9FuaHbCfVkUFrsMVk/dZo+x3hKDARm0YR7DfH1k1H/ma4oC5iSDZ6HLu+f329X7LPUWUUJzTw/YHJI5vPdzja9uJyCCPjusN+FvYcKr7i/Mc8ZNoYufKUkwViy6+Qxcs7m7B1L+MVyPPMZJNanZQ1nXpNagvSo5PXosuIN3sXXwGOeTKbA77rC+Y7MmMvdfSmgEXvP5ixUcsf1Fp9CIIcAR5Aq8i0Lrj7Bsm0de1sVrqUqdfmFWzbT9kWpQPyJGsxOMChQ8Az60mx/X8GVvZJQENokBqfgZhGzmyX8XUYYxtCHNG29hWg2JHAXZnps9p6Cm0UA2eZmSf9fBs+ufoAoKWIi1vx1RQV4YHbr6kqv3uAqZlYg10o0KDa5FLoUe95BT77sv+G6bh4s23fYtl0eucb7Zuo/hQ1q4tdGHTbeS0MYE6i9v40FXM9TazZ+jpcvg83bNxlkyXzFbqCDlfsm58buyu9J2pDaJyilPWlgdaq+/62ggQIV3CTB/3GsmPozEi9DO31ufIHfGDPGTelN4iJmcIu1EdOTYTRBgcvRbp2jR3JVYBoiNEpfKXrHfdkydcHlX3y7F67UvCup0HynRdnQWxf+DDUL6MULH6mtTfHJyPs1yvxw1m4E993LrClm9PtVWuf3zpVIrvee1n94e+rUDOz7WbACH9gx3rlz2XCC0YiCCa1KIDOMfSKYyw0JHOFvW/jgRBAa+cjG07B22w+JpwD9C/B8hgOfZ+54AmHrPoK6yaDjYYHxHuGYYYxC2kpN4HYWkxctXxg892nRSzyeLRei3fKdrxWU5l3WHI3NzDh0OerZxABePsyDWEo3jxRugaVI06DvbfzlNGsevuD7tH3LdSA4jHCvNaE3dL2lgYkm7Pu+kwfC4Hd6l4pM', 'schema.py': 'eNqNVG1u00AQ/R8pdxjMH0eAW/HTUlAjFCQkBFXafyWyFnuWmm52rd0NIgqWOAQX6RU4Cidh9sOx06ShjiXH4zdv3ozfOEmS8Wj+nYkFmrWwYMpbXDH4++s32FsEY5msmK5Ao11rCXbTIHClgQkBSGlrZjFrNpSn68aabDxKHCPXagUVs6wUzBg0UK8apW0fegm8RlFFJNHW8msHmsnNeOR+Fzv4eOQv8PYWy7sgNR+PgA7JVpiTTh1uG1euyuGLUiJE8EeDpXUx4oUpfFQSwxNW2jUTh3GrBGomS+LlQjELP/3DPYxUNpSlqGs4RCvkUBQULYrUoOCTKNIdNEq7Ng5+Obu6SqDm4CBZUAwoDELybvb+Q9LnNExbl3LDk5ttIGiXsPV5rvE2WfbgjrBrGGrjZHrRAx073ow1Dcoq5UmXMd3uEbTJ5JA9DO3p3AEfmcPNM32UeTf2p5NTyvTP/XY//Si5f18nudLtDthOhhTR+gnQ+cJfsm+qlqnPnzzm1H6nYlnLzF1RVwOvGotNwWsx9G/pDG5yELWxNwO3L8kFfmNS8hijQMFpmEpvpg4Z1aLWSgdX7lkW4DlNwbphXF3PL4EzKlqRz4HsXXXmvWi0alDbTe/l4M1gZXj1Bmpp84PBmPUqLTsbu29DSbgw9dDN5EQFqywT/ykgUKZPpDOl0tjT+fXNj6yIGxTQGZ1DGmA6hfMHDon1z7Pzw6YHq3s2oBl+CWgwK6Y3vRx6MYMKopYYl/uavBHXOtqkzeN9qNGebfsabXRJfD0AqW877pj/n2evObl4+UjrD/r0SvpNAJgvFp8WnQKfsbdUx17yKUrqOy0nR1bqs4y75OEE+AcnCfRs'}
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



def _has_generated_python_file() -> bool:
    if not DESKTOP.exists():
        return False
    initial_python_names = {Path(rel).name for rel, _ in INIT_MAP if Path(rel).suffix.lower() == ".py"}
    allowed_names = {"eval.py"}
    allowed_names.update(initial_python_names)
    try:
        items = list(DESKTOP.iterdir())
    except Exception:
        return False
    for path in items:
        if path.name in allowed_names or path.name == "_runtime":
            continue
        try:
            if path.is_file() and path.suffix.lower() == ".py":
                return True
        except Exception:
            continue
    return False

def _run() -> bool:
    if _has_generated_python_file():
        return False

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
