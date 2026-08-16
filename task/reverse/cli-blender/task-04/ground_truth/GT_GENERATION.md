# Ground-truth generation

Date: 2026-08-14 (Asia/Shanghai)

## Scope and diagnosis

The task instruction, `geometry_report.csv`, and `hole_table.csv` agree on a
4.0 x 2.0 x 0.2 closed plate, six diameter-0.30 through-bores at X=-1.2/0/1.2
and Y=-0.5/+0.5, and a centered 2.0 x 0.8 top pocket cut 0.08 deep. The old
ground truth used Y=-0.4/+0.4 for the two bore rows. Blender 4.2.3 opened that
file successfully, but the formal evaluator returned `False`.

No init or evaluator file was changed. The init inputs remain authoritative.

## Native generation

- Snapshot: `Blender-4.2.3`
- Instance: `i-yestjr8h6owh2yrgnct8` (`10.0.6.67`)
- Executable: `/usr/local/bin/blender`
- Reported version: `Blender 4.2.3 LTS`
- Build hash/date: `0e22e4fcea03`, 2024-10-14 23:31:34
- Generation command:
  `blender --background --factory-startup --python generate_task04.py -- /home/user/Desktop/answer.blend`

The script created the plate, applied six separate Exact Boolean cylindrical
cuts at the table coordinates, applied one Exact Boolean rectangular pocket,
deleted every cutter, and saved one mesh object named `Plate`.

Final native mesh evidence before saving:

- dimensions: 4.0 x 2.0 x 0.200000003
- vertices / edges / faces: 802 / 1221 / 409
- connected components: 1 (confirmed by the evaluator)
- Euler characteristic: -10
- boundary edges: 0
- non-manifold edges: 0
- volume: 1.3885473206
- bore centers: (-1.2,-0.5), (0,-0.5), (1.2,-0.5),
  (-1.2,0.5), (0,0.5), (1.2,0.5)
- pocket: 2.0 x 0.8, top Z=0.1, floor Z=0.02, depth 0.08

## Hashes

- old rejected `answer.blend`:
  `8e0fde31453b6a284acac7f4651145889a4e855e964b31a1f5e4124eeebdb164`
- regenerated `answer.blend`:
  `a48d7a1b9ac554441faa2d9c097c65daf923de819dda5544efebdd19002a09ac`
- `reference_view.png`:
  `44ce2dfc0dd113cf160e99cda615bc9d0e67cc12f152ef1b408d004cf7be02c1`
- `geometry_report.csv`:
  `8e2eff8f26516e6e92a7e5efaae3a78c216174c2f72c0980a9fadfdfc54a4306`
- `hole_table.csv`:
  `cb71051423e6167acd03dcd5f34b8375b46c29b7a96d15453350b46e181a0ef2`

## Validation

- regenerated formal GT: `True`
- equivalent scene with only non-mesh evidence metadata and a different world
  color: `True`
- old GT with bore rows at Y=-0.4/+0.4: `False`
- regenerated GT with an injected second mesh object: `False`

The downloaded local GT hash matches the instance artifact that passed the
formal evaluator.

The same four-case matrix was independently rerun after the local replacement
against a newly uploaded, hash-checked copy on the clean `Blender-4.2.3`
instance. It again returned `True / True / False / False`; the instance-side
formal GT SHA-256 was
`a48d7a1b9ac554441faa2d9c097c65daf923de819dda5544efebdd19002a09ac`.

## Official Blender 4.2 references

- https://download.blender.org/release/Blender4.2/
- https://docs.blender.org/manual/en/4.2/modeling/modifiers/generate/booleans.html
- https://docs.blender.org/api/4.2/bpy.types.Object.html
- https://docs.blender.org/api/4.2/bpy.types.Depsgraph.html
- https://docs.blender.org/api/4.2/bpy.types.Mesh.html
- https://docs.blender.org/manual/en/4.2/files/blend/compatibility.html

The Boolean manual documents Difference and the Exact solver and warns that
manifold operands are the supported basis for reliable results. The API
documentation supports evaluating the final object through the dependency graph
and `Object.to_mesh()`, matching the evaluator's inspection path. The blend-file
compatibility documentation confirms that Blender normally converts older files
when opening them; the delivered file was then saved natively by 4.2.3.
