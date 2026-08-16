# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path


TASK_ID = "c-open-abaqus-ansys-autocad-task-15-windows"
DESKTOP_CANDIDATES = [
    Path(os.environ.get("USERPROFILE", r"C:\Users\user")) / "Desktop",
    Path(r"C:\Users\user\Desktop"),
    Path(r"C:\Users\User\Desktop"),
]
ABAQUS_LAUNCHER = r"C:\SIMULIA\CAE\2025LE\win_b64\code\bin\SMALauncherLE.exe"
ANSYS_EXEC = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
DETAILS = []


def log(message):
    DETAILS.append(str(message))


def desktop_dir():
    for path in DESKTOP_CANDIDATES:
        if path.is_dir():
            return path
    return DESKTOP_CANDIDATES[1]


def nonempty(path):
    try:
        return path.is_file() and path.stat().st_size > 0
    except Exception:
        return False


def run_owned(command, cwd, timeout):
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=creationflags,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=60,
            )
        else:
            process.kill()
        try:
            process.communicate(timeout=30)
        except Exception:
            pass
        raise RuntimeError("native solver validation timed out")
    return {"returncode": process.returncode, "stdout": stdout, "stderr": stderr}


def cleanup_owned_processes(work):
    if os.name != "nt":
        return
    time.sleep(1.0)
    query = (
        "Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,Name,ExecutablePath,CommandLine | "
        "ConvertTo-Json -Compress"
    )
    execution = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", query],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if execution.returncode != 0:
        raise RuntimeError("cannot inventory native solver cleanup processes")
    rows = [] if not execution.stdout.strip() else json.loads(execution.stdout)
    if isinstance(rows, dict):
        rows = [rows]
    marker = str(work).lower()
    allowed = {
        "python.exe",
        "ansys.exe",
        "ansys261.exe",
        "ansyscl.exe",
        "smalauncherle.exe",
        "abqlauncher.exe",
        "abq2025le.exe",
        "pre.exe",
        "standard.exe",
        "package.exe",
        "mpiexec.exe",
        "hydra_service.exe",
        "hydra_bstrap_proxy.exe",
        "hydra_pmi_proxy.exe",
    }
    matched = []
    for row in rows:
        command = str(row.get("CommandLine") or "")
        if marker not in command.lower():
            continue
        executable = Path(str(row.get("ExecutablePath") or ""))
        name = (executable.name or str(row.get("Name") or "")).lower()
        if name not in allowed:
            raise RuntimeError("unsafe native cleanup process match: %r" % row)
        pid = int(row.get("ProcessId") or 0)
        if pid > 0 and pid != os.getpid():
            matched.append(pid)
    for pid in sorted(set(matched), reverse=True):
        stopped = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if stopped.returncode not in (0, 128):
            probe = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-Command",
                    "Get-CimInstance Win32_Process -Filter 'ProcessId=%s' | ConvertTo-Json -Compress" % pid,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if probe.returncode != 0 or probe.stdout.strip():
                raise RuntimeError("cannot stop owned native solver process %s" % pid)


def files(root, suffix):
    return sorted(
        [path for path in root.iterdir() if nonempty(path) and path.suffix.lower() == suffix],
        key=lambda path: path.name.lower(),
    )


def finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def strict_json_object(path):
    def pairs(values):
        output = {}
        for key, value in values:
            if key in output:
                raise ValueError("duplicate JSON key: %s" % key)
            output[key] = value
        return output

    def invalid_constant(value):
        raise ValueError("non-finite JSON value: %s" % value)

    return json.loads(
        path.read_text(encoding="utf-8-sig"),
        object_pairs_hook=pairs,
        parse_constant=invalid_constant,
    )


def load_metrics(root):
    path = root / "metrics.json"
    if not nonempty(path):
        raise RuntimeError("metrics.json is missing")
    data = strict_json_object(path)
    if not isinstance(data, dict) or set(data) != {"first_frequency", "frequency_list"}:
        raise RuntimeError("metrics.json must contain exactly first_frequency and frequency_list")
    frequencies = data.get("frequency_list")
    if not isinstance(frequencies, list) or len(frequencies) != 3:
        raise RuntimeError("frequency_list must contain exactly three values")
    if any(not finite_number(value) or float(value) <= 0.0 for value in frequencies):
        raise RuntimeError("frequency_list values must be finite positive numbers")
    if any(float(frequencies[index]) > float(frequencies[index + 1]) for index in range(2)):
        raise RuntimeError("frequency_list must be nondecreasing")
    first = data.get("first_frequency")
    if not finite_number(first) or float(first) <= 0.0:
        raise RuntimeError("first_frequency must be a finite positive number")
    if not math.isclose(float(first), float(frequencies[0]), rel_tol=2.0e-3, abs_tol=0.1):
        raise RuntimeError("first_frequency must equal frequency_list[0]")
    return [float(value) for value in frequencies]


def select_branch(root):
    caes = files(root, ".cae")
    odbs = files(root, ".odb")
    dbs = files(root, ".db")
    rsts = files(root, ".rst")
    unsupported = files(root, ".rth") + files(root, ".wbpj")
    if unsupported:
        raise RuntimeError("unsupported or wrong-analysis native artifact is present")
    has_abaqus = bool(caes or odbs)
    has_ansys = bool(dbs or rsts)
    if has_abaqus and has_ansys:
        raise RuntimeError("mixed Abaqus and ANSYS native artifacts are ambiguous")
    if has_abaqus:
        if len(caes) != 1 or len(odbs) != 1:
            raise RuntimeError("exactly one Abaqus CAE/ODB pair is required")
        return "abaqus", caes[0], odbs[0]
    if has_ansys:
        if len(dbs) != 1 or len(rsts) != 1:
            raise RuntimeError("exactly one ANSYS DB/RST pair is required")
        return "ansys", dbs[0], rsts[0]
    raise RuntimeError("no supported native solver artifact pair is present")


def frequency_lists_close(actual, expected, rel_tol=2.0e-3, abs_tol=0.1):
    return len(actual) == len(expected) and all(
        math.isclose(float(left), float(right), rel_tol=rel_tol, abs_tol=abs_tol)
        for left, right in zip(actual, expected)
    )


