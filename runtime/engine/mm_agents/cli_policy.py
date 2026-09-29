"""Policy checks for Engiworld CLI-mode actions.

CLI tasks are intended to be solved by driving the target engineering
application's command-line, batch, or official scripting interface.  This
module performs a conservative pre-execution check for common bypasses: direct
artifact editing, third-party Python packages that parse/generate engineering
files, package installation, and invoking a different CAD/CAE application.
"""

from __future__ import annotations

import ast
import io
import json
import os
import re
import sys
import textwrap
import tokenize
from dataclasses import dataclass
from typing import Dict, FrozenSet, Iterable, Optional


class CliPolicyViolation(ValueError):
    """Raised when a terminal-mode action attempts a disallowed bypass."""


CLI_POLICY_PROMPT = (
    "=== CLI task integrity rules ===\n"
    "Use the command-line, batch, headless, or official scripting interface of the required "
    "application(s) to perform the engineering work. Bash and Python may perform ordinary calculations, launch and "
    "orchestrate the required software, monitor jobs, and create supporting scripts, logs, configuration, or native "
    "driver inputs. Python standard-library modules and the required application's official Python API are available "
    "for those purposes. Pillow (`PIL`) may process image files, for example by cropping, rotating, or resizing them. "
    "Engineering project/model files and scored outputs must be inspected, changed, and produced "
    "through the required application or its official interface.\n"
    "The following operations are not allowed. They are rejected before execution:\n"
    "- Do not use text, binary, shell, or generic Python file tools to directly inspect, edit, patch, copy, or fabricate an "
    "engineering project/model/answer artifact instead of handling it through the required application(s).\n"
    "  Examples include `cat`, `grep`, `head`, `tail`, `strings`, `xxd`, `hexdump`, `file`, `stat`, "
    "Python `open`, `Path.read_text/read_bytes`, `Path.write_text/write_bytes`, `shutil.copy*`, "
    "`os.rename`, and `os.replace` on engineering artifact files, including when the artifact path is "
    "hidden behind a shell or Python variable.\n"
    "- Do not install packages during the task or use third-party Python packages to parse, generate, repair, or "
    "convert engineering files. The required application(s)' installed official Python API is allowed.\n"
    "- Do not import non-standard-library Python packages other than Pillow (`PIL`) for image processing, "
    "`win32com` or `comtypes` for the required application(s)' COM interfaces, and the required application(s)' official API.\n"
    "- Do not call another CAD/CAE/EDA/BIM/graphics application or converter to do the required "
    "application(s)' work.\n"
    "- Do not understand or operate the required application through desktop screenshots. Do not capture the "
    "desktop, or use terminal code or system APIs to move or click the mouse, type keys, or otherwise control "
    "the GUI. Rejected examples include `System.Drawing.CopyFromScreen`, `ImageGrab.grab`, "
    "`pyautogui.screenshot`, `mss`, `BitBlt`, `PrintWindow`, `xwd`, and `scrot` for desktop capture, and "
    "PyAutoGUI mouse or keyboard calls, `SetCursorPos`, `SendInput`, `SendKeys`, and `xdotool` for desktop control.\n"
    "- Do not use interactive text editors or in-place patchers such as vim, nano, notepad, "
    "`sed -i`, `perl -pi`, PowerShell `Set-Content`, or similar direct-edit operations.\n"
    "- Do not parse task-provided neutral exchange files with generic JSON/XML/text tools or hand-write "
    "a scored text/JSON/CAM output, instead of obtaining the content through the required application(s).\n"
    "- Do not read evaluation-only material such as ground-truth directories, evaluator scripts, GT manifests, "
    "or extracting/listing archives that were not explicitly provided as task inputs.\n"
    "- Do not open or inspect an undeclared pre-existing answer/result artifact for hints. Treat such files as "
    "untrusted leftovers and produce the requested output only from declared task inputs.\n"
    "- Do not rename or re-export a supplied baseline as an optimized answer without a material design change or "
    "hand-writing a placeholder for a required stage when one of the named applications is unavailable.\n"
    "- Do not hide a disallowed operation in Base64, hexadecimal, compressed, marshalled, dynamically imported, "
    "or otherwise encoded code. Encoded payloads are checked before execution.\n"
    "Native textual driver sources such as an "
    "OpenSCAD `.scad` program, a FEniCS Python program, an APDL/input deck, or OpenFOAM dictionaries may "
    "be edited when that is the normal interface to the required application; the resulting engineering "
    "answer must still be produced by running that application."
)


_STDLIB_MODULES: FrozenSet[str] = frozenset(getattr(sys, "stdlib_module_names", ())) | {
    "__future__",
    "winreg",
}

_BASE_ALLOWED_IMPORTS: FrozenSet[str] = _STDLIB_MODULES | frozenset({
    # Common Windows automation used only to launch/drive the target app.
    "win32api",
    "win32com",
    "comtypes",
    "win32con",
    "win32gui",
    "pythoncom",
    "pywintypes",
    "PIL",
})

_TARGET_IMPORTS: Dict[str, FrozenSet[str]] = {
    "abaqus": frozenset({
        "abaqus", "abaqusConstants", "caeModules", "odbAccess", "regionToolset",
        "mesh", "part", "material", "section", "assembly", "step", "interaction",
        "load", "job", "sketch", "visualization", "xyPlot", "displayGroupOdbToolset",
        "connectorBehavior", "driverUtils", "backwardCompatibility",
    }),
    "ansys": frozenset({"ansys", "pyansys", "mapdl", "fluent"}),
    "archicad": frozenset({"archicad"}),
    "blender": frozenset({"bpy", "bmesh", "mathutils", "addon_utils", "bpy_extras"}),
    "bonsai": frozenset({"bpy", "bmesh", "mathutils", "addon_utils", "bpy_extras", "ifcopenshell", "bonsai"}),
    "calculix": frozenset({"ccx", "cgx"}),
    "fenics": frozenset({"fenics", "dolfin", "dolfinx", "ufl", "mshr", "petsc4py"}),
    "floris": frozenset({"floris"}),
    "freecad": frozenset({
        "FreeCAD", "FreeCADGui", "Part", "Mesh", "Draft", "Import", "ImportGui", "Arch",
        "Sketcher", "TechDraw", "MeshPart", "PartDesign", "Drawing", "importOBJ",
    }),
    "freecad-path": frozenset({
        "FreeCAD", "FreeCADGui", "Part", "Mesh", "Draft", "Import", "ImportGui", "Arch",
        "Sketcher", "TechDraw", "Path", "PathScripts", "MeshPart", "PartDesign", "Drawing", "importOBJ",
        "linuxcnc_post", "PathTests",
    }),
    "kicad": frozenset({"pcbnew", "_pcbnew"}),
    "openstudio": frozenset({"openstudio"}),
    "openfast": frozenset({"openfast_io"}),
}

