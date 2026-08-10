# Ground Truth Generation

Generated with a local Python artifact-generation workflow before repository packaging.

Package APIs used:
- `trimesh`, `manifold3d`, and `numpy`: Boolean-union the reference primitives into one watertight solid, export STL geometry, and compute reference metrics
- `ezdxf`: profile and required-zone DXF drawing
- Python `json`: constraints, reference metrics, and score metadata

The reference is not a unique answer. The evaluator assigns a continuous score from the submitted STL geometry.