ABAQUS_CHECKER = r'''# -*- coding: utf-8 -*-
from __future__ import print_function

import builtins
import json
import math
import os
import sys
import traceback

from abaqus import openMdb
from abaqusConstants import ANALYSIS, ISOTROPIC, OFF, PERCENTAGE, SINGLE
from caeModules import *
from odbAccess import openOdb

CAE_PATH = __CAE_PATH__
ODB_PATH = __ODB_PATH__
WORK_DIR = __WORK_DIR__
RESULT_PATH = __RESULT_PATH__
METRICS = __METRICS__


def close(actual, expected, rel_tol=2.0e-3, abs_tol=0.1):
    return math.isclose(float(actual), float(expected), rel_tol=rel_tol, abs_tol=abs_tol)


def exact(actual, expected, rel_tol=2.0e-4, abs_tol=0.02):
    return math.isclose(float(actual), float(expected), rel_tol=rel_tol, abs_tol=abs_tol)


def repo_item(repository, name):
    target = str(name).upper()
    for key in repository.keys():
        if str(key).upper() == target:
            return repository[key]
    raise KeyError(name)


def coordinates(nodes):
    return [tuple(float(value) for value in node.coordinates[:3]) for node in nodes]


def mesh_bounds(nodes):
    rows = coordinates(nodes)
    if not rows:
        raise RuntimeError('mesh has no nodes')
    return {
        'x': (builtins.min(row[0] for row in rows), builtins.max(row[0] for row in rows)),
        'y': (builtins.min(row[1] for row in rows), builtins.max(row[1] for row in rows)),
        'z': (builtins.min(row[2] for row in rows), builtins.max(row[2] for row in rows)),
    }


def resolve_connectivity(nodes, connectivity, uses_node_labels):
    node_list = list(nodes)
    by_label = dict((int(node.label), tuple(float(value) for value in node.coordinates[:3])) for node in node_list)
    values = [int(value) for value in connectivity]
    if uses_node_labels and all(value in by_label for value in values):
        return [(value, by_label[value]) for value in values]
    if not uses_node_labels and all(0 <= value < len(node_list) for value in values):
        return [
            (
                int(node_list[value].label),
                tuple(float(component) for component in node_list[value].coordinates[:3]),
            )
            for value in values
        ]
    raise RuntimeError('mesh connectivity cannot be resolved')


def validate_mesh(nodes, elements, uses_node_labels):
    if len(elements) != 20:
        raise RuntimeError('beam must contain exactly 20 elements')
    element_types = sorted(set(str(element.type).upper() for element in elements))
    if not element_types or any(not (value.startswith('B31') or value.startswith('B32')) for value in element_types):
        raise RuntimeError('elements must use B31/B32 beam formulations: %r' % element_types)
    bb = mesh_bounds(nodes)
    expected_bounds = {'x': (0.0, 500.0), 'y': (0.0, 0.0), 'z': (0.0, 0.0)}
    for axis in expected_bounds:
        if any(abs(bb[axis][index] - expected_bounds[axis][index]) > 1.0e-6 for index in (0, 1)):
            raise RuntimeError('beam bounds are wrong on %s: %r' % (axis, bb[axis]))
    node_signature = dict(
        (int(node.label), tuple(float(value) for value in node.coordinates[:3]))
        for node in nodes
    )
    if len(node_signature) != len(nodes):
        raise RuntimeError('beam mesh contains duplicate node labels')
    spans = []
    graph = {}
    used_node_labels = set()
    endpoint_coordinates = {}
    element_signature = {}
    for element in elements:
        members = resolve_connectivity(nodes, element.connectivity, uses_node_labels)
        if len(members) not in (2, 3):
            raise RuntimeError('beam element connectivity is invalid')
        used_node_labels.update(label for label, point in members)
        element_label = int(element.label)
        if element_label in element_signature:
            raise RuntimeError('beam mesh contains duplicate element labels')
        element_signature[element_label] = (
            str(element.type).upper(),
            tuple(label for label, point in members),
        )
        points = [point for label, point in members]
        if any(abs(point[1]) > 1.0e-6 or abs(point[2]) > 1.0e-6 for point in points):
            raise RuntimeError('beam element is not on global X')
        low = builtins.min(point[0] for point in points)
        high = builtins.max(point[0] for point in points)
        if not math.isclose(high - low, 25.0, rel_tol=1.0e-9, abs_tol=1.0e-6):
            raise RuntimeError('beam element span is not 25 mm')
        ordered = sorted(members, key=lambda item: item[1][0])
        left = ordered[0]
        right = ordered[-1]
        if len(members) == 3:
            middle = ordered[1][1]
            expected_middle = tuple(
                0.5 * (left[1][index] + right[1][index]) for index in range(3)
            )
            if any(abs(middle[index] - expected_middle[index]) > 1.0e-6 for index in range(3)):
                raise RuntimeError('B32 middle node is not at the element midpoint')
        if left[0] == right[0]:
            raise RuntimeError('beam element has identical endpoint nodes')
        graph.setdefault(left[0], set()).add(right[0])
        graph.setdefault(right[0], set()).add(left[0])
        endpoint_coordinates[left[0]] = left[1]
        endpoint_coordinates[right[0]] = right[1]
        spans.append((round(low, 6), round(high, 6)))
    expected_spans = [(float(value), float(value + 25)) for value in range(0, 500, 25)]
    if sorted(spans) != expected_spans:
        raise RuntimeError('mesh is not 20 equal divisions from X=0 to X=500')
    if used_node_labels != set(int(node.label) for node in nodes):
        raise RuntimeError('beam mesh contains orphan or unused nodes')
    if len(graph) != 21:
        raise RuntimeError('beam endpoint topology must contain exactly 21 shared nodes')
    starts = [label for label, point in endpoint_coordinates.items() if abs(point[0]) <= 1.0e-6]
    finishes = [label for label, point in endpoint_coordinates.items() if abs(point[0] - 500.0) <= 1.0e-6]
    if len(starts) != 1 or len(finishes) != 1:
        raise RuntimeError('beam topology does not have unique X=0 and X=500 endpoints')
    for label, neighbors in graph.items():
        expected_degree = 1 if label in (starts[0], finishes[0]) else 2
        if len(neighbors) != expected_degree:
            raise RuntimeError('beam elements do not form one continuous chain')
    visited = set()
    pending = [starts[0]]
    while pending:
        label = pending.pop()
        if label in visited:
            continue
        visited.add(label)
        pending.extend(graph[label] - visited)
    if visited != set(graph):
        raise RuntimeError('beam element chain is disconnected')
    return {
        'bounds': bb,
        'element_types': element_types,
        'nodes': node_signature,
        'elements': element_signature,
    }


def abaqus_flag_enabled(value):
    return str(value).strip().upper() in ('ON', 'TRUE', 'YES', '1')


def material_values(model, section):
    material_name = str(section.material)
    material = repo_item(model.materials, material_name)
    elastic_object = material.elastic
    density_object = material.density
    if str(elastic_object.type).upper() != str(ISOTROPIC).upper():
        raise RuntimeError('Abaqus elastic material must be isotropic')
    if abaqus_flag_enabled(getattr(elastic_object, 'temperatureDependency', OFF)):
        raise RuntimeError('Abaqus elastic material cannot be temperature dependent')
    if int(getattr(elastic_object, 'dependencies', 0)) != 0:
        raise RuntimeError('Abaqus elastic material cannot have field dependencies')
    if abaqus_flag_enabled(getattr(elastic_object, 'noCompression', OFF)) or abaqus_flag_enabled(getattr(elastic_object, 'noTension', OFF)):
        raise RuntimeError('Abaqus elastic material cannot suppress tension or compression')
    if abaqus_flag_enabled(getattr(density_object, 'temperatureDependency', OFF)):
        raise RuntimeError('Abaqus density cannot be temperature dependent')
    if int(getattr(density_object, 'dependencies', 0)) != 0:
        raise RuntimeError('Abaqus density cannot have field dependencies')
    elastic = [[float(value) for value in row] for row in elastic_object.table]
    density = [[float(value) for value in row] for row in density_object.table]
    if len(elastic) != 1 or len(elastic[0]) != 2:
        raise RuntimeError('elastic material table is invalid')
    if not math.isclose(elastic[0][0], 210000.0, rel_tol=2.0e-6) or not math.isclose(elastic[0][1], 0.3, rel_tol=2.0e-6):
        raise RuntimeError('Abaqus E/nu values are wrong')
    if len(density) != 1 or len(density[0]) != 1 or not math.isclose(density[0][0], 7.85e-9, rel_tol=2.0e-6, abs_tol=1.0e-14):
        raise RuntimeError('Abaqus density is wrong')


def parse_keyword(line):
    fields = [value.strip() for value in line[1:].split(',')]
    name = fields[0].upper()
    params = {}
    flags = set()
    for value in fields[1:]:
        if not value:
            continue
        if '=' in value:
            key, item = value.split('=', 1)
            key = key.strip().upper()
            if key in params:
                raise RuntimeError('duplicate Abaqus keyword parameter: %s' % key)
            params[key] = item.strip().upper()
        else:
            flags.add(value.upper())
    return name, params, flags


def parse_input_records(input_path):
    with open(input_path, 'r') as stream:
        lines = stream.readlines()
    records = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line or line.startswith('**'):
            index += 1
            continue
        if not line.startswith('*'):
            raise RuntimeError('Abaqus input contains data outside a keyword record')
        header = line
        index += 1
        while header.rstrip().endswith(','):
            while index < len(lines) and (not lines[index].strip() or lines[index].strip().startswith('**')):
                index += 1
            if index >= len(lines) or lines[index].lstrip().startswith('*'):
                raise RuntimeError('Abaqus keyword continuation is incomplete')
            header += lines[index].strip()
            index += 1
        keyword, params, flags = parse_keyword(header)
        data = []
        while index < len(lines):
            value = lines[index].strip()
            if value.startswith('*') and not value.startswith('**'):
                break
            if value and not value.startswith('**'):
                data.append(value)
            index += 1
        records.append({'keyword': keyword, 'params': params, 'flags': flags, 'data': data})
    if not records:
        raise RuntimeError('Abaqus input deck contains no keyword records')
    part = None
    assembly = None
    instance = None
    step_open = False
    for record in records:
        keyword = record['keyword']
        if keyword == 'PART':
            if part is not None or assembly is not None or step_open:
                raise RuntimeError('Abaqus input has invalid PART nesting')
            part = record['params'].get('NAME')
            if not part:
                raise RuntimeError('Abaqus PART is unnamed')
        elif keyword == 'ASSEMBLY':
            if part is not None or assembly is not None or step_open:
                raise RuntimeError('Abaqus input has invalid ASSEMBLY nesting')
            assembly = record['params'].get('NAME')
            if not assembly:
                raise RuntimeError('Abaqus ASSEMBLY is unnamed')
        elif keyword == 'INSTANCE':
            if assembly is None or instance is not None:
                raise RuntimeError('Abaqus input has invalid INSTANCE nesting')
            instance = record['params'].get('NAME')
            if not instance:
                raise RuntimeError('Abaqus INSTANCE is unnamed')
        elif keyword == 'STEP':
            if part is not None or assembly is not None or step_open:
                raise RuntimeError('Abaqus input has invalid STEP nesting')
            step_open = True
        record['_part'] = part
        record['_assembly'] = assembly
        record['_instance'] = instance
        record['_in_step'] = step_open
        if keyword == 'END INSTANCE':
            if instance is None:
                raise RuntimeError('Abaqus END INSTANCE has no matching INSTANCE')
            instance = None
        elif keyword == 'END ASSEMBLY':
            if assembly is None or instance is not None:
                raise RuntimeError('Abaqus END ASSEMBLY has no matching ASSEMBLY')
            assembly = None
        elif keyword == 'END PART':
            if part is None:
                raise RuntimeError('Abaqus END PART has no matching PART')
            part = None
        elif keyword == 'END STEP':
            if not step_open:
                raise RuntimeError('Abaqus END STEP has no matching STEP')
            step_open = False
    if part is not None or assembly is not None or instance is not None or step_open:
        raise RuntimeError('Abaqus input contains an unterminated block')
    return records


def numeric_fields(line, allow_empty=False):
    output = []
    for token in line.split(','):
        value = token.strip()
        if not value:
            if allow_empty:
                output.append(None)
            continue
        try:
            number = float(value)
        except Exception:
            raise RuntimeError('Abaqus numeric data row is invalid: %s' % line)
        if not math.isfinite(number):
            raise RuntimeError('Abaqus numeric data row contains a non-finite value')
        output.append(number)
    return output


def set_record_entries(record):
    tokens = []
    for line in record['data']:
        tokens.extend([value.strip().upper() for value in line.split(',') if value.strip()])
    if 'GENERATE' in record['flags']:
        if len(tokens) % 3:
            raise RuntimeError('Abaqus generated set definition is invalid')
        output = []
        for offset in range(0, len(tokens), 3):
            try:
                start, finish, increment = [int(tokens[offset + index]) for index in range(3)]
            except Exception:
                raise RuntimeError('Abaqus generated set contains a non-integer value')
            if increment <= 0 or finish < start:
                raise RuntimeError('Abaqus generated set range is invalid')
            output.extend(range(start, finish + 1, increment))
        return output
    output = []
    for token in tokens:
        try:
            output.append(int(token))
        except ValueError:
            output.append(token)
    return output


def resolve_integer_set(repository, key, seen=None):
    seen = set() if seen is None else seen
    if key in seen:
        raise RuntimeError('Abaqus set definition is recursive')
    if key not in repository:
        raise RuntimeError('Abaqus set is undefined: %s' % (key,))
    seen.add(key)
    output = []
    for value in repository[key]:
        if isinstance(value, int):
            output.append(value)
        else:
            reference = (key[0], value)
            output.extend(resolve_integer_set(repository, reference, seen.copy()))
    return output


def audit_input_deck(records, model_mesh, material_name):
    output_keywords = set((
        'OUTPUT', 'NODE OUTPUT', 'ELEMENT OUTPUT', 'ENERGY OUTPUT', 'MODAL OUTPUT',
        'NODE PRINT', 'EL PRINT', 'ENERGY PRINT', 'NODE FILE', 'EL FILE',
        'MODAL FILE',
    ))
    allowed_keywords = set((
        'HEADING', 'PREPRINT', 'PART', 'END PART', 'NODE', 'ELEMENT', 'NSET',
        'ELSET', 'BEAM SECTION', 'ASSEMBLY', 'INSTANCE', 'END INSTANCE',
        'END ASSEMBLY', 'MATERIAL', 'DENSITY', 'ELASTIC', 'DAMPING', 'BOUNDARY',
        'STEP', 'FREQUENCY', 'RESTART', 'END STEP',
    )).union(output_keywords)
    allowed_params = {
        'HEADING': set(),
        'PART': {'NAME'},
        'END PART': set(),
        'NODE': {'NSET'},
        'ELEMENT': {'TYPE', 'ELSET'},
        'NSET': {'NSET', 'INSTANCE'},
        'ELSET': {'ELSET', 'INSTANCE'},
        'BEAM SECTION': {'ELSET', 'MATERIAL', 'SECTION', 'POISSON', 'TEMPERATURE'},
        'ASSEMBLY': {'NAME'},
        'INSTANCE': {'NAME', 'PART'},
        'END INSTANCE': set(),
        'END ASSEMBLY': set(),
        'MATERIAL': {'NAME'},
        'DENSITY': {'DEPENDENCIES'},
        'ELASTIC': {'TYPE', 'DEPENDENCIES'},
        'DAMPING': {'ALPHA', 'BETA', 'COMPOSITE', 'STRUCTURAL'},
        'BOUNDARY': {'OP', 'TYPE'},
        'STEP': {'NAME', 'NLGEOM'},
        'FREQUENCY': {'EIGENSOLVER', 'NORMALIZATION', 'ACOUSTIC COUPLING'},
        'RESTART': {'FREQUENCY', 'NUMBER INTERVALS', 'TIME MARKS', 'OVERLAY'},
        'END STEP': set(),
    }
    allowed_flags = {
        'NSET': {'GENERATE', 'UNSORTED', 'INTERNAL'},
        'ELSET': {'GENERATE', 'UNSORTED', 'INTERNAL'},
        'STEP': {'PERTURBATION'},
        'FREQUENCY': {'SIM'},
        'RESTART': {'WRITE'},
        'OUTPUT': {'FIELD', 'HISTORY'},
    }
    external_params = {'INPUT', 'FILE', 'USER', 'EXTERNAL'}
    for record in records:
        keyword = record['keyword']
        if keyword not in allowed_keywords:
            raise RuntimeError('Abaqus input contains unsupported keyword *%s' % keyword)
        if set(record['params']).intersection(external_params):
            raise RuntimeError('Abaqus input references external or user data')
        expected_params = allowed_params.get(keyword)
        if expected_params is not None and set(record['params']) - expected_params:
            raise RuntimeError('Abaqus *%s contains unsupported parameters' % keyword)
        if record['flags'] - allowed_flags.get(keyword, set()):
            raise RuntimeError('Abaqus *%s contains unsupported flags' % keyword)
        if keyword == 'BOUNDARY' and (record['_part'] is not None or record['_assembly'] is not None):
            raise RuntimeError('Abaqus boundary is in an invalid model-data scope')
        if keyword == 'BOUNDARY':
            if record['params'].get('OP', 'MOD') not in ('MOD', 'NEW'):
                raise RuntimeError('Abaqus boundary operation is unsupported')
            if record['params'].get('TYPE', 'DISPLACEMENT') != 'DISPLACEMENT':
                raise RuntimeError('Abaqus boundary type is unsupported')
        elif keyword == 'RESTART' and 'WRITE' not in record['flags']:
            raise RuntimeError('Abaqus input imports a previous analysis state')
        elif keyword == 'DAMPING':
            for value in record['params'].values():
                try:
                    number = float(value)
                except Exception:
                    raise RuntimeError('Abaqus material damping value is invalid')
                if not math.isfinite(number) or number < 0.0:
                    raise RuntimeError('Abaqus material damping value is invalid')

    steps = [index for index, record in enumerate(records) if record['keyword'] == 'STEP']
    ends = [index for index, record in enumerate(records) if record['keyword'] == 'END STEP']
    frequencies = [index for index, record in enumerate(records) if record['keyword'] == 'FREQUENCY']
    if len(steps) != 1 or len(ends) != 1 or len(frequencies) != 1:
        raise RuntimeError('Abaqus input must contain exactly one frequency step')
    if not steps[0] < frequencies[0] < ends[0]:
        raise RuntimeError('Abaqus frequency procedure is outside its single step')
    step = records[steps[0]]
    if step['flags'] != {'PERTURBATION'} or step['params'].get('NLGEOM', 'NO') != 'NO':
        raise RuntimeError('Abaqus frequency step must be a linear perturbation step')
    frequency = records[frequencies[0]]
    if len(frequency['data']) != 1:
        raise RuntimeError('Abaqus frequency request is ambiguous')
    frequency_values = numeric_fields(frequency['data'][0], allow_empty=True)
    if (
        not frequency_values or frequency_values[0] is None
        or not float(frequency_values[0]).is_integer() or int(frequency_values[0]) < 3
    ):
        raise RuntimeError('Abaqus frequency step must request at least three modes')

    node_rows = {}
    node_parts = set()
    for record in records:
        if record['keyword'] != 'NODE':
            continue
        if record['_part'] is None:
            raise RuntimeError('Abaqus input defines nodes outside a part')
        if record['data']:
            node_parts.add(record['_part'])
        for line in record['data']:
            fields = [value.strip() for value in line.split(',')]
            if len(fields) < 2 or len(fields) > 4:
                raise RuntimeError('Abaqus input node row is invalid')
            try:
                label = int(fields[0])
                point = tuple(float(value) if value else 0.0 for value in fields[1:])
            except Exception:
                raise RuntimeError('Abaqus input node row is unreadable')
            point = (point + (0.0, 0.0, 0.0))[:3]
            if label in node_rows or any(not math.isfinite(value) for value in point):
                raise RuntimeError('Abaqus input contains duplicate or invalid nodes')
            node_rows[label] = point
    if set(node_rows) != set(model_mesh['nodes']):
        raise RuntimeError('Abaqus final input node labels do not match the CAE mesh')
    for label, point in node_rows.items():
        expected = model_mesh['nodes'][label]
        if any(abs(point[index] - expected[index]) > 1.0e-6 for index in range(3)):
            raise RuntimeError('Abaqus final input node coordinates do not match the CAE mesh')

    element_rows = {}
    implicit_part_elsets = {}
    element_parts = set()
    for record in records:
        if record['keyword'] != 'ELEMENT':
            continue
        if record['_part'] is None:
            raise RuntimeError('Abaqus input defines elements outside a part')
        if record['data']:
            element_parts.add(record['_part'])
        element_type = record['params'].get('TYPE', '').upper()
        if element_type not in ('B31', 'B32'):
            raise RuntimeError('Abaqus final input contains a non-B31/B32 element')
        required = 2 if element_type == 'B31' else 3
        for line in record['data']:
            fields = [value.strip() for value in line.split(',') if value.strip()]
            try:
                values = [int(value) for value in fields]
            except Exception:
                raise RuntimeError('Abaqus input element row is unreadable')
            if len(values) != required + 1 or values[0] in element_rows:
                raise RuntimeError('Abaqus input element connectivity is invalid or duplicated')
            element_rows[values[0]] = (element_type, tuple(values[1:]))
            implicit_name = record['params'].get('ELSET')
            if implicit_name:
                implicit_part_elsets.setdefault((record['_part'], implicit_name), []).append(values[0])
    if element_rows != model_mesh['elements']:
        raise RuntimeError('Abaqus final input elements do not match the CAE mesh')
    if len(node_parts) != 1 or node_parts != element_parts:
        raise RuntimeError('Abaqus final input mesh is not contained in one part')
    meshed_part = next(iter(element_parts))

    sections = [record for record in records if record['keyword'] == 'BEAM SECTION']
    if not sections:
        raise RuntimeError('Abaqus input has no beam section')
    part_elsets = dict((key, list(values)) for key, values in implicit_part_elsets.items())
    for record in records:
        if record['keyword'] != 'ELSET' or record['_part'] is None:
            continue
        name = record['params'].get('ELSET')
        if not name:
            raise RuntimeError('Abaqus ELSET is unnamed')
        part_elsets.setdefault((record['_part'], name), []).extend(set_record_entries(record))
    covered_elements = set()
    for section in sections:
        if section['_part'] != meshed_part:
            raise RuntimeError('Abaqus beam section is outside the meshed part')
        if section['params'].get('SECTION') != 'RECT' or section['params'].get('MATERIAL') != material_name.upper():
            raise RuntimeError('Abaqus input beam section or material reference is wrong')
        if 'POISSON' in section['params']:
            try:
                poisson = float(section['params']['POISSON'])
            except Exception:
                raise RuntimeError('Abaqus input beam-section Poisson ratio is invalid')
            if not math.isclose(poisson, 0.3, rel_tol=2.0e-6):
                raise RuntimeError('Abaqus input beam-section Poisson ratio is wrong')
        if len(section['data']) != 2:
            raise RuntimeError('Abaqus rectangular beam section data is ambiguous')
        dimensions = numeric_fields(section['data'][0])
        orientation = numeric_fields(section['data'][1])
        if len(dimensions) != 2 or any(not math.isclose(value, 10.0, rel_tol=1.0e-9, abs_tol=1.0e-6) for value in dimensions):
            raise RuntimeError('Abaqus input beam section is not 10 x 10 mm')
        if len(orientation) != 3 or math.sqrt(builtins.sum(value * value for value in orientation[1:])) <= 1.0e-12:
            raise RuntimeError('Abaqus input beam orientation is parallel to the beam axis')
        elset_name = section['params'].get('ELSET')
        if not elset_name:
            raise RuntimeError('Abaqus beam section has no element set')
        section_elements = set(resolve_integer_set(part_elsets, (meshed_part, elset_name)))
        if not section_elements or covered_elements.intersection(section_elements):
            raise RuntimeError('Abaqus beam-section assignments overlap or are empty')
        covered_elements.update(section_elements)
    if covered_elements != set(element_rows):
        raise RuntimeError('Abaqus beam-section assignments do not cover each beam element exactly once')

    material_indices = [
        index for index, record in enumerate(records)
        if record['keyword'] == 'MATERIAL' and record['params'].get('NAME') == material_name.upper()
    ]
    if len(material_indices) != 1:
        raise RuntimeError('Abaqus input does not define the used material exactly once')
    top_level = set((
        'MATERIAL', 'BOUNDARY', 'STEP', 'AMPLITUDE', 'PART', 'END PART', 'ASSEMBLY',
        'END ASSEMBLY', 'INSTANCE', 'END INSTANCE', 'NODE', 'ELEMENT', 'NSET', 'ELSET',
        'BEAM SECTION', 'ORIENTATION', 'HEADING', 'PREPRINT', 'RESTART', 'FREQUENCY',
        'END STEP', 'OUTPUT', 'NODE OUTPUT', 'ELEMENT OUTPUT', 'ENERGY OUTPUT',
        'MODAL OUTPUT', 'NODE PRINT', 'EL PRINT', 'ENERGY PRINT', 'NODE FILE',
        'EL FILE', 'MODAL FILE',
    ))
    all_material_blocks = {}
    material_property_indices = set()
    for index, record in enumerate(records):
        if record['keyword'] != 'MATERIAL':
            continue
        if record['_part'] is not None or record['_assembly'] is not None or record['_instance'] is not None or record['_in_step']:
            raise RuntimeError('Abaqus MATERIAL is outside top-level model-data scope')
        name = record['params'].get('NAME')
        if not name or name in all_material_blocks:
            raise RuntimeError('Abaqus input contains an unnamed or duplicate material')
        block = []
        for property_index in range(index + 1, len(records)):
            candidate = records[property_index]
            if candidate['keyword'] in top_level:
                break
            if candidate['keyword'] not in {'DENSITY', 'ELASTIC', 'DAMPING'}:
                raise RuntimeError('Abaqus material contains an unsupported property')
            if candidate['_part'] is not None or candidate['_assembly'] is not None or candidate['_instance'] is not None or candidate['_in_step']:
                raise RuntimeError('Abaqus material property is outside top-level model-data scope')
            block.append(candidate)
            material_property_indices.add(property_index)
        all_material_blocks[name] = block
    for index, record in enumerate(records):
        if record['keyword'] in {'DENSITY', 'ELASTIC', 'DAMPING'} and index not in material_property_indices:
            raise RuntimeError('Abaqus material property is outside a MATERIAL block')
    material_records = all_material_blocks[material_name.upper()]
    material_keywords = [record['keyword'] for record in material_records]
    if material_keywords.count('DENSITY') != 1 or material_keywords.count('ELASTIC') != 1 or set(material_keywords) - {'DENSITY', 'ELASTIC', 'DAMPING'} or material_keywords.count('DAMPING') > 1:
        raise RuntimeError('Abaqus used material contains unsupported or missing properties')
    elastic = [record for record in material_records if record['keyword'] == 'ELASTIC'][0]
    density = [record for record in material_records if record['keyword'] == 'DENSITY'][0]
    if elastic['flags'] or set(elastic['params']) - {'TYPE', 'DEPENDENCIES'} or elastic['params'].get('TYPE', 'ISOTROPIC') != 'ISOTROPIC' or elastic['params'].get('DEPENDENCIES', '0') != '0':
        raise RuntimeError('Abaqus input elastic law is not constant isotropic elasticity')
    if density['flags'] or set(density['params']) - {'DEPENDENCIES'} or density['params'].get('DEPENDENCIES', '0') != '0':
        raise RuntimeError('Abaqus input density has field dependencies')
    elastic_rows = [numeric_fields(line) for line in elastic['data']]
    density_rows = [numeric_fields(line) for line in density['data']]
    if len(elastic_rows) != 1 or len(elastic_rows[0]) != 2:
        raise RuntimeError('Abaqus input elastic table must be one E/nu row')
    if len(density_rows) != 1 or len(density_rows[0]) != 1:
        raise RuntimeError('Abaqus input density table must contain one value')
    if not math.isclose(elastic_rows[0][0], 210000.0, rel_tol=2.0e-6) or not math.isclose(elastic_rows[0][1], 0.3, rel_tol=2.0e-6):
        raise RuntimeError('Abaqus input E/nu values are wrong')
    if not math.isclose(density_rows[0][0], 7.85e-9, rel_tol=2.0e-6, abs_tol=1.0e-14):
        raise RuntimeError('Abaqus input density is wrong')


def parse_boundary_dofs(records, instance_nodes):
    part_nsets = {}
    assembly_nsets = {}
    instance_parts = {}
    boundaries = []
    reset_scopes = set()
    for record in records:
        keyword = record['keyword']
        params = record['params']
        data = record['data']
        if keyword == 'INSTANCE':
            name = params.get('NAME')
            part = params.get('PART')
            if not name or not part or name in instance_parts:
                raise RuntimeError('invalid or duplicate Abaqus instance mapping')
            instance_parts[name] = part
            if data:
                try:
                    transform = [float(value) for line in data for value in line.split(',') if value.strip()]
                except Exception:
                    raise RuntimeError('Abaqus instance transform is unreadable')
                if any(not math.isfinite(value) or abs(value) > 1.0e-12 for value in transform):
                    raise RuntimeError('Abaqus instance transform is not the global identity')
        elif keyword == 'NSET':
            name = params.get('NSET')
            if not name:
                raise RuntimeError('Abaqus NSET is unnamed')
            entries = set_record_entries(record)
            if record['_part'] is not None:
                part_nsets.setdefault((record['_part'], name), []).extend(entries)
            elif record['_assembly'] is not None:
                instance = params.get('INSTANCE') or record['_instance']
                members = assembly_nsets.setdefault(name, [])
                for entry in entries:
                    if isinstance(entry, int):
                        members.append(('NODE', instance, entry))
                    elif instance is not None:
                        members.append(('PART_SET', instance, entry))
                    elif '.' in entry:
                        prefix, suffix = entry.rsplit('.', 1)
                        if suffix.isdigit():
                            members.append(('NODE', prefix, int(suffix)))
                        else:
                            members.append(('PART_SET', prefix, suffix))
                    else:
                        members.append(('ASSEMBLY_SET', entry))
            else:
                raise RuntimeError('Abaqus NSET is outside PART/ASSEMBLY scope')
        elif keyword == 'NODE' and params.get('NSET'):
            if record['_part'] is None:
                raise RuntimeError('Abaqus implicit node set is outside PART scope')
            labels = []
            for line in data:
                try:
                    labels.append(int(line.split(',', 1)[0].strip()))
                except Exception:
                    raise RuntimeError('Abaqus implicit node-set membership is unreadable')
            part_nsets.setdefault((record['_part'], params['NSET']), []).extend(labels)
        elif keyword == 'BOUNDARY':
            scope = 'STEP' if record['_in_step'] else 'INITIAL'
            if params.get('OP') == 'NEW' and scope not in reset_scopes:
                boundaries = []
                reset_scopes.add(scope)
            for value in data:
                fields = [item.strip() for item in value.split(',')]
                if len(fields) < 2:
                    raise RuntimeError('Abaqus boundary row is incomplete')
                target = fields[0].upper()
                named_dofs = {
                    'ENCASTRE': set(range(1, 7)),
                    'PINNED': {1, 2, 3},
                    'XSYMM': {1, 5, 6},
                    'YSYMM': {2, 4, 6},
                    'ZSYMM': {3, 4, 5},
                    'XASYMM': {2, 3, 4},
                    'YASYMM': {1, 3, 5},
                    'ZASYMM': {1, 2, 6},
                }
                boundary_type = fields[1].upper()
                if boundary_type in named_dofs:
                    if any(field for field in fields[2:]):
                        raise RuntimeError('Abaqus named boundary row has extra data')
                    dofs = named_dofs[boundary_type]
                    magnitude = 0.0
                else:
                    try:
                        start = int(fields[1])
                        finish = int(fields[2]) if len(fields) > 2 and fields[2] else start
                        magnitude = float(fields[3]) if len(fields) > 3 and fields[3] else 0.0
                    except Exception:
                        raise RuntimeError('Abaqus boundary row is unreadable')
                    if start < 1 or finish > 6 or finish < start:
                        raise RuntimeError('Abaqus boundary constrains an unsupported DOF range')
                    dofs = set(range(start, finish + 1))
                if not math.isfinite(magnitude) or magnitude != 0.0:
                    raise RuntimeError('fixed-end boundary magnitude is nonzero')
                boundaries.append((target, dofs))

    def resolve_part_set(instance, name):
        part = instance_parts.get(instance)
        if part is None:
            raise RuntimeError('Abaqus boundary references an unknown instance: %s' % instance)
        return [(instance, value) for value in resolve_integer_set(part_nsets, (part, name))]

    def resolve_assembly_set(name, seen=None):
        seen = set() if seen is None else seen
        if name in seen:
            raise RuntimeError('recursive Abaqus assembly node set')
        if name not in assembly_nsets:
            raise RuntimeError('undefined Abaqus assembly node set: %s' % name)
        seen.add(name)
        output = []
        for entry in assembly_nsets[name]:
            if entry[0] == 'NODE':
                output.append((entry[1], entry[2]))
            elif entry[0] == 'PART_SET':
                output.extend(resolve_part_set(entry[1], entry[2]))
            else:
                output.extend(resolve_assembly_set(entry[1], seen.copy()))
        return output

    constrained = {}
    for target, dofs in boundaries:
        if target in assembly_nsets:
            members = resolve_assembly_set(target)
        elif '.' in target:
            instance, member = target.rsplit('.', 1)
            if member.isdigit():
                members = [(instance, int(member))]
            else:
                members = resolve_part_set(instance, member)
        else:
            matches = [
                (instance, name) for instance, part in instance_parts.items()
                for candidate_part, name in part_nsets
                if candidate_part == part and name == target
            ]
            if len(matches) != 1:
                raise RuntimeError('boundary target cannot be resolved unambiguously: %s' % target)
            members = resolve_part_set(matches[0][0], matches[0][1])
        for instance, label in members:
            candidates = []
            if instance is not None:
                candidates = [(name, node_label) for name, node_label in instance_nodes if name == instance and node_label == label]
            else:
                candidates = [(name, node_label) for name, node_label in instance_nodes if node_label == label]
            if len(candidates) != 1:
                raise RuntimeError('boundary node is ambiguous: %s/%s' % (instance, label))
            constrained.setdefault(candidates[0], set()).update(dofs)
    if not constrained:
        raise RuntimeError('no fixed-end constraints found')
    endpoints = {0.0: [], 500.0: []}
    for key, dofs in constrained.items():
        point = instance_nodes[key]
        if abs(point[1]) > 1.0e-6 or abs(point[2]) > 1.0e-6:
            raise RuntimeError('constraint is not on the beam axis')
        if abs(point[0]) <= 1.0e-6:
            endpoints[0.0].append((key, dofs))
        elif abs(point[0] - 500.0) <= 1.0e-6:
            endpoints[500.0].append((key, dofs))
        else:
            raise RuntimeError('interior beam node is constrained')
    required = set(range(1, 7))
    for location in (0.0, 500.0):
        if len(endpoints[location]) != 1 or endpoints[location][0][1] != required:
            raise RuntimeError('endpoint at X=%s is not fixed in DOFs 1-6' % location)


def mesh_signatures_match(left, right):
    if set(left['nodes']) != set(right['nodes']) or left['elements'] != right['elements']:
        return False
    for label in left['nodes']:
        if any(abs(left['nodes'][label][index] - right['nodes'][label][index]) > 1.0e-6 for index in range(3)):
            return False
    return True


def positive_modal_frames(odb, mesh_info):
    if len(odb.steps) != 1:
        raise RuntimeError('ODB must contain exactly one analysis step')
    candidates = []
    for step_name in odb.steps.keys():
        step = odb.steps[step_name]
        frames = []
        for frame in step.frames:
            frequency = float(getattr(frame, 'frequency', 0.0) or 0.0)
            if frequency > 0.0 and math.isfinite(frequency):
                frames.append(frame)
        if frames:
            candidates.append((step_name, frames))
    if len(candidates) != 1 or len(candidates[0][1]) < 3:
        raise RuntimeError('ODB must contain one modal step with at least three positive-frequency frames')
    frames = candidates[0][1]
    modes = [int(getattr(frame, 'mode', 0) or 0) for frame in frames[:3]]
    if modes != [1, 2, 3]:
        raise RuntimeError('ODB must contain modal frames 1, 2, and 3 in order')
    frequencies = [float(frame.frequency) for frame in frames[:3]]
    if any(frequencies[index] > frequencies[index + 1] for index in range(2)):
        raise RuntimeError('ODB first three frequencies are not nondecreasing')
    for frame in frames[:3]:
        field = repo_item(frame.fieldOutputs, 'U')
        values = list(field.values)
        if not values:
            raise RuntimeError('ODB mode shape U field is missing')
        labels = [int(value.nodeLabel) for value in values]
        if len(labels) != len(set(labels)) or set(labels) != set(mesh_info['nodes']):
            raise RuntimeError('ODB mode shape U field does not cover the complete beam mesh')
        maximum = builtins.max(
            math.sqrt(builtins.sum(float(component) ** 2 for component in value.data))
            for value in values
        )
        if not math.isfinite(maximum) or maximum <= 0.0:
            raise RuntimeError('ODB mode shape U field is empty')
    return frequencies


def validate_odb_mesh(odb):
    instances = []
    for key in odb.rootAssembly.instances.keys():
        instance = odb.rootAssembly.instances[key]
        node_count = len(instance.nodes)
        element_count = len(instance.elements)
        if bool(node_count) != bool(element_count):
            raise RuntimeError('ODB contains a node-only or element-only instance')
        if node_count:
            instances.append(instance)
    if len(instances) != 1:
        raise RuntimeError('ODB must contain exactly one meshed beam instance')
    return validate_mesh(instances[0].nodes, instances[0].elements, True)


def run():
    database = None
    submitted = None
    resolved = None
    try:
        os.chdir(WORK_DIR)
        database = openMdb(pathName=CAE_PATH)
        candidates = []
        for model_name in database.models.keys():
            model = database.models[model_name]
            for key in model.parts.keys():
                candidate_part = model.parts[key]
                node_count = len(candidate_part.nodes)
                element_count = len(candidate_part.elements)
                if bool(node_count) != bool(element_count):
                    raise RuntimeError('CAE contains a node-only or element-only part')
                if element_count:
                    candidates.append((model, candidate_part))
            for key in model.rootAssembly.instances.keys():
                instance = model.rootAssembly.instances[key]
                if bool(len(instance.nodes)) != bool(len(instance.elements)):
                    raise RuntimeError('CAE contains a node-only or element-only instance')
        if len(candidates) != 1:
            raise RuntimeError('CAE must contain exactly one meshed analysis part')
        model, part = candidates[0]
        model_mesh = validate_mesh(part.nodes, part.elements, False)
        analysis_instances = [
            model.rootAssembly.instances[key] for key in model.rootAssembly.instances.keys()
            if len(model.rootAssembly.instances[key].elements)
        ]
        if len(analysis_instances) != 1:
            raise RuntimeError('CAE analysis model must contain exactly one meshed instance')
        assembly_mesh = validate_mesh(analysis_instances[0].nodes, analysis_instances[0].elements, False)
        if not mesh_signatures_match(model_mesh, assembly_mesh):
            raise RuntimeError('CAE part and assembly mesh signatures do not match')

        assignments = list(part.sectionAssignments)
        section_names = sorted(set(str(assignment.sectionName) for assignment in assignments))
        if not assignments or len(section_names) != 1:
            raise RuntimeError('beam must use one unambiguous section definition')
        section = repo_item(model.sections, section_names[0])
        if section.__class__.__name__ != 'BeamSection':
            raise RuntimeError('assigned section is not a BeamSection')
        profile = repo_item(model.profiles, str(section.profile))
        if profile.__class__.__name__ != 'RectangularProfile':
            raise RuntimeError('beam profile is not rectangular')
        if not math.isclose(float(profile.a), 10.0, rel_tol=1.0e-9, abs_tol=1.0e-6) or not math.isclose(float(profile.b), 10.0, rel_tol=1.0e-9, abs_tol=1.0e-6):
            raise RuntimeError('beam profile is not 10 x 10 mm')
        material_values(model, section)

        frequency_steps = [model.steps[key] for key in model.steps.keys() if model.steps[key].__class__.__name__ == 'FrequencyStep']
        if len(model.steps) != 2 or len(frequency_steps) != 1 or int(frequency_steps[0].numEigen) < 3:
            raise RuntimeError('CAE must request at least the first three modes in one FrequencyStep')
        for repository_name in ('loads', 'predefinedFields', 'constraints', 'interactions'):
            repository = getattr(model, repository_name)
            if len(repository):
                raise RuntimeError('CAE contains unsupported loads, fields, constraints, or interactions')

        job_name = 'task15_eval_resolve'
        if job_name in database.jobs.keys():
            del database.jobs[job_name]
        job = database.Job(
            name=job_name,
            model=model.name,
            type=ANALYSIS,
            memory=90,
            memoryUnits=PERCENTAGE,
            explicitPrecision=SINGLE,
            nodalOutputPrecision=SINGLE,
            numCpus=1,
            numDomains=1,
        )
        job.writeInput(consistencyChecking=OFF)
        input_path = os.path.join(WORK_DIR, job_name + '.inp')
        if not os.path.isfile(input_path):
            raise RuntimeError('cannot regenerate Abaqus input deck from CAE')
        instance_nodes = {}
        for key in model.rootAssembly.instances.keys():
            instance = model.rootAssembly.instances[key]
            for node in instance.nodes:
                instance_nodes[(str(key).upper(), int(node.label))] = tuple(float(value) for value in node.coordinates[:3])
        records = parse_input_records(input_path)
        audit_input_deck(records, model_mesh, str(section.material))
        parse_boundary_dofs(records, instance_nodes)

        submitted = openOdb(path=ODB_PATH, readOnly=True)
        submitted_mesh = validate_odb_mesh(submitted)
        if not mesh_signatures_match(model_mesh, submitted_mesh):
            raise RuntimeError('submitted ODB mesh does not match the CAE model')
        submitted_frequencies = positive_modal_frames(submitted, submitted_mesh)
        if not all(close(METRICS[index], submitted_frequencies[index]) for index in range(3)):
            raise RuntimeError('metrics.json does not match submitted ODB first three frequencies')

        job.submit(consistencyChecking=OFF)
        job.waitForCompletion()
        resolved_path = os.path.join(WORK_DIR, job_name + '.odb')
        if not os.path.isfile(resolved_path) or os.path.getsize(resolved_path) <= 0:
            raise RuntimeError('isolated Abaqus re-solve did not produce an ODB: %s' % job.status)
        resolved = openOdb(path=resolved_path, readOnly=True)
        resolved_mesh = validate_odb_mesh(resolved)
        if not mesh_signatures_match(model_mesh, resolved_mesh):
            raise RuntimeError('re-solved ODB mesh does not match the CAE model')
        resolved_frequencies = positive_modal_frames(resolved, resolved_mesh)
        if not all(exact(submitted_frequencies[index], resolved_frequencies[index]) for index in range(3)):
            raise RuntimeError('submitted ODB is stale or does not match the CAE re-solve')
        return {
            'ok': True,
            'submitted_frequencies': submitted_frequencies,
            'resolved_frequencies': resolved_frequencies,
        }
    except Exception as exc:
        return {'ok': False, 'error': repr(exc), 'traceback': traceback.format_exc()}
    finally:
        for odb in (submitted, resolved):
            try:
                if odb is not None:
                    odb.close()
            except Exception:
                pass
        try:
            if database is not None:
                database.close()
        except Exception:
            pass


with open(RESULT_PATH, 'w') as stream:
    json.dump(run(), stream, indent=2, sort_keys=True)
    stream.write('\n')
'''