_TARGET_COMMANDS: Dict[str, FrozenSet[str]] = {
    "abaqus": frozenset({"abaqus", "abq", "abq2024", "abq2025", "abq2025le", "sma", "smalauncher"}),
    "altium-designer": frozenset({"altium", "dxp", "x2", "altiumdesigner"}),
    "ansys": frozenset({"ansys", "mapdl", "fluent", "cfx", "runwb2", "wb2", "mechanical"}),
    "archicad": frozenset({"archicad"}),
    "autocad": frozenset({"autocad", "acad", "accoreconsole"}),
    "blender": frozenset({"blender"}),
    "bonsai": frozenset({"blender", "bonsai"}),
    "brl-cad": frozenset({"mged", "brlcad", "rt", "rtarea", "g-stl", "asc2g", "ged"}),
    "cadence-orcad": frozenset({"capture", "orcad", "allegro", "pstswp"}),
    "calculix": frozenset({"ccx", "cgx"}),
    "eagle": frozenset({"eagle"}),
    "fenics": frozenset({"fenics", "dolfin", "dolfinx"}),
    "floris": frozenset({"floris"}),
    "freecad": frozenset({"freecad", "freecadcmd"}),
    "freecad-path": frozenset({"freecad", "freecadcmd"}),
    "kicad": frozenset({"kicad", "kicad-cli", "pcbnew", "eeschema"}),
    "librecad": frozenset({"librecad"}),
    "nx-cam": frozenset({"nx", "ugraf", "ugraf.exe", "run_journal"}),
    "openfast": frozenset({"openfast"}),
    "openfoam": frozenset({
        "openfoam", "blockmesh", "snappyhexmesh", "simplefoam", "pimplefoam",
        "icofoam", "potentialfoam", "foamrun", "foamdict", "parafoam",
    }),
    "openscad": frozenset({"openscad"}),
    "openstudio": frozenset({"openstudio", "energyplus", "ruby"}),
    "revit": frozenset({"revit"}),
    "sketchup": frozenset({"sketchup", "ruby"}),
    # SOLIDWORKS hosts the CAMWorks/SOLIDWORKS CAM API used by these tasks.
    "solidcam": frozenset({"solidcam", "solidworks", "sldworks"}),
    "solidworks": frozenset({"solidworks", "sldworks"}),
    "solvespace": frozenset({"solvespace"}),
    "zbrush": frozenset({"zbrush"}),
}

_KNOWN_SOFTWARE_COMMANDS: FrozenSet[str] = frozenset().union(*_TARGET_COMMANDS.values()) | frozenset({
    "freecadcmd", "freecad", "blender", "kicad-cli", "pcbnew", "eeschema",
    "openscad", "librecad", "qcad", "orcad", "capture", "eagle", "abaqus",
    "ansys", "mapdl", "fluent", "zbrush", "sketchup", "revit", "autocad",
    "acad", "accoreconsole", "mged", "ccx", "cgx", "openstudio", "energyplus",
    "solidworks", "sldworks", "solvespace",
})

_ALWAYS_ALLOWED_COMMANDS: FrozenSet[str] = frozenset({
    "bash", "sh", "cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh",
    "python", "python3", "py", "perl", "ruby", "java", "node",
    "mkdir", "touch", "ls", "dir", "find", "grep", "rg", "awk", "sed",
    "head", "tail", "cat", "type", "more", "less", "wc", "sort", "uniq",
    "cut", "tr", "xargs", "tee", "echo", "printf", "pwd", "cd", "whoami",
    "uname", "where", "which", "command", "test", "stat", "file", "strings",
    "xxd", "hexdump", "od", "ps", "tasklist", "pgrep", "pkill", "kill",
    "timeout", "sleep", "nohup", "start", "set", "export", "env", "mount",
    "df", "du", "date", "ver", "copy", "cp", "move", "mv", "del", "rm",
    "rmdir", "robocopy", "xcopy", "chmod", "chown", "icacls", "reg", "reg.exe",
})

_DISALLOWED_IMPORTS: FrozenSet[str] = frozenset({
    "olefile", "pandas", "numpy", "scipy", "skimage", "cv2", "matplotlib",
    "ezdxf", "ifcopenshell", "trimesh", "meshio", "cadquery", "open3d", "pyvista",
    "vtk", "occ", "OCC", "pythonocc", "gmsh", "lxml", "bs4", "yaml", "ruamel",
})

_PACKAGE_MANAGER_RE = re.compile(
    r"(?is)(\b(python(?:3)?|py)\b\s+-m\s+)?"
    r"\b(pip|conda|mamba|apt|apt-get|npm|yarn|winget|choco)\b"
    r"[\s\"',\]\[]+"
    r"\b(install|add|update|upgrade)\b"
)

_DIRECT_EDIT_RE = re.compile(
    r"(?im)(?<![/\\\w.-])(?:vim|vi|nano|notepad|code(?:\.exe)?)(?=$|[\s;&|\"'])|"
    r"\bsed\b[^\n;&|]*\s-i(?:\b|[A-Za-z])|\bperl\b[^\n;&|]*\s-\S*pi\S*|"
    r"(?<![A-Za-z])ed\s+"
)

_IMPORT_LINE_RE = re.compile(r"(?:^|[\n;\"'])\s*import\s+([^\n#;\"']+)")
_FROM_IMPORT_LINE_RE = re.compile(r"(?:^|[\n;\"'])\s*from\s+([A-Za-z_][\w.]*)\s+import\b")
_DYNAMIC_IMPORT_RE = re.compile(
    r"""(?ix)
    (?:__import__|importlib\.import_module)
    \s*\(\s*["']([A-Za-z_][\w.]*)["']
    """
)

_ARTIFACT_EXTENSIONS: FrozenSet[str] = frozenset({
    ".pcbdoc", ".schdoc", ".pcblib", ".schlib",
    ".kicad_pcb", ".kicad_sch", ".kicad_pro", ".brd", ".sch", ".dsn",
    ".blend", ".skp", ".zpr", ".ztl", ".ifc", ".dwg", ".dxf",
    ".stl", ".step", ".stp", ".iges", ".igs", ".obj", ".fbx", ".3dm",
    ".fcstd", ".cae", ".odb", ".odb_f", ".sim", ".rvt", ".rfa", ".sldprt",
    ".sldasm", ".slddrw", ".slvs",
    ".opj", ".olb", ".dra", ".pad", ".pln", ".pla", ".gsm", ".mod",
    ".wbpj", ".agdb", ".mechdat", ".rst", ".cas", ".dat.h5",
    ".edif", ".ipc2581", ".schematic.json", ".netlist.json",
    ".nc", ".gcode", ".ngc", ".tap",
})

_HELPER_EXTENSIONS: FrozenSet[str] = frozenset({
    ".py", ".pyw", ".sh", ".bash", ".bat", ".cmd", ".ps1", ".jou", ".jnl",
    ".scr", ".mac", ".inp", ".dat", ".json", ".csv", ".txt", ".log",
})

_ARTIFACT_EXT_RE = "|".join(
    re.escape(ext) for ext in sorted(_ARTIFACT_EXTENSIONS, key=len, reverse=True)
)
_ARTIFACT_PATH_RE = re.compile(rf"(?i)(?:{_ARTIFACT_EXT_RE})(?=$|[^A-Za-z0-9_])")

