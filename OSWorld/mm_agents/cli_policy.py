"""Policy checks for Engiworld CLI-mode actions.

CLI tasks are intended to be solved by driving the target engineering
application's command-line, batch, or official scripting interface.  This
module performs a conservative pre-execution check for common bypasses: direct
artifact editing, third-party Python packages that parse/generate engineering
files, package installation, and invoking a different CAD/CAE application.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from typing import Dict, FrozenSet, Iterable, Optional


class CliPolicyViolation(ValueError):
    """Raised when a terminal-mode action attempts a disallowed bypass."""


CLI_POLICY_PROMPT = (
    "=== CLI task integrity rules ===\n"
    "Use the command-line, batch, headless, or official scripting interface of the required "
    "application(s) to perform the engineering work. The CLI is for driving the required "
    "software, not for replacing it with unrelated file manipulation.\n"
    "The following are forbidden and will be rejected before execution:\n"
    "- Directly reading, inspecting, editing, patching, copying, or fabricating the project/model/answer "
    "artifact with text, binary, shell, or generic Python file tools instead of using the required application(s).\n"
    "  Examples include `cat`, `grep`, `head`, `tail`, `strings`, `xxd`, `hexdump`, `file`, `stat`, "
    "Python `open`, `Path.read_text/read_bytes`, `Path.write_text/write_bytes`, `shutil.copy*`, "
    "`os.rename`, and `os.replace` on engineering artifact files, including when the artifact path is "
    "hidden behind a shell or Python variable.\n"
    "- Installing or using third-party Python packages to parse, generate, repair, or convert "
    "engineering files, unless the package is the required application(s)' own official Python API.\n"
    "- Importing or using non-stdlib Python packages unless they are the required application(s)' official API.\n"
    "- Calling another CAD/CAE/EDA/BIM/graphics application or converter to do the required "
    "application(s)' work.\n"
    "- Using interactive text editors or in-place patchers such as vim, nano, notepad, "
    "`sed -i`, `perl -pi`, PowerShell `Set-Content`, or similar direct-edit operations.\n"
    "You may create temporary helper scripts, batch files, logs, and solver input files when "
    "they are used to drive the required application(s)."
)


_STDLIB_MODULES: FrozenSet[str] = frozenset(getattr(sys, "stdlib_module_names", ())) | {
    "__future__",
    "winreg",
}

_BASE_ALLOWED_IMPORTS: FrozenSet[str] = _STDLIB_MODULES | frozenset({
    # Common Windows automation used only to launch/drive the target app.
    "win32api",
    "win32com",
    "win32con",
    "win32gui",
    "pythoncom",
    "pywintypes",
})

_TARGET_IMPORTS: Dict[str, FrozenSet[str]] = {
    "abaqus": frozenset({
        "abaqus", "abaqusConstants", "caeModules", "odbAccess", "regionToolset",
        "mesh", "part", "material", "section", "assembly", "step", "interaction",
        "load", "job", "sketch", "visualization", "xyPlot", "displayGroupOdbToolset",
        "connectorBehavior", "driverUtils",
    }),
    "ansys": frozenset({"ansys", "pyansys", "mapdl", "fluent"}),
    "archicad": frozenset({"archicad"}),
    "blender": frozenset({"bpy", "bmesh", "mathutils"}),
    "bonsai": frozenset({"bpy", "bmesh", "mathutils", "ifcopenshell", "bonsai"}),
    "calculix": frozenset({"ccx", "cgx"}),
    "fenics": frozenset({"fenics", "dolfin", "dolfinx", "ufl", "mshr", "petsc4py"}),
    "floris": frozenset({"floris"}),
    "freecad": frozenset({
        "FreeCAD", "FreeCADGui", "Part", "Mesh", "Draft", "Import", "Arch",
        "Sketcher", "TechDraw",
    }),
    "freecad-path": frozenset({
        "FreeCAD", "FreeCADGui", "Part", "Mesh", "Draft", "Import", "Arch",
        "Sketcher", "TechDraw", "Path", "PathScripts",
    }),
    "kicad": frozenset({"pcbnew"}),
    "openstudio": frozenset({"openstudio"}),
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
    "solidcam": frozenset({"solidcam"}),
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
    "olefile", "pandas", "numpy", "scipy", "skimage", "cv2", "PIL", "matplotlib",
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
    r"(?im)(?<![/\\\w.-])(?:vim|vi|nano|notepad|code(?:\.exe)?)(?=$|[\s;&|])|"
    r"\bsed\b[^\n;&|]*\s-i(?:\b|[A-Za-z])|\bperl\b[^\n;&|]*\s-\S*pi\S*|"
    r"(?<![A-Za-z])ed\s+"
)

_IMPORT_LINE_RE = re.compile(r"(?m)^\s*import\s+([^\n#]+)")
_FROM_IMPORT_LINE_RE = re.compile(r"(?m)^\s*from\s+([A-Za-z_][\w.]*)\s+import\b")
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
    ".sldasm", ".slddrw", ".slvs", ".scad",
    ".opj", ".olb", ".dra", ".pad", ".pln", ".pla", ".gsm", ".mod",
    ".wbpj", ".agdb", ".mechdat", ".rst", ".cas", ".dat.h5",
})

_HELPER_EXTENSIONS: FrozenSet[str] = frozenset({
    ".py", ".pyw", ".sh", ".bash", ".bat", ".cmd", ".ps1", ".jou", ".jnl",
    ".scr", ".mac", ".inp", ".dat", ".json", ".csv", ".txt", ".log",
})

_ARTIFACT_EXT_RE = "|".join(
    re.escape(ext) for ext in sorted(_ARTIFACT_EXTENSIONS, key=len, reverse=True)
)
_ARTIFACT_PATH_RE = re.compile(rf"(?i)(?:{_ARTIFACT_EXT_RE})(?=$|[^A-Za-z0-9_])")

_IMAGE_EXTENSIONS: FrozenSet[str] = frozenset({
    ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff", ".ico",
})
_IMAGE_EXT_RE = "|".join(
    re.escape(ext) for ext in sorted(_IMAGE_EXTENSIONS, key=len, reverse=True)
)

_TEXT_ONLY_SHELL_VISUAL_RE = re.compile(
    r"""(?ix)
    (?<![A-Za-z0-9_./\\-])
    (?:
        gnome-screenshot|scrot|maim|grim|spectacle|flameshot|xwd|screencapture|
        snippingtool|snippingtool\.exe|magick|convert|identify|display|eog|feh|
        ristretto|shotwell|xdg-open|tesseract|pdfimages|pdftoppm|
        mutool\s+draw
    )
    (?:\.(?:exe|bat|cmd|ps1|sh))?
    (?=$|[\s'";&|()])
    """
)
_TEXT_ONLY_SHELL_IMAGE_FILE_RE = re.compile(
    rf"""(?ixm)
    (?:^|[;&|])\s*
    (?:cat|head|tail|strings|file|stat|xxd|hexdump|od|base64|identify|magick|convert|display|tesseract)\b
    [^\n;&|]*(?:{_IMAGE_EXT_RE})(?=$|[^A-Za-z0-9_])
    """
)
_TEXT_ONLY_PY_VISUAL_RE = re.compile(
    r"""(?ix)
    \bpyautogui\s*\.\s*screenshot\s*\(
    |
    \bImageGrab\s*\.\s*grab\s*\(
    |
    \bmss\s*\.
    |
    \bpyscreenshot\b
    |
    \b(?:Image|PIL\.Image)\s*\.\s*open\s*\(
    |
    \bcv2\s*\.\s*imread\s*\(
    |
    \b(?:plt|matplotlib\.pyplot|matplotlib\.image)\s*\.\s*imread\s*\(
    """
)
_TEXT_ONLY_PY_IMAGE_FILE_RE = re.compile(
    rf"""(?ixs)
    open\s*\([^)\n]*(?:{_IMAGE_EXT_RE})[^)\n]*,\s*["'][^"']*r[^"']*["']
    |
    Path\s*\([^)\n]*(?:{_IMAGE_EXT_RE})[^)\n]*\)\s*\.\s*open\s*\(
    |
    Path\s*\([^)\n]*(?:{_IMAGE_EXT_RE})[^)\n]*\)\s*\.\s*(?:read_text|read_bytes)
    """
)
_TEXT_ONLY_PY_IMAGE_CMD_RE = re.compile(
    rf"""(?ix)
    (?:cat|head|tail|strings|file|stat|xxd|hexdump|od|base64|identify|magick|convert|display|tesseract)\b
    [^\n]*(?:{_IMAGE_EXT_RE})(?=$|[^A-Za-z0-9_])
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
    (?:strings|xxd|hexdump|od|cat|head|tail|grep|awk|sed(?:\s+-n)?|file|stat)\b
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
    rf"""(?ixs)
    open\s*\([^)\n]*(?:{_ARTIFACT_EXT_RE})[^)\n]*,\s*["'][^"']*[wa+][^"']*["']
    |
    Path\s*\([^)\n]*(?:{_ARTIFACT_EXT_RE})[^)\n]*\)\s*\.\s*(?:write_text|write_bytes)
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
    open\s*\([^)\n]*(?:,\s*["'][^"']*r[^"']*["'])?
    |
    \.\s*(?:read|read_text|read_bytes)\s*\(
    """
)
_PY_ARTIFACT_ASSIGN_RE = re.compile(
    rf"""(?ix)
    \b([A-Za-z_]\w*)\s*=\s*
    (?:
        Path\s*\(\s*
    )?
    [rRuUbBfF]*["'][^"']*(?:{_ARTIFACT_EXT_RE})[^"']*["']
    """
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


def _check_package_install(script: str) -> None:
    if _PACKAGE_MANAGER_RE.search(script):
        raise CliPolicyViolation(
            "package installation is not allowed during CLI evaluation; use the target application's installed CLI/API"
        )


def _check_direct_editors(script: str) -> None:
    if _DIRECT_EDIT_RE.search(script):
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


def _check_shell_artifact_file_ops(script: str) -> None:
    if _SHELL_ARTIFACT_COPY_MOVE_RE.search(script):
        raise CliPolicyViolation(
            "copying or moving engineering artifact files directly is not allowed; produce them through the target application"
        )
    if _SHELL_ARTIFACT_BINARY_WRITE_RE.search(script):
        raise CliPolicyViolation(
            "direct shell or PowerShell writes to engineering artifact files are not allowed; drive the target application instead"
        )
    if _SHELL_ARTIFACT_INSPECT_RE.search(script):
        raise CliPolicyViolation(
            "direct shell inspection of engineering artifact files is not allowed; use the target application's CLI/API"
        )
    artifact_vars = _shell_artifact_variable_names(script)
    if artifact_vars and _uses_artifact_variable_shell_file_tool(script, artifact_vars):
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


def _check_python_artifact_bypass(script: str, policy: _TaskPolicy) -> None:
    has_artifact_path = bool(_ARTIFACT_PATH_RE.search(script))
    if _PY_ARTIFACT_LITERAL_WRITE_RE.search(script):
        raise CliPolicyViolation(
            "direct Python writes to engineering artifact files are not allowed; produce them through the target application"
        )
    if not has_artifact_path:
        return

    uses_target_api = _script_uses_target_api(script, policy)
    artifact_var_io = _uses_artifact_variable_file_io(script)
    if not uses_target_api and artifact_var_io and _PY_GENERIC_WRITE_RE.search(script):
        raise CliPolicyViolation(
            "direct Python writes to engineering artifact files are not allowed; produce them through the target application"
        )
    if not uses_target_api and _PY_ARTIFACT_MUTATION_RE.search(script):
        raise CliPolicyViolation(
            "direct Python copying, renaming, or byte-writing of engineering artifacts is not allowed"
        )
    if not uses_target_api and (artifact_var_io or has_artifact_path) and _PY_GENERIC_READ_RE.search(script):
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


def _check_text_only_visual_bypass(kind: str, script: str) -> None:
    if _TEXT_ONLY_SHELL_VISUAL_RE.search(script) or _TEXT_ONLY_PY_VISUAL_RE.search(script):
        raise CliPolicyViolation(
            "screen capture and image-reading Python code is not allowed in cli-text mode"
        )
    if _TEXT_ONLY_PY_IMAGE_FILE_RE.search(script) or _TEXT_ONLY_PY_IMAGE_CMD_RE.search(script):
        raise CliPolicyViolation(
            "reading raster image files is not allowed in cli-text mode; use only textual terminal output"
        )
    if kind == "bash":
        if _TEXT_ONLY_SHELL_VISUAL_RE.search(script):
            raise CliPolicyViolation(
                "screenshot, image-viewing, OCR, or image-rendering commands are not allowed in cli-text mode"
            )
        if _TEXT_ONLY_SHELL_IMAGE_FILE_RE.search(script):
            raise CliPolicyViolation(
                "shell inspection of raster image files is not allowed in cli-text mode"
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
    policy = _policy_for(task_config)
    if text_only:
        _check_text_only_visual_bypass(kind, script)
    _check_package_install(script)
    _check_direct_editors(script)
    _check_imports(script, policy)
    _check_cross_software(script, policy)
    _check_shell_artifact_file_ops(script)
    _check_redirect_artifact_writes(script)
    _check_python_artifact_bypass(script, policy)