def run_abaqus(work, cae_path, odb_path, metrics):
    candidate_cae = work / "candidate.cae"
    submitted_odb = work / "submitted.odb"
    shutil.copy2(cae_path, candidate_cae)
    shutil.copy2(odb_path, submitted_odb)
    checker = work / "check_task15_abaqus.py"
    result_path = work / "abaqus_check.json"
    source = ABAQUS_CHECKER
    replacements = {
        "__CAE_PATH__": repr(str(candidate_cae)),
        "__ODB_PATH__": repr(str(submitted_odb)),
        "__WORK_DIR__": repr(str(work)),
        "__RESULT_PATH__": repr(str(result_path)),
        "__METRICS__": repr([float(value) for value in metrics]),
    }
    for marker, value in replacements.items():
        source = source.replace(marker, value)
    checker.write_text(source, encoding="utf-8")
    if not Path(ABAQUS_LAUNCHER).is_file():
        raise RuntimeError("Abaqus 2025 Learning Edition launcher is unavailable")
    execution = run_owned(
        [ABAQUS_LAUNCHER, "cae", "noGUI=" + str(checker), "--"],
        cwd=work,
        timeout=900,
    )
    if execution["returncode"] != 0:
        raise RuntimeError("Abaqus checker failed: %s %s" % (execution["stdout"][-1000:], execution["stderr"][-1000:]))
    if not nonempty(result_path):
        raise RuntimeError("Abaqus checker did not produce a result")
    report = strict_json_object(result_path)
    if report.get("ok") is not True:
        raise RuntimeError(
            "Abaqus native validation failed: %s\n%s"
            % (report.get("error"), report.get("traceback", ""))
        )
    log("Abaqus 2025 native model/result/metrics re-solve matched")
    return True