_ARCHIVE_EXTENSIONS: FrozenSet[str] = frozenset({
    ".zip", ".7z", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz",
})
_ARCHIVE_EXT_RE = "|".join(
    re.escape(ext) for ext in sorted(_ARCHIVE_EXTENSIONS, key=len, reverse=True)
)
_ARCHIVE_PATH_RE = re.compile(
    rf"""(?ix)
    (?P<path>
        [A-Za-z]:[\\/][^\s'";&|]+(?:{_ARCHIVE_EXT_RE})
        |
        (?:[/\\.]|[A-Za-z0-9_-])[^\s'";&|]*?(?:{_ARCHIVE_EXT_RE})
    )
    (?=$|[\s'";&|)])
    """
)
_SHELL_ARCHIVE_TOOL_RE = re.compile(
    r"""(?ix)
    (?<![A-Za-z0-9_.-])
    (?:
        unzip|zipinfo|7z|7za|7zr|tar|bsdtar|jar|
        Expand-Archive|System\.IO\.Compression\.ZipFile
    )
    (?=$|[\s.(])
    """
)
_PY_ARCHIVE_TOOL_RE = re.compile(
    r"""(?ix)
    \b(?:zipfile|tarfile)\s*\.
    |
    \bshutil\s*\.\s*unpack_archive\s*\(
    |
    \b(?:ZipFile|TarFile)\s*\(
    """
)
_EVALUATION_MATERIAL_RE = re.compile(
    r"""(?ix)
    (?:^|[\\/])ground[_-]?truth(?:[\\/]|$)
    |
    (?:^|[\\/])eval\.py(?=$|[\s'";&|])
    |
    \bgt[_-]?generation(?:\.md)?\b
    |
    \bgt[_-]?manifest(?:\.json)?\b
    |
    \bnative[_-]?gt(?:[_-][A-Za-z0-9_.-]+)?\b
    """
)


_CLI_DESKTOP_CAPTURE_RE = re.compile(
    r"""(?ix)
    \bGraphics\s*\.\s*CopyFromScreen\s*\(
    |
    \bCopyFromScreen\s*\(
    |
    \bpyautogui\s*\.\s*screenshot\s*\(
    |
    \bImageGrab\s*\.\s*grab\s*\(
    |
    \bmss\s*\.\s*(?:mss|grab)\s*\(
    |
    \bpyscreenshot\b
    |
    \b(?:BitBlt|PrintWindow)\s*\(
    |
    (?<![A-Za-z0-9_./\\-])
    (?:gnome-screenshot|scrot|maim|grim|spectacle|flameshot|xwd|screencapture|snippingtool)
    (?:\.(?:exe|bat|cmd|ps1|sh))?
    (?=$|[\s'\";&|()])
    """
)
_CLI_DESKTOP_INPUT_RE = re.compile(
    r"""(?ix)
    \bpyautogui\s*\.\s*(?:
        click|doubleClick|rightClick|moveTo|moveRel|dragTo|dragRel|scroll|
        write|typewrite|press|keyDown|keyUp|hotkey|mouseDown|mouseUp
    )\s*\(
    |
    \b(?:SetCursorPos|mouse_event|keybd_event|SendInput|SendKeys)\s*\(
    |
    \[\s*System\.Windows\.Forms\.SendKeys\s*\]
    |
    (?<![A-Za-z0-9_./\\-])(?:xdotool|ydotool|wtype)(?=$|[\s'\";&|()])
    """
)


_REDIRECT_WRITE_RE = re.compile(
    r"""(?ix)
    (?:^|[;&|])\s*
    (?:
        cat\s+>|cat\s+<<[^>]*>|tee(?:\s+-a)?|echo\s+.+?>|printf\s+.+?>
    )
    \s*["']?([^"'\s;&|<]+)
    """
)
_SHELL_ARTIFACT_COPY_MOVE_RE = re.compile(
    rf"""(?ixm)
    (?:^|[;&|])\s*
    (?:cp|mv|copy|move|robocopy|xcopy|Copy-Item|Move-Item)\b
    [^\n;&|]*(?:{_ARTIFACT_EXT_RE})(?=$|[^A-Za-z0-9_])
    """
)
_SHELL_ARTIFACT_BINARY_WRITE_RE = re.compile(
    rf"""(?ixm)
    (?:^|[;&|])\s*
    (?:dd\b[^\n;&|]*\bof=|truncate\b[^\n;&|]*|Set-Content\b[^\n;&|]*|Add-Content\b[^\n;&|]*|Out-File\b[^\n;&|]*)
    [^\n;&|]*(?:{_ARTIFACT_EXT_RE})(?=$|[^A-Za-z0-9_])
    """
)
_SHELL_ARTIFACT_INSPECT_RE = re.compile(
    rf"""(?ixm)
    (?:^|[;&|])\s*
    (?:strings|xxd|hexdump|od|cat|type|head|tail|grep|awk|sed(?:\s+-n)?|file|stat)\b
    [^\n;&|]*(?:{_ARTIFACT_EXT_RE})(?=$|[^A-Za-z0-9_])
    |
    (?:^|[;&|])\s*
    (?:Get-Content|Select-String)\b
    [^\n;&|]*(?:{_ARTIFACT_EXT_RE})(?=$|[^A-Za-z0-9_])
    """
)
_SHELL_ARTIFACT_ASSIGN_RE = re.compile(
    rf"""(?ixm)
    ^\s*(?:export\s+)?([A-Za-z_]\w*)=
    (?:
        ["'][^"']*(?:{_ARTIFACT_EXT_RE})[^"']*["']
        |
        [^\s;&|]*(?:{_ARTIFACT_EXT_RE})[^\s;&|]*
    )
    """
)
_SHELL_ARTIFACT_FOR_RE = re.compile(
    rf"""(?ixms)
    ^\s*for\s+([A-Za-z_]\w*)\s+in\b
    (?:(?!\bdo\b).)*?(?:{_ARTIFACT_EXT_RE})
    (?:(?!\bdo\b).)*?\bdo\b
    """
)
_POWERSHELL_ARTIFACT_ASSIGN_RE = re.compile(
    rf"""(?ixm)
    \$([A-Za-z_]\w*)\s*=\s*
    ["'][^"']*(?:{_ARTIFACT_EXT_RE})[^"']*["']
    """
)
_PY_ARTIFACT_LITERAL_WRITE_RE = re.compile(
    rf"""(?ix)
    open\s*\([^\n]{{0,1000}}?(?:{_ARTIFACT_EXT_RE})[^\n]{{0,1000}}?,\s*["'][^"']*[wa+][^"']*["']
    |
    Path\s*\([^\n]{{0,1000}}?(?:{_ARTIFACT_EXT_RE})[^\n]{{0,1000}}?\)\s*\.\s*
    (?:write_text|write_bytes|open\s*\(\s*["'][^"']*[wa+][^"']*["'])
    """
)
_PY_ARTIFACT_MUTATION_RE = re.compile(
    r"""(?ix)
    \b(?:shutil\.(?:copy|copy2|copyfile|move)|os\.(?:replace|rename)|Path\s*\([^)]*\)\s*\.\s*rename)\s*\(
    |
    \.\s*(?:write_text|write_bytes)\s*\(
    """
)
_PY_GENERIC_WRITE_RE = re.compile(
    r"""(?ix)
    open\s*\([^)\n]*,\s*["'][^"']*[wax+][^"']*["']
    |
    \.\s*(?:write_text|write_bytes)\s*\(
    |
    \b[A-Za-z_]\w*\.write\s*\(
    """
)
_PY_BINARY_PARSE_RE = re.compile(
    r"""(?ix)
    \b(?:struct\b|struct\.(?:unpack|unpack_from|iter_unpack|pack|pack_into)|binascii\b|binascii\.|bytes\.fromhex|
    bytearray\s*\(|memoryview\s*\(|olefile\.|OleFileIO\b|CFB\b|DIFAT\b|miniFAT\b|
    compound\s+file|sector\s+shift|sector_size|fat_sids|mini_stream|openstream)\b
    """
)
_PY_ARTIFACT_READ_RE = re.compile(
    rf"""(?ixs)
    open\s*\([^)\n]*(?:{_ARTIFACT_EXT_RE})[^)\n]*,\s*["'][^"']*r[^"']*["']
    |
    Path\s*\([^)\n]*(?:{_ARTIFACT_EXT_RE})[^)\n]*\)\s*\.\s*(?:read_text|read_bytes)
    """
)
_PY_GENERIC_READ_RE = re.compile(
    r"""(?ix)
    \bopen\s*\([^)\n]*(?:,\s*["'][^"']*r[^"']*["'])?
    |
    \.\s*(?:read|read_text|read_bytes)\s*\(
    """
)
_PY_ARTIFACT_ASSIGN_RE = re.compile(
    rf"""(?ixm)
    ^\s*([A-Za-z_]\w*)\s*=\s*[^\n#]*(?:{_ARTIFACT_EXT_RE})(?=$|[^A-Za-z0-9_])
    """
)

