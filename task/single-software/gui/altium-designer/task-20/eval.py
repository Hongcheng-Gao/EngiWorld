from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path


DESKTOP = Path(r"C:\Users\user\Desktop")
DOCUMENT_NAMESPACE = (
    "http://schemas.datacontract.org/2004/07/"
    "Altium.Designer.PcbDrawing.DataSerialization.V1"
)
MAX_XML_SIZE = 64 * 1024 * 1024


def _read_7bit_integer(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    for _ in range(5):
        if offset >= len(data):
            raise ValueError("truncated 7-bit integer")
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, offset
        shift += 7
    raise ValueError("oversized 7-bit integer")


def _decompress_lz4_block(payload: bytes, expected_size: int) -> bytes:
    output = bytearray()
    offset = 0
    while offset < len(payload):
        token = payload[offset]
        offset += 1
        literal_length = token >> 4
        if literal_length == 15:
            while True:
                if offset >= len(payload):
                    raise ValueError("truncated LZ4 literal length")
                extra = payload[offset]
                offset += 1
                literal_length += extra
                if extra != 255:
                    break
        end = offset + literal_length
        if end > len(payload) or len(output) + literal_length > expected_size:
            raise ValueError("invalid LZ4 literal run")
        output.extend(payload[offset:end])
        offset = end
        if offset == len(payload):
            break
        if offset + 2 > len(payload):
            raise ValueError("truncated LZ4 match offset")
        match_offset = payload[offset] | (payload[offset + 1] << 8)
        offset += 2
        if match_offset <= 0 or match_offset > len(output):
            raise ValueError("invalid LZ4 match offset")
        match_length = (token & 0x0F) + 4
        if (token & 0x0F) == 15:
            while True:
                if offset >= len(payload):
                    raise ValueError("truncated LZ4 match length")
                extra = payload[offset]
                offset += 1
                match_length += extra
                if extra != 255:
                    break
        if len(output) + match_length > expected_size:
            raise ValueError("LZ4 block exceeds declared size")
        for _ in range(match_length):
            output.append(output[-match_offset])
    if len(output) != expected_size:
        raise ValueError("LZ4 block size mismatch")
    return bytes(output)


def _native_xml(data: bytes) -> bytes:
    if not data or data[0] != 1:
        raise ValueError("unsupported Draftsman compression version")
    offset = 1
    chunks = []
    total_size = 0
    while offset < len(data):
        unpacked_size, offset = _read_7bit_integer(data, offset)
        packed_size, offset = _read_7bit_integer(data, offset)
        if unpacked_size <= 0 or packed_size <= 0 or offset + packed_size > len(data):
            raise ValueError("invalid Draftsman block framing")
        total_size += unpacked_size
        if total_size > MAX_XML_SIZE:
            raise ValueError("Draftsman XML is too large")
        chunks.append(_decompress_lz4_block(data[offset:offset + packed_size], unpacked_size))
        offset += packed_size
    if offset != len(data) or not chunks:
        raise ValueError("invalid Draftsman stream boundary")
    return b"".join(chunks)


def _local(name: str) -> str:
    return str(name).rsplit("}", 1)[-1]


def _children(element, name: str):
    return [child for child in element if _local(child.tag) == name]


def _first_child(element, name: str):
    return next((child for child in element if _local(child.tag) == name), None)


def _text(element, name: str) -> str:
    child = _first_child(element, name)
    return (child.text or "").strip() if child is not None else ""


def _type_name(element) -> str:
    for key, value in element.attrib.items():
        if _local(key) == "type":
            return str(value).rsplit(":", 1)[-1]
    return ""


def _location(element):
    location = _first_child(element, "Location")
    if location is None:
        return None
    try:
        point = (float(_text(location, "X")), float(_text(location, "Y")))
    except ValueError:
        return None
    return point if all(math.isfinite(value) for value in point) else None


def _native_note(element) -> bool:
    texts = [
        (candidate.text or "").strip()
        for candidate in element.iter()
        if _local(candidate.tag) == "Text"
    ]
    return any(text for text in texts)


def _valid_bom_source(path: Path) -> bool:
    try:
        text = path.read_text(encoding="latin1")
    except OSError:
        return False
    if not text.startswith("|RECORD=BOM|"):
        return False
    catalog_items = []
    for line in text.splitlines():
        if "|RECORD=CatalogItem|" not in line:
            continue
        fields = {
            key.upper(): value
            for key, value in re.findall(r"(?:^|\|)([^|=]+)=([^|]*)", line)
        }
        if fields.get("LINENUMBER") and fields.get("USERCOMMENTS"):
            catalog_items.append((fields["LINENUMBER"], fields["USERCOMMENTS"]))
    return len(catalog_items) >= 4 and len(set(catalog_items)) == len(catalog_items)


def _valid_native_release(path: Path, bom_source: Path) -> bool:
    try:
        data = path.read_bytes()
        if not (4_000 <= len(data) <= 20_000_000):
            return False
        root = ET.fromstring(_native_xml(data))
    except (OSError, ValueError, ET.ParseError):
        return False

    if (_local(root.tag) != "Document" or
            not root.tag.startswith("{" + DOCUMENT_NAMESPACE + "}")):
        return False
    if not _valid_bom_source(bom_source):
        return False

    source_name = _text(root, "SourceDocumentName").replace("\\", "/").rsplit("/", 1)[-1]
    if source_name.casefold() != "ready_to_release.pcbdoc":
        return False

    board = _first_child(root, "BoardAssemblyInformation")
    fabrication_model = _first_child(root, "BoardFabricationInformation")
    if board is None or fabrication_model is None:
        return False
    primitives = [item for item in board.iter() if _local(item.tag) == "Primitive"]
    layers_geometry = [item for item in fabrication_model.iter() if _local(item.tag) == "LayersGeometry"]
    if len(primitives) < 8 or not layers_geometry:
        return False

    pages_container = _first_child(root, "Pages")
    if pages_container is None:
        return False
    pages = _children(pages_container, "Page")
    if not pages:
        return False

    records = []
    page_records = []
    for page in pages:
        items_container = _first_child(page, "Items")
        items = _children(items_container, "Item") if items_container is not None else []
        typed = [(item, _type_name(item)) for item in items]
        records.extend(typed)
        page_records.append((page, typed))
        size = _first_child(page, "Size")
        try:
            page_size = (float(_text(size, "Width")), float(_text(size, "Height")))
        except (TypeError, ValueError):
            return False
        if (not _text(page, "TemplateFileName") or
                not all(math.isfinite(value) and value > 0 for value in page_size)):
            return False

    by_type = {}
    for item, item_type in records:
        by_type.setdefault(item_type, []).append(item)

    fabrication_views = by_type.get("BoardFabricationViewData", [])
    drill_tables = by_type.get("DrillTableBoardView", [])
    stack_legends = by_type.get("LayerStackLegendView", [])
    dimensions = by_type.get("LinearDimension", [])
    if (not fabrication_views or not drill_tables or not stack_legends or not dimensions or
            any(_location(item) is None for item in fabrication_views + drill_tables + stack_legends)):
        return False
    if not any(_first_child(item, "StartAnchor") is not None and
               _first_child(item, "EndAnchor") is not None for item in dimensions):
        return False

    assembly_views = by_type.get("BoardAssemblyViewData", [])
    assembly_ids = {_text(item, "Id") for item in assembly_views if _text(item, "Id")}
    assembly_locations = {_location(item) for item in assembly_views if _location(item) is not None}
    if len(assembly_views) < 2 or len(assembly_ids) < 2 or len(assembly_locations) < 2:
        return False
    if any(not _text(item, "ViewSide") for item in assembly_views):
        return False

    bom_views = by_type.get("BillOfMaterialsView", [])
    valid_bom_view = False
    for bom_view in bom_views:
        column_names = set()
        for column in bom_view.iter():
            if _local(column.tag) != "BomColumnInfo":
                continue
            name = _text(column, "Name").strip().casefold()
            pattern = _text(column, "SourcePattern").strip()
            if name and pattern:
                column_names.add(name)
        if ({"designator", "quantity"}.issubset(column_names) and
                len(column_names) >= 3 and _location(bom_view) is not None and
                _text(bom_view, "DataSource")):
            valid_bom_view = True
            break
    if not valid_bom_view:
        return False

    bom_information = _first_child(root, "BillOfMaterialsInformation")
    bom_logic = _first_child(root, "BillOfMaterialsLogic")
    if bom_information is None or bom_logic is None or not _text(bom_logic, "DataSource"):
        return False

    for required_type in ("BoardFabricationViewData", "BoardAssemblyViewData"):
        relevant_pages = [
            typed for _, typed in page_records
            if any(item_type == required_type for _, item_type in typed)
        ]
        if not relevant_pages or not any(
            _native_note(item)
            for typed in relevant_pages
            for item, item_type in typed
            if item_type == "Note"
        ):
            return False

    parameters = _first_child(root, "Parameters")
    parameter_names = {
        _text(item, "Name").upper()
        for item in (parameters or [])
        if _local(item.tag) == "DrawingDocumentParameterData"
    }
    if (not any("REV" in name for name in parameter_names) or
            not any("PROJECT" in name or "SHEET" in name for name in parameter_names)):
        return False
    return True


def evaluate(root: Path = DESKTOP) -> bool:
    root = Path(root)
    return _valid_native_release(
        root / "release.PCBDwf",
        root / "ready_to_release.BomDoc",
    )


if __name__ == "__main__":
    print("True" if evaluate() else "False")