ANSYS_INPUT = r'''/BATCH
/CLEAR,NOSTART
/FILNAME,candidate,1
RESUME,candidate,db
/PREP7
ALLSEL,ALL
DOFSEL,ALL
*GET,NODE_COUNT,NODE,0,COUNT
*GET,ELEMENT_COUNT,ELEM,0,COUNT
CDWRITE,LOAD,load_audit,cdb,,,,UNBLOCKED
CDWRITE,DB,model_state_audit,cdb
/OUTPUT,model_listing,txt
ETLIST,ALL
SLIST,ALL
MPLIST,ALL
DLIST,ALL
CPLIST,ALL
CELIST,ALL
FLIST,ALL
SFLIST,ALL
SFELIST,ALL
SFALIST,ALL
BFLIST,ALL
BFELIST,ALL
ICLIST,ALL
ICLIST,ALL,,,VELO
ICLIST,ALL,,,ACC
INISTATE,LIST
INISTATE,LIST,MIND
NLIST,ALL
ELIST,ALL
/OUTPUT
FINISH

/SOLU
/OUTPUT,solution_status,txt
/STATUS,SOLU
/OUTPUT
FINISH

/POST1
FILE,submitted,rst
/OUTPUT,submitted_sets,txt
SET,LIST
/OUTPUT
SET,1,1
*GET,SUBMITTED_F1,ACTIVE,0,SET,FREQ
SET,1,2
*GET,SUBMITTED_F2,ACTIVE,0,SET,FREQ
SET,1,3
*GET,SUBMITTED_F3,ACTIVE,0,SET,FREQ
FINISH

/FILNAME,recheck_task15,1
/SOLU
ANTYPE,MODAL
MODOPT,LANB,3
MXPAND,3,,,YES
SOLVE
FINISH

/POST1
FILE,recheck_task15,rst
/OUTPUT,resolved_sets,txt
SET,LIST
/OUTPUT
SET,1,1
*GET,RESOLVED_F1,ACTIVE,0,SET,FREQ
SET,1,2
*GET,RESOLVED_F2,ACTIVE,0,SET,FREQ
SET,1,3
*GET,RESOLVED_F3,ACTIVE,0,SET,FREQ

*CFOPEN,ansys_check,json
*VWRITE
('{')
*VWRITE,NODE_COUNT,ELEMENT_COUNT
('  "node_count": ',E24.16,', "element_count": ',E24.16,',')
*VWRITE,SUBMITTED_F1,SUBMITTED_F2,SUBMITTED_F3
('  "submitted_frequencies": [',E24.16,',',E24.16,',',E24.16,'],')
*VWRITE,RESOLVED_F1,RESOLVED_F2,RESOLVED_F3
('  "resolved_frequencies": [',E24.16,',',E24.16,',',E24.16,']')
*VWRITE
('}')
*CFCLOS
FINISH
/EXIT,NOSAVE
'''