_GENERIC_FILE_READ_RE = re.compile(
    r"""(?ix)
    \b(?:cat|head|tail|strings|xxd|hexdump|od|grep|awk|sed|Get-Content|Select-String)\b
    |
    \b(?:open|Path)\s*\(
    |
    \.\s*(?:read|read_text|read_bytes)\s*\(
    |
    \b(?:json\.(?:load|loads)|xml\.(?:parse|fromstring)|ElementTree\.parse|ConvertFrom-Json)\b
    """
)

_GENERIC_FILE_WRITE_RE = re.compile(
    r"""(?ix)
    \b(?:Set-Content|Add-Content|Out-File|Copy-Item|Move-Item|tee)\b
    |
    \b(?:cp|mv|copy|move|robocopy|xcopy)\b
    |
    (?:^|[;&|])\s*(?:echo|printf|cat)\b[^\n;&|]*>
    |
    \bopen\s*\([^\n)]*,\s*[\"'][^\"']*[wax+][^\"']*[\"']
    |
    \.\s*(?:write|write_text|write_bytes)\s*\(
    |
    \b(?:json\.dump|shutil\.(?:copy|copy2|copyfile|move)|os\.(?:rename|replace))\s*\(
    """
)

_ENCODED_EXEC_RE = re.compile(
    r"""(?ixs)
    (?:exec|eval|compile)\s*\([^)]{0,500}
    (?:b64decode|fromhex|marshal\.loads|zlib\.decompress|codecs\.decode)
    |
    (?:b64decode|fromhex|marshal\.loads|zlib\.decompress|codecs\.decode)
    [^\n]{0,500}(?:exec|eval|compile)\s*\(
    |
    (?:powershell|pwsh)(?:\.exe)?\b[^\n]*(?:-enc|-encodedcommand)\b
    |
    \[Convert\]::FromBase64String\s*\(
    """
)

_MACHINE_CODE_EXTENSIONS: FrozenSet[str] = frozenset({
    ".nc", ".gcode", ".ngc", ".tap",
})
_MACHINE_CODE_EXT_RE = "|".join(
    re.escape(ext) for ext in sorted(_MACHINE_CODE_EXTENSIONS, key=len, reverse=True)
)
_MACHINE_CODE_PATH_RE = re.compile(
    rf"(?i)(?:{_MACHINE_CODE_EXT_RE})(?=$|[^A-Za-z0-9_])"
)


@dataclass(frozen=True)
class _TaskPolicy:
    domain: str
    domains: FrozenSet[str]
    allowed_imports: FrozenSet[str]
    allowed_commands: FrozenSet[str]


def _normalize_domain(raw: Optional[str]) -> str:
    if not raw:
        return ""
    s = raw.strip().lower().replace("_", "-")
    aliases = {
        "orcad": "cadence-orcad",
        "or-cad": "cadence-orcad",
        "freecadpath": "freecad-path",
        "altium": "altium-designer",
    }
    return aliases.get(s, s)


def _domain_from_task(task_config: Optional[dict]) -> str:
    if not task_config:
        return ""
    for key in ("_engiworld_domain", "application", "domain", "app"):
        if isinstance(task_config.get(key), str):
            return _normalize_domain(task_config[key])
    task_id = str(task_config.get("id", ""))
    m = re.match(r"(.+?)-task-\d+", task_id)
    if m:
        return _normalize_domain(m.group(1))
    return _normalize_domain(task_id.split("-task-", 1)[0])


def _domains_from_task(task_config: Optional[dict]) -> FrozenSet[str]:
    if not task_config:
        return frozenset()
    domains = []
    related = task_config.get("related_apps")
    if isinstance(related, (list, tuple)):
        domains.extend(_normalize_domain(str(item)) for item in related if item)
    roles = task_config.get("open_software_roles")
    if isinstance(roles, dict):
        candidates = roles.get("candidate_software")
        if isinstance(candidates, (list, tuple)):
            domains.extend(_normalize_domain(str(item)) for item in candidates if item)
        distractor = roles.get("distractor_software")
        if distractor:
            domains.append(_normalize_domain(str(distractor)))
    cleaned = [d for d in domains if d]
    if cleaned:
        return frozenset(cleaned)
    domain = _domain_from_task(task_config)
    return frozenset({domain}) if domain else frozenset()


def _policy_for(task_config: Optional[dict]) -> _TaskPolicy:
    domains = _domains_from_task(task_config)
    allowed_imports = set(_BASE_ALLOWED_IMPORTS)
    allowed_commands = set(_ALWAYS_ALLOWED_COMMANDS)
    for domain in domains:
        allowed_imports.update(_TARGET_IMPORTS.get(domain, frozenset()))
        allowed_commands.update(_TARGET_COMMANDS.get(domain, frozenset()))
    label = ",".join(sorted(domains))
    return _TaskPolicy(label, frozenset(domains), frozenset(allowed_imports), frozenset(allowed_commands))


def _strip_command_suffix(token: str) -> str:
    normalized = token.strip().strip('"').strip("'").replace("\\", "/")
    base = os.path.basename(normalized).lower()
    for suffix in (".exe", ".bat", ".cmd", ".ps1", ".sh"):
        if base.endswith(suffix):
            base = base[:-len(suffix)]
            break
    return base


def _iter_command_like_tokens(script: str) -> Iterable[str]:
    for match in re.finditer(r"(?<![A-Za-z0-9_./\\-])([A-Za-z]:[\\/][^\s;&|]+|[/\\]?[A-Za-z0-9_.@:+-]+(?:\.(?:exe|bat|cmd|ps1|sh))?)", script):
        token = match.group(1)
        if not token or token.startswith("-") or token.isdigit():
            continue
        yield token


def _iter_imported_modules(script: str) -> Iterable[str]:
    for match in _IMPORT_LINE_RE.finditer(script):
        for item in match.group(1).split(","):
            module = item.strip().split(" as ", 1)[0].strip().split(".", 1)[0]
            if re.match(r"^[A-Za-z_]\w*$", module):
                yield module
    for match in _FROM_IMPORT_LINE_RE.finditer(script):
        yield match.group(1).split(".", 1)[0]
    for match in _DYNAMIC_IMPORT_RE.finditer(script):
        yield match.group(1).split(".", 1)[0]


def _script_uses_target_api(script: str, policy: _TaskPolicy) -> bool:
    target_imports = frozenset().union(*(_TARGET_IMPORTS.get(domain, frozenset()) for domain in policy.domains))
    if not target_imports:
        return False
    target_roots = {module.split(".", 1)[0] for module in target_imports}
    return any(module in target_roots for module in _iter_imported_modules(script))


