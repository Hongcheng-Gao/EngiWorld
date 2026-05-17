# -*- coding: utf-8 -*-
"""
Generate task/task-false/<app>/* — English instructions, ids: c-<app>-<os> / v-<app>-<os>.

Design (per user request):
- A small number of fictional/contradictory tasks (currently 3; one per app folder).
- cross_domain and missing_init counts are kept similar (after fictional: ~12 vs ~13).
- cross_domain: pasted workflow text is copied verbatim from a real benchmark task body (often task-c task-02/21/etc.),
  prefixed with incompatible-tool constraints only (large CAD/CAM/EDA/BIM/CFD crosses); no other-task id names.
- missing_init: same instruction text as a real EngiWorld task that normally uploads init files,
  but this JSON uses an empty upload list.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "task" / "task-false"

EVAL_TEMPLATE = '''# -*- coding: utf-8 -*-
# Infeasible verdict check. Stdout must be exactly True\\n or False\\n.
import sys

VERDICT_FILE = r"{verdict_file}"

def main() -> None:
    try:
        raw = open(VERDICT_FILE, encoding="utf-8", errors="replace").read()
    except OSError:
        raw = ""
    ok = raw.strip().lower() == "false"
    sys.stdout.write("True\\n" if ok else "False\\n")

if __name__ == "__main__":
    main()
'''


def judgment_tail(path_hint: str) -> str:
    return (
        " Judgment: If and only if the above is impossible under the stated constraints "
        "(no undocumented workarounds that violate the constraint text), create the UTF-8 text file `{p}` "
        "whose entire content is exactly one line: false (ASCII lowercase, no quotes). "
        "If you judge the task feasible, do not fabricate the impossible deliverable; "
        "do not write a misleading verdict."
    ).format(p=path_hint)


def build_instruction(body: str, path_hint: str, kind: str) -> str:
    prefix = ""
    if kind == "missing_init":
        prefix = (
            "Environment note: this task profile performs no file pre-upload (empty upload list); "
            "the input paths below are therefore not provisioned for you. "
        )
    return prefix + body + judgment_tail(path_hint)


# --- Verbatim-style bodies from real benchmark tasks (see task/task-c and task/task-v). ---

CADENCE_ORCAD_T01 = (
    "There are two independent OrCAD designs in `C:\\Users\\User\\Desktop\\`: "
    "`C:\\Users\\User\\Desktop\\design_a.DSN` (a BCD sample containing 20 components `U30..U49`) and "
    "`C:\\Users\\User\\Desktop\\design_b.DSN` (a FULLADD sample containing the schematic folders `HALFADD` and `FULLADD`). "
    "Open the two designs in Capture, extract every Part reference designator, and write a merged list to "
    "`C:\\Users\\User\\Desktop\\merged_refdes.txt`. Requirements: - One refdes per line. "
    "- Prefix every refdes from `C:\\Users\\User\\Desktop\\design_a.DSN` with `A:`, for example `A:U30`. "
    "- Prefix every refdes from `C:\\Users\\User\\Desktop\\design_b.DSN` with `B:`, for example `B:U1` and `B:U2`. "
    "- Sort first by prefix (`A` before `B`), then lexicographically by the original refdes. "
    "- Use `\\n` line endings; a trailing blank line is optional. Only output the merged refdes list. "
    "Do not output modified DSN files."
)

SOLIDWORKS_T21 = (
    "Using SolidWorks command-line automation, use input file C:\\Users\\User\\Desktop\\cli_021_three_plate_assembly.step "
    "containing base_plate, spacer, and top_plate. The base_plate and top_plate are each 120 x 80 x 6 mm, and the spacer "
    "is 20 x 20 x 30 mm. Keep all three as independent parts. Move the spacer to the center on top of base_plate, then "
    "place top_plate on top of the spacer so the stack is vertical and all XY centers align. Export "
    "C:\\Users\\User\\Desktop\\cli_021_stack_assembly_out.step as an assembly or multi-body STEP retaining three independent "
    "solids, and write C:\\Users\\User\\Desktop\\cli_021_massprops.txt containing assembly mass or volume properties."
)

FREECAD_T21 = (
    "Open /home/user/Desktop/freecad_task-21_input.step. It contains five separate solids: one base plate plus four loose "
    "fixture components. Keep all components unchanged and do not fuse them. Place the base plate at X=0..120, Y=0..70, Z=0..8. "
    "Move the 65 x 10 x 12 mm rail so it spans X=12..77, Y=12..22, Z=8..20. Rotate the 40 x 12 x 12 mm rail 90 degrees about Z "
    "and place it so it spans X=84..96, Y=18..58, Z=8..20. Move the triangular rib so its bounding box is X=24..36, Y=40..64, "
    "Z=8..32, with material at the low-Y/high-Z corner and no material at the high-Y/high-Z corner. Move the cylindrical boss "
    "to center (96,52), diameter 18 mm, Z=8..30. Export a five-solid compound as /home/user/Desktop/freecad_task-21_output.step."
)

KICAD_T21 = (
    "V-Score Panel with Rail You have a single-board design in `/home/user/Desktop/A.kicad_pcb` (50x30 mm, containing R1, C1, D1 "
    "footprints). You must create a panelized version with rails and V-score markings for depaneling. Generate `/home/user/Desktop/panel.kicad_pcb` "
    "as a 3-column x 2-row panel of the A board. Requirements: 1. Panel outer Edge.Cuts outline must be within a 180x120 mm bounding box. "
    "2. Include 6 copies of A board's footprints (refdes prefixed: A1_R1, A1_C1, A1_D1, A2_R1,... A6_D1) placed in a 3x2 grid with 50 mm "
    "horizontal spacing and 30 mm vertical spacing, plus 5 mm rails at top and bottom and 5 mm margins on left and right. "
    "3. Add at least 5 V-score lines on the Eco1.User layer: 2 vertical interior seams (between columns), 1 horizontal interior seam "
    "(between rows), plus top and bottom rail boundary lines. 4. Include exactly 12 Fiducial:Fiducial_1mm_Mask2mm footprints: 3 per rail "
    "corner group (top-left, top-right, bottom-left, bottom-right corners of the panel rails). 5. All 6 board instances must not overlap: "
    "centroid distance between instances >= 20 mm. 6. Also write `/home/user/Desktop/edgecuts.svg` as the native KiCad CLI Edge.Cuts SVG "
    "export of your final panel. 7. Also write `/home/user/Desktop/eco1.svg` as the native KiCad CLI Eco1.User SVG export of your final panel. "
    "Write /home/user/Desktop/panel.kicad_pcb, /home/user/Desktop/edgecuts.svg, and /home/user/Desktop/eco1.svg."
)

ALTIUM_T02 = (
    "Fix the native Altium rigid-flex board `C:\\Users\\Administrator\\Desktop\\broken_bluetooth_rigidflex.PcbDoc` and save the repaired "
    "document as `C:\\Users\\Administrator\\Desktop\\bluetooth_rigidflex.PcbDoc`. The repaired document must restore the rigid/flex substack "
    "naming fragments, the flex dielectric material and dielectric-height fragments, and the bend-line region fragment."
)

BRLCAD_T21 = (
    "Use BRL-CAD to read /home/user/Desktop/block_a.step and /home/user/Desktop/cyl_b.step. Reorient the cylinder so its axis is along Y and "
    "passes through the center of the block, then fuse it with the block. Cut a central through hole of diameter 10 mm along Z through the "
    "fused solid. Save the completed STL mesh as /home/user/Desktop/out.stl."
)

NXCAM_T21 = (
    "Read the initial file(s) from the Desktop path(s): C:\\Users\\User\\Desktop\\cli_plate.step, C:\\Users\\User\\Desktop\\tools.txt. "
    "Create a Milling CAM setup and Face Milling operation for C:\\Users\\User\\Desktop\\cli_plate.step. Set the MCS origin at the blank top-face "
    "center. Use T1 to machine the top face to Z=10.000 mm with S6000 rpm and F750 mm/min. Tool definition: T1 is a 12 mm face mill, S6000 rpm, "
    "F750 mm/min. Write the required output file(s) using exactly this Desktop path: C:\\Users\\User\\Desktop\\task-21.nc."
)

EAGLE_T02 = (
    "Open `/home/user/Desktop/audit.brd` in EAGLE, then run the provided silkscreen-audit User Language Program and save its output as "
    "`/home/user/Desktop/silk_audit.txt`. Each line in the output has the form: `text=\"VALUE\" x=X.XXX y=Y.YYY size=S.SSS layer=tPlace|bPlace` "
    "Requirements: 1. `/home/user/Desktop/silk_audit.txt` exists and is non-empty. 2. Every line conforms to the above format. "
    "3. Number of reported lines equals the number of <text> elements in /home/user/Desktop/audit.brd on layers 21/22 with size < 0.8 mm. "
    "4. Every expected violation appears in the report (by value, x, y, size, layer). 5. No false positives (no reported text has size >= 0.8 mm)."
)

FENICS_T02 = (
    "You are given an incomplete template `/home/user/Desktop/neumann_base.py`. Complete the following: 1. Modify and generate `/home/user/Desktop/neumann.py`: "
    "- Use `MeshFunction` to mark boundaries: left boundary (`x=0`) as Dirichlet `u=0`, right boundary (`x=1`) as Neumann `g=4` "
    "- Include the Neumann term in the variational form: `inner(g, v)*ds(1)` - Solve and extract the value at point `(1.0, 0.5)` "
    "- Extract the global maximum value 2. Run: `cd outputs && python neumann.py` 3. Save results to `/home/user/Desktop/summary.txt` in this format: `point_value, max_value`"
)

FLORIS_T02 = (
    "You are given an incomplete script `/home/user/Desktop/yaw_base.py`. FLORIS can perform wake steering through yaw control. Complete the following from the command line: "
    "1. Write a complete script `/home/user/Desktop/yaw.py`: - Compute baseline case power (`yaw=0°`) - Compute power with upstream yaw of `20°` "
    "- Extract `turbine_1` (downstream) power in both cases 2. Execute and save to `/home/user/Desktop/summary.txt` in this format: `baseline_t1_kw, yawed_t1_kw, power_gain_percent`"
)

OPENFAST_T02 = (
    "You are given the TurbSim input template `/home/user/Desktop/turbsim_base.inp`. Complete the following from the command line: "
    "1. Modify and generate `/home/user/Desktop/turbsim.inp`: - Set IEC turbulence class B (`IECturbc=B`) - Set reference wind speed to 8 m/s and `RefHt=90 m` "
    "- Run TurbSim to generate `/home/user/Desktop/wind_8ms.bts` 2. Create the OpenFAST main file `/home/user/Desktop/case_turb.fst`: "
    "- In InflowWind, use `WindType=3` (TurbSim binary), and set `Filename` to `wind_8ms.bts` - Set simulation time to 60 s "
    "3. Execute `turbsim turbsim.inp` and `openfast case_turb`. 4. Write a post-processing script to parse `case_turb.out`: "
    "- Extract the `GenPwr` time series and compute mean and standard deviation - Save to `/home/user/Desktop/summary.txt` in this format: `mean_pwr_kw, std_pwr_kw` "
    "5. Do not use GUI tools."
)

OPENFOAM_T02 = (
    "You are given an incomplete cavity template `/home/user/Desktop/cavity_base/`. Complete a lid-driven cavity analysis from the command line: "
    "1. Modify and create `/home/user/Desktop/cavity/`: - Build a square-cavity geometry and set mesh density and properties appropriate for `Re ≈ 1000` "
    "- Set lid-driven boundary conditions; all other walls are no-slip - Configure transient solver parameters until the flow stabilizes "
    "2. Run the solver to convergence. 3. Extract the velocity component at the geometric center and verify the main vortex rotation direction. "
    "4. Write a post-processing script to output `/home/user/Desktop/summary.txt`: - Geometric-center `Ux` - Format: `center_ux` 5. Do not use GUI tools."
)

REVIT_T13 = (
    "The init file is located at C:\\Users\\Administrator\\Desktop\\init.ifc. You need to open it yourself before doing the task. "
    "Storefront Retrofit IFC And Revit Elevation Sheet PDF This task starts from init.ifc and uses the local reference image init_sheet.png. "
    "In Revit, modify the starting model into a storefront scheme, export the model as result.ifc, and export a one-page Revit elevation sheet as "
    "result.pdf in the Desktop. 1. The output folder contains result.ifc and result.pdf; result.ifc is at least 500 bytes and result.pdf is at least 200 bytes. "
    "2. Result.ifc uses an IFC4 schema. 3. All IfcRoot GlobalId values are unique. 4. The IFC model contains exactly 1 IfcProject, 1 IfcSite, 1 IfcBuilding, "
    "1 IfcBuildingStorey, 1 IfcSpace, 4 IfcWall entities, 1 IfcSlab, 1 IfcDoor entity, and 4 IfcWindow entities. 5. The IFC model contains 0 IfcRoof, 0 IfcStair, "
    "0 IfcColumn, 0 IfcBeam, 0 IfcCurtainWall, and 0 IfcBuildingElementProxy entities. 6. After replacing hyphens and underscores with spaces and lowercasing names, "
    "the IfcSpace name list contains the exact space name retail space. 7. Result.pdf contains exactly 1 page exported from a Revit sheet. "
    "8. The extracted text from result.pdf contains the case-insensitive tokens STOREFRONT ELEVATION and Main street facade. Any item not explicitly required may vary."
)

ARCHICAD_T18 = (
    "Three-Storey Shell Conversion Without Zones This task starts from C:\\Users\\Administrator\\Desktop\\init.ifc. Reference images are provided on the Desktop: "
    "C:\\Users\\Administrator\\Desktop\\init_plan.png, C:\\Users\\Administrator\\Desktop\\init_section.png. Modify the Archicad model as needed and save the required output as "
    "C:\\Users\\Administrator\\Desktop\\result.ifc. 1. The output folder contains C:\\Users\\Administrator\\Desktop\\result.ifc with size at least 500 bytes. "
    "2. C:\\Users\\Administrator\\Desktop\\result.ifc uses an IFC4 schema. 3. All IfcRoot GlobalId values are unique. 4. The IFC model contains exactly 3 IfcBuildingStorey entities "
    "and exactly 0 IfcSpace entities. 5. The IFC model contains at least 12 IfcWall entities, at least 3 IfcSlab entities, at least 9 IfcDoor entities, and at least 6 IfcWindow entities. "
    "6. The shaped IFC product bounding box is within 0.5 m of min [0.0, 0.0, -0.048] and max [12.0, 8.0, 10.2]. Any item not explicitly required may vary."
)

AUTOCAD_T21 = (
    "Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\\Users\\Administrator\\Desktop\\cli_blank_seed.dxf. Start from cli_blank_seed.dxf. "
    "Draw a 200 x 120 drawing frame on OUTLINE, a title block rectangle from (130,0) to (200,25), divider lines from (130,12.5) to (200,12.5) and from (165,0) to (165,25), "
    "add text ACAD-21 on ANNOTATION, and keep all geometry in autocad_result.dxf. Export exactly one DXF deliverable named "
    "C:\\Users\\Administrator\\Desktop\\autocad_result.dxf to the output folder."
)

OPENSTUDIO_T18 = (
    "Two-Office Balanced Layout Model This task starts from Desktop input files: /home/user/Desktop/init.osm, /home/user/Desktop/weather.epw. "
    "Reference image is provided on the Desktop: /home/user/Desktop/init_plan.png. Modify the OpenStudio model as needed and save the required output as /home/user/Desktop/result.osm. "
    "1. The output folder contains /home/user/Desktop/result.osm with size at least 500 bytes. 2. /home/user/Desktop/result.osm contains exactly one OS:Version object whose version identifier starts with 3.10. "
    "3. /home/user/Desktop/result.osm contains exactly 1 OS:BuildingStory, 2 OS:Space objects, and 2 OS:ThermalZone objects. 4. The OS:Space names are exactly NorthOffice and SouthOffice. "
    "5. Every OS:Space references the OS:BuildingStory, references an OS:ThermalZone, and has floor area greater than 0.05 m2. 6. The model has exactly 12 OS:Surface objects: 2 Floor surfaces, "
    "2 RoofCeiling surfaces, and 8 Wall surfaces. 7. The surface Outside Boundary Condition counts are exactly 2 Ground, 8 Outdoors, and 2 Surface. 8. The model has exactly 6 OS:SubSurface objects, "
    "all counted window subsurfaces are FixedWindow, and the fixed-window count is exactly 6. 9. The model contains exactly 2 OS:ZoneHVAC:IdealLoadsAirSystem objects, 2 OS:ZoneHVAC:EquipmentList objects, "
    "2 OS:ThermostatSetpoint:DualSetpoint objects, 1 OS:People object, 1 OS:Lights object, and 1 OS:ElectricEquipment object. 10. The surface geometry bounding box has X span 12.00 m, Y span 12.00 m, and Z span 3.20 m, "
    "each with tolerance +/-0.05 m. 11. The sum of floor surface areas is 144.00 m2 with tolerance +/-0.50 m2. 12. The sum of exterior wall gross areas is 153.60 m2 with tolerance +/-0.50 m2. "
    "13. The total fixed-window area is 30.72 m2 with tolerance +/-0.50 m2. Any item not explicitly required may vary."
)

BONSAI_T20 = (
    "Merge House And Garage Models With Summary CSV This task starts from /home/user/Desktop/house.ifc and /home/user/Desktop/garage.ifc and may use the local reference images on the Desktop: "
    "/home/user/Desktop/combined_overview.png, /home/user/Desktop/garage_plan.png, /home/user/Desktop/house_plan.png. Merge the provided models and save the required outputs as "
    "/home/user/Desktop/result.ifc and /home/user/Desktop/result.csv. 1. The output folder contains /home/user/Desktop/result.ifc and /home/user/Desktop/result.csv; /home/user/Desktop/result.ifc is at least 500 bytes "
    "and /home/user/Desktop/result.csv is not empty. 2. /home/user/Desktop/result.ifc uses an IFC4 schema. 3. The IFC model contains exactly 1 IfcProject, 1 IfcSite, 1 IfcBuilding, 1 IfcBuildingStorey, 4 IfcSpace entities, "
    "10 IfcWall entities, and 3 IfcSlab entities. 4. The IFC model contains 0 IfcDoor, 0 IfcWindow, 0 IfcRoof, 0 IfcBuildingElementProxy, 0 IfcFurniture, 0 IfcColumn, 0 IfcBeam, 0 IfcStair, and 0 IfcFlowTerminal entities. "
    "5. All IfcRoot GlobalId values are unique. 6. The single IfcProject is named exactly Merged House Garage, the single IfcSite is named exactly Default Site, the single IfcBuilding is named exactly Default Building, "
    "and the single IfcBuildingStorey is named exactly Ground Floor, each ignoring leading and trailing whitespace only. 7. The IfcSpace names are exactly House Living, House Bed, House Kitchen, and Garage Bay, "
    "ignoring leading and trailing whitespace only. 8. House Living has bounding-box dimensions 3.70 m by 5.40 m by 2.80 m, House Bed has 3.50 m by 2.70 m by 2.80 m, House Kitchen has 3.50 m by 2.50 m by 2.80 m, "
    "and Garage Bay has 5.40 m by 3.90 m by 2.80 m, each in any axis order with tolerance +/-0.08 m. 9. The slab names are exactly House Slab, Garage Slab, and Connector Apron, ignoring leading and trailing whitespace only. "
    "House Slab has bounding-box dimensions 8.00 m by 6.00 m by 0.20 m, Garage Slab has 6.00 m by 4.50 m by 0.20 m, and Connector Apron has 2.00 m by 1.20 m by 0.12 m, each in any axis order with tolerance +/-0.08 m. "
    "10. All spaces and slabs are spatially assigned to Ground Floor. 11. /home/user/Desktop/result.csv has exactly these headers in this order: BuildingPart, Storey, GrossFootprintArea, SpaceCount. "
    "12. /home/user/Desktop/result.csv has exactly 2 data rows: House with Storey Ground Floor, GrossFootprintArea 48.0, and SpaceCount 3; and Garage with Storey Ground Floor, GrossFootprintArea 27.0, and SpaceCount 1, "
    "each numeric value with tolerance +/-0.02. Any item not explicitly required may vary."
)

FREECADPATH_T21 = (
    "Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/cli_plate.step. Create a FreeCAD Path/CAM Job and a top Face operation. "
    "Set the Job origin at the stock top-face center. Use T1 to target final top Z=10.000 mm with S6000 rpm and F750 mm/min. Tool definition: T1 is a face mill, S6000 rpm, F750 mm/min. "
    "Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-21.nc."
)

OPENSCAD_T21 = (
    "Operate on /home/user/Desktop/task-021_initial.scad. Use OpenSCAD command-line parameters or edit the source so width=90, depth=70, back_height=80 "
    "(the back plate rises 80 mm above the 5 mm base, so overall height is 85 mm), and slot_width=12. Export the modified CAD model as /home/user/Desktop/task-021_output.stl. "
    "The task is to generate the modified model, not to submit a new script file."
)

SKETCHUP_T21 = (
    "TIN Terrain from Contour Lines The file `C:\\Users\\Administrator\\Desktop\\contours.dxf` contains exactly 10 elevation-labeled contour polylines traced from an underlying height field. "
    "Each contour is a single LWPOLYLINE entity on layer `CONTOURS`: - Each LWPOLYLINE is 2D (all vertices share that polyline's Z elevation). "
    "- The elevation is stored in the DXF `elevation` attribute of the LWPOLYLINE (the standard way CAD encodes a 3D elevation on a 2D polyline). "
    "- Elevations are all distinct and span the surface's real Z range (approximately 21 m to 37 m). - Each contour has at least 8 vertices "
    "(they are not axis-aligned rectangles; they are natural iso-elevation curves of the height field). - The horizontal footprint covers a terrain domain of X in [0, 100] m and Y in [0, 80] m. "
    "Your task (SketchUp Sandbox `From Contours` equivalent): 1. Load `C:\\Users\\Administrator\\Desktop\\contours.dxf` via ezdxf and collect the 3D vertex set "
    "(every vertex becomes a `(x, y, z)` point with `z = LWPOLYLINE.elevation`). 2. Compute a triangulation of the XY point set (2D Delaunay is the standard approach used by Sandbox From Contours). "
    "3. Lift each 2D triangle back into 3D using the vertices' Z values (so vertex `i` in the mesh sits at exactly the contour's elevation). The resulting mesh is a TIN (Triangulated Irregular Network) - "
    "an open, triangulated surface that interpolates between the contours. 4. Export the TIN as `C:\\Users\\Administrator\\Desktop\\answer.skp` (Wavefront OBJ, triangles only). "
    "The TIN is an open surface, not a closed solid (like any SketchUp From-Contours terrain). Requirements: 1. `C:\\Users\\Administrator\\Desktop\\answer.skp` can be opened and inspected as a native SketchUp model with triangular faces. "
    "2. Triangle count is at least 200 (10 contours x 24 vertices = 240 input points; Delaunay yields on the order of ~400 triangles). 3. The mesh is an open surface (not watertight). "
    "4. `C:\\Users\\Administrator\\Desktop\\contours.dxf` parses via ezdxf and contains exactly 10 LWPOLYLINE entities, each with >= 8 vertices and all distinct elevations. "
    "5. Mesh XY bounding box matches the DXF's contour XY extent within 0.5 m. 6. Mesh Z range brackets the DXF Z range within 0.1 m on each side. "
    "7. Every LWPOLYLINE vertex, at its elevation Z, lies on the mesh surface within 100 mm (checked via nearest-triangle-surface distance)."
)

LIBRECAD_T01 = (
    "Look at /home/user/Desktop/gui01_room_outline_seed.dxf in LibreCAD. Use the four guide corner points in the file to draw a 6000 mm by 4000 mm room outside outline as a closed rectangle on layer WALL. "
    "Draw one interior partition wall line on layer WALL from (3000,0) to (3000,4000). Leave a 900 mm door opening centered on the bottom wall by breaking or deleting the wall segment from x=2550 to x=3450. "
    "On layer DOOR, add a 900 mm door leaf line and a 90 degree door swing arc. Save the result as /home/user/Desktop/gui01_room_outline_completed.dxf."
)

SOLVESPACE_T01 = (
    "Open /home/user/Desktop/seed_ss_gui_01_baseplate.dxf and continue editing that drawing rather than starting from an empty document. Keep the baseplate as the source geometry, resize the outer rectangle to width 120 and height 80, "
    "update the two circular holes to diameter 10 with centers at (25,40) and (95,40), and update the horizontal centerline on layer CENTER so it runs from (0,40) to (120,40). "
    "Construction or guide geometry from the seed may be changed or removed unless it is explicitly required above. Save the completed drawing as /home/user/Desktop/final_ss_gui_01.dxf."
)

ZBRUSH_T01 = (
    "Sculpt a Weathered Rock with DynaMesh + ClayBuildup + DamStandard + TrimDynamic Look at `C:\\Users\\Administrator\\Desktop\\scene.obj`. It contains a ZBrush Tool whose first (and only) SubTool, named StartingBall, "
    "is a smooth UV sphere of radius 0.5 BU centred at origin, with ~512 faces (lat-lon 16 x 32 tessellation). The SubTool has no polygroups beyond the default, no UVs, and no polypaint. "
    "Load this OBJ into ZBrush, DynaMesh it to a uniform high resolution, sculpt it into a weathered rock with ClayBuildup (coarse base shape), DamStandard (sharp cracks), and TrimDynamic (flat trim planes), "
    "then export the result as `C:\\Users\\Administrator\\Desktop\\output.obj` (OBJ format). Rename the SubTool to Rock before export. The exported `C:\\Users\\Administrator\\Desktop\\output.obj` must satisfy: "
    "- Exactly one SubTool, named Rock. - Face count in the range [30000, 100000] (DynaMesh produces many faces; any reasonable working resolution yields this range). "
    "- The mesh is manifold: every edge is shared by exactly two faces. - The total discrete curvature (sum over edges of (1 - <n_i, n_j>)) is clearly non-zero, confirming the mesh is not a smooth sphere anymore. "
    "- At least 100 vertices have low local normal variance (< 0.05), confirming the presence of the flat trim regions. No polygroups, UVs, or polypaint are required."
)

# --- Cross-domain: large CAD/CAM/EDA/BIM/CFD crosses (incompatible prefix + pasted benchmark body). ---

CROSS_PREFIX_ANSYS = (
    "Complete the entire workflow below using only ANSYS Mechanical 2024R1 interactive GUI objects "
    "(no Siemens NX, no NX CAM sessions, no external CAM post unrelated to Mechanical). "
)

CROSS_PREFIX_BLENDER = (
    "Complete the entire workflow below using only Blender 4.2.3 (viewport, Geometry Nodes, scripting confined to Blender; "
    "no FreeCAD, no FreeCAD Path workbench, no `freecadcmd` or headless FreeCAD batch runs). "
)

CROSS_PREFIX_FENICS = (
    "Complete the entire workflow below using only the FEniCS Python API and scientific Python in the FEniCS environment "
    "(no OpenSCAD binary, no `openscad` CLI as the solid-modeling engine for the export below). "
)

CROSS_PREFIX_FLORIS = (
    "Complete the entire workflow below using only FLORIS command-line wake tools "
    "(no BRL-CAD, no `mged`, no CSG solid modeling for the Boolean and STL workflow below). "
)

CROSS_PREFIX_OPENFOAM = (
    "Complete the entire workflow below using only OpenFOAM 11 terminal utilities for meshing, solving, and post-processing "
    "(no FreeCAD GUI, no FreeCAD Part/PD workbench for placing the STEP solids in the compound below). "
)

CROSS_PREFIX_OPENFAST = (
    "Complete the entire workflow below using only TurbSim and OpenFAST command-line tools "
    "(no KiCad, no `kicad-cli`, no PCB editor for V-score panelization below). "
)

CROSS_PREFIX_FREECADPATH = (
    "Complete the entire workflow below using only FreeCAD with Path/CAM modules "
    "(no EAGLE, no CadSoft EAGLE for `.brd` or ULP execution below). "
)

CROSS_PREFIX_OPENSCAD = (
    "Complete the entire workflow below using only OpenSCAD language and exporters "
    "(no LibreCAD, no interactive DXF editing for architectural room outlines below). "
)

CROSS_PREFIX_SKETCHUP = (
    "Complete the entire workflow below using only SketchUp modeling and Ruby API inside SketchUp "
    "(no AutoCAD, no AutoCAD-native DXF authoring workflows below). "
)

CROSS_PREFIX_LIBRECAD = (
    "Complete the entire workflow below using only LibreCAD 2D drafting "
    "(no FreeCAD, no multi-solid STEP import and 3D placement workflow below). "
)

CROSS_PREFIX_SOLVESPACE = (
    "Complete the entire workflow below using only SolveSpace "
    "(no OpenFOAM, no `blockMesh`, no `icoFoam`/`simpleFoam` incompressible CFD below). "
)

CROSS_PREFIX_ZBRUSH = (
    "Complete the entire workflow below using only ZBrush sculpting and export tools "
    "(no Autodesk Revit, no Revit IFC import/export, no Revit sheet PDF publishing below). "
)

# Pasted bodies: keep strings identical to task/task-c/* benchmark instruction bodies above.
CROSS_BODY_ANSYS = CROSS_PREFIX_ANSYS + NXCAM_T21
CROSS_BODY_BLENDER = CROSS_PREFIX_BLENDER + FREECADPATH_T21
CROSS_BODY_FENICS = CROSS_PREFIX_FENICS + OPENSCAD_T21
CROSS_BODY_FLORIS = CROSS_PREFIX_FLORIS + BRLCAD_T21
CROSS_BODY_OPENFOAM = CROSS_PREFIX_OPENFOAM + FREECAD_T21
CROSS_BODY_OPENFAST = CROSS_PREFIX_OPENFAST + KICAD_T21
CROSS_BODY_FREECADPATH = CROSS_PREFIX_FREECADPATH + EAGLE_T02
CROSS_BODY_OPENSCAD = CROSS_PREFIX_OPENSCAD + LIBRECAD_T01
CROSS_BODY_SKETCHUP = CROSS_PREFIX_SKETCHUP + AUTOCAD_T21
CROSS_BODY_LIBRECAD = CROSS_PREFIX_LIBRECAD + FREECAD_T21
CROSS_BODY_SOLVESPACE = CROSS_PREFIX_SOLVESPACE + OPENFOAM_T02
CROSS_BODY_ZBRUSH = CROSS_PREFIX_ZBRUSH + REVIT_T13

SPECS: list[dict] = [
    # ---- fictional / contradictory (3; one per folder; no duplicate app dirs) ----
    {
        "folder": "abaqus",
        "channel": "c",
        "kind": "fictional_ui",
        "snapshot": "Abaqus-2023",
        "os_suffix": "windows",
        "verdict_file": r"C:\Users\Administrator\Desktop\engiworld_infeasible_verdict.txt",
        "upload_path": r"C:\Users\Administrator\Desktop\eval.py",
        "vm_cmd": r"python C:\Users\Administrator\Desktop\eval.py",
        "path_hint": r"C:\Users\Administrator\Desktop\engiworld_infeasible_verdict.txt",
        "body": (
            "Using only Abaqus/CAE native material GUI (no user subroutines, no external plugins, no Python scripting), "
            "define an isotropic linear elastic solid with Young's modulus E = 200000 MPa and Poisson's ratio nu = 0.5 exactly, "
            "then run a static general step and expect a converged linear stiffness without singularities."
        ),
    },
    {
        "folder": "calculix",
        "channel": "c",
        "kind": "fictional_ui",
        "snapshot": "CalculiX-2.21",
        "os_suffix": "ubuntu",
        "verdict_file": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "upload_path": "/home/user/Desktop/eval.py",
        "vm_cmd": "python /home/user/Desktop/eval.py",
        "path_hint": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "body": (
            "In a CalculiX `.inp` deck using only documented CalculiX material models (no user subroutines), "
            "define `*HYPERELASTIC, NEO-HOOKE` with a single constant `C10 = sqrt(-1)` MPa and obtain a real-valued converged displacement field."
        ),
    },
    {
        "folder": "solidcam",
        "channel": "v",
        "kind": "fictional_ui",
        "snapshot": "SolidCAM-2025",
        "os_suffix": "windows",
        "verdict_file": r"C:\Users\User\Desktop\engiworld_infeasible_verdict.txt",
        "upload_path": r"C:\Users\User\Desktop\eval.py",
        "vm_cmd": r"python C:\Users\User\Desktop\eval.py",
        "path_hint": r"C:\Users\User\Desktop\engiworld_infeasible_verdict.txt",
        "body": (
            "Select technology `HSM-Warp-9X` from SolidCAM 2025 stock Technology Database entries only "
            "(no importing XML technology tables)."
        ),
    },
    # ---- cross_domain (~12): large CAD/CAM/EDA/BIM/CFD cross + pasted benchmark body ----
    {
        "folder": "ansys",
        "channel": "v",
        "kind": "cross_domain",
        "snapshot": "ANSYS-2024R1",
        "os_suffix": "windows",
        "verdict_file": r"C:\Users\Administrator\Desktop\engiworld_infeasible_verdict.txt",
        "upload_path": r"C:\Users\Administrator\Desktop\eval.py",
        "vm_cmd": r"python C:\Users\Administrator\Desktop\eval.py",
        "path_hint": r"C:\Users\Administrator\Desktop\engiworld_infeasible_verdict.txt",
        "body": CROSS_BODY_ANSYS,
    },
    {
        "folder": "blender",
        "channel": "c",
        "kind": "cross_domain",
        "snapshot": "Blender-4.2.3",
        "os_suffix": "ubuntu",
        "verdict_file": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "upload_path": "/home/user/Desktop/eval.py",
        "vm_cmd": "python /home/user/Desktop/eval.py",
        "path_hint": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "body": CROSS_BODY_BLENDER,
    },
    {
        "folder": "fenics",
        "channel": "c",
        "kind": "cross_domain",
        "snapshot": "FEniCS",
        "os_suffix": "ubuntu",
        "verdict_file": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "upload_path": "/home/user/Desktop/eval.py",
        "vm_cmd": "python /home/user/Desktop/eval.py",
        "path_hint": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "body": CROSS_BODY_FENICS,
    },
    {
        "folder": "floris",
        "channel": "c",
        "kind": "cross_domain",
        "snapshot": "FLORIS4.6.4",
        "os_suffix": "ubuntu",
        "verdict_file": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "upload_path": "/home/user/Desktop/eval.py",
        "vm_cmd": "python /home/user/Desktop/eval.py",
        "path_hint": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "body": CROSS_BODY_FLORIS,
    },
    {
        "folder": "openfoam",
        "channel": "c",
        "kind": "cross_domain",
        "snapshot": "OpenFOAM11",
        "os_suffix": "ubuntu",
        "verdict_file": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "upload_path": "/home/user/Desktop/eval.py",
        "vm_cmd": "python /home/user/Desktop/eval.py",
        "path_hint": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "body": CROSS_BODY_OPENFOAM,
    },
    {
        "folder": "openfast",
        "channel": "c",
        "kind": "cross_domain",
        "snapshot": "openfast5",
        "os_suffix": "ubuntu",
        "verdict_file": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "upload_path": "/home/user/Desktop/eval.py",
        "vm_cmd": "python /home/user/Desktop/eval.py",
        "path_hint": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "body": CROSS_BODY_OPENFAST,
    },
    {
        "folder": "freecad-path",
        "channel": "c",
        "kind": "cross_domain",
        "snapshot": "freecad-path0.21.2",
        "os_suffix": "ubuntu",
        "verdict_file": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "upload_path": "/home/user/Desktop/eval.py",
        "vm_cmd": "python /home/user/Desktop/eval.py",
        "path_hint": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "body": CROSS_BODY_FREECADPATH,
    },
    {
        "folder": "openscad",
        "channel": "c",
        "kind": "cross_domain",
        "snapshot": "OpenSCAD2021.01",
        "os_suffix": "ubuntu",
        "verdict_file": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "upload_path": "/home/user/Desktop/eval.py",
        "vm_cmd": "python /home/user/Desktop/eval.py",
        "path_hint": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "body": CROSS_BODY_OPENSCAD,
    },
    {
        "folder": "sketchup",
        "channel": "v",
        "kind": "cross_domain",
        "snapshot": "SketchUp2026",
        "os_suffix": "windows",
        "verdict_file": r"C:\Users\Administrator\Desktop\engiworld_infeasible_verdict.txt",
        "upload_path": r"C:\Users\Administrator\Desktop\eval.py",
        "vm_cmd": r"python C:\Users\Administrator\Desktop\eval.py",
        "path_hint": r"C:\Users\Administrator\Desktop\engiworld_infeasible_verdict.txt",
        "body": CROSS_BODY_SKETCHUP,
    },
    {
        "folder": "librecad",
        "channel": "v",
        "kind": "cross_domain",
        "snapshot": "LibreCAD2.2.0.2",
        "os_suffix": "ubuntu",
        "verdict_file": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "upload_path": "/home/user/Desktop/eval.py",
        "vm_cmd": "python /home/user/Desktop/eval.py",
        "path_hint": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "body": CROSS_BODY_LIBRECAD,
    },
    {
        "folder": "solvespace",
        "channel": "v",
        "kind": "cross_domain",
        "snapshot": "solvespace3.1ds1-3.1build2",
        "os_suffix": "ubuntu",
        "verdict_file": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "upload_path": "/home/user/Desktop/eval.py",
        "vm_cmd": "python /home/user/Desktop/eval.py",
        "path_hint": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "body": CROSS_BODY_SOLVESPACE,
    },
    {
        "folder": "zbrush",
        "channel": "v",
        "kind": "cross_domain",
        "snapshot": "ZBrush-2024",
        "os_suffix": "windows",
        "verdict_file": r"C:\Users\Administrator\Desktop\engiworld_infeasible_verdict.txt",
        "upload_path": r"C:\Users\Administrator\Desktop\eval.py",
        "vm_cmd": r"python C:\Users\Administrator\Desktop\eval.py",
        "path_hint": r"C:\Users\Administrator\Desktop\engiworld_infeasible_verdict.txt",
        "body": CROSS_BODY_ZBRUSH,
    },
    # ---- missing_init (~13): aligned with real tasks; empty upload ----
    {
        "folder": "solidworks",
        "channel": "v",
        "kind": "missing_init",
        "snapshot": "SolidWorks-2025",
        "os_suffix": "windows",
        "verdict_file": r"C:\Users\User\Desktop\engiworld_infeasible_verdict.txt",
        "upload_path": r"C:\Users\User\Desktop\eval.py",
        "vm_cmd": r"python C:\Users\User\Desktop\eval.py",
        "path_hint": r"C:\Users\User\Desktop\engiworld_infeasible_verdict.txt",
        "body": SOLIDWORKS_T21,
    },
    {
        "folder": "freecad",
        "channel": "c",
        "kind": "missing_init",
        "snapshot": "FreeCAD0.21.2",
        "os_suffix": "ubuntu",
        "verdict_file": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "upload_path": "/home/user/Desktop/eval.py",
        "vm_cmd": "python /home/user/Desktop/eval.py",
        "path_hint": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "body": FREECAD_T21,
    },
    {
        "folder": "kicad",
        "channel": "c",
        "kind": "missing_init",
        "snapshot": "kicad-10.0.2",
        "os_suffix": "ubuntu",
        "verdict_file": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "upload_path": "/home/user/Desktop/eval.py",
        "vm_cmd": "python /home/user/Desktop/eval.py",
        "path_hint": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "body": KICAD_T21,
    },
    {
        "folder": "cadence-orcad",
        "channel": "v",
        "kind": "missing_init",
        "snapshot": "OrCAD24.1",
        "os_suffix": "windows",
        "verdict_file": r"C:\Users\User\Desktop\engiworld_infeasible_verdict.txt",
        "upload_path": r"C:\Users\User\Desktop\eval.py",
        "vm_cmd": r"python C:\Users\User\Desktop\eval.py",
        "path_hint": r"C:\Users\User\Desktop\engiworld_infeasible_verdict.txt",
        "body": CADENCE_ORCAD_T01,
    },
    {
        "folder": "altium-designer",
        "channel": "v",
        "kind": "missing_init",
        "snapshot": "altium-designer",
        "os_suffix": "windows",
        "verdict_file": r"C:\Users\Administrator\Desktop\engiworld_infeasible_verdict.txt",
        "upload_path": r"C:\Users\Administrator\Desktop\eval.py",
        "vm_cmd": r"python C:\Users\Administrator\Desktop\eval.py",
        "path_hint": r"C:\Users\Administrator\Desktop\engiworld_infeasible_verdict.txt",
        "body": ALTIUM_T02,
    },
    {
        "folder": "brl-cad",
        "channel": "c",
        "kind": "missing_init",
        "snapshot": "BRL-CAD7.32.2",
        "os_suffix": "ubuntu",
        "verdict_file": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "upload_path": "/home/user/Desktop/eval.py",
        "vm_cmd": "python /home/user/Desktop/eval.py",
        "path_hint": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "body": BRLCAD_T21,
    },
    {
        "folder": "nx-cam",
        "channel": "c",
        "kind": "missing_init",
        "snapshot": "NX-CAM",
        "os_suffix": "windows",
        "verdict_file": r"C:\Users\User\Desktop\engiworld_infeasible_verdict.txt",
        "upload_path": r"C:\Users\User\Desktop\eval.py",
        "vm_cmd": r"python C:\Users\User\Desktop\eval.py",
        "path_hint": r"C:\Users\User\Desktop\engiworld_infeasible_verdict.txt",
        "body": NXCAM_T21,
    },
    {
        "folder": "eagle",
        "channel": "c",
        "kind": "missing_init",
        "snapshot": "eagle-7.7.0",
        "os_suffix": "ubuntu",
        "verdict_file": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "upload_path": "/home/user/Desktop/eval.py",
        "vm_cmd": "python /home/user/Desktop/eval.py",
        "path_hint": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "body": EAGLE_T02,
    },
    {
        "folder": "revit",
        "channel": "v",
        "kind": "missing_init",
        "snapshot": "Revit2025",
        "os_suffix": "windows",
        "verdict_file": r"C:\Users\Administrator\Desktop\engiworld_infeasible_verdict.txt",
        "upload_path": r"C:\Users\Administrator\Desktop\eval.py",
        "vm_cmd": r"python C:\Users\Administrator\Desktop\eval.py",
        "path_hint": r"C:\Users\Administrator\Desktop\engiworld_infeasible_verdict.txt",
        "body": REVIT_T13,
    },
    {
        "folder": "archicad",
        "channel": "v",
        "kind": "missing_init",
        "snapshot": "ArchiCAD-27",
        "os_suffix": "windows",
        "verdict_file": r"C:\Users\Administrator\Desktop\engiworld_infeasible_verdict.txt",
        "upload_path": r"C:\Users\Administrator\Desktop\eval.py",
        "vm_cmd": r"python C:\Users\Administrator\Desktop\eval.py",
        "path_hint": r"C:\Users\Administrator\Desktop\engiworld_infeasible_verdict.txt",
        "body": ARCHICAD_T18,
    },
    {
        "folder": "autocad",
        "channel": "v",
        "kind": "missing_init",
        "snapshot": "AutoCAD2024",
        "os_suffix": "windows",
        "verdict_file": r"C:\Users\Administrator\Desktop\engiworld_infeasible_verdict.txt",
        "upload_path": r"C:\Users\Administrator\Desktop\eval.py",
        "vm_cmd": r"python C:\Users\Administrator\Desktop\eval.py",
        "path_hint": r"C:\Users\Administrator\Desktop\engiworld_infeasible_verdict.txt",
        "body": AUTOCAD_T21,
    },
    {
        "folder": "openstudio",
        "channel": "c",
        "kind": "missing_init",
        "snapshot": "OpenStudio-1.11.0",
        "os_suffix": "ubuntu",
        "verdict_file": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "upload_path": "/home/user/Desktop/eval.py",
        "vm_cmd": "python /home/user/Desktop/eval.py",
        "path_hint": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "body": OPENSTUDIO_T18,
    },
    {
        "folder": "bonsai",
        "channel": "c",
        "kind": "missing_init",
        "snapshot": "Bonsai-0.8.5",
        "os_suffix": "ubuntu",
        "verdict_file": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "upload_path": "/home/user/Desktop/eval.py",
        "vm_cmd": "python /home/user/Desktop/eval.py",
        "path_hint": "/home/user/Desktop/engiworld_infeasible_verdict.txt",
        "body": BONSAI_T20,
    },
]


def main() -> None:
    seen_folders: set[str] = set()
    OUT.mkdir(parents=True, exist_ok=True)
    for spec in SPECS:
        folder = spec["folder"]
        ch = spec["channel"]
        kind = spec["kind"]
        snapshot = spec["snapshot"]
        os_suffix = spec["os_suffix"]
        verdict_file = spec["verdict_file"]
        upload_path = spec["upload_path"]
        vm_cmd = spec["vm_cmd"]
        path_hint = spec["path_hint"]
        body = spec["body"]

        if folder in seen_folders:
            raise RuntimeError(f"Duplicate folder in SPECS: {folder}")
        seen_folders.add(folder)

        app_dir = OUT / folder
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / "eval.py").write_text(EVAL_TEMPLATE.format(verdict_file=verdict_file), encoding="utf-8")

        slug = folder.replace("/", "-")
        task_id = f"{ch}-{slug}-{os_suffix}"
        instruction = build_instruction(body, path_hint, kind)

        data = {
            "id": task_id,
            "snapshot": snapshot,
            "instruction": instruction,
            "source": f"engiworld synthetic benchmark; routing=task-{ch}; kind={kind}",
            "config": [{"type": "upload_file", "parameters": {"files": []}}],
            "trajectory": "trajectories/",
            "related_apps": [folder],
            "evaluator": {
                "postconfig": [
                    {
                        "type": "upload_file",
                        "parameters": {
                            "files": [
                                {
                                    "local_path": "task-false/eval.py",
                                    "path": upload_path,
                                }
                            ]
                        },
                    }
                ],
                "func": "exact_match",
                "result": {
                    "type": "vm_command_line",
                    "command": vm_cmd,
                    "shell": "true",
                },
                "expected": {"type": "rule", "rules": {"expected": "True\n"}},
            },
            "proxy": False,
            "fixed_ip": False,
            "possibility_of_env_change": "low",
        }
        json_path = app_dir / "task-false.json"
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("wrote", json_path.relative_to(ROOT), task_id, kind)


if __name__ == "__main__":
    main()