FLOAT_RE = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?"


def ansys_number_is_zero(value):
    try:
        number = float(str(value).replace("D", "E").replace("d", "e"))
    except Exception:
        return False
    return math.isfinite(number) and abs(number) <= 1.0e-12


def ansys_export_has_no_forbidden_state(text, used_sections, used_materials):
    records = []
    for physical_line in text.splitlines():
        for raw_record in physical_line.split("$"):
            line = raw_record.split("!", 1)[0].strip()
            if not line or line.startswith("/"):
                continue
            fields = [field.strip() for field in line.split(",")]
            token = re.split(r"\s+", fields[0], maxsplit=1)[0].upper()
            if token:
                records.append((token, fields[1:]))

    forbidden = {
        "F", "FJ", "FK", "SLOAD",
        "SF", "SFE", "SFA", "SFL", "SFK", "SFGRAD", "SFCONTROL",
        "BF", "BFE", "BFA", "BFL", "BFK", "BFV", "TUNIF",
        "IC", "ICROTATE", "INISTATE", "INRES", "LDREAD", "LREAD", "UPGEOM",
        "CMACEL", "CMOMEGA", "CMDOMEGA",
    }
    zero_vectors = {"ACEL", "OMEGA", "DOMEGA", "CGOMEGA", "CGOMGA", "DCGOMG"}
    seen_zero_vectors = set()
    current_section = None
    temperatures = {}
    allowed_material_properties = {
        "EX", "NUXY", "PRXY", "DENS", "ALPD", "BETD", "DMPR", "DMPS"
    }
    current_sdamp = None
    sdamp_blocks = []
    for token, arguments in records:
        if token not in {"TB", "TBTEMP", "TBFIELD", "TBDATA", "TBIN"}:
            current_sdamp = None
        if token in forbidden:
            return False
        if token in zero_vectors:
            values = [value for value in arguments if value]
            if not values or any(not ansys_number_is_zero(value) for value in values):
                return False
            seen_zero_vectors.add(token)
        elif token == "IRLF":
            if not arguments or not ansys_number_is_zero(arguments[0]):
                return False
        elif token == "BFUNIF":
            if len(arguments) < 2 or arguments[0].upper() != "TEMP":
                return False
            if arguments[1].upper() != "_TINY" and not ansys_number_is_zero(arguments[1]):
                return False
        elif token == "PSTRES":
            if not arguments or arguments[0].upper() not in {"OFF", "0"}:
                return False
        elif token == "PERTURB":
            if not arguments or arguments[0].upper() not in {"OFF", "0"}:
                return False
        elif token in {"ALPHAD", "BETAD", "DMPRAT", "DMPSTR"}:
            try:
                value = ansys_float(arguments[0])
            except Exception:
                return False
            if value < 0.0:
                return False
        elif token == "SECTYPE":
            try:
                current_section = int(float(arguments[0]))
            except Exception:
                return False
            if current_section in used_sections and (
                len(arguments) < 3
                or arguments[1].upper() != "BEAM"
                or arguments[2].upper() not in {"RECT", "RECTANGLE"}
            ):
                return False
        elif token == "SECDATA" and current_section in used_sections:
            try:
                values = [ansys_float(value) for value in arguments if value]
            except Exception:
                return False
            if len(values) != 2 or any(not math.isclose(value, 10.0, rel_tol=1.0e-9, abs_tol=1.0e-6) for value in values):
                return False
        elif token == "SECOFFSET" and current_section in used_sections:
            if not arguments or arguments[0].upper() not in {"CENT", "CENTROID"}:
                return False
        elif token == "SECCONTROL" and current_section in used_sections:
            try:
                values = [ansys_float(value) for value in arguments if value]
            except Exception:
                return False
            if any(abs(value) > 1.0e-12 for value in values):
                return False
        elif token in {"SECFUNCTION", "SECBLOCK", "SECREAD"} and current_section in used_sections:
            return False
        elif token == "MPTEMP":
            try:
                if len(arguments) < 4 or arguments[0].upper() != "UNBL":
                    return False
                start = int(float(arguments[1]))
                count = int(float(arguments[2]))
                values = [ansys_float(value) for value in arguments[3:] if value]
            except Exception:
                return False
            if start < 1 or count < 1 or len(values) != count:
                return False
            for offset, value in enumerate(values):
                temperatures[start + offset] = value
        elif token == "MPDATA":
            try:
                if len(arguments) < 6 or arguments[0].upper() != "UNBL":
                    return False
                count = int(float(arguments[1]))
                label = arguments[2].upper()
                material = int(float(arguments[3]))
                start = int(float(arguments[4]))
                values = [ansys_float(value) for value in arguments[5:] if value]
            except Exception:
                return False
            if material in used_materials:
                if label not in allowed_material_properties or count != 1 or start < 1 or len(values) != 1:
                    return False
                if start not in temperatures or abs(temperatures[start]) > 1.0e-12:
                    return False
                if label in {"ALPD", "BETD", "DMPR", "DMPS"} and values[0] < 0.0:
                    return False
        elif token == "MP":
            try:
                label = arguments[0].upper()
                material = int(float(arguments[1]))
                value = ansys_float(arguments[2])
            except Exception:
                return False
            if material in used_materials and (
                label not in allowed_material_properties
                or (label in {"ALPD", "BETD", "DMPR", "DMPS"} and value < 0.0)
            ):
                return False
        elif token == "TB":
            try:
                label = arguments[0].upper()
                material = int(float(arguments[1]))
            except Exception:
                return False
            if material in used_materials:
                option = arguments[4].upper() if len(arguments) > 4 and arguments[4] else "STRU"
                option = {"1": "STRU", "2": "ALPD", "3": "BETD"}.get(option, option)
                if label not in {"SDAMP", "SDAM"} or option not in {"STRU", "ALPD", "BETD"}:
                    return False
                current_sdamp = {"material": material, "option": option, "has_data": False}
                sdamp_blocks.append(current_sdamp)
            else:
                current_sdamp = None
        elif token == "TBTEMP" and current_sdamp is not None:
            try:
                values = [ansys_float(value) for value in arguments if value]
            except Exception:
                return False
            if len(values) != 1:
                return False
        elif token == "TBFIELD" and current_sdamp is not None:
            try:
                field = arguments[0].upper()
                values = [ansys_float(value) for value in arguments[1:] if value]
            except Exception:
                return False
            if field not in {"TEMP", "TEMPS"} or len(values) != 1:
                return False
        elif token == "TBDATA" and current_sdamp is not None:
            try:
                start = int(float(arguments[0]))
                values = [ansys_float(value) for value in arguments[1:] if value]
            except Exception:
                return False
            if start < 1 or not values or any(value < 0.0 for value in values):
                return False
            current_sdamp["has_data"] = True
        elif token == "TBIN" and current_sdamp is not None:
            pass
    required = {"ACEL", "OMEGA", "DOMEGA", "CGOMEGA", "DCGOMG"}
    return required.issubset(seen_zero_vectors) and all(block["has_data"] for block in sdamp_blocks)


