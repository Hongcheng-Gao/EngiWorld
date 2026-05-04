from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': 'eNq1V1tv1DgUfs+vOGteEmjTaUtX2hFTtJRZ1F0oqC3LSoAiT3ymk62dZG2nF0H/+x7bySRpCyxIG2k0SXwu33dudhhj8wsuG24rDUv6WW7ON3d3IX7x9hAWWOYrxfX5FHRTAq9reZ39LfM6X2Q7kl+jTk2uk5QxFi11pSDLlo1tNGYZFKqutAVelpXltqhKE0XtO43dnbk23e2VkilajZjOJSos7SndAzcwPw22a25Xslh0ht/QYxSRgdQtpEVpUNt4sgHG6tgtxgSmkAQlSTWaSl5gnJCsJtPtH2wByyulqpIlSXBi8hUq3vk4WGF+foymkXYDXJzCPcADKKt/+BTmjyc7UXT668kf2eFzmAFDfiaR4sei6OX8KDue00uNKXmpCUusWbz59IN4FD+dfkjpP3mafDAPY6U+q0ImbMPJHr44en08P/j1ZJ5EUSRwCZmtMqViM3XcEtjch6WsuIXPcFSVOI2ALkWOgsfUINf5KjaJXyiWhNWCCmLu0kgpKr2uf0e8SNmbjFV6pqumjreToN3KOhEy1K3uJKmsLlHHCcyItFIMUBr0Yg9hkk529h532CnUXMW6qiyF67RL7gaUXOHXCLlirKEowammy6IUXMqYpVtbAk1xVupGotny1lnSkyOUdXqGNmbOAfMAvau1xIBWG9hWwfUBUg4YG5P3gQpsMPQKxqZZqMIYKutMFLrn0RdJcEhyFFtfjmOVQVEGXyTWK8euDbNCzNrSclWNta/nmatvskUYvWLOS1EIwpQ5mobMvGehRdOFFo4OLw3lyj999CqWayJMkusScMF26i7etwz2gatJw/HZ8qLjiONVYayJk3GY147q0euFRn7eFWcrU5hB7n1AUtS6cmFZMoGyuEDNFxJ9MS+rphQO6yfCcwMxXtWYWxRAFqBawqdbHG4Sdrv6dYie1dcDl1RpLg2nbj4YjAO0xFWHW2ozhVc51hbm/o+y6WbUCHfupoZJaVpiKeLBDIkdmJmrs0JkNO8oOTU3BsXsN07tszEK0peujuuMeZA+Jn+9ekm2eG4bLn19YNKW8IjxD8M71c1/QPdNZKw6Z13ZPgjDFXam8GTQ0PuwkBW9rqk7aEx4UeGKYD0Fbo8AlnyT1xp5ILjiJhsa6Jm1dMkhlaMrNFeS/XJPcAy5BTswNCDsanxsMMxK5odBedZqJetpHYRvNcOoaLvY7U4hlzTseZkj+EmIFrWB/RnN4O09UAri318evDl4BjubfrsGVZTBkVcMwznMDCXeFRrdz82M8PSGi/7hz4KHB7px9x+7zaPxU+dTGOiDeR9mfDIeLgO3N97AgguvPYWLILlBN0XZGk4Li4rmigvMRRcXILELeATbuPkLPPFcb763CNaBy84wm9Tbe7SJ3SmE2KWMACb31IBDzPZnzrnb/zz0OwzvVERgtU75KJ2Pp6DMu0LY1SiDlLJCNYpGFac0X7r1kEJ1SYEbxZu1+t/fE8pk3vJXo0EOh2VMM9ZhaPPQQr4vVKxdGxltA6Iu7w/GHgVDPNeFlMHy7oSCEWiLu7SD5A/QFplwmoH27uR+2uIubTGivTv5Mu1bRjva4n7aP0/dibmRXIOm4QBavipKasPTqt46LEvUW88qa+mg2ldI4CyHvTzQci3bPXoDwxfBVtvJZIKq07TNOO7jpK/vtaebTutLHdwa/N9amBqDoIjMBeqbXRxwfk8j90TvZK9lNk5hP6MjYpr5kwd9B7kDcpYpTmAzNu2GvMQydt8udMK4SOCnGe2DPWwiRMfRxvAzGqj1tV3RIcOdPNP6Gk7ePnt1eHJy+Pooe354TMkMZ0IyZaygE1O/7bt3dCyzdFpv8flvl9ngENsCeL/9MYgEz0EwNY2iT7/ruN2Z1uYmDn8nk1caHcXtdBK2te0k+hdSXkal', 'common/schema.py': 'eJyNVF2O0zAQfq/UOwzhJRWQXfEYqWgrVCQkBKvuvpUqMsmYhnXtyHYRVYnEIbjIXoGjcBLGP2lSWpZNIiWefPPNj79xkiTj0fwrEws0W2HBlGvcMPj94yfYNYKxTFZMV6DRbrUEu2sQuNLAhAAkty2zmDU78tN1Y002HiWOkWu1gYpZVgpmDBqoN43Stjc9B16jqCKSaGv5uQPN5G48cvfVAT4e+Re8XmN5F1LNxyOgS7IN5pSnDsvGhaty+KSUCBb81mBpnY14YQrvlcTwh5V2y8Sp3SqBmsmSeLlQzMJ3//MII5UNYcnqCg7WCjkUBVmLIjUo+CQm6S5qpd0aB7+e3dwkUHNwkCxkDCgMQvJm9vZd0vs0TFvnsuTJch8I2hXsvZ8rvE1WPbgj7AqG2rg0fdKDPA68GWsalFXKk85juj8iaJPJKXto2uO5Az4yh8UTfZb50PbHk5PL9Nf9/tj9LLnfrwe50v0B2E6GFFH6CdDzzL+yL6qWqfef/Eup/UzFsJaZu6KuBlo1FpuC12Ko39IJ3OQgamOXA7WvSAV+YlLSGCNDwamZSu+mDhmzRa2VDqo8kizAU+qCdc24uZ1fA2cUtCKdA8m76sR71WjVoLa7XstBm0HK8OIV1NLmJ40x201adjJ2Z0NJuND1UM3kgQhWWSb+E0CgTB9JZ0qlsafz45ufGRHXKKAnKodygOkULv9SSIx/mV2eFj0Y3YsBzfAkoMZsmN716dDGDCKIWmIc7lvSRhzrKJM2j+sQo73Y9zHaqJK4PQCpLzvOmP/Os5ecVHzudPAaOa7TZ9JPAsB8sfiw6DLwHkdDdW6TH6KkutNycmakPso4Sx5OgD8nCfRs'}
CALL_FUNC = 'evaluate'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('apply_jlcpcb_2layer.scr', '/home/user/Desktop/apply_jlcpcb_2layer.scr'), ('jlcpcb_2layer.dru', '/home/user/Desktop/jlcpcb_2layer.dru'), ('loose.brd', '/home/user/Desktop/loose.brd')]


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