def _script_uses_target_command(script: str, policy: _TaskPolicy) -> bool:
    target_commands = frozenset().union(*(
        _TARGET_COMMANDS.get(domain, frozenset()) for domain in policy.domains
    ))
    for command in target_commands:
        norm = _strip_command_suffix(command)
        pattern = re.compile(
            rf"(?i)(^|[\\/\s'\";&|]){re.escape(norm)}"
            rf"(?:\.(?:exe|bat|cmd|ps1|sh))?(?=$|[\\/\s'\";&|])"
        )
        for match in pattern.finditer(script):
            tail = script[match.end():match.end() + 80]
            if not re.match(r"(?is)^\s+(?:--?version|--help|/\?)\b", tail):
                return True
    return False


def _normalized_task_file_names(values: Iterable[str]) -> FrozenSet[str]:
    names = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            continue
        normalized = value.replace("\\", "/").rstrip("/")
        name = normalized.rsplit("/", 1)[-1].strip().lower()
        if name:
            names.add(name)
    return frozenset(names)


def _task_input_names(task_config: Optional[dict]) -> FrozenSet[str]:
    if not task_config:
        return frozenset()
    names = []
    for operation in task_config.get("config") or []:
        if not isinstance(operation, dict) or operation.get("type") != "upload_file":
            continue
        parameters = operation.get("parameters") or {}
        for file_spec in parameters.get("files") or []:
            if not isinstance(file_spec, dict):
                continue
            names.extend((file_spec.get("path"), file_spec.get("local_path")))
    return _normalized_task_file_names(name for name in names if name)


def _expected_output_names(task_config: Optional[dict]) -> FrozenSet[str]:
    if not task_config:
        return frozenset()
    return _normalized_task_file_names(task_config.get("_engiworld_expected_outputs") or [])


def _task_input_archive_names(task_config: Optional[dict]) -> FrozenSet[str]:
    return frozenset(
        name
        for name in _task_input_names(task_config)
        if any(name.endswith(ext) for ext in _ARCHIVE_EXTENSIONS)
    )


def _script_mentions_name(script: str, name: str) -> bool:
    return bool(re.search(
        rf"(?i)(?<![A-Za-z0-9_.-]){re.escape(name)}(?![A-Za-z0-9_.-])",
        script.replace("\\", "/"),
    ))


def _archive_names_mentioned(script: str) -> FrozenSet[str]:
    names = set()
    for match in _ARCHIVE_PATH_RE.finditer(script.replace("\\", "/")):
        normalized = match.group("path").rstrip("/")
        name = normalized.rsplit("/", 1)[-1].strip().lower()
        if name:
            names.add(name)
    return frozenset(names)


def _check_evaluation_material_and_archives(
    script: str,
    task_config: Optional[dict],
) -> None:
    normalized = script.replace("\\", "/")
    if _EVALUATION_MATERIAL_RE.search(normalized):
        raise CliPolicyViolation(
            "evaluation-only material is not accessible during an agent episode"
        )

    uses_archive_tool = bool(
        _SHELL_ARCHIVE_TOOL_RE.search(script)
        or _PY_ARCHIVE_TOOL_RE.search(script)
    )
    if not uses_archive_tool:
        return

    allowed_archives = _task_input_archive_names(task_config)
    mentioned_archives = _archive_names_mentioned(script)
    if not allowed_archives:
        raise CliPolicyViolation(
            "archive inspection or extraction is allowed only for archives explicitly provided as task inputs"
        )
    if not mentioned_archives:
        raise CliPolicyViolation(
            "archive operations must name an archive explicitly provided as a task input"
        )

    disallowed = mentioned_archives - allowed_archives
    if disallowed:
        raise CliPolicyViolation(
            "archive operation references a file that was not provided as a task input: "
            + ", ".join(sorted(disallowed))
        )

    for name in _expected_output_names(task_config):
        if _script_mentions_name(script, name):
            raise CliPolicyViolation(
                f"extracting scored output {name!r} from an archive is not allowed"
            )


def _check_task_bound_file_bypass(script: str, policy: _TaskPolicy, task_config: Optional[dict]) -> None:
    uses_target = _script_uses_target_api(script, policy) or _script_uses_target_command(script, policy)

    # Software-selection tasks deliberately use neutral inputs. They still have to
    # flow through one of the candidate engineering applications; generic
    # JSON/XML/text parsing is exactly the bypass this task family measures.
    if (task_config or {}).get("_engiworld_task_family") in {"software-selection", "open"} and not uses_target:
        for name in _task_input_names(task_config):
            if _script_mentions_name(script, name) and _GENERIC_FILE_READ_RE.search(script):
                raise CliPolicyViolation(
                    f"directly parsing task input {name!r} is not allowed; use a candidate application's CLI/API"
                )

    if not uses_target and _GENERIC_FILE_WRITE_RE.search(script):
        for name in _expected_output_names(task_config):
            if _script_mentions_name(script, name):
                raise CliPolicyViolation(
                    f"directly fabricating scored output {name!r} is not allowed; produce it through the required application"
                )


def _check_encoded_execution(script: str) -> None:
    if _ENCODED_EXEC_RE.search(script):
        raise CliPolicyViolation(
            "encoded or obfuscated code execution is not allowed during CLI evaluation"
        )


def _check_package_install(script: str) -> None:
    if _PACKAGE_MANAGER_RE.search(script):
        raise CliPolicyViolation(
            "package installation is not allowed during CLI evaluation; use the target application's installed CLI/API"
        )


def _python_command_text(script: str, depth: int = 0) -> Optional[str]:
    """Extract launch arguments from Python, keeping data and code distinct.

    Nested script literals are inspected too: writing a Python helper must not
    hide a later call to a different application. No submitted code is run.
    """
    if depth > 8:
        return script
    try:
        tree = ast.parse(textwrap.dedent(script))
    except (SyntaxError, ValueError):
        return None
    if not tree.body or all(
        isinstance(node, ast.Expr) and not isinstance(node.value, ast.Call)
        for node in tree.body
    ):
        return None  # A bare shell command can also parse as a Python expression.

    bindings = {}
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bindings.setdefault(target.id, []).append(node.value)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                aliases[alias.asname or alias.name] = alias.name

    def strings(node, seen=frozenset()):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.value
        elif isinstance(node, ast.Name) and node.id not in seen:
            for value in bindings.get(node.id, []):
                yield from strings(value, seen | {node.id})
        elif isinstance(node, (ast.List, ast.Tuple)):
            for value in node.elts:
                yield from strings(value, seen)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = list(strings(node.left, seen)), list(strings(node.right, seen))
            for a in left:
                for b in right:
                    yield a + b
        elif isinstance(node, ast.JoinedStr):
            # Preserve the literal command prefix of f-string launch arguments.
            yield ''.join(value.value if isinstance(value, ast.Constant) else ' '
                          for value in node.values)

    def call_name(node, seen=frozenset()):
        if isinstance(node, ast.Attribute):
            return node.attr
        if isinstance(node, ast.Name):
            if node.id not in seen and node.id in bindings:
                for value in bindings[node.id]:
                    name = call_name(value, seen | {node.id})
                    if name:
                        return name
            return aliases.get(node.id, node.id)
        return ''

    launchers = {
        'run', 'Popen', 'call', 'check_call', 'check_output', 'system', 'popen',
        'startfile', 'WinExec', 'ShellExecute', 'ShellExecuteW', 'ShellExecuteA',
        'execv', 'execve', 'execvp', 'execvpe', 'execl', 'execlp', 'spawnv', 'spawnve',
        'spawnvp', 'spawnvpe', 'Dispatch', 'DispatchEx', 'GetObject',
        'Exec', 'Run', 'CreateObject',
    }
    commands = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and call_name(node.func) in launchers:
            for arg in list(node.args) + [kw.value for kw in node.keywords if kw.arg in {'args', 'executable'}]:
                for value in strings(arg):
                    nested = _python_command_text(value, depth + 1)
                    if re.fullmatch(r'(?i)SldWorks\.Application(?:\.\d+)?', value):
                        commands.append('sldworks')
                    elif re.fullmatch(r'(?i)AutoCAD\.Application(?:\.\d+)?', value):
                        commands.append('acad')
                    else:
                        commands.append(value if nested is None else nested)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if '\n' in node.value or ';' in node.value:
                nested = _python_command_text(node.value, depth + 1)
                if nested is not None:
                    commands.append(nested)
    return '\n'.join(commands)


