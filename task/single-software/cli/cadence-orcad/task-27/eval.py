from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\user\Desktop')
BUNDLE = {'eval_inner.py': 'eNqVVU1v2zgQvRvwf2B5WTK1ZaToYWFEKYyuty2wSIIk6KGWK7AipbArkQJJdYum+e87Q0m2XGQPa8A2yZn35oNPo9LZhuR52YXOqTwnummtC0QYY4MI2ho/n81nw+lXb81h49R8ViK6FeGh1l9G6A1sEfN+e7sladwyCKBroOeJU97W3xTjSSucMmE++2Nzv82jq1NJYZsWPJmj7M16t1l+2u/E8sf+8dVT5l/yN7+eZPLxfDGsMrk+/PSm10+Uz2429+//mx6p1rssW+1/rjiefb64/C2jmT9jfP8yGvjZ6SFw/nX9Lv+4vb37cH31HPWdLcM/UB1k8VE5D00E6Bq+fPc5c5k5Q5YFgj68u7q+3b7d3G35DHsmVUlyY10jav1DsaC+hzXxwXGyvMT/9YzAB48h6NC4xHdfGL3A3SWwopFP3YYGDG64e9bttKbo7Wh2fjGcnWJqbZQH0A4XiYPMdMs4Ka2LJqJNdIbbbmtRKEaxbGCg8MsT39Y6sLjeRzqnQH0mWpOvVhsWSaZsfUBdxkUyxOPj4ti7ommZEY2KXVsQ24W2gxaiCMcekp/kyhq1nsfQwmAdvR9ZEcT2hgqbEjW8IrRytjMyD64LD/TEDVKCJwVpEvVd++AZH5gnhZW00d5rU5FHRD7RA3Zy2UjhlIAo0DmmTGElIFLahXL5O/ROOWedT6muAKMo5+RFOsUfo1bhfxH1wGfT7tMlUpclCHlIe7BiE+eHzqtvos77NnrW/+dSu6N6pS7CEGLo9jAbjs6T6TBGihMlJY+0Fd7TNflT1F6Bjo4gGkMMLPypB6J0MHWUDqNSNXZ5vnydSFejCE0hna7rpLYVnZaNZUKwg4hG/fCjC1wZek1Axzx3FLoOE5LugQS9fnWKbet9p/Xt+uIQde86dWoqHlTxd2/cHfno1VsSayA4V0F9cthCSaQRoXggogzKxdm8kiIoMgolDnW66Ln2Jzc6phYnPmgzxybAOyFNCc3zRmiT53QofXxPuArmuI9CiI9TC4mOh8nGVV0DQ/4Gd268VdEmQspcDEY2vczRxVX4WIJnJEJfP8JbpwGEr6JEdk3r2Yn00DOZSGoBEpAQJX0FwjceX3LCF1qnUUkcOP8FL0AlYw==', 'ground_truth/collision_report.json': 'eNrFk0ELgjAYhu+B/2F4FpmaIB3z1qUOdSlCSicNNiduQSX+95wLNRblZXT64Pn43j28sNqaAWCnjBDMMSu4vQDQ6VhJTimiqBCSHSQCoFaj3VYoz5Dc2DvPdnp8SyhtoQ8HdFcoGCGOMyRPt+vN6LZion+9A4/kzIRgVAVA920lWPkKdqHCjfNF0tclA10yNCXpu+FvyXhak2FoTHJCk/G0Jj34T8nVhyY9qFvOTVlGUyyXe90y0iV9U5LeYCnHUf17fkGEJDmWkaK6ImvWPAED5eK7', 'ground_truth/demo-1-4.drl': 'eNpNjMtOg0AUhvckvMO/cWUYBoGY0rjAMrYkXGphUVdkyoyGOGWaKcbUp3do1HgWJ+f7L2dZsDRjuwTBHVxnufkhe67qjAEJ0maV57PwlBdXQcij9gIvIsIovGoDEEKg+EWaM9p6Cz4KPNZtW5e2lbEmX1cJssRXuufqU5t3n41vgz2U8Ml0PHXa9Fx0J6MP8t6f35ODEbYLYKOVPA9fEgHBAwJKCb0OWmsYPvbSyre/qu/9+VVdddsibVmGMi8aPH/wcRqmi42HrnPjOusFdZ09DeNF/EJju2eKafSPomimMJipDG38G/G6TgU=', 'ground_truth/ncdrill.log': 'eNq9VE1z2jAQPbsz/Q97g0zHxoY2abkpthI8YyzHFv3IhVFsETw1FiOLEvrrK9lA0kwOTct0fUC7q337dllt3z6FnL1904dTyAEo9iFIwyiCSNz/E9DJGAWSbcv6CZkxFHwlnDtZvA4oEwu1ZZLDZy6bUtQaaPjB8TJ35L6SEVN8QMsVf2Q01XBoLWF4Ad6nsftx7A1h6A7P/0OPTjVH3QeJFDlvGtNxPQsJk2zFlW4YLMqKQ6/O52tjc9SD6oHjOG2QuYlSNMUUp5nWf8Nub1yRdIqopmxZQ2ekDVPkT8IY2+TqKsPUsh7GruMasXaHk77dL+t8eWbiMQ5SRLFleVrzCUmDMNZ6ZlnoMiPRjGJtJzOazKg9i0OqHTi+jsJsou2UkMjWITi1rDD2U4yyML7WjhQnGFHbJ4FB+oYN+WyWJCnOMjvCKLBvcUq0LyZPPTRFYfSyC9/MUGR1xjZthiPs071loiENCasWNdd6dNC9YVtWoAu0UOaHocHEpqmm5i7FXrVTXaam31lJQsNpeIvn7bM9mnE8QbGPgzn+6uMoIvEew0eRSeF1HXbb/+YLSmMd2M+S6WR6ZY/OR2djmNWlaqDZNYqvoGzgjpuRaLalype8gO2S13DPay6ZMo5CllUFYqPWG9WNSsEUc/ZDFbReYz4A7W8qAUUpea6E3EEvGA8qkbNqK+T3Aa7vS32oioGjVuu5kDkr5msp7vjFcfBacCM9sxJsz37vFLLqQS65fqMFLISEpTBZc1HXOo1JTUkCrC7gklBKpnuAv386Rw6dxJtV+5uVP/f74d3ABqpJSFbnnSmpuqYB3GxYrUq1ewYCngOe2z0Do3anweGgs5B4nkR6GILHmNERxNDSKRWruurHf75RXgbhrAAl2Q9ePYNyndEIFpwr6LuO50K3K9pt8gvIFnT0'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('README.md', r'C:\Users\user\Desktop\README.md'), ('components.json', r'C:\Users\user\Desktop\components.json'), ('demo.brd', r'C:\Users\user\Desktop\demo.brd'), ('nc_param.txt', r'C:\Users\user\Desktop\nc_param.txt'), ('shell_spec.json', r'C:\Users\user\Desktop\shell_spec.json')]


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
