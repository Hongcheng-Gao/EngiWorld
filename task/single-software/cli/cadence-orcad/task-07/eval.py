from __future__ import annotations

import base64
import importlib.util
import os
import shutil
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\user\Desktop')
ORCAD_CAPTURE_PATH = r"C:\\Cadence\\SPB_24.1\\tools\\bin\\capture.exe"
BUNDLE = {'_common/README.md': 'eNqtVMtqGzEU3Rv8Dxey6AM/2u1kUYLdQCElIQ6EUhdLnrn2qJZ1FT08NWTRj+gX9kt6pRm7bmi7ihaDfXWf55yrMxCLkrZbMmMBP7//AF9LhxXgTuoogyIDVsftUpl1v9fvvd+h20OQfvPCg0hOI7sXbNAbD4Eg1AguGsPucO0mF1OYSBuiQ9gpCaEhWCmNHmp0WKSEj3DJBvjjPMItPbU9/3lMxYdPD/zF9vynLS4acht0o1BqcZhck1kPtdoxBXel5r9kGVQZoJGhrBk5sWijFg8RI47FADxFV/KNNHsQr9tsX2kJlSNrOY8yA9jSDjNBoiLDUV0DTNVCmUXZcpSpfISbfaiZ9hq1RXcOjVMhxTKzKevd5GrAzajgYUUum1kTlSpDpjbVkFxWuv9D3++dncEsSBeihZdkSgSudlSLR+9Ze6+SoxCi32uHhGkx1lRKnTAYkytlNU5i9OODiH9D2u8VBZq1YouuiqK9KAqfanZJ+71PFFnxFHXFJRHE52MEtAFfIAdgdd4ykIT97yZOqREMfIZnwp1JU8G9MhU1I7hCucPjpGTRjDo8brvNYYoOO9atWIeDpQadZ2Z4umkxl0aWZCo5t5myEX5LCM2Pzc1zc/PcXP4O37yddxmB509csL+VoZ4HmlMMNoZFpdwRnzvu/xCwRoNOJi1I8FupddICLDUtB5An9qBCp40BpImtU4Z1Im4uZjMBYxCXFx+uBDQq1FBhkEr7w+j39Z7Ttvi1qudS/Eok8RvQMpoW+wNsSSw8pX6X4jtjnt/hQ1QuNzmRFSZhXW+C5Jxr5oN1XVIiO5E64N/Gx2121qpE45GVhrxtKb0y7MXx7Sw1h3n4OBter1bsOvRhz2pf8/RSp3QBRzCzqiWQNS3BYNPvWUe8mz4nPHlTmyy5JUI00cul3oPX1ORC7VWtQhbPSVtul3PkB1htudw0LXgql14K3k3G3/D6JfWcPCNsQ2cd8pezqAp9QMsTM3+0ym8Lc/ALEa7kpw==', '_common/allegro_native.py': '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', '_common/pspice_native.py': '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', '_common/run_in_capture.py': 'eNqdVm1v2zYQ/m7A/+GgDqiEOXI77EOhzAWKJAMKDG0XpOiHLJAZiYrZ0KJKUrFdz/99dxT15iVtt3xwRPLueC/PPccgCKYTXZepKNOMVbbWPK52cHICKy4rrsGumIVcq8oAg6uzP+CzugVRWoUnHFCzFOXdyVmjOp1slL5HrS81rzmwMocNE9ZAobSTf+A6F5mFQkgOaINVFWc6nk6mk4+G3XEIC63WeJNl5v65Af7AJPoTJSQB+OeOK2ZXUqAb60ppCx9w2Zz6DbMzzRo/YhKORWm4tuGLGRirQ1II05ScSNMo1two+cDDCGU1L625fnkDcwjSTK3XqgyiaHD3OFftjePd1tk22sXRedgc05/NZHqr8t3iueGYlhyuVcVLOE/mdl3NVW1ju7WwuTmFqsY8/oQSK3EKmVSG0+r5rLeF0ilFu3Dx6WBsJIgGolasOYmbxctfXvj9iNz+oLnmX2phhOUJuJrVmDpYMay/1JzlO0wh05bn8F6fvTkHX/oZkOO4S+W+yuR0cobZIwR8EmWuNjOHBqNqnaEQBShVxiThZa50xvI5ldzMfdLnDZBizA+QpgMpwDJJeHkn8FDmSdLIJIlzaAkORm8L57THoTBQKtvCdAbLcSGWUDApDdyy7J7gaLmUKNeFPZ3wLcus3MFmJbJVB9tlE8dygPC6cgddYpcd5hFetbToXEC95kCE2Kvp/jRtAcRK9JNZoUpDUfhdZbpPh2n/TZd0i7oWuTf7aF9MJ39+vPh4kZ6/vUQg9tB4Iv1N4lLXwAFC4vz9u0YXlXtD2B25KnlA5qeTnBePI7xFd0Jt52HWojRxvvjNLm0JcQte1cOyUlKiZcs1ckEChVTMCcStAHbZLXZDArdKSTy50jXHowhOXrutpBHD7J8jjWGJvFNYPeK0EZ95MMOQxmauwlTOxtCyjWA5YDCAS46apXHXg2hQ6PCywWsqrfIagT+D35k0dO7jRiEfO/BtJTTP0dQV7mJxJHqAjGS46Y1lCjOBFEVtxmURd7E1H12F4vV9LnToCW3hcoI3CGNTde+WntTa+v6QQqPyDM4kZyVi1nGBHNO6dwkz0OYpdmZMGCUDAtK7wWqIi7gusQfvw6g/5tuMV4hnrtfCGOyRC62VPtKvmDGth1jTVCDLIBqoPWL6+RX5fcW318mrm16oZGuOQkVAi32jdiDSCXoZcuoI/K1qI8S1boW6bpkf20ShoE/gJ80qV1QCIsIPcUj2TMUy7ohD4EhydIBweCM3bIczVNZmhQnPCSzG4bU15yg6w5IYzglrd8g5CJHSiLzDNE7TMSP7Qm00QThH5wdjqQieAautOrlDTteM2P52B/96J/xVBkOdPgSa25AkwwzAfn8kvm878XB0cDjeGIbeHUXjEsUbjTMrtXxrQx8TArjMVI6MvghqW5y8CjoMIzxb3ugvqjQSQVgE1+NAbxoeyGHf1v1w6jiBRgUVa99i9xBEP2AtxMuPiOZ4TtEsfcwWfbeq42q6UYT6yVNq4Ifvfxm9T9t6eg4/pYN58g4Q7ol1HaFhCDVS3e77fu+7SjOTVsqIbRgdIOprmuPrBKmDGpo4NaafMIKf++niEb9yY3wg8lunO0DDYwzmstztYrwWWQUp0oivHF7DiyNO0m4muJEwstsyxmPM+CQ6v4uri8vL95fNK9VjZJTUsX7nAr3pmq45bpYZ+am0WQSaVxLbunsJH8XnZtr4cRkbyXkVjob3/2w+MueSDqxAQ7Dvynkwp93oofZpp2wb9di97qVCAXu1cPwacW8GZ+5veKc6NPj31Gejyi4Auu9bA87fTVb8qB9NPH9MJmN80eSm8+QbBWnT7+fhhfuHM4IeMj+UykzVMm9SRe+KLnnkRgJ7PuKvUQT/ANhdaOM=', '_common/worker.tcl': 'eNqtVttuGzcQfTfgf5is5MAu7JWToi9boECRFEgLJC5sA3mQFg61O2vR4pJbkmtFMAT0I/qF/ZLOcKlrLNsoohdJvJw5M3Nmhr3ed/wcHvRgZuwUbeoLBfDv3/8A4L1QrfDS6LgHypgG/ER4sK12ILWTJYLQYBrU8E40vrUIDp2jS4TJsB/MDLwB1GKsEKSHY6PVHDRi6XhjjFAajWB0gdCQkR2Yk4xRAN6kcOWF9fA+GxlbiHLkjVFuNJZ6FK+k+BXhWJlbYgaygkpa58HLGk/SDuRtChdM1U8QrsnRd6auhS7hs9Ql8TyO32e/7Ows7/+Ywp/CeYycwseZ1hL199lAmUIoDtUgEBx44aZucFMQlNGDdXw3LmcZ6ltJW6rMsu5Eljn2M4bvgsNC0dZS354G3jEXjVHKwRNmu3M3f7XYIicT7ZwB31JgC6NLlwL8qufwQ8h4JSk5lWnJY7JB0ZcuOlbCccyz9A7MTIMWNbpGFMhwlbF01qigkxMQHYCG2tzTVcovU04HnOIBuHZcSkuGr2lxCe8KKxtPIAxnCdmQuXGgY2FmpSfPg23yoJSFhz+uLj7BWBRThi+lmwIJUkAj/ARMtaTJaMXEGMfXj1nLaTOHqTYzB7PgIt0mQU9Dbvn09Tq45H2JSo7RCo+k1lpqWQuVAWhD0vV87JR/41ePVgtFP7A4hbvWceLgS+fcF+bTOrRnrm0aJclbVp3sBBizuhJ8Y01Bmo/hoZwqtAy2JH8CbmJaVUJFtcOVFArJW7K5CqPj9YlwIXCe8kDRQFWxi9+3XxwerGQQGsVjSoaHwwMW+b2wMlR/0OINSQCSl+k22QFgGYX7LwUIwttFWQYe4Hxnx8tielM7bjc/ndPmgh3lvDxRqPCw+MbRaKFbpU700I8rq6P8aVrKVzIarpCj/HIQyqIo50ucZH3HImlFd/8X+8K7J2rdcij1espR7O/c2NzavuTQr8L2plvazz6EBcufYSZ8MeEra0PRFe5eLwgvjZvnorvJ7Px5ZoRokdhwzSTPMmCazzLYVc//ygqL5NWGSmKiIRBc+nlnxg6GyhlS3fBWmTGcaUPjpVGCesqZnzfUNWEY0nhnaKm/UXGh0Sd5nsdcG5JYMWFM6AfgDWWyMa7viOWFVOFQvn2EEl03MCyoEKcMWFMjjv/ikMnhLK4nRx+yo4/Z0VWSv6QCRsN+QM+Xsc6gz4ySbQa2IIOssk32/GkbRSNPQe+cAibpGRDH9I4XC0BrN/53tVosduH2EwX47fLy4pKbeiBIPAky2b7eg8/Uj8NTKaXdrtA0DY/lhOQs8Lzzq84fh1tBc9Sm22jsOKFQpp23rPtaUJ0kIb+QsIFksaWCVdsMDPP8W7iqhGF4xPUD8Cx/xP0+HeLt7S1Kt0Pe2wjq+mcPPpIDKxfZJ34JpNtZLKkcnyK8Ph1z3QWQRjRSUFlhnNmAsthz1mLQ8/JsUP3mhfglKprn0F/OgU46e1tDHhtID36vyEd6NQRb9G3xLL5vTnmu3/P7iQriHrVEetGR/6y0odQVvyHIiHvcShR/Dq9fw6v+U0dWkt0vVWVEiWVKDw6lnhpo4VV+K3XaNcj/AKnJ1W8=', 'eval_inner.py': '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', 'ground_truth/complex_stim.out': 'eNqtVMtu00AU3VfKPxx1FbeNO7aTpg7qwiSGBuWl2KmEEI2sdJpYOHbwjKsCArHoomz5FDbd5wf6D/0S7sRp4wCLLriy5MXVedxzZJd2sEcDDLxFOOEw6npVZyj3kiuYzDQ1rPebMa0GMxvMBlj10KTnqLRTUjQYpMllGPEGdr3mqdt1/HbTqHh+u7uLd5gk80XEr8dChnNdhHO8V7DSWt8fOj2v7fZ8OD2n89ZrextB3+0O3KHjj4YuTpSBus4YQ8t9jaZi2PuvU3RF03Udj4S7ytrQ9UYd31vt4fHpnMcSIlB34SqIMi5wmSZznJXbPQ1lOeNQ12ZRJiCSLJ1wraGgZ2PHHxvdpxNXR+k127Jtd58uoylD8CkMNMCvF0lMQmEQIQ0FP4C1vCsbFX5eoXa0Jz5rm89SGTG2zWcS3ySJhQzIuIWzAvzoGXCL4Aq1DxHGZfP++/LOwIfTz+o1FxoBLdqxAuvxM1irxLrIIsExC6czLJJUhkl88OhvlfW/Mu6PfAo5uJQ8xbCJzuDVAe5vSIfpNWUnj7pfDDp3YehWzbJqGxfyRPnHCzz8uM3TxcPtT/DzLxV5eH/zVVv+Av+YhaSvGk+5oErIr7ZWsP5UMHW7atcLZcY8SOlYKSN+AZkUsu8Xk39EH9e3U5I8uPhUodokRyAlj7NAZYRvdCv5Zbpdy1OhXja2jv8mNrbjz2MPrngaTJWxWZpkVAFFmSdPRG/6L9Hs95qdUctt5W2sv8q+73RWa/rAXWz9IeiA0s5vP+4M/A==', 'ground_truth/stim_samples.json': 'eNqF0LEKgzAQBuC94DuEzDZE01jtaukDdHAp5QjlaAWNYiIUxHdvoku1Bcf7k//juCHYEUINPmvU1tATufmAkIFqVaObKb5b6EqDNPQ5tWBU3VYI/nOEe+FiWkCp3RgzmR1CPza99c9MSDGGa/HRaGOVtiAKhy5FsRQF45x/iTHLJP8VTakRGg3n3G+5FJMtMT3+Edu+Mgi2U6603jHdEiPORw/eJ5Za1UPti5zJOblC85oS6ZpTksNlvmcS7Fz3A9PqaX0='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('complex_stim.cir', r'C:\Users\user\Desktop\complex_stim.cir'), ('complex_stim.stl', r'C:\Users\user\Desktop\complex_stim.stl')]


RUN_IN_CAPTURE_PAYLOAD = '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'


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
    helper_path = root / "_common" / "run_in_capture.py"
    helper_path.parent.mkdir(parents=True, exist_ok=True)
    helper_path.write_bytes(_decode(RUN_IN_CAPTURE_PAYLOAD))


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
    os.environ["ENGIWORLD_ORCAD_CAPTURE_EXE"] = ORCAD_CAPTURE_PATH


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