def _command_check_text(script: str, *, comments_only: bool = False) -> str:
    """Mask Python identifiers/comments, retaining strings that may launch commands.

    Whole Python actions and individual Python lines inside shell heredocs are
    recognized. Shell command lines remain available to the command checks.
    """
    if not comments_only:
        # Analyze each Python heredoc as a complete program so continuations,
        # function bodies and nested command strings retain their meaning.
        heredoc = re.compile(r"(?m)^(?P<header>[^\n]*<<-?\s*['\"]?(?P<tag>[A-Za-z_]\w*)['\"]?[^\n]*)\n(?P<body>[\s\S]*?)^(?P=tag)\s*$")
        def inspect_heredoc(match):
            body = match.group('body')
            commands = _python_command_text(body)
            if commands is None:
                try:
                    json.loads(body)
                    return match.group('header') + '\n'
                except (ValueError, TypeError):
                    pass
                # Native driver sources commonly contain C/C++ line comments.
                commands = re.sub(r'(?m)^\s*//[^\n]*', '', body)
                if re.search(r'\busing\s+System\s*;', commands):
                    declared = set(re.findall(r'\b(?:double|float|int|long|decimal|bool)\s+([A-Za-z_]\w*)\s*=', commands))
                    # Keep quoted executable names; mask declared numeric
                    # variables such as nx in C# geometry calculations.
                    if declared:
                        token_pattern = re.compile(r'"(?:\\.|[^"\\])*"|\b[A-Za-z_]\w*\b')
                        commands = token_pattern.sub(lambda token: ' ' * len(token[0]) if token[0] in declared else token[0], commands)
            return match.group('header') + '\n' + commands + '\n'
        script = heredoc.sub(inspect_heredoc, script)
        python_commands = _python_command_text(script)
        if python_commands is not None:
            return python_commands
        # Python -c/--python-expr payloads appear as string tokens in a shell
        # action. Inspect their launches instead of treating variable names or
        # printed descriptions inside them as executable names.
        lines = script.splitlines(keepends=True)
        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line))
        replacements = []
        try:
            for token in tokenize.generate_tokens(io.StringIO(script).readline):
                if token.type != tokenize.STRING:
                    continue
                try:
                    value = ast.literal_eval(token.string)
                except (SyntaxError, ValueError):
                    continue
                if not isinstance(value, str):
                    continue
                nested = _python_command_text(value)
                if nested is not None:
                    start = offsets[token.start[0] - 1] + token.start[1]
                    end = offsets[token.end[0] - 1] + token.end[1]
                    replacements.append((start, end, nested))
        except (tokenize.TokenError, IndentationError):
            pass
        for start, end, replacement in reversed(replacements):
            script = script[:start] + '\n' + replacement + '\n' + script[end:]
        # Handle Python lines in shell heredocs, including ordinary data strings.
        script = ''.join(
            line if (commands := _python_command_text(line.strip())) is None else commands + '\n'
            for line in script.splitlines(keepends=True)
        )
    lines = script.splitlines(keepends=True)
    try:
        tree = ast.parse(script)
        if tree.body and all(isinstance(node, ast.Expr) and not isinstance(node.value, ast.Call) for node in tree.body):
            raise SyntaxError
        python_rows = set(range(1, len(lines) + 1))
    except SyntaxError:
        python_rows = set()
        for row, line in enumerate(lines, 1):
            try:
                tree = ast.parse(line.strip())
            except SyntaxError:
                continue
            # A bare name can be a shell command, e.g. `blender`.
            if tree.body and not any(
                isinstance(node, ast.Expr) and not isinstance(node.value, ast.Call)
                for node in tree.body
            ):
                python_rows.add(row)
    # A bare command is also valid Python syntax; retain it for shell checks.
    for row, line in enumerate(lines, 1):
        if re.fullmatch(r"\s*[\w.-]+\s*", line):
            python_rows.discard(row)
    try:
        for token in tokenize.generate_tokens(io.StringIO(script).readline):
            row, col = token.start
            end_row, end_col = token.end
            if row != end_row or row > len(lines):
                continue
            if token.type == tokenize.COMMENT or (
                not comments_only and token.type == tokenize.NAME and row in python_rows
            ):
                lines[row - 1] = lines[row - 1][:col] + " " * (end_col - col) + lines[row - 1][end_col:]
    except (tokenize.TokenError, IndentationError):
        pass
    return "".join(lines)


def _check_direct_editors(script: str) -> None:
    if _DIRECT_EDIT_RE.search(_command_check_text(script)):
        raise CliPolicyViolation(
            "direct text-editor or in-place patch operations are not allowed; drive the target application instead"
        )


def _check_imports(script: str, policy: _TaskPolicy) -> None:
    for module in _iter_imported_modules(script):
        if module in policy.allowed_imports:
            continue
        if module in _DISALLOWED_IMPORTS:
            raise CliPolicyViolation(
                f"Python import {module!r} is not allowed for this CLI task; use the target application's official API"
            )
        if policy.domain and module not in _STDLIB_MODULES:
            raise CliPolicyViolation(
                f"Python import {module!r} is not allowed for this CLI task; use the target application's official API"
            )


def _check_cross_software(script: str, policy: _TaskPolicy) -> None:
    script = _command_check_text(script)
    allowed = {_strip_command_suffix(c) for c in policy.allowed_commands}
    lowered = script.lower()
    for cmd in _KNOWN_SOFTWARE_COMMANDS:
        norm = _strip_command_suffix(cmd)
        if norm in allowed:
            continue
        pattern = re.compile(
            rf"(?i)(^|[\\/\s'\";&|]){re.escape(norm)}"
            rf"(?:\.(?:exe|bat|cmd|ps1|sh))?(?=$|[\\/\s'\";&|])"
        )
        if pattern.search(lowered):
            raise CliPolicyViolation(
                f"calling non-target software command {norm!r} is not allowed for {policy.domain or 'this'} CLI task"
            )
    for token in _iter_command_like_tokens(script):
        cmd = _strip_command_suffix(token)
        if cmd in _KNOWN_SOFTWARE_COMMANDS and cmd not in allowed:
            raise CliPolicyViolation(
                f"calling non-target software command {cmd!r} is not allowed for {policy.domain or 'this'} CLI task"
            )


def _path_ext(path: str) -> str:
    clean = path.strip().strip('"').strip("'")
    clean = clean.replace("\\", "/").split("/")[-1]
    lowered = clean.lower()
    for ext in sorted(_ARTIFACT_EXTENSIONS | _HELPER_EXTENSIONS, key=len, reverse=True):
        if lowered.endswith(ext):
            return ext
    return os.path.splitext(lowered)[1]


