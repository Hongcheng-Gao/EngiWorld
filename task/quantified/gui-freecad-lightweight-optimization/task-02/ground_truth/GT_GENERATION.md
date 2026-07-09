# Ground Truth Generation

Generated with a local Python artifact-generation workflow before repository packaging.

Package APIs used:
- `trimesh` and `numpy`: baseline/reference STL geometry and reference metrics
- `ezdxf`: profile and required-zone DXF drawing
- Python `json`: constraints, reference metrics, and score metadata

The reference is not a unique answer. The evaluator assigns a continuous score from the submitted STL geometry.
