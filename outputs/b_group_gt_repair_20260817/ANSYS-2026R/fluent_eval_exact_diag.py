from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import traceback
from pathlib import Path


DESKTOP = Path(r"C:\Users\user\Desktop")
LOG = DESKTOP / "exact_eval_diagnosis.log"


def emit(step: str, value: object) -> None:
    line = "EXACT_DIAG " + json.dumps({"step": step, "value": value}, default=str, sort_keys=True)
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def main() -> int:
    LOG.write_text("", encoding="utf-8")
    spec = importlib.util.spec_from_file_location("official_eval", DESKTOP / "eval.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    try:
        before = module.require_files()
        emit("require_files", {str(path): digest for path, digest in before.items()})
    except Exception as exc:
        emit("require_files_exception", {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
        return 1
    inspected = False
    try:
        with tempfile.TemporaryDirectory(prefix="ansys_fluent_exact_diag_", ignore_cleanup_errors=True) as temp:
            root = Path(temp)
            shutil.copy2(module.CASE_FILE, root / "case.cas")
            shutil.copy2(module.DATA_FILE, root / "case.dat")
            emit("temp_files", {
                "root": str(root),
                "case_sha256": module.digest(root / "case.cas"),
                "data_sha256": module.digest(root / "case.dat"),
            })
            try:
                inspected = module.inspect_case_data(root)
                emit("inspect_case_data_return", inspected)
            except Exception as exc:
                emit("inspect_case_data_exception", {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
    except Exception as exc:
        emit("temp_staging_exception", {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
    try:
        after = {path: module.digest(path) for path in module.FILES}
        unchanged = before == after
        emit("after_files", {"unchanged": unchanged, "hashes": {str(path): digest for path, digest in after.items()}})
    except Exception as exc:
        unchanged = False
        emit("after_files_exception", {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
    emit("exact_evaluate_components", {"inspect_case_data": inspected, "before_equals_after": unchanged, "result": inspected and unchanged})
    return 0 if inspected and unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