def _check_redirect_artifact_writes(script: str) -> None:
    for match in _REDIRECT_WRITE_RE.finditer(script):
        target = match.group(1)
        ext = _path_ext(target)
        if ext in _ARTIFACT_EXTENSIONS and ext not in _HELPER_EXTENSIONS:
            raise CliPolicyViolation(
                f"directly writing artifact file {target!r} is not allowed; produce it through the target application"
            )


def _declared_input_read_with_target(
    script: str,
    policy: _TaskPolicy,
    task_config: Optional[dict],
) -> bool:
    """Allow a narrow open-task handoff probe before a candidate app starts.

    Some neutral-input tasks need one shell action to inspect a declared input
    and then pass that input to a candidate application. This is different
    from reading an undeclared answer/evaluator artifact or fabricating output.
    """
    if (task_config or {}).get("_engiworld_task_family") not in {"software-selection", "open"}:
        return False
    if not (_script_uses_target_api(script, policy) or _script_uses_target_command(script, policy)):
        return False
    declared = _task_input_names(task_config)
    if not declared:
        return False
    mentions = {
        match.group(1).lower()
        for match in re.finditer(
            rf"(?i)(?<![A-Za-z0-9_.-])([A-Za-z0-9_.-]+(?:{_ARTIFACT_EXT_RE}))(?=$|[^A-Za-z0-9_])",
            script.replace("\\", "/"),
        )
    }
    return bool(mentions) and mentions <= declared


def _check_shell_artifact_file_ops(
    script: str,
    policy: _TaskPolicy,
    task_config: Optional[dict],
) -> None:
    allow_declared_input_read = _declared_input_read_with_target(script, policy, task_config)
    if _SHELL_ARTIFACT_COPY_MOVE_RE.search(script):
        raise CliPolicyViolation(
            "copying or moving engineering artifact files directly is not allowed; produce them through the target application"
        )
    if _SHELL_ARTIFACT_BINARY_WRITE_RE.search(script):
        raise CliPolicyViolation(
            "direct shell or PowerShell writes to engineering artifact files are not allowed; drive the target application instead"
        )
    if _SHELL_ARTIFACT_INSPECT_RE.search(script) and not allow_declared_input_read:
        raise CliPolicyViolation(
            "direct shell inspection of engineering artifact files is not allowed; use the target application's CLI/API"
        )
    artifact_vars = _shell_artifact_variable_names(script)
    if (
        artifact_vars
        and _uses_artifact_variable_shell_file_tool(script, artifact_vars)
        and not allow_declared_input_read
    ):
        raise CliPolicyViolation(
            "direct shell inspection or copying of engineering artifact variables is not allowed; use the target application's CLI/API"
        )


def _shell_artifact_variable_names(script: str) -> FrozenSet[str]:
    names = {match.group(1) for match in _SHELL_ARTIFACT_ASSIGN_RE.finditer(script)}
    names.update(match.group(1) for match in _SHELL_ARTIFACT_FOR_RE.finditer(script))
    names.update(match.group(1) for match in _POWERSHELL_ARTIFACT_ASSIGN_RE.finditer(script))
    return frozenset(names)


def _uses_artifact_variable_shell_file_tool(script: str, names: FrozenSet[str]) -> bool:
    if not names:
        return False
    escaped = "|".join(re.escape(name) for name in sorted(names, key=len, reverse=True))
    shell_var = rf"(?:\$\{{?(?:{escaped})\}}?|%(?:{escaped})%)"
    return bool(re.search(
        rf"""(?ixm)
        (?:^|[;&|])\s*
        (?:strings|xxd|hexdump|od|cat|head|tail|grep|awk|sed(?:\s+-n)?|file|stat|
           cp|mv|copy|move|robocopy|xcopy|Copy-Item|Move-Item|Get-Content|Select-String)\b
        [^\n;&|]*{shell_var}
        """,
        script,
    ))


def _artifact_variable_names(script: str) -> FrozenSet[str]:
    return frozenset(match.group(1) for match in _PY_ARTIFACT_ASSIGN_RE.finditer(script))


def _uses_artifact_variable_file_io(script: str) -> bool:
    names = _artifact_variable_names(script)
    if not names:
        return False
    escaped = "|".join(re.escape(name) for name in sorted(names, key=len, reverse=True))
    return bool(re.search(
        rf"""(?ix)
        open\s*\(\s*(?:{escaped})\b
        |
        \b(?:{escaped})\s*\.\s*(?:read|read_text|read_bytes|write|write_text|write_bytes)\s*\(
        |
        Path\s*\(\s*(?:{escaped})\b
        """,
        script,
    ))


def _uses_artifact_variable_generic_write(script: str) -> bool:
    names = _artifact_variable_names(script)
    if not names:
        return False
    escaped = "|".join(re.escape(name) for name in sorted(names, key=len, reverse=True))
    return bool(re.search(
        rf"""(?ix)
        open\s*\(\s*(?:{escaped})\b[^\n,]*,\s*["'][^"']*[wax+][^"']*["']
        |
        \b(?:{escaped})\s*\.\s*(?:write|write_text|write_bytes)\s*\(
        |
        Path\s*\(\s*(?:{escaped})\b[^\n)]*\)\s*\.\s*
        (?:write_text|write_bytes|open\s*\(\s*["'][^"']*[wax+][^"']*["'])
        """,
        script,
    ))


def _without_process_stream_reads(script: str) -> str:
    """Exclude reads of known subprocess stdout/stderr from file-read checks."""
    try:
        tree = ast.parse(script)
    except (SyntaxError, ValueError):
        return script
    processes = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        if (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                and func.value.id == 'subprocess' and func.attr in {'Popen', 'run'}):
            processes.update(target.id for target in node.targets if isinstance(target, ast.Name))
    if not processes:
        return script
    names = '|'.join(re.escape(name) for name in processes)
    return re.sub(rf'\b(?:{names})\s*\.\s*(?:stdout|stderr)\s*\.\s*read\s*\(',
                  'process_output(', script)


def _without_http_response_reads(script: str) -> str:
    """Exclude HTTP response reads while retaining file URLs and file handles."""
    try:
        tree = ast.parse(script)
    except (SyntaxError, ValueError):
        return script
    aliases = {}
    bindings = {}
    rebound = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                aliases[item.asname or item.name.split('.')[0]] = item.name if item.asname else item.name.split('.')[0]
        elif isinstance(node, ast.ImportFrom):
            for item in node.names:
                aliases[item.asname or item.name] = f'{node.module}.{item.name}'
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id in bindings:
                        rebound.add(target.id)
                    bindings[target.id] = node.value
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if isinstance(item.optional_vars, ast.Name):
                    target = item.optional_vars.id
                    if target in bindings:
                        rebound.add(target)
                    bindings[target] = item.context_expr
    def name(node):
        if isinstance(node, ast.Name):
            return aliases.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            return name(node.value) + '.' + node.attr
        return ''
    def http_url(node, seen=frozenset()):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value.lower().startswith(('http://', 'https://'))
        if isinstance(node, ast.JoinedStr) and node.values:
            return http_url(node.values[0], seen)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return http_url(node.left, seen)
        if isinstance(node, ast.Name) and node.id not in seen and node.id not in rebound:
            return http_url(bindings.get(node.id), seen | {node.id})
        if isinstance(node, ast.Call) and name(node.func) == 'urllib.request.Request':
            return bool(node.args) and http_url(node.args[0], seen)
        return False
    response_names = set()
    for node in ast.walk(tree):
        assignments = []
        if isinstance(node, ast.Assign):
            assignments = [(target, node.value) for target in node.targets]
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            assignments = [(item.optional_vars, item.context_expr) for item in node.items]
        for target, value in assignments:
            if (isinstance(target, ast.Name) and target.id not in rebound
                    and isinstance(value, ast.Call) and name(value.func) == 'urllib.request.urlopen'
                    and value.args and http_url(value.args[0])):
                response_names.add(target.id)
        if isinstance(node, ast.ExceptHandler) and node.name and name(node.type) == 'urllib.error.HTTPError':
            response_names.add(node.name)
    if not response_names:
        return script
    names = '|'.join(re.escape(n) for n in sorted(response_names))
    return re.sub(rf'\b(?:{names})\s*\.\s*read\s*\(', 'http_response_body(', script)


