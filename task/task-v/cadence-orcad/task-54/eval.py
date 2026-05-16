from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': 'eNqVVMtu2zAQvOsrtryUbGy5DXoojCiAgabIqQiKnGq5DCNSNluJEkgqCOL637ukJFvu41AfZJGamR3uLre0TQ2cl53vrOIcdN021oMwpvHC68a4JBn2vrvGjO9WJWVgtsLvKv040u5wmSS3N19uIIsLitK6QmGWWuWa6klRlrbCKuOTj6v7Gx6RVqVFU7cIpJasV/Ovm7WYv2z2lwc4W+XuIpf7dzPcz2Uul8cHLvfvD4Qld6v7239oBo3lYv3t6vp1TnL3ZnOB+CSRqgRuGluLSr8o6tWzX4LzlsH8OvwvE8Bf2EbRwXLqukdKrsLqmsziRzaFDS4irBL1oxRQL/t81OnWNl1L3zKWGlGrKdsqLIKJG5itthKFoiS3ucEYBJ8sRT+6pUfbRd3SIBINz6DpfNv5PtBoH37C58ao/hTCOHTXw2ABgRr3t8F0rNoCSPBnJPe28zsyRekSsCmCSKqetfOOsl524r0ktXZOmy3sA+9ARuYkxUHAKoEh8KBUmaKRSMhI58v5BzyqsraxLiN6ixxFGINX2ZR/jLn1/6UTeX+z3FsFqctSWUemtQi5G7KtnkTF+9w52v9zqe2pWaQufK8+ZHi4Aifs5BIMQeKtyWBPWuEcWcInUTnsCXLikBhgEGGHyCsbG8sC2gAlqjKpf/ahSVQl4+vklOFUGOHYK2ObsCMCqxNAJ8rJ2ppggvHakw1KBNBvmJijHppMWfE0gXNvO3X2pdip4kf/bX0UIw9DJuZPgKd5wB6TcLYnHwbbDmrhix2I0isbx89CCq9gbI84s8gsSm+SP13iNMNm5CETOO2yDAjntdCGc9InYByAdotjymHx48Vp0e+4la7stqtxgt2FlR1qKdpUSMnF8I1OSzgg7DZcPwRGmQB1A7m1GilhwKayq1tHz5otANNJF82w7hJjZJfY5MaFwS1coXUWu4ex5BejtNbX', 'ground_truth/eld.txt': 'eNq1WF1r20gUfTf4P4hClxaGseZb435AmpRlIXVKMLvtk1EiJTWrWEZRaPPvdyyNbI11HY3W7ovRHA9zj47OnLnSRVrGyyxNgnkR36bBZbq6L38EN8/BZfycFkG8SoJ/lomBrtN1XpTj0cV0kuW3cfYzL/6dfF7dL81Flkxw+bBe5MVtnCzWRX6TEja5e8qyODHjzKycLIr8qUwTfFMk49GXfBWcrYuAqoDoKQmnjAQ0pHI8Go9maRnM4ocUzfMyzoLN0LJ687DMHt+imllrSg1Akyz2OsjvgmouulyuUntHduZ5viqX90/502MzPS77Zrx2agITPhvdvubLVfkYjEfnZ9fX3xd/zRAVkcIiRJ+u5vOrL9shCUMchkhUP3SDUBwy9D4OfhTp3YdXvypFp7+ep2/M1GpyQBSvLt6++giA7yfxxz9WN4/rdz2LML5hsLeIBTeLDCNPohpTFGuBjiztw1+GgAgNOJy/rKqbv3BID9BnDdN25X3whPL/ObtAnLGK4/zqK6JKW6pYCKs6qyGusSYg7Ug10kRb1h3MW/MI0jxqa+5Dmlvdza9+mbRgXdIN5ktaQLtF8EOkrUdMmYqs+eUNbwtZ2xxZ9UR6zwxMCGI0qtJjI7mxUeVlkyeaWeqy+ldjJnrMLTVg7gbs402qwnuL7IODeNMaUgTTQ9vSu+hh5hoQXB+jN6sRojGnfWFIoDAnv1vwrc15HSAKh6qxOR9gc8ihYmCs9Epg2TNEqRLbZLHX7RTfw17MltYp2sH6mDNog7KDhqHMWKHOwUZ3O3SOUBd7mTwQjMorGHc5Cty/G4sb6oxu87ryur12eLtYz7Om0LOmg5i3/NLB2swXjBLTmPAde3vtNi68j/0uCjQQD3qYZRyzs8Ps+Wl1dxJiGPedxiGge9hlbnQ3hpehc55K4AZk6C19q3YH8zW8AgyvHPoiFFJpSUxQEiWcDWuHDn8X60lKBSWlGto1QruHHbgH8xxMJIakfR/N0ElNF+vxL4P8y4ZtAqc7YmD4/H1+jjiNtjuguYZ2AKNYkZf9I4CtKwZuXQk1/u4rhxdrFgnLmske13PA9b5nFK/bAMWq5s+y3gP9WdecCdYaHVnPKyUhg6j/YRDSGERzdOTTPZHY3zbdodgPdk4wj7xzfZdfAsg0MfAFSULJJNta7zhv+5d6KCIsaNO+qAEpQqHnS09PfPHp7BoR4jZfBGi+iPbPcgV9exj6BUBAJ7LQHfYLRiJzVOqdZSRAXw6g3zJNF/Q9TIHPCcJpfL8jSurvLFW3TrrfXOxL0qHs3q0rgVrSi66sdp67xD7mS5dEpHp1Mi9QEZzb3uW8zkgBnZFioMRWY4E56xFZAyLrE4v8HxUNW6g=', 'ground_truth/eln.txt': 'eNp9kT1vwjAQhvdI+Q8eW8lyfOfYidloy1CpoAp1gCkyiQuoIYlco/79GpIUkaHT+e55fZ8fzpSWvNlm7w9kbbvW+Th6mSV1W5r6p3VfyaLZH8OjrhLmT13RutJURefanQWRfJ7r2lTBr0OaqnDt2duK7VwVR8u2IfPOEcwI6BnwmQCCHFUcxdHKerIyJ0sXvjyM1R9Ox/r7kS5NczDem2YSf7eutI0nN96DOHqer9fb4nVFUeYZk5wi55xxTgE1E3koF3wAKjDHCxYwYC5ZrgcsKGImL2HEEQuWQo9RUND6ikHffnPeY4EU0iE82qsZcSEQKORpj+TYHjKVDZL0/wxpyBB6UANSE4nkUmVaQZgSMinvNZopfacJuS5Lgsk8inEZRxsqRL8IIUaCDEOfm+JpvqYAwx7+tpgzlQ60EJCHynrSgWQ6KLYUYXIg3h/oFw1llzA='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('fulladd_placed_routed.brd', '/home/user/Desktop/fulladd_placed_routed.brd')]


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
