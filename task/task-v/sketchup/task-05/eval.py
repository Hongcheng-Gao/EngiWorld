from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\user\Desktop')
BUNDLE = {'_shared/__init__.py': 'eNoDAAAAAAE=', '_shared/common.py': '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', 'eval_inner.py': 'eNqtWety28YV/s+n2MI/CMQgAspUkipmGsemY08VK2MraSeqglkSSxIRLix2SZHRqNOH6BP2SfqdXdwJJm6nHFsksXvOnut3zllaljXb8XjLVZazJf5/+PPox5F/zv79z3+xl2se4WnOE8HuI7VmYR7FsQiZVLlQi7XI2S9ZlCrpDQbvBQ8ly7Zqs1VeyIXL7nl8J1mkJJMLkQq2yvlm7TKehmwn8mgZCXkxYMzmDvtqyr5gYSRVlC4U2/AcRPaExWIl2VM2qc+TDlHMHXYFFjyO2Xye7dm577Py7+TcZ0mixY1S9vTTERvTAyJbOGzGF2tiO5QsEXLNIsk4BFUiV9FqrVjC02iZxSHjSzxjai3wP8+2q/VoncWCLbZKEquwZsXWXLJQKLFQfI4t1T5m0+oui7cwHzSIFio+gEJK8OQpMQcrei230GSipW+oMGWfn/nM9+nLz8/Acp5FYcHPGViWNVjmWcKCYLlV21wEAYuSTZYrWDjNFFdRlsrBoHyWr2BWKcrvmSw/yYM0jEKu+CLmUgpZcqoeuQzuisOKXbpNNgcGxdPNYDB4M3s/g7iZ9DZcrb0wylOEjF1+53NJ7zYkjWLI6TgDHGrWolTC9rbvVtRplid6e/mAQsymI1xmeZ7lgNwoLtc8F6G3yJIkS0uRPyyyXLzkecjYE5Zmf+cXbDbxzyDlEzaiFxP7DXyFKF6JLBEqP5jn/+1r8Prq6vr792/fXUN136Po068nOhARcZezb4M3s7ffvjEbyKtm3fhXr394+9NMr/qTgpzW9fI331z9Nbi+ujTL43q5junv3r4Lvn/x/voDo/ypXuDQlzqD1z9cXgZ06o9Xlz98R+dWInzS/VgITsw+987EaMIQgzDhd1EaJdukG/AXOlUkDDuUVcYk8EdE0cTjDPmfiyTbCZaZyH/CsjxEimVLdjapo3yDR5Q2trrP2Bllw1mRF8gInVXAGyiDw6N05XiM/SCJGWeLjEJph7jf6aRFelMiI9UUW8Yc5hA7kWKjBCHELpmDbzPFPW3VN1eXs9pMY88Xo3NtjHGdkQipUCxZsMiAiQsVIJQVTxdC2oC/gELXudAJjlT9C7BQm+jVi1kTDjUawkHbnCQLAREwiCZ60OEZROEFiwGMZCf7PsvjMEAyLUQA/FNIS8AKJ3VwOqiFdNgj28RbqQ8jQs0MxASW5uA0C+ETm8CekBaG26bK8QhQaG+RR6QVD/lAP9NYOS2feS/Ne62n2aWtobJgsp/YSaE7vThI043H85wf7MRloTpsxBRPlnHG1WcTp9oZQU4Pab0RbDpl9vgzt8GGXqWpPHIvttkTl52m14v9DAadB5BGHMCuUMWUoCm7uSWnlw4g/8gL9kDo5pb+cZl2RaCdA5yEc+SjZjI/BCsg9pQ9PNYGoqpokwtcOkSkytUOCYjn9B3ypCEw1QCzCSC3OdgtRVF2uFJ5wWuYcITCfthRF+jWflCyTdjXla+Ig2fondZmsV+IjWIz/YZycsxqg9pQPSQVwHolVFOwKBy6TCuGjK91pS/DPw0rYgpHFFTU7A79Yh3FIWwALje3msfNbVsQGCOSZfbZC/QYZaDqgPe+LXD+HRg6xzqsKLLXXlkNjte1D1ce3nD4yquk36Z3aXafDo8odGrlUaK18ehTRKgkj8+m104W+SFNhtB+j2JKdNxR6RvuT5MQEJwifMJexzAtUFBlFXIACuBE6lF4nKOJO9Qrjtd//lKL4AFxEsqzcb9e2hKUDZBV7y9zdjR22bN+CUUsxf+P2zpLjJ3WiI3FnX2zA2LiK4JR2vZOGqi48W9dNnac234m92BhE6evWeJdOzcXLrt4dtu7VaOGxzcbkYb2w0k1hhRBwwudL+7pXYg7bMLf39hjoCfOFjwmhnVE7KTzG2TakCDQ77/LXiMbdt/373zst5tBP08KBdjj21jZpArlcGkh+76AS6cDO/HvZfSJTNbYSruTJqiWeEILDTQqkJ5y1dRFJCvVOXNEI1dpR0qr5mxdPttnG0x36yJi9ClKi44Kt7BH1TRQVx0tD4FetfXful14WawyQUOGEU/XanTcQxpf0B+hoLvspxG6gZTmJ997ds4SwkfNZFj1fbQXo1C19x+mmaoLPrWKbqNP1GWPHFXZZ0PaaxEbtSml4nTTCpFbL0GrzveRnPq1S5N9706+P9r5qxYQxWl/c3bLRjgD782a92tDW7/tA9KiCqwNQgAaJ/tGZB1DS63yScLChV0TFV4UmJwDM/JK27wHGH4KP8oFVKnGkaJ4U7vUGJX0bFNTYsKpJ2jLUEBtjHMVhYDNdMBU7aU5y+NhaFt6wDJbLJe95tAZOdZgqnkt0fFhxFXsgdg8Wk63G5ILkxyt9qEVx9Chp/E1zWBf60CRK47lNR0k2vmWuPoJE3me5ei2xB/yfhFPMrrOt21gXVoPsUiLLHtsJBT00StGKSxVlxDVcAhHS6sAiyf6tuKFQkBwtIQfe2fhNUWt5CI1VaC772Algi+sWuRaWAr2asyrNywtowPdPbRUK+RIBeZbkD5UtI9Owb9SpQIZQ4O5KjPSozA24WB+AHSIvaI29BRg9ONZv9qIvjwgHoEZIkXY0ZzWHGosJk2FtWh2C/B8ArypMYAmevyynu4nlb6npah1OCVLw4tHEjUsUMr1vCtWg75fuDKufu9Oq3uhZVyB7WYSNH3OruhzumjbQXG00X9rwqoJAAJIYvKryDO0Rz61VRUEkS7VYU6nDFQLp/G/saUH+BFdGvY15ldPsztqvfhc2lhHl4bV6s7FYc+nrLwi6TQCNFOXVOP/iUpXn/oapEXmdEGsxcfKjBMDcqLVbpiyu/b3pWWyCilsFPxk7Pv+hTdePsLpD0b81jOrQ/9ghG3sSZJGlB1trwxRUPjmpP7HR9S1QRr7koTZFJQPpX1aa07DBEVhaJXhEr7bVisrgZVmerimiw0K3lcvZg0kblznmguKZAtMnov+G12vJAtbt8DF9WxJ+rzvLpbS0ewreNDL7rnyRWl490rfvOCL4VlcenFICEHSFdgznhDme3VqrRp9VXH9ghmMdBrULWapkakYdCs4qOccDGsVgrWWwJwWeBSbvq7V1VbdDhm3LUY1mFZQYoaM9uCzLHaYeaK9pmj2KtTwrs27XXpzSpOYppou8WmTZ/gop1S427NABAwjZedZFtsq8eh7ZYr2VlS0LKHrEqZFNTBa+BelTYeI+XqhL4qM20yz1LiML5k19tPPBP0X+K1DbNQHf0//zv0OM7I2XVHmudBMNjF0D8nmnRl7Tg6Za8jcteDU1d97sFNTQYoAUoBK36nZgHHYNLTnGlPBtDNikXIFAWGeIYJ5i18XHHOnQqbXVcGsY25Nh07nOo3Cm0KuEmFUM28z8T2/27GXoVn133q7W3FwywM64peM+0bATp48nbJxL21x9Wrk/4p1bn2POXeSrMW3txLoFqeWp1MMjhN6Wjc/3Trx0N39+Gmj6akQECjZe57zEYKu+U4EWseOoF1w+S0x23uPhEQWrbP7xi9k3RJjf/XQ8cMnY/HHspj8/KwKhy+PSEtPVj8g0H7norPvKbPoVyQ9dkHeUBfP4gRLZ2lYYGEZmk7TjIPOjKSnwISDWdES6REkp6wqfm/zXuQrZFSqvtcr1RRIX8gVAS/WbWs0wgQI8YrrEnMZbLq8fCXNVTBR6Teik3bVntE3+t2tDtvQCKGf9hTe8se/9VZF8VHxEcmGJslBjeUbAvPisZfchfS5cR+9UkdD7Uf/GHj6/gmxucppVg1UvlVrch1P5T1sUI/HOqq1FuaOfKXctiCQvTNWOy0jYb0e11sTfVg4K8doZCNzckAUubB1NeCT+Smt0L3QbThCUKPdGNGBlUDfQQUB5Y0VBBQrQWAZP+Q8wsYPBwljzvaRsk0kOYP/AFoJ9GA='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = []


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
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