def _without_helper_file_io(script: str) -> str:
    """Identify helper sources and logs by the file being opened, not nearby text."""
    try:
        tree = ast.parse(script)
    except (SyntaxError, ValueError):
        return re.sub(
            r'''\bopen(?=\s*\(\s*[rRuU]?["'][^"'\n]*\.(?:py|cs|ps1|sh|scr|lsp|scad|pas|tcl)["']\s*,\s*["'][wax]b?["']\s*[,\)])''',
            'helper_source_open', script,
        )
    bindings = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bindings.setdefault(target.id, []).append(node.value)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if isinstance(item.optional_vars, ast.Name):
                    bindings.setdefault(item.optional_vars.id, []).append(item.context_expr)
        elif isinstance(node, ast.arg):
            bindings.setdefault(node.arg, []).append(None)
    def path_value(node, seen=frozenset()):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name) and node.id not in seen:
            values = bindings.get(node.id, [])
            if len(values) == 1:
                return path_value(values[0], seen | {node.id})
        if isinstance(node, ast.Call):
            function = ast.unparse(node.func)
            if function in {'Path', 'pathlib.Path'} and len(node.args) == 1:
                return path_value(node.args[0], seen)
            if function == 'os.path.join':
                values = [path_value(arg, seen) for arg in node.args]
                if values and all(value is not None for value in values):
                    return '/'.join(values)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Div)):
            left, right = path_value(node.left, seen), path_value(node.right, seen)
            if left is not None and right is not None:
                return left + ('/' if isinstance(node.op, ast.Div) else '') + right
        return None
    helper_extensions = _HELPER_EXTENSIONS | {'.cs', '.lsp', '.scad', '.pas', '.tcl', '.vbs'}
    def helper_path(node):
        value = path_value(node)
        return value is not None and _path_ext(value) in helper_extensions and _path_ext(value) not in _ARTIFACT_EXTENSIONS
    def helper_open(node):
        return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'open' and node.args and helper_path(node.args[0]))
    handles = {name for name, values in bindings.items() if values and all(helper_open(value) for value in values)}
    for node in ast.walk(tree):
        if helper_open(node):
            node.func = ast.Name(id='helper_file_open', ctx=ast.Load())
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {'read', 'read_text', 'read_bytes'}:
            receiver = node.func.value
            if ((isinstance(receiver, ast.Name) and receiver.id in handles)
                    or helper_path(receiver)
                    or helper_open(receiver)
                    or (isinstance(receiver, ast.Call) and isinstance(receiver.func, ast.Name) and receiver.func.id == 'helper_file_open')):
                node.func.attr = 'helper_file_read'
    return ast.unparse(tree)


def _check_python_artifact_bypass(
    script: str,
    policy: _TaskPolicy,
    task_config: Optional[dict],
) -> None:
    has_artifact_path = bool(_ARTIFACT_PATH_RE.search(script))
    if _PY_ARTIFACT_LITERAL_WRITE_RE.search(script):
        raise CliPolicyViolation(
            "direct Python writes to engineering artifact files are not allowed; produce them through the target application"
        )
    if _uses_artifact_variable_generic_write(script):
        raise CliPolicyViolation(
            "direct Python writes to engineering artifact files are not allowed; produce them through the target application"
        )
    if _MACHINE_CODE_PATH_RE.search(script) and _PY_GENERIC_WRITE_RE.search(script):
        raise CliPolicyViolation(
            "hand-writing machine code is not allowed; generate it with the target CAM application's official postprocessor"
        )
    if not has_artifact_path:
        return

    uses_target_api = _script_uses_target_api(script, policy)
    allow_declared_input_read = _declared_input_read_with_target(script, policy, task_config)
    artifact_var_io = _uses_artifact_variable_file_io(script)
    if _PY_ARTIFACT_MUTATION_RE.search(script):
        raise CliPolicyViolation(
            "direct Python copying, renaming, or byte-writing of engineering artifacts is not allowed"
        )
    if (
        not uses_target_api
        and not allow_declared_input_read
        and (artifact_var_io or has_artifact_path)
        and _PY_GENERIC_READ_RE.search(_without_helper_file_io(_without_http_response_reads(_without_process_stream_reads(script))))
    ):
        raise CliPolicyViolation(
            "direct Python inspection of engineering artifact files is not allowed; use the target application's CLI/API"
        )
    if not uses_target_api and _PY_BINARY_PARSE_RE.search(script):
        raise CliPolicyViolation(
            "manual binary parsing or patching of engineering artifacts is not allowed; use the target application's CLI/API"
        )
    if not uses_target_api and _PY_ARTIFACT_READ_RE.search(script) and _PY_BINARY_PARSE_RE.search(script):
        raise CliPolicyViolation(
            "manual parsing of engineering artifact files is not allowed; use the target application's CLI/API"
        )




def _check_desktop_access_bypass(script: str) -> None:
    if _CLI_DESKTOP_CAPTURE_RE.search(script) or re.search(
        r"\b(?:import\s+PIL\.ImageGrab|from\s+PIL\.ImageGrab\s+import|from\s+PIL\s+import\s+[^;\n]*\bImageGrab\b)",
        script,
    ):
        raise CliPolicyViolation(
            "capturing the desktop is not allowed in CLI tasks; use readimg for task drawings or visual files "
            "produced by the required application"
        )
    if _CLI_DESKTOP_INPUT_RE.search(script):
        raise CliPolicyViolation(
            "controlling the desktop mouse or keyboard from a terminal action is not allowed in CLI tasks"
        )


def validate_cli_action(
    kind: str,
    script: str,
    task_config: Optional[dict] = None,
    *,
    text_only: bool = False,
) -> None:
    """Validate a terminal-mode action before it is sent to the VM.

    Raises:
        CliPolicyViolation: if the action tries a known non-target bypass.
    """
    if kind not in {"bash", "python"}:
        return
    script = script or ""
    if kind == "python":
        script = _command_check_text(script, comments_only=True)
    policy = _policy_for(task_config)
    _check_desktop_access_bypass(script)
    # Observation profiles gate readimg in the runner; programmatic image
    # processing has the same permissions in both terminal profiles.
    _check_evaluation_material_and_archives(script, task_config)
    _check_encoded_execution(script)
    _check_package_install(script)
    _check_direct_editors(script)
    _check_imports(script, policy)
    _check_cross_software(script, policy)
    _check_shell_artifact_file_ops(script, policy, task_config)
    _check_redirect_artifact_writes(script)
    _check_python_artifact_bypass(script, policy, task_config)
    _check_task_bound_file_bypass(script, policy, task_config)
