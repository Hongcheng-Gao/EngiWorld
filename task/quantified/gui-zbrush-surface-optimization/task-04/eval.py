from __future__ import annotations

import json
import math
import os
from collections import defaultdict, deque
from pathlib import Path

TASK = {'instruction_tail': 'Optimize a symmetric thumb-rest pocket. The opened `seed.obj` is the starting mesh. Use ZBrush sculpting/modeling tools to optimize the shape, then export `C:\\Users\\user\\Desktop\\optimized.obj`. Create a centered pocket with soft shoulders. The exact field targets about Z=-0.58 at the center, so a useful center-depth band is approximately 0.52 to 0.62 OBJ units below Z=0. The exported OBJ must remain one edge-connected open height-field surface with one regular boundary loop and at least 98% coverage of that fixed grid. It must have no unused vertices, degenerate faces, non-manifold edges, additional boundary loops, overlapping XY triangle interiors, or multiple surface heights at a sample. A topology or coverage failure receives a score of 0, so changing vertex density cannot improve the sampling weight.', 'kind': 'thumb', 'metric': 'thumb-pocket fixed-grid height-field RMSE with span, mean-height, and face-count penalties', 'target': {'amp': 0.36, 'freq': 2.0, 'ridge': -0.22, 'smooth': 0.13}, 'title': 'Optimize thumb-rest clay sculpt'}
BASELINE = {'score': 88.0391}
GRID_SIZE = 40
EPS = 1e-9


def z_target(kind, x, y, target):
    amp = target["amp"]
    freq = target["freq"]
    ridge = target["ridge"]
    if kind == "grip":
        return amp * math.sin(freq * math.pi * (x + 1) / 2) * (1 - 0.25 * y * y) + ridge * math.exp(-8 * x * x)
    if kind == "rock":
        return amp * (0.55 * math.sin(freq * x + 1.7 * y) + 0.45 * math.sin(2.2 * x - freq * y)) + ridge * math.cos(4 * x * y)
    if kind == "gasket":
        r = math.sqrt(x * x + y * y)
        ring = math.exp(-18 * (r - 0.62) ** 2)
        return amp * ring + ridge * math.exp(-12 * (x * x + y * y))
    if kind == "thumb":
        pocket = -amp * math.exp(-4.5 * (x * x + 0.65 * y * y))
        shoulders = 0.16 * math.exp(-16 * (abs(x) - 0.55) ** 2) * (1 - 0.3 * y * y)
        return pocket + shoulders + ridge * math.exp(-8 * y * y)
    if kind == "texture":
        return amp * math.sin(freq * (x + 0.25 * y)) * (0.45 + 0.55 * (y + 1) / 2) + ridge * x
    return 0.0


def parse_obj(path):
    verts = []
    faces = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if line.startswith("v "):
            parts = line.split()
            if len(parts) >= 4:
                verts.append(tuple(map(float, parts[1:4])))
        elif line.startswith("f "):
            indices = []
            for token in line.split()[1:]:
                value = int(token.split("/")[0])
                indices.append(value - 1 if value > 0 else len(verts) + value)
            if len(indices) >= 3:
                faces.append(indices)
    return verts, faces


def triangulate(faces):
    triangles = []
    for face_index, face in enumerate(faces):
        for index in range(1, len(face) - 1):
            triangles.append((face[0], face[index], face[index + 1], face_index))
    return triangles