def ansys_listing_has_no_forbidden_loads(text):
    upper = text.upper()
    return (
        "NO NODAL FORCES TO LIST" in upper
        and upper.count("NO SURFACE LOADS TO LIST") >= 2
        and (
            "NO AREAS DEFINED" in upper
            or "NO SURFACE LOADS ON AREAS TO LIST" in upper
        )
        and "NO NODAL BODY FORCES TO LIST" in upper
        and "NO ELEMENT BODY FORCES TO LIST" in upper
        and "NO INITIAL CONDITIONS TO LIST" in upper
    )


def parse_ansys_model_listing(text):
    upper = text.upper()
    if "NO COUPLED SETS TO LIST" not in upper:
        raise RuntimeError("ANSYS model contains unsupported coupled-DOF sets")
    if "NO CONSTRAINT EQUATIONS TO LIST" not in upper:
        raise RuntimeError("ANSYS model contains unsupported constraint equations")
    type_map = {
        int(number): name.upper()
        for number, name in re.findall(r"ELEMENT TYPE\s+(\d+)\s+IS\s+(BEAM188|BEAM189)", upper)
    }
    if not type_map:
        raise RuntimeError("ANSYS model does not define BEAM188/BEAM189")

    node_block_match = re.search(r"LIST ALL SELECTED NODES.*?(?=LIST ALL SELECTED ELEMENTS)", upper, re.DOTALL)
    if not node_block_match:
        raise RuntimeError("ANSYS node listing is missing")
    node_rows = {}
    node_pattern = re.compile(r"^\s*(\d+)\s+(%s)\s+(%s)\s+(%s)\s+%s\s+%s\s+%s\s*$" % ((FLOAT_RE,) * 6), re.MULTILINE)
    for match in node_pattern.finditer(node_block_match.group(0)):
        node_rows[int(match.group(1))] = (float(match.group(2)), float(match.group(3)), float(match.group(4)))
    if not node_rows:
        raise RuntimeError("ANSYS node coordinates are unreadable")

    element_block_match = re.search(r"LIST ALL SELECTED ELEMENTS.*", upper, re.DOTALL)
    if not element_block_match:
        raise RuntimeError("ANSYS element listing is missing")
    elements = []
    for line in element_block_match.group(0).splitlines():
        parts = line.split()
        if len(parts) < 8 or not all(value.lstrip("+-").isdigit() for value in parts[:6]):
            continue
        values = [int(value) for value in parts]
        elements.append(
            {
                "element": values[0],
                "material": values[1],
                "type": values[2],
                "section": values[5],
                "nodes": [value for value in values[6:] if value > 0],
            }
        )
    if len(elements) != 20:
        raise RuntimeError("ANSYS model must contain exactly 20 elements")
    if any(element["type"] not in type_map for element in elements):
        raise RuntimeError("ANSYS used element type is not BEAM188/BEAM189")

    spans = []
    graph = {}
    endpoint_coordinates = {}
    referenced_nodes = set()
    structural_nodes = set()
    for element in elements:
        count = 2 if type_map[element["type"]] == "BEAM188" else 3
        raw_ids = element["nodes"]
        if len(raw_ids) not in (count, count + 1):
            raise RuntimeError("ANSYS beam connectivity arity is invalid")
        if any(value not in node_rows for value in raw_ids):
            raise RuntimeError("ANSYS beam references an unknown node")
        referenced_nodes.update(raw_ids)
        ids = raw_ids[:count]
        structural_nodes.update(ids)
        if len(ids) != count:
            raise RuntimeError("ANSYS beam connectivity is incomplete")
        points = [node_rows[value] for value in ids]
        if any(abs(point[1]) > 1.0e-6 or abs(point[2]) > 1.0e-6 for point in points):
            raise RuntimeError("ANSYS beam is not aligned to global X")
        low = min(point[0] for point in points)
        high = max(point[0] for point in points)
        if not math.isclose(high - low, 25.0, rel_tol=1.0e-9, abs_tol=1.0e-6):
            raise RuntimeError("ANSYS beam element is not 25 mm long")
        ordered = sorted(zip(ids, points), key=lambda item: item[1][0])
        left = ordered[0]
        right = ordered[-1]
        if count == 3:
            middle = ordered[1][1]
            expected_middle = tuple(
                0.5 * (left[1][index] + right[1][index]) for index in range(3)
            )
            if any(abs(middle[index] - expected_middle[index]) > 1.0e-6 for index in range(3)):
                raise RuntimeError("ANSYS BEAM189 middle node is not at the element midpoint")
        if left[0] == right[0]:
            raise RuntimeError("ANSYS beam element has identical endpoint nodes")
        graph.setdefault(left[0], set()).add(right[0])
        graph.setdefault(right[0], set()).add(left[0])
        endpoint_coordinates[left[0]] = left[1]
        endpoint_coordinates[right[0]] = right[1]
        spans.append((round(low, 6), round(high, 6)))
    expected_spans = [(float(value), float(value + 25)) for value in range(0, 500, 25)]
    if sorted(spans) != expected_spans:
        raise RuntimeError("ANSYS mesh is not 20 equal divisions")
    unused_nodes = set(node_rows) - referenced_nodes
    if unused_nodes:
        raise RuntimeError("ANSYS beam mesh contains orphan or unused nodes: %r" % sorted(unused_nodes))
    if len(graph) != 21:
        raise RuntimeError("ANSYS beam endpoint topology must contain exactly 21 shared nodes")
    starts = [node for node, point in endpoint_coordinates.items() if abs(point[0]) <= 1.0e-6]
    finishes = [node for node, point in endpoint_coordinates.items() if abs(point[0] - 500.0) <= 1.0e-6]
    if len(starts) != 1 or len(finishes) != 1:
        raise RuntimeError("ANSYS beam topology does not have unique X=0 and X=500 endpoints")
    for node, neighbors in graph.items():
        expected_degree = 1 if node in (starts[0], finishes[0]) else 2
        if len(neighbors) != expected_degree:
            raise RuntimeError("ANSYS beam elements do not form one continuous chain")
    visited = set()
    pending = [starts[0]]
    while pending:
        node = pending.pop()
        if node in visited:
            continue
        visited.add(node)
        pending.extend(graph[node] - visited)
    if visited != set(graph):
        raise RuntimeError("ANSYS beam element chain is disconnected")

    section_blocks = {}
    matches = list(re.finditer(r"SECTION ID NUMBER:\s*(\d+)", upper))
    for index, match in enumerate(matches):
        finish = matches[index + 1].start() if index + 1 < len(matches) else len(upper)
        section_blocks[int(match.group(1))] = upper[match.start():finish]
    for section_id in set(element["section"] for element in elements):
        block = section_blocks.get(section_id, "")
        if "BEAM SECTION SUBTYPE:  RECTANGLE" not in block:
            raise RuntimeError("ANSYS used beam section is not rectangular")
        values = {}
        for key, label in (("area", "AREA"), ("iyy", "IYY"), ("izz", "IZZ")):
            match = re.search(r"^\s*%s\s*=\s*(%s)" % (label, FLOAT_RE), block, re.MULTILINE)
            if not match:
                raise RuntimeError("ANSYS section property %s is missing" % label)
            values[key] = float(match.group(1))
        if not math.isclose(values["area"], 100.0, rel_tol=2.0e-3) or not math.isclose(values["iyy"], 833.333333333, rel_tol=2.0e-3) or not math.isclose(values["izz"], 833.333333333, rel_tol=2.0e-3):
            raise RuntimeError("ANSYS rectangular section is not 10 x 10 mm")
        if "BEAM SECTION IS OFFSET TO CENTROID" not in block:
            raise RuntimeError("ANSYS used beam section is not centroidal")

    material_listing = re.search(
        r"LIST MATERIALS.*?(?=(?:LIST|NO)\s+CONSTRAINTS)", upper, re.DOTALL
    )
    if not material_listing:
        raise RuntimeError("ANSYS material listing is missing or truncated")
    material_text = material_listing.group(0)
    material_blocks = {}
    matches = list(re.finditer(r"MATERIAL NUMBER\s+(\d+)", material_text))
    for index, match in enumerate(matches):
        finish = matches[index + 1].start() if index + 1 < len(matches) else len(material_text)
        material_blocks[int(match.group(1))] = material_text[match.start():finish]
    for material_id in set(element["material"] for element in elements):
        block = material_blocks.get(material_id, "")
        property_matches = list(re.finditer(r"^\s*TEMP\s+([A-Z][A-Z0-9_]*)\s*$", block, re.MULTILINE))
        property_rows = {}
        for index, match in enumerate(property_matches):
            finish = property_matches[index + 1].start() if index + 1 < len(property_matches) else len(block)
            values = re.findall(FLOAT_RE, block[match.end():finish])
            label = match.group(1)
            if label in property_rows or len(values) != 1:
                raise RuntimeError("ANSYS used material property %s is duplicated or temperature dependent" % label)
            property_rows[label] = float(values[0])
        poisson_labels = set(property_rows).intersection({"NUXY", "PRXY"})
        damping_labels = {"ALPD", "BETD", "DMPR", "DMPS"}
        if set(property_rows) - {"EX", "NUXY", "PRXY", "DENS"}.union(damping_labels) or set(property_rows).intersection({"EX", "DENS"}) != {"EX", "DENS"} or not poisson_labels:
            raise RuntimeError("ANSYS used material contains extra stiffness properties or lacks isotropic E/nu/density")
        properties = {
            "ex": property_rows["EX"],
            "nu": property_rows[next(iter(poisson_labels))],
            "density": property_rows["DENS"],
        }
        if not math.isclose(properties["ex"], 210000.0, rel_tol=2.0e-6) or any(not math.isclose(property_rows[label], 0.3, rel_tol=2.0e-6) for label in poisson_labels) or not math.isclose(properties["density"], 7.85e-9, rel_tol=2.0e-6, abs_tol=1.0e-14):
            raise RuntimeError("ANSYS material values are wrong")
        if any(property_rows[label] < 0.0 for label in damping_labels.intersection(property_rows)):
            raise RuntimeError("ANSYS material damping value is invalid")

    constraints = {}
    for node, dof, real_value in re.findall(r"^\s*(\d+)\s+(UX|UY|UZ|ROTX|ROTY|ROTZ)\s+(%s)\s+%s\s*$" % (FLOAT_RE, FLOAT_RE), upper, re.MULTILINE):
        if abs(float(real_value)) > 1.0e-12:
            raise RuntimeError("ANSYS endpoint constraint value is nonzero")
        constraints.setdefault(int(node), set()).add(dof)
    if not constraints:
        raise RuntimeError("ANSYS constraints are missing")
    required_dofs = {"UX", "UY", "UZ", "ROTX", "ROTY", "ROTZ"}
    endpoint_nodes = {0.0: [], 500.0: []}
    for node, dofs in constraints.items():
        point = node_rows.get(node)
        if point is None:
            raise RuntimeError("ANSYS constrained node is not in the model")
        if abs(point[0]) <= 1.0e-6:
            endpoint_nodes[0.0].append((node, dofs))
        elif abs(point[0] - 500.0) <= 1.0e-6:
            endpoint_nodes[500.0].append((node, dofs))
        else:
            raise RuntimeError("ANSYS interior beam node is constrained")
    for location in (0.0, 500.0):
        if len(endpoint_nodes[location]) != 1 or endpoint_nodes[location][0][1] != required_dofs:
            raise RuntimeError("ANSYS endpoint at X=%s is not fully fixed" % location)
    if not ansys_listing_has_no_forbidden_loads(text):
        raise RuntimeError("ANSYS model contains an extra load or initial-condition category")
    element_signature = {
        element["element"]: (
            188 if type_map[element["type"]] == "BEAM188" else 189,
            tuple(element["nodes"]),
        )
        for element in elements
    }
    if len(element_signature) != len(elements):
        raise RuntimeError("ANSYS model contains duplicate element labels")
    return {
        "nodes": node_rows,
        "elements": element_signature,
        "structural_nodes": structural_nodes,
        "used_sections": set(element["section"] for element in elements),
        "used_materials": set(element["material"] for element in elements),
    }


