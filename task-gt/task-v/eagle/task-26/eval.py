from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': 'eNqdWWty2zgS/s9T9NJbNWQiU5Hy+KGNksrISso1eZVsZ7cq8dAUCVko8zUEKFubSdUeYq8yF5ij7Em2GwAfkmjLHlUikUCj0c8P3bBt29NVEJeBzApY4H8ZiKvD4Qtw5iWPIwjg+fPnEAgZzGMG85inV6wAES5ZEkgewqLIEnwtAhkuXc+yzkRwyUYW4Cdfy2WWAkP2Xr6Gk7OfPxyfnBx/+ugfHc8sa/MdklJICLNUBjyFC7ORhxtdgINiXQSpuK4G/vef/4JcMijYghUsDZl1WWRlGvmyKOWyDxEvWIgKraEUTCjSOJCSFa4Hp0su4LIIIlQjZwWqnAh4JHBlKMsiiA+tLI3XjwCl5hGqiBrgP2Lxrw/v1c5pBtPZpEe/786O1e/0zbv3U+DpKgvVEg+OJQR5HnMmLMFvAO0VXomRpQwz8MhiPJc+F77ax79JYppR/PHZY7JgzJvGLGGpPMVnCIMU8qAQTMmy4DHzFLOhV1lN+OgqH2kkQM0skBAzdB8qweAlTb6C62WGbC4ituIhE0xeQFZYsO9j6C+QpSz4vJQMEvI6GvjCec1d3PxCi/TUg2Ug/IL9VqIjInxYREhViURCCEiDhEUwG/RgNuzBBH+d99OjAYoCRwMXR4b7RQoKBkEcQ16gGqkEJwwEO0RLsFRwyVcqQnBrV8v1TMslSnTM2hfrZJ7F4hZTfZlMQBMqeSFIo5pgv2DE4d3How0O7IYjb2fFA+XBCz03uOjfw/SadngBMZ8XAcb1NZdLqB1I0vZxvx58mt3DaloeHQXGN5jf5BTF1jDrn5x9NoZ7rg2XMim2mZHhXo3hKbzE2VfAdMQKzAWlZQ0U+8Vy2E2OWUtWTnjKkzIhSXqg9To7NbK88CCPg1JwxCO/CCl/ylZwzQb92RDMoIpP6P/67Vv02Pn2zaNf9/XXqw/nr/9+D7OTzycDzayK9f2rdrZLyyT/84/z129xU8+ybdtSoOn7ixIRh/k+8CTPVIylmVT4ISzLjBWsehLLUvK4fluL6lGyJCc8qN678SMQMD3VO+eBXGIgVdt+xlfLQoYeTXiUPoV0nvQwKAqHJh0UFfn7vuthomXxijku0iLySvMDfbDDLEmy1HZdy5wJ5Plqjwnh34yJMpY9oANHPwMcIHz+Foxg+uzJ0LJO35z84h8fwRhsFlzGDA8i27Jm/pc378+m/myKEwXzcKcc5XEK+1dlaa/lVtu1DmBiAmCEJ8Elx2h8DFlOdg1iTJqQJ/jbGipTLglDFgjUTtov+3k/6f/5h9umeWtN7idFy9soy9vjL1O/+dpdi6hp92jo+N3HT7Pp5M3J1LUsK2ILQKPjkUa56s/XBkQdBZ4jxAEhv05PKw+f9xSejshlLhy+gmYKfoePCEf6SMbgm2xDZJxlV2UO2QKBwRwQ8zWQ1S6IZwvvPYpdYnMdIN+x2tJDZGKF46pxqh9ySn0tZZ0rfAFO7l0y6di0xnYJ5W3brRbDeKx4jjayq2CYHsjLar2QKsY8TJctzBHlPOFCoJ98PPhbNqjDTPNFOhRaBfTmklZY672QrFnsUEXk82hsgpPyguUqI8aUIcgLY14tPIDPqiRR0BexGM1bqLqJtP4HLOismgfhFcgMmnoGRAYb9YvhlQeCqhfC5KwkJEAuPL3UMEjrxkolTL1WtaQdhAZHKCEiTx07wnEb2waxbJY2YthtdyFNx8pmY5yvR1ks2JbnPFYUGZlx0ZZNybQgRSlGvqMEP+wujxeVNf+ZFVe6wsQzM8nRVYdhhqUkGiyAxodUG/2E2iblJWIGCB6xQ7ZY4GEitLHUsVbBpHfKCJPwFD2qykSMQIRHGTVaXNPOJlhk5NbjMRZ4MU6o+S7LKxMppPZIVAcnenpVw0SyG/KAGsXQC9DvOOLUQXR4eKgBEwYjXYeq2vPwoR/FThbrRq0iy2hnRAeyKkYvxpNDmzfC4enhZ6T7aVGyjVH0KQGz1pPdhCyXMFU/5AM0INvZSKXrDue3AUZMB2vKJmZS0NMVs4dFNEsjp3V+OPVKyqqx3VFK272aRiVRNNZ7N8O61sAJW9XUKknRxq2FAbYDQTy2syubEsIIT7GOQa0LcRXkI/huNPhhVrtuOwf1wpZlNmJc18JjZS+P8B4hwrG9fl9NqG+7Iy6GI9OYNZWlgAeFxQKxyXQLtP/X8zsBPCIag+B11VnBeEO12qbaIUGj7ByJHtq/CJdOJBT17fOrLShq61AFysYx8+BY2umkdiNpnmWx097Z7YqqjV5Cl9sbFXtfP+mqEpMQfsIdf9oNvw03kSlTYqgwtIm2nfB4OoKq+aoK/KpFumd4bPduGCH2bICVij0b0vdEPU+Gto4bBcSoBZKlKohSCqJtJvyumgYrGBewNSfIODcaYUOIgR4qpGFoPzxZmx7RA+eM2lhcQ3lG6/TNQKvqNXzqroQaRjyFBTZQS6Y6lDV2NlgE/ZsVGTbpPI7wmPV03MQsGqBGd4lskzi2Jt9PXJOiIRRzo65qNJrXJsiNWavAVbv9XnN5QFx3tOO7ke2QGc2WXUG97c7HGBONO+zzXexs9eZ2hYdVqBgkNa+Ioubpxx1x/WxUddRV8+5Qn/6YekQX7hXYZIlVGG6cQjR2iS5oj92GhGRPJLyznG2qBT5v0ZrevSGPs+sNcoWyzm0wu8te4a3TCbi7xAcwK/GQezOq7hDw5NQ3EHbfPA1tePPxaBekMC7NnYDXBnLVQqbg1HwwxCtGW0iN1DaysIk+0kBWv65GOz1146SNIqTihIK0OdWvt3DSrt3gZIzx86gFj9T9UTT11c1NH07OPoMTs5SzNFy7G5qrxkdfmRCsO0qZLZVv0aFrNSnQsbpD7q7VKOf26gM4yqgivkqza0Q6jqV3EfBY35tiwSmpWhOB5GKxplx8pMH1EQJiILc4XQeCWAUxFaprs4qzyKt6HcSHmIe8voSCOcPA9jbYEML8FczavKrrgKzKyoSgxmb7z2PyMi3ouKXbPYG/28jfHlX+xBjHPcw7Pv24Ha2ejzpvxh5QpKkLt47ikMbpyxwEB3DCsHKJ6GKQekxqMREpM0Sq6WzCxVJdF2OQl+qGPUWb8BWXa0qal4JfpkH8ymvXrMS/BXm3SKFX/rXDiHh2uBPTzaEpV1mu05PKpFvLjavq1bf75MWouT3Ud4X96oZP3O8AKfYe87P6gB7uJR0a0nAv10nFdeUrEZxioIFfCd/gPjV1OTa06MpClRRVcaRPXFOLI5OhYjLcy2R4BxMlthPulSTslsQYVHeFqrAm5VyVnErNv2G/+dpW780loKeKZkPaYmtsvsltWHMb7uM23OUWbsoW1rKFG7JNdrmFW7I9NEk67rg78kXbjkTQetOTkrkrdb5vQDKF6Qjs6LG6N23x1pPDOyYn1crmrrNF8qMDQtVe5LCeYU3m7hlOZKwtGG2aZIuaBp9s4vt0TWj7foIdmu/bo6aUTh26vQ6Ky5VLbhk22JUXPMXILNVfJe/+iySWL/pOD1kJGWFD3xRPNIZdtnSGJrP17fW4dQlpBPg6ONckemdN6IkySQK6Z9JzNbsnKsMMTZhhd4IqDrwnOkMGrvV/D02afA==', 'common/schema.py': 'eJyNVF2O0zAQfq/UOwzhJRWQXfEYqWgrVCQkBKvuvpUqMsmYhnXtyHYRVYnEIbjIXoGjcBLGP2lSWpZNIiWefPPNj79xkiTj0fwrEws0W2HBlGvcMPj94yfYNYKxTFZMV6DRbrUEu2sQuNLAhAAkty2zmDU78tN1Y002HiWOkWu1gYpZVgpmDBqoN43Stjc9B16jqCKSaGv5uQPN5G48cvfVAT4e+Re8XmN5F1LNxyOgS7IN5pSnDsvGhaty+KSUCBb81mBpnY14YQrvlcTwh5V2y8Sp3SqBmsmSeLlQzMJ3//MII5UNYcnqCg7WCjkUBVmLIjUo+CQm6S5qpd0aB7+e3dwkUHNwkCxkDCgMQvJm9vZd0vs0TFvnsuTJch8I2hXsvZ8rvE1WPbgj7AqG2rg0fdKDPA68GWsalFXKk85juj8iaJPJKXto2uO5Az4yh8UTfZb50PbHk5PL9Nf9/tj9LLnfrwe50v0B2E6GFFH6CdDzzL+yL6qWqfef/Eup/UzFsJaZu6KuBlo1FpuC12Ko39IJ3OQgamOXA7WvSAV+YlLSGCNDwamZSu+mDhmzRa2VDqo8kizAU+qCdc24uZ1fA2cUtCKdA8m76sR71WjVoLa7XstBm0HK8OIV1NLmJ40x201adjJ2Z0NJuND1UM3kgQhWWSb+E0CgTB9JZ0qlsafz45ufGRHXKKAnKodygOkULv9SSIx/mV2eFj0Y3YsBzfAkoMZsmN716dDGDCKIWmIc7lvSRhzrKJM2j+sQo73Y9zHaqJK4PQCpLzvOmP/Os5ecVHzudPAaOa7TZ9JPAsB8sfiw6DLwHkdDdW6TH6KkutNycmakPso4Sx5OgD8nCfRs'}
CALL_FUNC = 'evaluate'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('README.txt', '/home/user/Desktop/README.txt'), ('led.lbr', '/home/user/Desktop/led.lbr'), ('linear.lbr', '/home/user/Desktop/linear.lbr'), ('rcl.lbr', '/home/user/Desktop/rcl.lbr'), ('supply1.lbr', '/home/user/Desktop/supply1.lbr')]


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
