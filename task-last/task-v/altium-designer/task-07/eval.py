from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\user\Desktop')
BUNDLE = {'_shared/build_native_task.py': 'eNqVU0tPhDAQvpPwHyacIOKaeDKb4M09Gg/e1DSVDmxdaMl0quu/t+W1ajysPRCmfI/5pqUh24MQjWdPKATofrDEII2xLFlb49IkTebdN2fNWri9Z92lSRMVBsn7Tr8u9IdQRl6aKGyA0CELlu4glCaXL2/bEVfA5S2wHzp8imU5br5s0wTC0kZzhEIFCwuuIBu3G91hNsHav0AtWW+UYPK8n3G6WRU3eNSOXV7MTnFNkTbUMyHmC7JYue2ZzPYHbzHsD+GZD5LQsKseyWMJo5Swh7Esvoc5G04Yjs6sNuXMP42/tsOnMOEw33GcWe6spxqn6Zeg0PG3k7i3Brdr4nALYIL/lZqkdgi7oHlveRenfUdkaTaY+4v6mynG2ZnmccbOr2e1qdHiFOuDNKPA44A1oxLxbubxGq65JMstKF3z71wR9d+ORs5kyXjk/DSEaLxRvh9cHi3LcBIqiFXXQci4+FdJV2td7WTnsIALyJ5NVp74aGqrtGmrzHNzebN8Cr5fqAUoRg==', '_shared/native_altium.py': 'eNrVWFtv2zYUfg+Q/6DxSUpcI277sAXQCjdxi2CpUzjpsM32BFqiHC0yJVBU4iDOf985JCVRshOvGPYwA4FNniu/c+FhYpGtnCCIS1kKFgROssozIR3KeSapTDJeHB4cHpjdv4qM1wvBDg9ilM6pvE2TRSX6FZaGIh/zhC8rwoVkgi5ShgqvLkfBl+HnizPHdxZktj4/ma3PPs3Wg8FsPYLfQ/j+CH+DIawHBEUODyIWO4wX6CgH3+5ZkKXMRfOnyqrnvPnZGWecnR4eOPCJqKSgHxn6gtEoWDxKVriepiaxA2dUTP1CUiGLh0TeurVnntGCH0GTgjm/0rRkIyEy4cbkSanldMWenaRQqih3hqlMypUDSpwwg2OXPHKiLCxXjEviNcdQ7qRwCD7oHqCQwlgWDILCt/3vRyzMIuYSrYD0HIZOFT5JljwTzDaUU1GwIE9yFsQJS6PCLdgSvTlFQ8pglIRyCose7syN7awEjjYFoHx61tQ4E6hZOgl3jL5+kaeJdMmG2MAByMQnCp2EKxGLiJ8w43CGkjW7dz3nXkVN1Dp9OOLAa1jAuekd+nPfAgq2rURZS0FDGRThbaBCwcHJogt2mhRyiseszr07v4xtCUrBajd4hrpIs/CuUPR+nPAogXx3rRwis81kdHY1OfcHs03/6IP7wbd3NvXi3U+4+sMjvUYaTVvLOKXLwgdD12bT+NCc9NQ6G/g0nTeRW1EZ3mI8tMdWRNQGcCuO/lJkZe6eWMDrFNLR6aSVErVYI1ZANlIJ9nxVlA3pHutoaxdcxzza2le5Jlborw2sBed7jedscwMg+e70z838yJttxlCbenUMK0gh7WInARHYQHnUc7Ca8XBiZc4+8HrW6q3XFsUOoiR8h6jeQDq67cM2dto8LLXVnGkQdilq8NmlCuAOVjr3CkZFeGsD9O79FkDHFUDndZwsjFoFrFR3HGpFVzHUiLUiqpMRO0dbnsCFIVhMTk1K9ZcM6vwyWUxYzATjITSxXkeksQlizaLLdq8joYHvEsMK3wrOLsMaSIHMgoRLt+VaFqrrsP8b8bY8e9wn9PsOISghwB9SuQDpp+cuWdCHQAUDqOrbYnj+P1RHHf2pfdT5FNXMX8jipn31aZ4zHrn1jtdq9Q1j0/Gx0y8egyYzus2+uc7sjt+56aqGaV91aA0RfuVOsYFrFQfy6Wyw8nerwAyhgz7ecw1xbrTtv/PycBEoeM3dvPvas277f3HrGT+mYEphhd8AFQpV1/dsfXJCPDULbIgZGea7vRZlyl6+pJtZpHJc8Z/u5Ohcesav1yHqji6Tb5ejXy7G580IA+x7JxjlVJXAOwcwrw2eEtgNyD8YXbZRQaH/EJXrq2+Ts9H56Pri83h4czVpoeOAVvJ1eHMzmoy/Dzbl9ffApgR2w7bIqIgqyRfbgFUBrye5VrRnIK7Hqhca8Uf0abZRPRcasmfPf4ampz497Fkznh0Ac7+UOTxc2A6YsMSOWwPcwOvgpjkb4NBZEBeFVPVn4dVzjnoqO++ARb0Y9DWgfjobNamZgW0HtIbBKlVUE6TZA8POWG301Ub1LEP1NQsuKnI9brEU3mLNjIjQo6puHjetpJO/SNAduSpvgJwQrzb0g99xdm/qGteM3+Y5qMCh8ABsDI6HX0bbxhrR/a2laRitkGo4WgGlabrVTrfjua+VIOOLsap6v9BBeCUCCvdXQYfpFw1Y9wIMVPgPh5b7+FrXZdh97KtX8oOAolMdzEXRflRCh3BRqAfORdDR/Le96rajRZgk/icK6eRByZAZx5c0h6d1wpc+KWX85kf7KV1NeGpmsStAuQKUdr7DifXsD+lgbW8FTXUf8bhNrm0ZtNk6ZLm0/gvxksa/AR3nVXA=', 'eval_inner.py': 'eNqlVk2L3DgQvftXVJSLDT3OBzmEBgcCO2FPS8iGXIZBaOyyWxtb8kjyfND0f9+SbPljM9thmD50t+R6Va+eniXVRnfAeT24wSDnILteGwdCKe2Ek1rZJJnm/rFaxf/20Sa1h/bCHVp5E3FfaZgkf15+u4QiDFLKLVvKnOUGrW7vMM3yXhhULqEkucfnUlk0Ln27A+tM6tFTCLwBxu2B/lcsy5KxpCJed8hF6+TQxcK2PPCbR16hlQ0FaAPwGpS+FXu4/PD2fZIkFdaAd6LlenD94Gw6/vJKmgwuPkElS7dPgD7Lg9jEKnRpI8QKZbnvgSJXMKKtbSnb1jPhTrdohCox/7s8/KFLFpCNi8AgF0EaowdVcWcGd2B+Ah96LB1WuZd+RBkM7RZwZL2wlu3hi2gt7qjgXJ4mvY4r0qckgGVNkriZc44P0pIQ2dj2kv6KGRS+5DUVqmcaU4fgFxQ6aa1UzR6OMd2JrdKQndSUbaztzONSZs5YBFflrRaVTSdFSGFBKuCDS1GVuqIqBRtcffHReyCmKHXXW8L/svBp5DPG4kOJvYPL8EN+BmH93G9aHpS4oSadBvKm5xp7p3LYkQFLapzSnO/Z4O0gTWgzdnzFZjdsabPrAKm1uZFVhWqDmWdXADshejIkmjvcAOIkJ8MPv1YKwGkFvYbEGKvUoksjZXolwI+DzJPsZJ+46ufVi5lXZEnHpyScIs/LSN2vUu0g9OQTxi5z6bDb+LjR/h0J5POG2ljDj6cszLGQhy2Wov487lUxVliy/U+j6SYgMGXHpdIp/xGIlgehGjLBoOL6tI/7UOlIX6/MaQf3gva6Y6hKY7bJm/2Hxm/lCcmkmt13Vp2rBXlNthFGdOjQm2vU6Ht065M6+VIvl2mu4e1FzigPT8rjv1+qjtdlfpmeaZeVOKvZMwL5vZbqpX9p5Tdolr1YKugGO+Y1WCKdgiBgUW8muFvL90y9IqtwunhO382Amyf0+pY/x2dXycJz4XFvpHMYhIbjtLfM+8qJ7VYgpdWFE4aU9OydhRZrB/fSHWizWFrbz3nmxdskYqJtQRvZSCXaaX+oJbaVnfeIagq/Tp5oPKEV41yRenQFKgq6dPBOSMU5G5cs3opMQywtjkqJnhSIU/ln0wwdXVm++pGJt4M+F1XFxfQsXR/SU4Rp/ClGgSGND7UTmIgPrffl5tbiA/LV0T6dAZKyh6O0GsjE6Yjdkf1IKle83wEq6294gq4lsgh3hmlX97cwugjQ9cv7dgRGw5MFMkCKhXdZ8i+BVjwc', 'ground_truth/expected.json': 'eNqr5uVSUFAqyc9JLUrMS06NT6qMT0ktzkzPSyzJL1KyUqgGyQNVBBmbAHlKpqpKOnARS3QREyOQiCGyGmOoGpBALVhYKS2/KCkzJSU1D8mmYqCyaKimMCMTuAHOhnBmoKEZQtgYzvQxBJsdCzG7oCi1OLWoLDW+LDGnFI9vIC4NSoUbA7IUKBKWnIzu+KBsdC8HZSCJgLUF5SC7GCjgbIDsVpBAcmpaErKjgWI+BpBg4eUCIgA5B1FG'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('oscillator_core.SchDoc', 'C:\\Users\\user\\Desktop\\oscillator_core.SchDoc')]


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
