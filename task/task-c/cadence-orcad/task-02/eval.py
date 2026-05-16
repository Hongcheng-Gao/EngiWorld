from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': 'eNqtGWtv27b2u34FR+CiUqoocS86DL7zijRNsA5dUixZgAvHEGiJdtTodUUqTeb5v+8cPiTKdpzuYvkQWeR58zwpSil/YHlUP5FF1RDJxP3h8ZsxKZnMHjhJqqLmpYCXqiTiK+c1ETznCb5HlFJv0VQFieNFK9uGxzHJirpqJGFlWUmFJTzPrH0RVWl/N1xj1kze5dncon2GV8/7+ey3MzJRLz6QznIgHEQNF1X+wP0gqlnDS+mdf7o8uY4VaEOnh69n7/x349v0Nf6PbtOD4N2f+HwdwML0jM8UCL6/o96Hk+uT+NePF/H7/16fXQGF0bH68y5vzn67+vny8jr+9PHXj9fx59NrtRsde56X8gWJ84qlPso9VhIGY4/AX7YgoLHSJ+KPmZDCNzv413AwT0kuqpKrNdk8bW2ieSIkLhR10JelseSP0udlUqVZuZzQVi4Of6BBoHD5Y8JrSc7UA8+HCcK3yK5oHPOmqZo4pmOyoMgGxGwEJwuW5XBqY7Lia7q2+iV5JbjPABaEkSGZd78anpvfYBKwyNuQsLmIZeUsj/jh9wE5/InMK1j2HEEA1GfkkMwD8uOEFOzRxxV4O0DCHanAyKFEjJvqq/DRCGMiZKMI52DcaZolcgoroWY8m2lW87xK7gU6BI9EnWfSb+iVBKcFaqwgpydX4C234oCGBIlqOyKP8TNkgdR0pqAwOhR5kpWGz3Q0nvX2ThjIW2jeBZPJHfD20d2AmYIPetDF3EIKzhoEXdDT8/c3J5/GIN3tagUvt+s1iuqvrJ+vd1B6WGQly7eJ3Zx/vNDEbm79y9+vb4NvoFVk5Q5KECVIBx63viX2LeRMRLA8931tm1ArHnZSh4Zn4ISKsk9Vyqxsee/LcEQRqyEVpf4AcjV4wz+KhwyenpXSsI2WTdXW/igIwh3Q5+/jc2r811fy7YW/0aLfdChWl/1YqKaDo7R+DmPdvQU2teS89NEGAfluQt46Mc4yiOMblrf8DGPcX1D+WEN65il5CxHDwWSp8kwBLl21ZUpWHa01Ddz4xDUTe9UDb8RdVcm4TiQCj8lmZKhQVD+1NMYKbAn+g3ENSNPeWDPNSam9AaItMxuIgskB8ktIfItx2DMIyJHD7QAzd3Rss4Zoi4I12R/c3xfVSviNVfKnSlnwAM8xYc3LJkvuwIKDLACUMQcoBt1JWFDrpauDAwAICR3YEjxgy7ZBqL2wRjdUNtE+OUPd+OjNWpumZkJADUBRUABHkE5KcBSFP2Q5w3S7q6y9xmQ9ejMb1i/FZY+H0bIChyrTLGWSE+wMxCLjgsg73usGdi8yafxrzgVWBjhK35APyT1/muSsmKeMKPfq9AYrDH2hj3CKhOLT2NoKX3ukPobcGNUwvR+6UDYmDYxxRAdi8+g04IZ1HfiCcyni0TGsxx3Uc3gvnIpDtow7ewug1sWvBrF1Gzs16It0xVwCl30BEJKvrNwP0tdaWDXxUDfVPOeFxcGNPjRMmrKsVarChY7Tdj80XdDelRJITxK8RKjiOSZASCerjuJai61Xe7Jr2scmwBogCIw/srpDdjR25ACZAWCqa8YMJUYo+z4sSlZ5G+ELBUWqJuUNBuaG5Ej3FUK8mnVyK+J2kQb7ax6qA2ECnQpkJdDG901iCJWH/AB5w+89Wy3+W69pTzYrG6UVNMbci9IB8RkkViUU/g7IT8hrvFW+ntF8oCJZAYn1LiMg6aEF1MqG+ipRQMt778a+ZWxcHAeVuGpl3UJ3rZ9xmjVdNteS9xt2hnBA+ylCwbJSxNhsA6SDdkSokGye5VBHIuyXqQLWIxEKsAVeiSSClQFcwZmA7noXrN2L5OMQBwKB7SQOGxpwKa3AakqCbewiSpgUmlbe0edkBzTD80X0nfI1XM1nExgnMIdDGjpnueBY3zpZqerRXWtDbuqKJv9fmzVYpMCTrdlDx6bhht1C1ybDkMVCZentGLZ6eacUPAptgGnKaY20iAQnS/RYVfHIypJc0w1Suj1SFD3rNkBQT4JWl65Xw81MqFkPkgPxMyAPR1ImHGFD5akBQKUIGS259J0JLRgkyS0dKKB85Y2WvC1xRGQQIdTbLaxjr51SfBOvooXyPefkl6vLC1LNv4AJn+NnXK2zjXHWzjRL+ZxlltI1zFL+Xbu4XvwNhrGJQs3XgN+74Z6xOyRKGjEBznXOEk47xejnqzqDBW3qsicNatJfLt+T08uL00+/fzj7sAWyXy+TWEhaQYuFmHlV3UP1veeE2Tsazds6dV4tX3KHPq4iML/0A3jEAhIG+ZEML0b2CrewmQkPtS1tdOVPBGpAnhN/9TynNZk/QTsT7D2g4S0JVG5g6lwLDPPF3zu4vvgsdVMwJL2RLv9f2kArtjUMGAxaNN2UGO49ihICB47hJLPnxucxeeGU2hJDAUq7ufYZuo3Rs+ClFHgT9Jis9/mP5WCM310GKl5aeG/QK8IyNou+a4vAcxocVRGGvX1I3Mamb2g2emgnJwxcRR1rhXGtx21IZLrBGUDg/WNsbGEhtQI7gFX3YqGWcgNi81xeahxNzTnKSuhospS8Us3Tq5c6QpPKzQ2danUdJYKXuBoufS5RnZp1B9cPiG+7t7Utw2TlsFoHNHhGKgdK93wvimXod9JliwUcstKM6LROdFr3d0niNpZKrG3X2j2WhRuD1bDFsKUZiKhBxnGMf9zMLq/vGsfiDlNY37C5s4kCGp/85409FMKa27AzYtnK0s2He2vafwiNvlR4GzBIBxz6yW1E1W0i2nXj3gea3eSOJ/d6fzrQ3Cpq6ufRRlN7ZCsXpGOQmgs4Djq8haN4oeFOp86HEKkSqjpXc/MxsJ3h3bTlJs1ha24+pWgKqmbiTUnCapZkEj/G3IGEwxuW0fG/tm5Zeh4zb0cl9eBgYgiXAj/PTMD+cVwwSKgxNV8uzBebZqmO2l0TT8I0vDXe2RmI6KRZtujAn/GtsaNUHbE0jZnZ893BwEA0S6wGAKgrLb4bZBzVBtMd7kXOJGFKCl7qqu8kaVvUUENDiPAUuE3eQB0uVb1mIsmyiZpOTCUGLXBKkP6xuiHTraXyq0A5HRkF3l/Ef2zA', 'ground_truth/osc_measure.txt': 'eNqt0T0LgzAQBuC5gv/hRksxXD6NgoMVBaEqVOvu0LEgpVvpf2+iFArNUMQMIeHeuzyQ7nGdYBrv4w3yrCsgBQq+t8vL45CdEniawysFQIJmFQdEsOWhrBpbHoL20u/TUJA4jvVcznqgRNpwiMJG66pJwGzBEjZpRWik5Zwuz239PbxvgS03021e8r3uB8hcwE8XZRsAJdFKsdVA7gKKbYEcabQaKFxAtS2Qclz/xdIF1NsCkWv9J/ANJJ+vkA==', 'ground_truth/stabilize.json': 'eNo9y7EOwiAUheGdhHcgnZVACwiOmvQRut7UFiOJhaZcXYzvLhHj+p3/vChhrLn4jHCG/gRr3xyZ4mL39eEa4niHodheceec/fkSYlXNOyEPVdPTb/mWEsI6YRkNF51tldStM0ZKq2u2eI8ZpCgR/C8lx+3haxFhGuMc5hF9LoOm5E3JB3hnLQ8='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('osc.cir', '/home/user/Desktop/osc.cir')]


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