def orient(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def point_strictly_inside(point, tri):
    values = [orient(tri[0], tri[1], point), orient(tri[1], tri[2], point), orient(tri[2], tri[0], point)]
    return all(value > EPS for value in values) or all(value < -EPS for value in values)


def proper_segment_intersection(a, b, c, d):
    ab_c = orient(a, b, c)
    ab_d = orient(a, b, d)
    cd_a = orient(c, d, a)
    cd_b = orient(c, d, b)
    return ab_c * ab_d < -EPS and cd_a * cd_b < -EPS


def projected_triangles_overlap(first, second):
    for index in range(3):
        a, b = first[index], first[(index + 1) % 3]
        for other in range(3):
            c, d = second[other], second[(other + 1) % 3]
            if proper_segment_intersection(a, b, c, d):
                return True
    if any(point_strictly_inside(point, second) for point in first):
        return True
    if any(point_strictly_inside(point, first) for point in second):
        return True
    centroid_first = tuple(sum(point[axis] for point in first) / 3.0 for axis in (0, 1))
    centroid_second = tuple(sum(point[axis] for point in second) / 3.0 for axis in (0, 1))
    return point_strictly_inside(centroid_first, second) or point_strictly_inside(centroid_second, first)


def topology_errors(verts, faces, triangles, normalized_xy):
    errors = []
    if not faces or not triangles:
        return ["mesh has no faces"]
    if any(index < 0 or index >= len(verts) for face in faces for index in face):
        return ["face index out of range"]
    used = {index for face in faces for index in face}
    if len(used) != len(verts):
        errors.append("mesh contains unused vertices")

    edge_faces = defaultdict(list)
    face_neighbors = defaultdict(set)
    degenerate = 0
    for a, b, c, face_index in triangles:
        if len({a, b, c}) < 3 or abs(orient(normalized_xy[a], normalized_xy[b], normalized_xy[c])) <= EPS:
            degenerate += 1
    for face_index, face in enumerate(faces):
        if len(set(face)) != len(face):
            degenerate += 1
        for i, a in enumerate(face):
            b = face[(i + 1) % len(face)]
            edge_faces[tuple(sorted((a, b)))].append(face_index)
    if degenerate:
        errors.append(f"mesh has {degenerate} degenerate faces/triangles")
    if any(len(owners) > 2 for owners in edge_faces.values()):
        errors.append("mesh has non-manifold edges")
    for owners in edge_faces.values():
        if len(owners) == 2:
            first, second = owners
            face_neighbors[first].add(second)
            face_neighbors[second].add(first)
    seen = set()
    queue = deque([0])
    while queue:
        current = queue.popleft()
        if current in seen:
            continue
        seen.add(current)
        queue.extend(face_neighbors[current] - seen)
    if len(seen) != len(faces):
        errors.append("mesh is not one edge-connected surface")

    boundary = [edge for edge, owners in edge_faces.items() if len(owners) == 1]
    boundary_graph = defaultdict(set)
    for a, b in boundary:
        boundary_graph[a].add(b)
        boundary_graph[b].add(a)
    if not boundary or any(len(neighbors) != 2 for neighbors in boundary_graph.values()):
        errors.append("open surface must have one regular boundary loop")
    elif boundary_graph:
        boundary_seen = set()
        queue = deque([next(iter(boundary_graph))])
        while queue:
            current = queue.popleft()
            if current in boundary_seen:
                continue
            boundary_seen.add(current)
            queue.extend(boundary_graph[current] - boundary_seen)
        if len(boundary_seen) != len(boundary_graph):
            errors.append("open surface has multiple boundary loops")

    bins = defaultdict(list)
    projected = []
    bin_count = 24
    for triangle_index, (a, b, c, _) in enumerate(triangles):
        tri = (normalized_xy[a], normalized_xy[b], normalized_xy[c])
        projected.append(tri)
        min_x, max_x = min(p[0] for p in tri), max(p[0] for p in tri)
        min_y, max_y = min(p[1] for p in tri), max(p[1] for p in tri)
        bx0 = max(0, min(bin_count - 1, int((min_x + 1) * 0.5 * bin_count)))
        bx1 = max(0, min(bin_count - 1, int((max_x + 1) * 0.5 * bin_count)))
        by0 = max(0, min(bin_count - 1, int((min_y + 1) * 0.5 * bin_count)))
        by1 = max(0, min(bin_count - 1, int((max_y + 1) * 0.5 * bin_count)))
        for bx in range(bx0, bx1 + 1):
            for by in range(by0, by1 + 1):
                bins[(bx, by)].append(triangle_index)
    checked = set()
    for candidates in bins.values():
        for offset, first_index in enumerate(candidates):
            for second_index in candidates[offset + 1:]:
                pair = (min(first_index, second_index), max(first_index, second_index))
                if pair in checked:
                    continue
                checked.add(pair)
                if projected_triangles_overlap(projected[first_index], projected[second_index]):
                    errors.append("mesh has overlapping projected triangle interiors")
                    return errors
    return errors


def interpolate_z(point, tri_ids, verts, normalized_xy):
    a, b, c = tri_ids
    pa, pb, pc = normalized_xy[a], normalized_xy[b], normalized_xy[c]
    denominator = orient(pa, pb, pc)
    if abs(denominator) <= EPS:
        return None
    wa = orient(pb, pc, point) / denominator
    wb = orient(pc, pa, point) / denominator
    wc = 1.0 - wa - wb
    if min(wa, wb, wc) < -1e-8:
        return None
    return wa * verts[a][2] + wb * verts[b][2] + wc * verts[c][2]


def sample_surface(verts, triangles, normalized_xy):
    samples = []
    overlap_samples = 0
    for row in range(GRID_SIZE):
        y = -1.0 + (row + 0.5) * 2.0 / GRID_SIZE
        for column in range(GRID_SIZE):
            x = -1.0 + (column + 0.5) * 2.0 / GRID_SIZE
            values = []
            for a, b, c, _ in triangles:
                z = interpolate_z((x, y), (a, b, c), verts, normalized_xy)
                if z is not None:
                    values.append(z)
            if values:
                if max(values) - min(values) > 1e-5:
                    overlap_samples += 1
                samples.append((x, y, sum(values) / len(values)))
    return samples, overlap_samples


def score(verts, faces):
    if not verts:
        return {"score": 0.0, "error": "no vertices"}
    if any(not math.isfinite(value) for vertex in verts for value in vertex):
        return {"score": 0.0, "error": "vertices contain NaN or infinity"}
    xs = [value[0] for value in verts]
    ys = [value[1] for value in verts]
    x_span = max(xs) - min(xs)
    y_span = max(ys) - min(ys)
    if x_span <= EPS or y_span <= EPS:
        return {"score": 0.0, "error": "degenerate XY span"}
    normalized_xy = [
        (-1.0 + 2.0 * (x - min(xs)) / x_span, -1.0 + 2.0 * (y - min(ys)) / y_span)
        for x, y, _ in verts
    ]
    triangles = triangulate(faces)
    errors = topology_errors(verts, faces, triangles, normalized_xy)
    samples, overlap_samples = sample_surface(verts, triangles, normalized_xy)
    coverage = len(samples) / float(GRID_SIZE * GRID_SIZE)
    if coverage < 0.98:
        errors.append(f"fixed-grid coverage {coverage:.4f} is below 0.98")
    if overlap_samples:
        errors.append(f"{overlap_samples} fixed-grid samples have multiple surface heights")

    if samples:
        errors_sq = [
            (z - z_target(TASK["kind"], x, y, TASK["target"])) ** 2
            for x, y, z in samples
        ]
        rmse = math.sqrt(sum(errors_sq) / len(errors_sq))
        mean_abs_height = sum(abs(z) for _, _, z in samples) / len(samples)
    else:
        rmse = float("inf")
        mean_abs_height = 0.0
    face_count = len(faces)
    face_penalty = max(0, 300 - face_count) * 0.03 + max(0, face_count - 8000) * 0.002
    bbox_penalty = abs(x_span - 2.0) * 8.0 + abs(y_span - 2.0) * 8.0
    smooth_penalty = abs(mean_abs_height - TASK["target"]["smooth"]) * 15.0
    raw_score = max(0.0, 100.0 - rmse * 110.0 - smooth_penalty - bbox_penalty - face_penalty)
    score_value = 0.0 if errors else raw_score
    return {
        "score": round(score_value, 4),
        "rmse": round(rmse, 5) if math.isfinite(rmse) else None,
        "mean_abs_height": round(mean_abs_height, 5),
        "bbox_penalty": round(bbox_penalty, 5),
        "grid_coverage": round(coverage, 5),
        "grid_samples": len(samples),
        "topology_valid": not errors,
        "topology_errors": errors,
        "vertex_count": len(verts),
        "face_count": face_count,
    }


def main():
    desktop = Path(os.environ.get("ENGIWORLD_DESKTOP", Path.home() / "Desktop"))
    output = desktop / TASK.get("output", "optimized.obj")
    if not output.exists():
        print(json.dumps({"score": 0.0, "error": "missing optimized.obj", "baseline_score": BASELINE["score"]}, sort_keys=True))
        return 0
    verts, faces = parse_obj(output)
    result = score(verts, faces)
    result.update({"metric_direction": "maximize", "metric_name": TASK["metric"], "baseline_score": BASELINE["score"]})
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
