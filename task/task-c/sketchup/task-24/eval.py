from __future__ import annotations



import base64

import importlib.util

import shutil

import tempfile

import zlib

from pathlib import Path





DESKTOP = Path('C:\\Users\\user\\Desktop')

BUNDLE = {'eval_inner.py': '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'}

CALL_FUNC = 'eval_outputs'

CALL_ARGS = ['__DESKTOP_DIR__']

INIT_MAP = [('params.json', 'C:\\Users\\user\\Desktop/params.json'), ('plan.dxf', 'C:\\Users\\user\\Desktop/plan.dxf')]





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





def _install_ifcopenshell_fallback() -> None:

    try:

        __import__("ifcopenshell")

        return

    except ImportError:

        pass

    import re

    import sys

    import types

    def _normalize_type_name(name: str) -> str:

        known = {

            "IFCPROJECT": "IfcProject",

            "IFCSITE": "IfcSite",

            "IFCBUILDING": "IfcBuilding",

            "IFCBUILDINGSTOREY": "IfcBuildingStorey",

            "IFCWALL": "IfcWall",

            "IFCDOOR": "IfcDoor",

            "IFCWINDOW": "IfcWindow",

            "IFCSLAB": "IfcSlab",

            "IFCRELAGGREGATES": "IfcRelAggregates",

            "IFCRELCONTAINEDINSPATIALSTRUCTURE": "IfcRelContainedInSpatialStructure",

        }

        return known.get(name.upper(), name)

    class _IfcEntity:

        def __init__(self, eid: str, etype: str, args_text: str):

            self._id = eid

            self._type = _normalize_type_name(etype)

            self._args_text = args_text

            self.Name = None

            self.IsDecomposedBy = []

            self.ContainsElements = []

            self.ContainedInStructure = []

        def is_a(self, type_name=None):

            if type_name is None:

                return self._type

            return self._type.upper() == str(type_name).upper()

    class _IfcModel:

        def __init__(self, schema: str, entities_by_id: dict[str, _IfcEntity]):

            self.schema = schema

            self._entities_by_id = entities_by_id

        def by_type(self, type_name: str):

            want = str(type_name).upper()

            return [ent for ent in self._entities_by_id.values() if ent._type.upper() == want]

    def _split_top_level_args(text: str) -> list[str]:

        parts: list[str] = []

        buf: list[str] = []

        depth = 0

        in_string = False

        i = 0

        while i < len(text):

            ch = text[i]

            if ch == "'":

                buf.append(ch)

                if in_string and i + 1 < len(text) and text[i + 1] == "'":

                    buf.append(text[i + 1])

                    i += 1

                else:

                    in_string = not in_string

            elif not in_string and ch == "(":

                depth += 1

                buf.append(ch)

            elif not in_string and ch == ")":

                depth -= 1

                buf.append(ch)

            elif not in_string and ch == "," and depth == 0:

                parts.append("".join(buf).strip())

                buf = []

            else:

                buf.append(ch)

            i += 1

        tail = "".join(buf).strip()

        if tail:

            parts.append(tail)

        return parts

    def _parse_name(parts: list[str]):

        if len(parts) <= 2:

            return None

        value = parts[2]

        if len(value) >= 2 and value[0] == "'" and value[-1] == "'":

            return value[1:-1].replace("''", "'")

        return None

    def _parse_refs(text: str) -> list[str]:

        return re.findall(r"#\d+", text or "")

    def _open_ifc(path):

        raw = Path(path).read_text(encoding="utf-8", errors="ignore")

        schema_match = re.search(r"FILE_SCHEMA\(\('([^']+)'\)\)", raw, re.IGNORECASE)

        schema = schema_match.group(1) if schema_match else ""

        data_match = re.search(r"DATA;(.*)ENDSEC;", raw, re.IGNORECASE | re.DOTALL)

        data = data_match.group(1) if data_match else raw

        entities_by_id: dict[str, _IfcEntity] = {}

        for match in re.finditer(r"(#\d+)\s*=\s*([A-Z0-9_]+)\((.*?)\);", data, re.IGNORECASE | re.DOTALL):

            eid, etype, args_text = match.groups()

            entities_by_id[eid] = _IfcEntity(eid, etype, args_text)

        for ent in entities_by_id.values():

            ent.Name = _parse_name(_split_top_level_args(ent._args_text))

        for ent in entities_by_id.values():

            parts = _split_top_level_args(ent._args_text)

            etype = ent._type.upper()

            if etype == "IFCRELAGGREGATES" and len(parts) >= 2:

                parent = entities_by_id.get(parts[-2].strip())

                children = [entities_by_id[ref] for ref in _parse_refs(parts[-1]) if ref in entities_by_id]

                ent.RelatedObjects = children

                if parent is not None:

                    parent.IsDecomposedBy.append(ent)

            elif etype == "IFCRELCONTAINEDINSPATIALSTRUCTURE" and len(parts) >= 2:

                children = [entities_by_id[ref] for ref in _parse_refs(parts[-2]) if ref in entities_by_id]

                structure = entities_by_id.get(parts[-1].strip())

                ent.RelatedElements = children

                ent.RelatingStructure = structure

                if structure is not None:

                    structure.ContainsElements.append(ent)

                for child in children:

                    child.ContainedInStructure.append(ent)

        return _IfcModel(schema, entities_by_id)

    module = types.ModuleType("ifcopenshell")

    module.open = _open_ifc

    sys.modules["ifcopenshell"] = module


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

        _install_ifcopenshell_fallback()
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