def ansys_float(value):
    number = float(str(value).replace("D", "E").replace("d", "e"))
    if not math.isfinite(number):
        raise ValueError("non-finite ANSYS number")
    return number


def parse_ansys_result_set_listing(text):
    upper = (text or "").upper()
    if "INDEX OF DATA SETS ON RESULTS FILE" not in upper or "LOAD STEP" not in upper or "SUBSTEP" not in upper:
        return None
    number_pattern = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?"
    pattern = re.compile(
        r"^\s*(\d+)\s+(%s)\s+(\d+)\s+(\d+)\s+(\d+)\s*$" % number_pattern,
        re.IGNORECASE,
    )
    rows = []
    for line in (text or "").splitlines():
        if not re.match(r"^\s*\d+", line):
            continue
        match = pattern.fullmatch(line)
        if match is None:
            return None
        rows.append(
            {
                "set": int(match.group(1)),
                "frequency": ansys_float(match.group(2)),
                "load_step": int(match.group(3)),
                "substep": int(match.group(4)),
                "cumulative": int(match.group(5)),
            }
        )
    return rows if rows else None


def read_ansys_modal_rst(path):
    import site

    package_candidates = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        package_candidates.append(str(Path(appdata) / "Python" / "Python311" / "site-packages"))
    if not any(Path(candidate).is_dir() for candidate in package_candidates):
        try:
            package_candidates.append(site.getusersitepackages())
        except Exception:
            pass
    for candidate in package_candidates:
        if isinstance(candidate, str) and Path(candidate).is_dir() and candidate not in sys.path:
            sys.path.insert(0, candidate)
    saved_userprofile = os.environ.get("USERPROFILE")
    try:
        if appdata:
            os.environ["USERPROFILE"] = str(Path(appdata).parent.parent)
        from ansys.mapdl import reader as pymapdl_reader
        import numpy as np
    except Exception as exc:
        raise RuntimeError("ANSYS RST reader import failed: %r\n%s" % (exc, traceback.format_exc()))
    finally:
        if saved_userprofile is None:
            os.environ.pop("USERPROFILE", None)
        else:
            os.environ["USERPROFILE"] = saved_userprofile
    try:
        result = pymapdl_reader.read_binary(str(path))
    except Exception as exc:
        raise RuntimeError("ANSYS RST binary cannot be opened: %r" % (exc,))
    labels = [int(value) for value in result.mesh.nnum]
    rows = [tuple(float(value) for value in row[:3]) for row in result.mesh.nodes]
    if len(labels) != len(rows) or len(labels) != len(set(labels)):
        raise RuntimeError("ANSYS RST contains duplicate or unreadable node labels")
    coords = dict(zip(labels, rows))
    if any(any(not math.isfinite(value) for value in point) for point in coords.values()):
        raise RuntimeError("ANSYS RST contains non-finite node coordinates")
    type_codes = {int(row[0]): int(row[1]) for row in result.mesh.ekey}
    elements = {}
    structural_nodes = set()
    for raw_record in result.mesh.elem:
        record = [int(value) for value in raw_record]
        if len(record) < 13:
            raise RuntimeError("ANSYS RST beam element record is truncated")
        code = type_codes.get(record[1])
        label = record[8]
        if code not in (188, 189) or label <= 0 or label in elements:
            raise RuntimeError("ANSYS RST contains an unsupported or duplicate beam element")
        slot_count = 3 if code == 188 else 4
        structural_count = 2 if code == 188 else 3
        if len(record) < 10 + slot_count:
            raise RuntimeError("ANSYS RST beam connectivity is truncated")
        fixed_connectivity = tuple(record[10:10 + slot_count])
        structural = fixed_connectivity[:structural_count]
        optional = fixed_connectivity[structural_count:]
        if any(value <= 0 for value in structural) or any(value < 0 for value in optional):
            raise RuntimeError("ANSYS RST beam connectivity is invalid")
        connectivity = tuple(value for value in fixed_connectivity if value > 0)
        if any(value not in coords for value in connectivity):
            raise RuntimeError("ANSYS RST beam references a missing node")
        structural_nodes.update(structural)
        elements[label] = (code, connectivity)
    if len(elements) != 20 or set(coords) != set(
        value for code, connectivity in elements.values() for value in connectivity
    ):
        raise RuntimeError("ANSYS RST mesh has the wrong element count or unused nodes")
    nsets = int(result.nsets)
    frequencies = tuple(float(value) for value in result.time_values)
    if (
        nsets < 3 or len(frequencies) != nsets
        or any(not math.isfinite(value) or value <= 0.0 for value in frequencies)
        or any(frequencies[index] > frequencies[index + 1] for index in range(len(frequencies) - 1))
    ):
        raise RuntimeError("ANSYS RST modal result-set frequencies are invalid")
    if "NSL :" not in str(result.available_results).upper():
        raise RuntimeError("ANSYS RST does not advertise nodal solution data")
    ordered_structural = sorted(structural_nodes)
    mode_vectors = []
    for index in range(3):
        try:
            mode_labels, mode_rows = result.nodal_solution(index)
        except Exception as exc:
            raise RuntimeError("ANSYS RST mode %d has no expanded nodal solution: %s" % (index + 1, exc))
        mode_labels = [int(value) for value in mode_labels]
        values = np.asarray(mode_rows, dtype=float)
        if (
            len(mode_labels) != len(set(mode_labels)) or values.ndim != 2
            or values.shape[0] != len(mode_labels) or values.shape[1] < 3
            or not np.isfinite(values).all()
        ):
            raise RuntimeError("ANSYS RST mode %d nodal solution is incomplete" % (index + 1))
        index_by_label = {label: offset for offset, label in enumerate(mode_labels)}
        if not structural_nodes.issubset(index_by_label):
            raise RuntimeError("ANSYS RST mode %d omits structural beam nodes" % (index + 1))
        vector = np.concatenate([values[index_by_label[label], :] for label in ordered_structural])
        if not np.isfinite(vector).all() or float(np.max(np.abs(vector))) <= 0.0:
            raise RuntimeError("ANSYS RST mode %d displacement field is empty" % (index + 1))
        mode_vectors.append(vector)
    return {
        "nodes": coords,
        "elements": elements,
        "structural_nodes": structural_nodes,
        "nsets": nsets,
        "frequencies": frequencies,
        "mode_vectors": mode_vectors,
        "numpy": np,
    }


def validate_ansys_result_sets(rows, rst):
    if rows is None or len(rows) != rst["nsets"]:
        return False
    expected = list(range(1, len(rows) + 1))
    substeps = [row["substep"] for row in rows]
    cumulative = [row["cumulative"] for row in rows]
    if (
        [row["set"] for row in rows] != expected
        or substeps[:3] != [1, 2, 3]
        or cumulative[:3] != [1, 2, 3]
        or any(substeps[index] >= substeps[index + 1] for index in range(len(substeps) - 1))
        or any(cumulative[index] >= cumulative[index + 1] for index in range(len(cumulative) - 1))
        or any(row["load_step"] != 1 or row["frequency"] <= 0.0 for row in rows)
        or any(rows[index]["frequency"] > rows[index + 1]["frequency"] for index in range(len(rows) - 1))
    ):
        return False
    return all(
        math.isclose(row["frequency"], rst["frequencies"][index], rel_tol=1.0e-6, abs_tol=1.0e-4)
        for index, row in enumerate(rows)
    )


def ansys_rst_mesh_matches(left, right):
    if left["elements"] != right["elements"] or left["structural_nodes"] != right["structural_nodes"] or set(left["nodes"]) != set(right["nodes"]):
        return False
    return all(
        all(math.isclose(left["nodes"][label][index], right["nodes"][label][index], rel_tol=1.0e-9, abs_tol=1.0e-6) for index in range(3))
        for label in left["nodes"]
    )


def ansys_modal_subspaces_match(submitted, resolved):
    np = submitted["numpy"]
    groups = []
    current = [0]
    for index in range(1, 3):
        if (
            math.isclose(submitted["frequencies"][index - 1], submitted["frequencies"][index], rel_tol=2.0e-4, abs_tol=0.02)
            or math.isclose(resolved["frequencies"][index - 1], resolved["frequencies"][index], rel_tol=2.0e-4, abs_tol=0.02)
        ):
            current.append(index)
        else:
            groups.append(current)
            current = [index]
    groups.append(current)
    for group in groups:
        left = np.column_stack([submitted["mode_vectors"][index] for index in group])
        right = np.column_stack([resolved["mode_vectors"][index] for index in group])
        if np.linalg.matrix_rank(left) != len(group) or np.linalg.matrix_rank(right) != len(group):
            return False
        left_q = np.linalg.qr(left, mode="reduced")[0][:, :len(group)]
        right_q = np.linalg.qr(right, mode="reduced")[0][:, :len(group)]
        singular_values = np.linalg.svd(np.dot(left_q.T, right_q), compute_uv=False)
        if len(singular_values) != len(group) or float(np.min(singular_values)) < 0.995:
            return False
    return True


def run_ansys(work, db_path, rst_path, metrics):
    candidate_db = work / "candidate.db"
    submitted_rst = work / "submitted.rst"
    shutil.copy2(db_path, candidate_db)
    shutil.copy2(rst_path, submitted_rst)
    input_path = work / "check_task15_ansys.inp"
    input_path.write_text(ANSYS_INPUT, encoding="ascii")
    output_path = work / "ansys_run.out"
    execution = run_owned(
        [
            ANSYS_EXEC,
            "-b",
            "-dis",
            "-np",
            "1",
            "-j",
            "task15_eval",
            "-dir",
            str(work),
            "-i",
            str(input_path),
            "-o",
            str(output_path),
        ],
        cwd=work,
        timeout=900,
    )
    if execution["returncode"] != 0:
        raise RuntimeError("ANSYS native checker returned nonzero")
    run_text = output_path.read_text(encoding="utf-8", errors="replace") if nonempty(output_path) else ""
    errors = re.findall(r"NUMBER OF ERROR\s+MESSAGES ENCOUNTERED=\s*(\d+)", run_text)
    if not errors or int(errors[-1]) != 0 or "RUN COMPLETED" not in run_text.upper():
        raise RuntimeError("ANSYS native checker did not complete without errors")
    log("ANSYS checker stage: native batch completed")
    report_path = work / "ansys_check.json"
    listing_path = work / "model_listing.txt"
    load_audit_path = work / "load_audit.cdb"
    model_state_path = work / "model_state_audit.cdb"
    status_path = work / "solution_status.txt"
    submitted_sets_path = work / "submitted_sets.txt"
    resolved_sets_path = work / "resolved_sets.txt"
    resolved_rst_path = work / "recheck_task15.rst"
    if any(
        not nonempty(path)
        for path in (
            report_path,
            listing_path,
            load_audit_path,
            model_state_path,
            status_path,
            submitted_sets_path,
            resolved_sets_path,
            resolved_rst_path,
        )
    ):
        raise RuntimeError("ANSYS native checker outputs are missing")
    report = strict_json_object(report_path)
    if int(round(float(report.get("element_count", 0)))) != 20:
        raise RuntimeError("ANSYS database does not contain exactly 20 elements")
    submitted = [float(value) for value in report.get("submitted_frequencies", [])]
    resolved = [float(value) for value in report.get("resolved_frequencies", [])]
    if len(submitted) != 3 or len(resolved) != 3:
        raise RuntimeError("ANSYS submitted/re-solved first three modes are missing")
    if not frequency_lists_close(metrics, submitted):
        raise RuntimeError("metrics.json does not match submitted RST first three frequencies")
    if not frequency_lists_close(submitted, resolved, rel_tol=2.0e-4, abs_tol=0.02):
        raise RuntimeError("submitted RST is stale or does not match the DB re-solve")
    model_info = parse_ansys_model_listing(
        listing_path.read_text(encoding="utf-8", errors="replace")
    )
    log("ANSYS checker stage: DB listings parsed")
    reported_node_count = report.get("node_count")
    if (
        not finite_number(reported_node_count)
        or float(reported_node_count) <= 0.0
        or not float(reported_node_count).is_integer()
        or int(reported_node_count) != len(model_info["nodes"])
    ):
        raise RuntimeError("ANSYS node count does not match the complete node listing")
    submitted_rst_info = read_ansys_modal_rst(submitted_rst)
    log("ANSYS checker stage: submitted RST binary parsed")
    resolved_rst_info = read_ansys_modal_rst(resolved_rst_path)
    log("ANSYS checker stage: re-solved RST binary parsed")
    if resolved_rst_info["nsets"] != 3:
        raise RuntimeError("ANSYS isolated re-solve did not produce exactly three expanded modes")
    submitted_set_rows = parse_ansys_result_set_listing(
        submitted_sets_path.read_text(encoding="utf-8", errors="replace")
    )
    resolved_set_rows = parse_ansys_result_set_listing(
        resolved_sets_path.read_text(encoding="utf-8", errors="replace")
    )
    if not validate_ansys_result_sets(submitted_set_rows, submitted_rst_info):
        raise RuntimeError("ANSYS submitted RST contains another load step or an invalid modal set index")
    if not validate_ansys_result_sets(resolved_set_rows, resolved_rst_info):
        raise RuntimeError("ANSYS isolated re-solve result-set index is invalid")
    if not ansys_rst_mesh_matches(model_info, submitted_rst_info):
        differing = [
            label for label in sorted(set(model_info["elements"]).union(submitted_rst_info["elements"]))
            if model_info["elements"].get(label) != submitted_rst_info["elements"].get(label)
        ]
        log(
            "ANSYS submitted mesh mismatch diagnostics: DB/RST nodes=%s/%s structural=%s/%s differing_elements=%r first=%r/%r"
            % (
                len(model_info["nodes"]),
                len(submitted_rst_info["nodes"]),
                len(model_info["structural_nodes"]),
                len(submitted_rst_info["structural_nodes"]),
                differing[:5],
                model_info["elements"].get(differing[0]) if differing else None,
                submitted_rst_info["elements"].get(differing[0]) if differing else None,
            )
        )
        raise RuntimeError("ANSYS submitted RST mesh does not match the DB")
    if not ansys_rst_mesh_matches(model_info, resolved_rst_info):
        raise RuntimeError("ANSYS isolated re-solve RST mesh does not match the DB")
    if not frequency_lists_close(submitted, list(submitted_rst_info["frequencies"][:3]), rel_tol=2.0e-4, abs_tol=0.02):
        raise RuntimeError("ANSYS submitted RST binary frequencies do not match POST1")
    if not frequency_lists_close(resolved, list(resolved_rst_info["frequencies"][:3]), rel_tol=2.0e-4, abs_tol=0.02):
        raise RuntimeError("ANSYS re-solved RST binary frequencies do not match POST1")
    if not ansys_modal_subspaces_match(submitted_rst_info, resolved_rst_info):
        raise RuntimeError("ANSYS submitted RST mode shapes do not match the DB re-solve")
    for audit_path in (load_audit_path, model_state_path):
        if not ansys_export_has_no_forbidden_state(
            audit_path.read_text(encoding="utf-8", errors="replace"),
            model_info["used_sections"],
            model_info["used_materials"],
        ):
            raise RuntimeError("ANSYS model contains loads, prestress, or an initial state")
    status_text = status_path.read_text(encoding="utf-8", errors="replace").upper()
    if "ANALYSIS TYPE" not in status_text or "MODAL" not in status_text:
        raise RuntimeError("ANSYS saved solution state is not modal")
    log("ANSYS v261 native model/result/metrics re-solve matched")
    return True


def evaluate():
    root = desktop_dir()
    work = None
    passed = False
    try:
        metrics = load_metrics(root)
        branch, model_path, result_path = select_branch(root)
        temp_root = Path(os.environ.get("TEMP") or tempfile.gettempdir())
        work = Path(tempfile.mkdtemp(prefix="engiworld_task15_eval_", dir=str(temp_root)))
        if branch == "abaqus":
            passed = run_abaqus(work, model_path, result_path, metrics)
        else:
            passed = run_ansys(work, model_path, result_path, metrics)
    except Exception as exc:
        log(exc)
        passed = False
    finally:
        if work is not None:
            try:
                cleanup_owned_processes(work)
            except Exception as exc:
                log("owned process cleanup failed: %s" % exc)
                passed = False
            try:
                shutil.rmtree(str(work))
            except Exception as exc:
                log("temporary evaluator cleanup failed: %s" % exc)
                passed = False
    return passed, root


def write_results(root, passed):
    try:
        (root / "eval_detail.txt").write_text("\n".join(DETAILS) + "\n", encoding="utf-8")
        (root / "eval_result.txt").write_text("True\n" if passed else "False\n", encoding="utf-8")
    except Exception:
        pass


def main():
    passed, root = evaluate()
    write_results(root, passed)
    sys.stdout.write("True\n" if passed else "False\n")


if __name__ == "__main__":
    main()
