# Full instruction cleanup diff


_changed=306, unchanged=490, apply=YES_

### Per-app counts

- task-c/abaqus: 20
- task-c/ansys: 14
- task-c/autocad: 20
- task-c/calculix: 20
- task-c/eagle: 1
- task-c/fenics: 20
- task-c/floris: 20
- task-c/freecad: 19
- task-c/freecad-path: 20
- task-c/fusion360: 20
- task-c/openfoam: 19
- task-c/openscad: 15
- task-c/ptc-creo: 20
- task-v/abaqus: 20
- task-v/altium-designer: 1
- task-v/ansys: 10
- task-v/eagle: 5
- task-v/freecad: 20
- task-v/librecad: 1
- task-v/openscad: 2
- task-v/sketchup: 19


## task-c/abaqus/task-01

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to build and solve a 2D axisymmetric finite-element model of a circular plate.
+Use Abaqus/CAE to build and solve a 2D axisymmetric finite-element model of a circular plate.
 
```

## task-c/abaqus/task-02

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to build and solve a 2D axisymmetric finite-element model of an internally pressurized thick-walled cylinder.
+Use Abaqus/CAE to build and solve a 2D axisymmetric finite-element model of an internally pressurized thick-walled cylinder.
 
```

## task-c/abaqus/task-03

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a tensile analysis of a thin rectangular shell plate with a central circular hole.
+Use Abaqus/CAE to perform a tensile analysis of a thin rectangular shell plate with a central circular hole.
 
```

## task-c/abaqus/task-04

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to complete the following task.
+Use Abaqus/CAE to complete the following task.
 
```

## task-c/abaqus/task-05

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a tensile analysis of a rectangular solid block:
+Use Abaqus/CAE to perform a tensile analysis of a rectangular solid block:
 
```

## task-c/abaqus/task-06

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a steady-state heat conduction analysis:
+Use Abaqus/CAE to perform a steady-state heat conduction analysis:
 
```

## task-c/abaqus/task-07

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a torsion analysis of a circular shaft (Variant A):
+Use Abaqus/CAE to perform a torsion analysis of a circular shaft (Variant A):
 
```

## task-c/abaqus/task-08

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to build a contact analysis assembly from scratch:
+Use Abaqus/CAE to build a contact analysis assembly from scratch:
 
@@ -24,3 +24,3 @@
 
-6. Interaction (key GUI operations):
+6. Interaction:
    - Create a General Contact (Standard) or Surface-to-Surface Contact (Standard) interaction
```

## task-c/abaqus/task-09

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a simply supported beam analysis under a uniformly distributed load:
+Use Abaqus/CAE to perform a simply supported beam analysis under a uniformly distributed load:
 
```

## task-c/abaqus/task-10

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a torsion analysis of a circular shaft (Variant B):
+Use Abaqus/CAE to perform a torsion analysis of a circular shaft (Variant B):
 
```

## task-c/abaqus/task-11

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a simply supported beam analysis under a uniformly distributed load:
+Use Abaqus/CAE to perform a simply supported beam analysis under a uniformly distributed load:
 
```

## task-c/abaqus/task-12

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a linear buckling analysis of a thin plate (Variant A):
+Use Abaqus/CAE to perform a linear buckling analysis of a thin plate (Variant A):
 
```

## task-c/abaqus/task-13

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a modal analysis of a cantilever beam (Variant A):
+Use Abaqus/CAE to perform a modal analysis of a cantilever beam (Variant A):
 
```

## task-c/abaqus/task-14

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a constrained thermal stress analysis (Case A):
+Use Abaqus/CAE to perform a constrained thermal stress analysis (Case A):
 
```

## task-c/abaqus/task-15

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a constrained thermal stress analysis (Case B):
+Use Abaqus/CAE to perform a constrained thermal stress analysis (Case B):
 
```

## task-c/abaqus/task-16

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a transient heat-transfer analysis of a rectangular solid block (Variant A):
+Use Abaqus/CAE to perform a transient heat-transfer analysis of a rectangular solid block (Variant A):
 
```

## task-c/abaqus/task-17

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a thermal stress analysis:
+Use Abaqus/CAE to perform a thermal stress analysis:
 
```

## task-c/abaqus/task-18

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a modal analysis of a cantilever beam (Variant B):
+Use Abaqus/CAE to perform a modal analysis of a cantilever beam (Variant B):
 
```

## task-c/abaqus/task-19

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a linear buckling analysis of a thin plate (Variant B):
+Use Abaqus/CAE to perform a linear buckling analysis of a thin plate (Variant B):
 
```

## task-c/abaqus/task-20

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a static tensile analysis of a thin rectangular shell plate with a central circular hole (Variant A):
+Use Abaqus/CAE to perform a static tensile analysis of a thin rectangular shell plate with a central circular hole (Variant A):
 
```

## task-c/ansys/task-01

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use ANSYS via the Command Line Interface (CLI) to build and solve a 3D solid cantilever beam model.
+Use ANSYS to build and solve a 3D solid cantilever beam model.
 
```

## task-c/ansys/task-07

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use ANSYS Mechanical APDL via the Command Line Interface (CLI) to build and solve a 3D solid cantilever beam model.
+Use ANSYS Mechanical APDL to build and solve a 3D solid cantilever beam model.
 
```

## task-c/ansys/task-09

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use ANSYS Fluent via the Command Line Interface (CLI) to complete a 2D lid-driven cavity flow analysis.
+Use ANSYS Fluent to complete a 2D lid-driven cavity flow analysis.
 
```

## task-c/ansys/task-10

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use ANSYS Fluent via the Command Line Interface (CLI) to complete a 2D laminar channel-flow analysis.
+Use ANSYS Fluent to complete a 2D laminar channel-flow analysis.
 
```

## task-c/ansys/task-11

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use ANSYS Workbench via the Command Line Interface (CLI) to complete a nonlinear Static Structural contact analysis.
+Use ANSYS Workbench to complete a nonlinear Static Structural contact analysis.
 
```

## task-c/ansys/task-12

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use ANSYS Workbench via the Command Line Interface (CLI) to complete a Transient Structural analysis.
+Use ANSYS Workbench to complete a Transient Structural analysis.
 
```

## task-c/ansys/task-13

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use ANSYS Mechanical APDL via the Command Line Interface (CLI) to complete a nonlinear static structural analysis.
+Use ANSYS Mechanical APDL to complete a nonlinear static structural analysis.
 
```

## task-c/ansys/task-14

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use ANSYS Mechanical APDL via the Command Line Interface (CLI) to complete a harmonic response analysis.
+Use ANSYS Mechanical APDL to complete a harmonic response analysis.
 
```

## task-c/ansys/task-15

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use ANSYS Fluent via the Command Line Interface (CLI) to complete a 3D laminar pipe-flow analysis.
+Use ANSYS Fluent to complete a 3D laminar pipe-flow analysis.
 
```

## task-c/ansys/task-16

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use ANSYS Fluent via the Command Line Interface (CLI) to complete a 2D laminar channel-flow analysis.
+Use ANSYS Fluent to complete a 2D laminar channel-flow analysis.
 
```

## task-c/ansys/task-17

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use ANSYS Fluent via the Command Line Interface (CLI) to complete a 2D laminar Couette-flow analysis.
+Use ANSYS Fluent to complete a 2D laminar Couette-flow analysis.
 
```

## task-c/ansys/task-18

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use ANSYS Workbench via the Command Line Interface (CLI) to complete a Static Structural analysis.
+Use ANSYS Workbench to complete a Static Structural analysis.
 
```

## task-c/ansys/task-19

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use ANSYS Workbench via the Command Line Interface (CLI) to complete a linear eigenvalue buckling analysis.
+Use ANSYS Workbench to complete a linear eigenvalue buckling analysis.
 
```

## task-c/ansys/task-20

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use ANSYS Workbench via the Command Line Interface (CLI) to complete a Steady-State Thermal analysis.
+Use ANSYS Workbench to complete a Steady-State Thermal analysis.
 
```

## task-c/autocad/task-21

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\cli_blank_seed.dxf. Recreate the target 2D CAD drawing for task 21 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\cli_blank_seed.dxf. Recreate the target 2D CAD drawing for task 21 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/autocad/task-22

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\inspect_me.dxf. Recreate the target 2D CAD drawing for task 22 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\inspect_me.dxf. Recreate the target 2D CAD drawing for task 22 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/autocad/task-23

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\plate_raw.dxf. Recreate the target 2D CAD drawing for task 23 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\plate_raw.dxf. Recreate the target 2D CAD drawing for task 23 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/autocad/task-24

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\inch_valve.dxf. Recreate the target 2D CAD drawing for task 24 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\inch_valve.dxf. Recreate the target 2D CAD drawing for task 24 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/autocad/task-25

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\bracket_seed.dxf. Recreate the target 2D CAD drawing for task 25 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\bracket_seed.dxf. Recreate the target 2D CAD drawing for task 25 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/autocad/task-26

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\base.dxf, C:\Users\Administrator\Desktop\slider.dxf, C:\Users\Administrator\Desktop\pin.dxf, C:\Users\Administrator\Desktop\cover.dxf. Recreate the target 2D CAD drawing for task 26 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\base.dxf, C:\Users\Administrator\Desktop\slider.dxf, C:\Users\Administrator\Desktop\pin.dxf, C:\Users\Administrator\Desktop\cover.dxf. Recreate the target 2D CAD drawing for task 26 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/autocad/task-27

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\surface_leak.dxf. Recreate the target 2D CAD drawing for task 27 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\surface_leak.dxf. Recreate the target 2D CAD drawing for task 27 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/autocad/task-28

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\profile_seed.dxf. Recreate the target 2D CAD drawing for task 28 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\profile_seed.dxf. Recreate the target 2D CAD drawing for task 28 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/autocad/task-29

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\segmented_flange.dxf. Recreate the target 2D CAD drawing for task 29 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\segmented_flange.dxf. Recreate the target 2D CAD drawing for task 29 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/autocad/task-30

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\nozzle_seed.dxf. Recreate the target 2D CAD drawing for task 30 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\nozzle_seed.dxf. Recreate the target 2D CAD drawing for task 30 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/autocad/task-31

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\housing.dxf. Recreate the target 2D CAD drawing for task 31 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\housing.dxf. Recreate the target 2D CAD drawing for task 31 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/autocad/task-32

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\family_seed.dxf. Recreate the target 2D CAD drawing for task 32 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\family_seed.dxf. Recreate the target 2D CAD drawing for task 32 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/autocad/task-33

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\base.dxf, C:\Users\Administrator\Desktop\arm.dxf, C:\Users\Administrator\Desktop\bracket.dxf, C:\Users\Administrator\Desktop\pin.dxf, C:\Users\Administrator\Desktop\cap.dxf. Recreate the target 2D CAD drawing for task 33 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\base.dxf, C:\Users\Administrator\Desktop\arm.dxf, C:\Users\Administrator\Desktop\bracket.dxf, C:\Users\Administrator\Desktop\pin.dxf, C:\Users\Administrator\Desktop\cap.dxf. Recreate the target 2D CAD drawing for task 33 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/autocad/task-34

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\base_mm.dxf, C:\Users\Administrator\Desktop\cover_inch.dxf, C:\Users\Administrator\Desktop\pin_mirrored.dxf. Recreate the target 2D CAD drawing for task 34 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\base_mm.dxf, C:\Users\Administrator\Desktop\cover_inch.dxf, C:\Users\Administrator\Desktop\pin_mirrored.dxf. Recreate the target 2D CAD drawing for task 34 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/autocad/task-35

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\volume_seed.dxf. Recreate the target 2D CAD drawing for task 35 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\volume_seed.dxf. Recreate the target 2D CAD drawing for task 35 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/autocad/task-36

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\cast_part.dxf. Recreate the target 2D CAD drawing for task 36 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\cast_part.dxf. Recreate the target 2D CAD drawing for task 36 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/autocad/task-37

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\panel_layout.dxf. Recreate the target 2D CAD drawing for task 37 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\panel_layout.dxf. Recreate the target 2D CAD drawing for task 37 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/autocad/task-38

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\base.dxf, C:\Users\Administrator\Desktop\slider.dxf, C:\Users\Administrator\Desktop\stop1.dxf, C:\Users\Administrator\Desktop\stop2.dxf, C:\Users\Administrator\Desktop\pin.dxf. Recreate the target 2D CAD drawing for task 38 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\base.dxf, C:\Users\Administrator\Desktop\slider.dxf, C:\Users\Administrator\Desktop\stop1.dxf, C:\Users\Administrator\Desktop\stop2.dxf, C:\Users\Administrator\Desktop\pin.dxf. Recreate the target 2D CAD drawing for task 38 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/autocad/task-39

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\part1.dxf, C:\Users\Administrator\Desktop\part2.dxf, C:\Users\Administrator\Desktop\part3.dxf, C:\Users\Administrator\Desktop\part4.dxf. Recreate the target 2D CAD drawing for task 39 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\part1.dxf, C:\Users\Administrator\Desktop\part2.dxf, C:\Users\Administrator\Desktop\part3.dxf, C:\Users\Administrator\Desktop\part4.dxf. Recreate the target 2D CAD drawing for task 39 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/autocad/task-40

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\base_bad.dxf, C:\Users\Administrator\Desktop\arm_bad.dxf, C:\Users\Administrator\Desktop\pin_bad.dxf, C:\Users\Administrator\Desktop\cap_bad.dxf. Recreate the target 2D CAD drawing for task 40 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Use AutoCAD. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\base_bad.dxf, C:\Users\Administrator\Desktop\arm_bad.dxf, C:\Users\Administrator\Desktop\pin_bad.dxf, C:\Users\Administrator\Desktop\cap_bad.dxf. Recreate the target 2D CAD drawing for task 40 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```

## task-c/calculix/task-01

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 Note that in CalculiX, `B32` is a 3-node quadratic beam element, but the current model defines only 2 nodes.
-Complete the following from the command line:
+Complete the following:
 
```

## task-c/calculix/task-02

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a composite laminate template `/home/user/Desktop/laminate_base.inp`.
-Complete the following from the command line:
+Complete the following:
 
```

## task-c/calculix/task-03

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a solid block template `/home/user/Desktop/rigid_base.inp`.
-Complete the following from the command line:
+Complete the following:
 
```

## task-c/calculix/task-04

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a two-part template `/home/user/Desktop/tie_base.inp` (`Part_A` and `Part_B` touch at `X=50` but are not connected).
-Complete the following from the command line:
+Complete the following:
 
@@ -13,2 +13 @@
 
-4. Do not use the CGX GUI.
```

## task-c/calculix/task-05

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a solid block template `/home/user/Desktop/equation_base.inp`.
-Complete the following from the command line:
+Complete the following:
 
```

## task-c/calculix/task-06

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given an axisymmetric cylinder template `/home/user/Desktop/cylinder_transform.inp`.
-Complete the following from the command line:
+Complete the following:
 
```

## task-c/calculix/task-07

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a static template `/home/user/Desktop/dynamic_base.inp`.
-Complete the following from the command line:
+Complete the following:
 
@@ -15,2 +15 @@
 
-3. Do not use the CGX GUI.
```

## task-c/calculix/task-08

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a template with completed modal analysis `/home/user/Desktop/modal_dynamic_base.inp`.
-Complete the following from the command line:
+Complete the following:
 
```

## task-c/calculix/task-09

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a template with completed modal analysis `/home/user/Desktop/ssd_base.inp`.
-Complete the following from the command line:
+Complete the following:
 
```

## task-c/calculix/task-10

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a `90°` sector annulus template `/home/user/Desktop/cyclic_base.inp`.
-Complete the following from the command line:
+Complete the following:
 
@@ -13,2 +13 @@
 
-3. Do not use the CGX GUI.
```

## task-c/calculix/task-11

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a heat-conduction template `/home/user/Desktop/thermal_bc_base.inp`.
-Complete the following from the command line:
+Complete the following:
 
@@ -13,2 +13 @@
 
-4. Do not use the CGX GUI.
```

## task-c/calculix/task-12

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a template with completed modal analysis `/home/user/Desktop/earthquake_base.inp`.
-Complete the following from the command line:
+Complete the following:
 
```

## task-c/calculix/task-13

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a template where a beam and a solid are disconnected: `/home/user/Desktop/mpc_base.inp`.
-Complete the following from the command line:
+Complete the following:
 
@@ -14,2 +14 @@
 
-4. Do not use the CGX GUI.
```

## task-c/calculix/task-14

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given an assembly template missing contact definitions: `/home/user/Desktop/friction_base.inp`.
-Complete the following from the command line:
+Complete the following:
 
@@ -17,2 +17 @@
 
-3. Do not use the CGX GUI.
```

## task-c/calculix/task-15

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given an orthotropic material template `/home/user/Desktop/aniso_base.inp`.
-Complete the following from the command line:
+Complete the following:
 
@@ -13,2 +13 @@
 
-4. Do not use the CGX GUI.
```

## task-c/calculix/task-16

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a template with damping already defined: `/home/user/Desktop/complex_base.inp`.
-Complete the following from the command line:
+Complete the following:
 
@@ -15,2 +15 @@
 
-5. Do not use the CGX GUI.
```

## task-c/calculix/task-17

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a solid block template `/home/user/Desktop/gravity_base.inp`.
-Complete the following from the command line:
+Complete the following:
 
```

## task-c/calculix/task-18

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a solid block template `/home/user/Desktop/pretension_base.inp`.
-Complete the following from the command line:
+Complete the following:
 
@@ -13,2 +13 @@
 
-4. Do not use the CGX GUI.
```

## task-c/calculix/task-19

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a base template `/home/user/Desktop/print_base.inp`.
-Complete the following from the command line:
+Complete the following:
 
```

## task-c/calculix/task-20

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a base template `/home/user/Desktop/restart_base.inp`.
-Complete the following from the command line:
+Complete the following:
 
```

## task-c/eagle/task-07

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Open `/home/user/Desktop/legacy.sch` in EAGLE's schematic editor. It contains a single TO-220 LM7805 linear regulator (U1) wired between VIN and VOUT nets with two decoupling caps (C1=100n on VIN, C2=10u on VOUT) and GND return. Replace U1 with a pin-compatible AMS1117-5.0 in SOT-223. Save the result as `/home/user/Desktop/replaced.sch`.
+Open `/home/user/Desktop/legacy.sch` in EAGLE. It contains a single TO-220 LM7805 linear regulator (U1) wired between VIN and VOUT nets with two decoupling caps (C1=100n on VIN, C2=10u on VOUT) and GND return. Replace U1 with a pin-compatible AMS1117-5.0 in SOT-223. Save the result as `/home/user/Desktop/replaced.sch`.
 
```

## task-c/fenics/task-01

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given an incomplete FEniCS Python script `/home/user/Desktop/poisson_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -18,2 +18 @@
 
-4. Do not use any FEniCS GUI (`plot` command).
```

## task-c/fenics/task-02

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given an incomplete template `/home/user/Desktop/neumann_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -18,2 +18 @@
 
-4. Do not use any GUI.
```

## task-c/fenics/task-03

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given an incomplete solid-mechanics template `/home/user/Desktop/elasticity_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -18,2 +18 @@
 
-3. Do not use any GUI.
```

## task-c/fenics/task-04

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a heat-conduction template `/home/user/Desktop/thermal_subdomain_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -15,2 +15 @@
 
-3. Do not use any GUI.
```

## task-c/fenics/task-05

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given an incomplete modal-analysis template `/home/user/Desktop/eigenvalue_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -16,2 +16 @@
 
-3. Do not use any GUI.
```

## task-c/fenics/task-06

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a nonlinear Poisson-equation template `/home/user/Desktop/nonlinear_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -15,2 +15 @@
 
-3. Do not use any GUI.
```

## task-c/fenics/task-07

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a transient heat-conduction template `/home/user/Desktop/transient_heat_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -13,2 +13 @@
 
-3. Do not use any GUI.
```

## task-c/fenics/task-08

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a Stokes-flow template `/home/user/Desktop/stokes_base.py` (2D pipe).
-Complete the following from the command line:
+Complete the following:
 
@@ -18,2 +18 @@
 
-3. Do not use any GUI.
```

## task-c/fenics/task-09

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a very coarse-mesh template `/home/user/Desktop/plate_hole_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -17,2 +17 @@
 
-3. Do not use any GUI.
```

## task-c/fenics/task-10

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a Poisson-equation template `/home/user/Desktop/adaptive_base.py` whose exact solution has a high-gradient peak at the center.
-Complete the following from the command line:
+Complete the following:
 
@@ -15,2 +15 @@
 
-3. Do not use any GUI.
```

## task-c/fenics/task-11

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given an incomplete Navier-Stokes template `/home/user/Desktop/navier_stokes_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -18,2 +18 @@
 
-3. Do not use any GUI.
```

## task-c/fenics/task-12

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a template `/home/user/Desktop/thermomech_base.py` with completed thermal analysis.
-Complete the following from the command line:
+Complete the following:
 
@@ -18,2 +18 @@
 
-3. Do not use any GUI.
```

## task-c/fenics/task-13

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a placeholder-containing template `/home/user/Desktop/re_scan_base.py`.
-Complete parameterized batch scanning from the command line:
+Complete parameterized batch scanning:
 
@@ -16,2 +16 @@
 
-5. Do not use any GUI.
```

## task-c/fenics/task-14

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given an incomplete DG template `/home/user/Desktop/dg_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -15,2 +15 @@
 
-3. Do not use any GUI.
```

## task-c/fenics/task-15

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a hyperelastic template `/home/user/Desktop/hyperelastic_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -19,2 +19 @@
 
-3. Do not use any GUI.
```

## task-c/fenics/task-16

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Complete the full FEniCS workflow from modeling to post-processing purely from the command line:
+Complete the full FEniCS workflow from modeling to post-processing purely:
 
@@ -16,2 +16 @@
 
-4. Do not use any GUI.
```

## task-c/fenics/task-17

```diff
--- before
+++ after
@@ -11,2 +11 @@
 
-3. Do not use any GUI.
```

## task-c/fenics/task-18

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given an incomplete template `/home/user/Desktop/mixed_dim_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -18,2 +18 @@
 
-3. Do not use any GUI.
```

## task-c/fenics/task-19

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a post-processing template `/home/user/Desktop/lift_drag_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -18,2 +18 @@
 
-3. Do not use any GUI.
```

## task-c/fenics/task-20

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given two input files `/home/user/Desktop/job_a.py` and `/home/user/Desktop/job_b.py`.
-Complete automated multi-job management and comparison reporting from the command line:
+Complete automated multi-job management and comparison reporting:
 
@@ -20,2 +20 @@
 
-4. Do not use any GUI.
```

## task-c/floris/task-01

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a FLORIS configuration file `/home/user/Desktop/two_turbine.yaml` and an incomplete script `/home/user/Desktop/wake_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -15,2 +15,2 @@
 
-4. Do not use FLORIS visualization GUI (such as `fmodel.plot` commands).
+plot` commands).
```

## task-c/floris/task-02

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 FLORIS can perform wake steering through yaw control.
-Complete the following from the command line:
+Complete the following:
 
```

## task-c/floris/task-03

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 FLORIS includes multiple wake models (Jensen, Gauss, GCH, CC, etc.).
-Complete the following from the command line:
+Complete the following:
 
@@ -11,2 +11 @@
 
-3. Do not use any GUI.
```

## task-c/floris/task-04

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given an incomplete script `/home/user/Desktop/aep_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -14,2 +14 @@
 
-3. Do not use any GUI.
```

## task-c/floris/task-05

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a yaw-optimization template `/home/user/Desktop/yaw_opt_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -13,2 +13 @@
 
-3. Do not use any GUI.
```

## task-c/floris/task-06

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a template `/home/user/Desktop/loss_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -12,2 +12 @@
 
-3. Do not use any GUI.
```

## task-c/floris/task-07

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a post-processing template `/home/user/Desktop/flow_plane_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -13,2 +13 @@
 
-3. Do not use any GUI.
```

## task-c/floris/task-08

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a template `/home/user/Desktop/ti_scan_base.py`.
-Complete a parameterized batch scan from the command line:
+Complete a parameterized batch scan:
 
@@ -12,2 +12 @@
 
-3. Do not use any GUI.
```

## task-c/floris/task-09

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a layout-optimization template `/home/user/Desktop/layout_opt_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -12,2 +12 @@
 
-3. Do not use any GUI.
```

## task-c/floris/task-10

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a three-turbine in-line template.
-Complete the following from the command line:
+Complete the following:
 
@@ -12,2 +12 @@
 
-3. Do not use any GUI.
```

## task-c/floris/task-11

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a parallel-computation template `/home/user/Desktop/parallel_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -15,2 +15 @@
 
-4. Do not use any GUI.
```

## task-c/floris/task-12

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given an uncertainty-analysis template `/home/user/Desktop/uncertain_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -11,2 +11 @@
 
-3. Do not use any GUI.
```

## task-c/floris/task-13

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 FLORIS v4 supports mixing turbine types in one wind farm.
-Complete the following from the command line:
+Complete the following:
 
@@ -12,2 +12 @@
 
-3. Do not use any GUI.
```

## task-c/floris/task-14

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a custom turbine definition `/home/user/Desktop/custom_turbine.yaml`.
-Complete the following from the command line:
+Complete the following:
 
@@ -11,2 +11 @@
 
-3. Do not use any GUI.
```

## task-c/floris/task-15

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a broken FLORIS script `/home/user/Desktop/broken.py`.
-Complete diagnose-fix-rerun purely from the command line:
+Complete diagnose-fix-rerun purely:
 
@@ -11,2 +11 @@
 
-4. Do not use any GUI.
```

## task-c/floris/task-16

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Complete the full FLORIS workflow from modeling to post-processing purely from the command line:
+Complete the full FLORIS workflow from modeling to post-processing purely:
 
@@ -16,2 +16 @@
 
-4. Do not use any GUI.
```

## task-c/floris/task-17

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given two input files `/home/user/Desktop/job_baseline.py` and `/home/user/Desktop/job_yaw.py`.
-Complete automated multi-job management and comparison reporting from the command line:
+Complete automated multi-job management and comparison reporting:
 
@@ -19,2 +19 @@
 
-4. Do not use any GUI.
```

## task-c/floris/task-18

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a parameter-scan template `/home/user/Desktop/spacing_scan_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -11,2 +11 @@
 
-3. Do not use any GUI.
```

## task-c/floris/task-19

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a template `/home/user/Desktop/curve_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -12,2 +12 @@
 
-3. Do not use any GUI.
```

## task-c/floris/task-20

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a template `/home/user/Desktop/wind_sector_base.py`.
-Complete the following from the command line:
+Complete the following:
 
@@ -17,2 +17 @@
 
-4. Do not use any GUI.
```

## task-c/freecad/task-22

```diff
--- before
+++ after
@@ -1 +1 @@
-Using the FreeCAD command-line API, import /home/user/Desktop/freecad_task-22_input.step. Cut a 2 row by 6 column array of vertical through holes, each diameter 7 mm, through the 12 mm plate. The first column is at X=25 mm, the column spacing is 25 mm, and the two rows are at Y=25 mm and Y=55 mm. Export /home/user/Desktop/freecad_task-22_output.step.
+Using FreeCAD, import /home/user/Desktop/freecad_task-22_input.step. Cut a 2 row by 6 column array of vertical through holes, each diameter 7 mm, through the 12 mm plate. The first column is at X=25 mm, the column spacing is 25 mm, and the two rows are at Y=25 mm and Y=55 mm. Export /home/user/Desktop/freecad_task-22_output.step.
```

## task-c/freecad/task-23

```diff
--- before
+++ after
@@ -1 +1 @@
-Using FreeCAD CLI, open /home/user/Desktop/freecad_task-23_input.step. Add ten parallel heat-sink fins on the top of the base and fuse them to the base. Each fin is 100 x 3 x 30 mm, runs along X, has its bottom on Z=8 mm, and has center X=60 mm. The fin Y coordinates start at 12.5 mm and repeat every 6 mm for ten fins. Export /home/user/Desktop/freecad_task-23_output.step.
+Using FreeCAD, open /home/user/Desktop/freecad_task-23_input.step. Add ten parallel heat-sink fins on the top of the base and fuse them to the base. Each fin is 100 x 3 x 30 mm, runs along X, has its bottom on Z=8 mm, and has center X=60 mm. The fin Y coordinates start at 12.5 mm and repeat every 6 mm for ten fins. Export /home/user/Desktop/freecad_task-23_output.step.
```

## task-c/freecad/task-24

```diff
--- before
+++ after
@@ -1 +1 @@
-Using FreeCAD CLI/API, import /home/user/Desktop/freecad_task-24_input.step. Cut a top-opening internal cavity of size 110 x 60 x 24 mm centered at (70,45), leaving a 6 mm bottom floor. Then cut a 30 x 12 mm rectangular connector opening through the front wall on the Y=0 side, centered at X=70 mm and Z=18 mm. Export /home/user/Desktop/freecad_task-24_output.step.
+Using FreeCAD, import /home/user/Desktop/freecad_task-24_input.step. Cut a top-opening internal cavity of size 110 x 60 x 24 mm centered at (70,45), leaving a 6 mm bottom floor. Then cut a 30 x 12 mm rectangular connector opening through the front wall on the Y=0 side, centered at X=70 mm and Z=18 mm. Export /home/user/Desktop/freecad_task-24_output.step.
```

## task-c/freecad/task-25

```diff
--- before
+++ after
@@ -1 +1 @@
-Using the FreeCAD command line, open /home/user/Desktop/freecad_task-25_input.step. Make a circular flange by cutting a center through hole of diameter 40 mm, then cut eight through bolt holes of diameter 9 mm on a bolt circle radius of 45 mm, with the first hole on +X and the rest every 45 degrees. Export /home/user/Desktop/freecad_task-25_output.step.
+Using FreeCAD, open /home/user/Desktop/freecad_task-25_input.step. Make a circular flange by cutting a center through hole of diameter 40 mm, then cut eight through bolt holes of diameter 9 mm on a bolt circle radius of 45 mm, with the first hole on +X and the rest every 45 degrees. Export /home/user/Desktop/freecad_task-25_output.step.
```

## task-c/freecad/task-26

```diff
--- before
+++ after
@@ -1 +1 @@
-Using FreeCAD CLI, open /home/user/Desktop/freecad_task-26_input.step. Add four cylindrical bosses of diameter 18 mm and height 12 mm at centers (20,20), (80,20), (20,50), and (80,50), with boss bottoms on Z=10 mm, and fuse them to the plate. Cut one vertical through hole of diameter 6 mm through each boss and the base plate. Export /home/user/Desktop/freecad_task-26_output.step.
+Using FreeCAD, open /home/user/Desktop/freecad_task-26_input.step. Add four cylindrical bosses of diameter 18 mm and height 12 mm at centers (20,20), (80,20), (20,50), and (80,50), with boss bottoms on Z=10 mm, and fuse them to the plate. Cut one vertical through hole of diameter 6 mm through each boss and the base plate. Export /home/user/Desktop/freecad_task-26_output.step.
```

## task-c/freecad/task-27

```diff
--- before
+++ after
@@ -1 +1 @@
-Using the FreeCAD command-line API, import /home/user/Desktop/freecad_task-27_input.step. Add 4 mm chamfers or equivalent bevels to the four top outside edges and add 3 mm fillets or equivalent rounded edges to the four vertical bottom outside edges. Keep the original 100 x 50 x 20 mm bounding box. Export /home/user/Desktop/freecad_task-27_output.step.
+Using FreeCAD, import /home/user/Desktop/freecad_task-27_input.step. Add 4 mm chamfers or equivalent bevels to the four top outside edges and add 3 mm fillets or equivalent rounded edges to the four vertical bottom outside edges. Keep the original 100 x 50 x 20 mm bounding box. Export /home/user/Desktop/freecad_task-27_output.step.
```

## task-c/freecad/task-28

```diff
--- before
+++ after
@@ -1 +1 @@
-Using FreeCAD CLI, open /home/user/Desktop/freecad_task-28_input.step. Keep the base plate fixed. Move the left support to the top face of the base with center at (30,30), and move the right support to the top face with center at (90,30). The supports must touch the base but remain separate solids. Export a compound STEP named /home/user/Desktop/freecad_task-28_output.step.
+Using FreeCAD, open /home/user/Desktop/freecad_task-28_input.step. Keep the base plate fixed. Move the left support to the top face of the base with center at (30,30), and move the right support to the top face with center at (90,30). The supports must touch the base but remain separate solids. Export a compound STEP named /home/user/Desktop/freecad_task-28_output.step.
```

## task-c/freecad/task-29

```diff
--- before
+++ after
@@ -1 +1 @@
-Using FreeCAD CLI/API, open /home/user/Desktop/freecad_task-29_input.step. Cut five through obround slots along X. The slot centers are at X=25, 50, 75, 100, and 125 mm with Y=30 mm. Each obround slot has total length 18 mm, width 6 mm, and passes through the full 8 mm thickness. Export /home/user/Desktop/freecad_task-29_output.step.
+Using FreeCAD, open /home/user/Desktop/freecad_task-29_input.step. Cut five through obround slots along X. The slot centers are at X=25, 50, 75, 100, and 125 mm with Y=30 mm. Each obround slot has total length 18 mm, width 6 mm, and passes through the full 8 mm thickness. Export /home/user/Desktop/freecad_task-29_output.step.
```

## task-c/freecad/task-30

```diff
--- before
+++ after
@@ -1 +1 @@
-Using the FreeCAD command line, open /home/user/Desktop/freecad_task-30_input.step. Cut a through square window at the plate center (50,50). The nominal window side length is 50 mm, and the four inside corners should have radius 6 mm or equivalent rounded geometry. Do not change the outside envelope. Export /home/user/Desktop/freecad_task-30_output.step.
+Using FreeCAD, open /home/user/Desktop/freecad_task-30_input.step. Cut a through square window at the plate center (50,50). The nominal window side length is 50 mm, and the four inside corners should have radius 6 mm or equivalent rounded geometry. Do not change the outside envelope. Export /home/user/Desktop/freecad_task-30_output.step.
```

## task-c/freecad/task-31

```diff
--- before
+++ after
@@ -1 +1 @@
-Using FreeCAD CLI, open /home/user/Desktop/freecad_task-31_input.step. Add two locating pins of diameter 10 mm and height 20 mm at centers (25,35) and (85,35). Also cut two ordinary through holes of diameter 6 mm at centers (55,20) and (55,50). Fuse the pins to the base plate and export /home/user/Desktop/freecad_task-31_output.step.
+Using FreeCAD, open /home/user/Desktop/freecad_task-31_input.step. Add two locating pins of diameter 10 mm and height 20 mm at centers (25,35) and (85,35). Also cut two ordinary through holes of diameter 6 mm at centers (55,20) and (55,50). Fuse the pins to the base plate and export /home/user/Desktop/freecad_task-31_output.step.
```

## task-c/freecad/task-32

```diff
--- before
+++ after
@@ -1 +1 @@
-Using FreeCAD CLI/API, open /home/user/Desktop/freecad_task-32_input.step. Add four triangular reinforcing ribs to the L bracket and fuse them to the bracket. The ribs are 5 mm thick and located at X=20, 45, 75, and 100 mm, with triangular section legs of about 35 mm and 45 mm. Then cut two vertical through holes of diameter 10 mm in the base at X=30 mm and X=90 mm, Y=25 mm. Export /home/user/Desktop/freecad_task-32_output.step.
+Using FreeCAD, open /home/user/Desktop/freecad_task-32_input.step. Add four triangular reinforcing ribs to the L bracket and fuse them to the bracket. The ribs are 5 mm thick and located at X=20, 45, 75, and 100 mm, with triangular section legs of about 35 mm and 45 mm. Then cut two vertical through holes of diameter 10 mm in the base at X=30 mm and X=90 mm, Y=25 mm. Export /home/user/Desktop/freecad_task-32_output.step.
```

## task-c/freecad/task-33

```diff
--- before
+++ after
@@ -1 +1 @@
-Using the FreeCAD command-line API, import /home/user/Desktop/freecad_task-33_input.step. Create four countersunk through holes at (25,20), (115,20), (25,50), and (115,50). Each hole has a 6 mm through cylindrical section plus a top countersink or counterbore of diameter 14 mm and depth 4 mm. Export /home/user/Desktop/freecad_task-33_output.step.
+Using FreeCAD, import /home/user/Desktop/freecad_task-33_input.step. Create four countersunk through holes at (25,20), (115,20), (25,50), and (115,50). Each hole has a 6 mm through cylindrical section plus a top countersink or counterbore of diameter 14 mm and depth 4 mm. Export /home/user/Desktop/freecad_task-33_output.step.
```

## task-c/freecad/task-34

```diff
--- before
+++ after
@@ -1 +1 @@
-Using FreeCAD CLI/API, open /home/user/Desktop/freecad_task-34_input.step. Split the rectangular body along the X=40 mm plane into two independent solids: a left solid of size 40 x 50 x 20 mm and a right solid of size 60 x 50 x 20 mm. Keep both pieces and export a two-solid compound STEP named /home/user/Desktop/freecad_task-34_output.step.
+Using FreeCAD, open /home/user/Desktop/freecad_task-34_input.step. Split the rectangular body along the X=40 mm plane into two independent solids: a left solid of size 40 x 50 x 20 mm and a right solid of size 60 x 50 x 20 mm. Keep both pieces and export a two-solid compound STEP named /home/user/Desktop/freecad_task-34_output.step.
```

## task-c/freecad/task-35

```diff
--- before
+++ after
@@ -1 +1 @@
-Using FreeCAD CLI/API, open /home/user/Desktop/freecad_task-35_input.step. Along the rail centerline Y=20 mm, cut seven vertical through holes of diameter 5 mm. The first center is X=20 mm and the spacing is 20 mm. Also cut a shallow top groove 140 x 12 x 3 mm centered at Y=20 mm, with groove bottom at Z=7 mm. Export /home/user/Desktop/freecad_task-35_output.step.
+Using FreeCAD, open /home/user/Desktop/freecad_task-35_input.step. Along the rail centerline Y=20 mm, cut seven vertical through holes of diameter 5 mm. The first center is X=20 mm and the spacing is 20 mm. Also cut a shallow top groove 140 x 12 x 3 mm centered at Y=20 mm, with groove bottom at Z=7 mm. Export /home/user/Desktop/freecad_task-35_output.step.
```

## task-c/freecad/task-36

```diff
--- before
+++ after
@@ -1 +1 @@
-Using FreeCAD CLI, open /home/user/Desktop/freecad_task-36_input.step. Create and fuse a semicircular pipe clamp on top of the base. The base is 100 x 40 x 8 mm. The arch has outside radius 18 mm, inside radius 12 mm, length 60 mm along X, and centerline Y=20 mm. Its highest point must be about Z=26 mm. Export /home/user/Desktop/freecad_task-36_output.step.
+Using FreeCAD, open /home/user/Desktop/freecad_task-36_input.step. Create and fuse a semicircular pipe clamp on top of the base. The base is 100 x 40 x 8 mm. The arch has outside radius 18 mm, inside radius 12 mm, length 60 mm along X, and centerline Y=20 mm. Its highest point must be about Z=26 mm. Export /home/user/Desktop/freecad_task-36_output.step.
```

## task-c/freecad/task-37

```diff
--- before
+++ after
@@ -1 +1 @@
-Using FreeCAD CLI/API, open /home/user/Desktop/freecad_task-37_input.step. Cut a centered through rectangular window of size 90 x 50 mm at center (65,45). Then cut four vertical through corner holes of diameter 8 mm, each 12 mm from its adjacent outside edges. Export /home/user/Desktop/freecad_task-37_output.step.
+Using FreeCAD, open /home/user/Desktop/freecad_task-37_input.step. Cut a centered through rectangular window of size 90 x 50 mm at center (65,45). Then cut four vertical through corner holes of diameter 8 mm, each 12 mm from its adjacent outside edges. Export /home/user/Desktop/freecad_task-37_output.step.
```

## task-c/freecad/task-38

```diff
--- before
+++ after
@@ -1 +1 @@
-Using FreeCAD CLI/API, import /home/user/Desktop/freecad_task-38_input.step. Keep the base fixed. Rotate the vertical plate 90 degrees about Z, then move it onto the center of the base top face so its bottom is at Z=10 mm and its center is at (40,15). Do not fuse the solids. Export the two-solid compound as /home/user/Desktop/freecad_task-38_output.step.
+Using FreeCAD, import /home/user/Desktop/freecad_task-38_input.step. Keep the base fixed. Rotate the vertical plate 90 degrees about Z, then move it onto the center of the base top face so its bottom is at Z=10 mm and its center is at (40,15). Do not fuse the solids. Export the two-solid compound as /home/user/Desktop/freecad_task-38_output.step.
```

## task-c/freecad/task-39

```diff
--- before
+++ after
@@ -1 +1 @@
-Using FreeCAD CLI/API, open /home/user/Desktop/freecad_task-39_input.step. Add two cylindrical locating bosses of diameter 20 mm and height 15 mm at centers (40,50) and (120,50) and fuse them to the plate. Cut four corner through holes of diameter 8 mm, each 15 mm from the outside edges. Also cut a 50 x 20 mm through rectangular slot centered at (80,50). Export /home/user/Desktop/freecad_task-39_output.step.
+Using FreeCAD, open /home/user/Desktop/freecad_task-39_input.step. Add two cylindrical locating bosses of diameter 20 mm and height 15 mm at centers (40,50) and (120,50) and fuse them to the plate. Cut four corner through holes of diameter 8 mm, each 15 mm from the outside edges. Also cut a 50 x 20 mm through rectangular slot centered at (80,50). Export /home/user/Desktop/freecad_task-39_output.step.
```

## task-c/freecad/task-40

```diff
--- before
+++ after
@@ -1 +1 @@
-Using FreeCAD CLI/API, open /home/user/Desktop/freecad_task-40_input.step. Place two support blocks on the base top face, centered at (60,60) and (140,60), and fuse them to the base. Cut one vertical through hole of diameter 12 mm through each support and the base. Cut four corner mounting holes of diameter 6 mm, each 15 mm from adjacent outside edges. Export /home/user/Desktop/freecad_task-40_output.step.
+Using FreeCAD, open /home/user/Desktop/freecad_task-40_input.step. Place two support blocks on the base top face, centered at (60,60) and (140,60), and fuse them to the base. Cut one vertical through hole of diameter 12 mm through each support and the base. Cut four corner mounting holes of diameter 6 mm, each 15 mm from adjacent outside edges. Export /home/user/Desktop/freecad_task-40_output.step.
```

## task-c/freecad-path/task-21

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/cli_plate.step. Create a FreeCAD Path/CAM Job and a top Face operation. Set the Job origin at the stock top-face center. Use T1 to target final top Z=10.000 mm with S6000 rpm and F750 mm/min. Tool definition: T1 is a face mill, S6000 rpm, F750 mm/min. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-21.nc.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/cli_plate.step. Create a FreeCAD Path/CAM Job and a top Face operation. Set the Job origin at the stock top-face center. Use T1 to target final top Z=10.000 mm with S6000 rpm and F750 mm/min. Tool definition: T1 is a face mill, S6000 rpm, F750 mm/min. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-21.nc.
```

## task-c/freecad-path/task-22

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/slot_plate.step. Create a center slot toolpath in FreeCAD Path/CAM using Slot, Pocket Shape, or Profile. Machine the slot down to Z=0.000 mm using T1 at S8500 rpm and F500 mm/min. Tool definition: T1 is a 6 mm flat end mill, S8500 rpm, F500 mm/min. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-22.nc.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/slot_plate.step. Create a center slot toolpath in FreeCAD Path/CAM using Slot, Pocket Shape, or Profile. Machine the slot down to Z=0.000 mm using T1 at S8500 rpm and F500 mm/min. Tool definition: T1 is a 6 mm flat end mill, S8500 rpm, F500 mm/min. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-22.nc.
```

## task-c/freecad-path/task-23

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/p1.step, /home/user/Desktop/p2.step, /home/user/Desktop/p3.step. Create three separate FreeCAD Path/CAM Jobs. Each Job origin must be at that part's top-face center. Use T1 to machine the outside Profile of each part down to the bottom. Tool definition: T1 is an end mill reused for the three outside Profile jobs. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/p1.nc, /home/user/Desktop/p2.nc, /home/user/Desktop/p3.nc.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/p1.step, /home/user/Desktop/p2.step, /home/user/Desktop/p3.step. Create three separate FreeCAD Path/CAM Jobs. Each Job origin must be at that part's top-face center. Use T1 to machine the outside Profile of each part down to the bottom. Tool definition: T1 is an end mill reused for the three outside Profile jobs. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/p1.nc, /home/user/Desktop/p2.nc, /home/user/Desktop/p3.nc.
```

## task-c/freecad-path/task-24

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/hole_table_plate.step, /home/user/Desktop/hole_table.csv. Create FreeCAD Path/CAM drilling operations from the table coordinates, diameters, and depths. Through holes must break through the bottom by 1 mm; blind holes must follow the table depth. Tool definitions are driven by /home/user/Desktop/hole_table.csv and must match each listed hole diameter/depth. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-24.nc.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/hole_table_plate.step, /home/user/Desktop/hole_table.csv. Create FreeCAD Path/CAM drilling operations from the table coordinates, diameters, and depths. Through holes must break through the bottom by 1 mm; blind holes must follow the table depth. Tool definitions are driven by /home/user/Desktop/hole_table.csv and must match each listed hole diameter/depth. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-24.nc.
```

## task-c/freecad-path/task-25

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/multi_feature.step, /home/user/Desktop/tool_library.csv. Use only tools from that CSV tool library to complete Face, Pocket or Adaptive, Drilling, and Profile operations in FreeCAD Path/CAM. No tool outside the CSV may be used. Tool rule: use only tools listed in /home/user/Desktop/tool_library.csv. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-25.nc.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/multi_feature.step, /home/user/Desktop/tool_library.csv. Use only tools from that CSV tool library to complete Face, Pocket or Adaptive, Drilling, and Profile operations in FreeCAD Path/CAM. No tool outside the CSV may be used. Tool rule: use only tools listed in /home/user/Desktop/tool_library.csv. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-25.nc.
```

## task-c/freecad-path/task-26

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/job_input.step. Complete a FreeCAD Path/CAM Job containing Pocket, Drilling, and Profile operations. Tool definitions: use an end mill for pockets, a drill for holes, and a profile end mill for outside contours. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-26.nc.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/job_input.step. Complete a FreeCAD Path/CAM Job containing Pocket, Drilling, and Profile operations. Tool definitions: use an end mill for pockets, a drill for holes, and a profile end mill for outside contours. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-26.nc.
```

## task-c/freecad-path/task-27

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/variant_template.step, /home/user/Desktop/variants.json. Create five parameterized FreeCAD Path/CAM pocket Jobs. Each variant must use its own pocket length, pocket width, target bottom Z, tool diameter, and program number. Tool rule: each variant in /home/user/Desktop/variants.json supplies pocket size, bottom Z, tool diameter, and program number. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/variant_01.nc, /home/user/Desktop/variant_02.nc, /home/user/Desktop/variant_03.nc, /home/user/Desktop/variant_04.nc, /home/user/Desktop/variant_05.nc.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/variant_template.step, /home/user/Desktop/variants.json. Create five parameterized FreeCAD Path/CAM pocket Jobs. Each variant must use its own pocket length, pocket width, target bottom Z, tool diameter, and program number. Tool rule: each variant in /home/user/Desktop/variants.json supplies pocket size, bottom Z, tool diameter, and program number. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/variant_01.nc, /home/user/Desktop/variant_02.nc, /home/user/Desktop/variant_03.nc, /home/user/Desktop/variant_04.nc, /home/user/Desktop/variant_05.nc.
```

## task-c/freecad-path/task-28

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/rest_shape.step. Create FreeCAD Path/CAM rest machining. First use T1 to clear the main pocket, then use T2 to machine all small-radius corners and narrow remaining regions. The target floor is Z=6.000 mm. Tool definitions: T1 is a clearing end mill; T2 is a smaller rest-machining end mill. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-28.nc.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/rest_shape.step. Create FreeCAD Path/CAM rest machining. First use T1 to clear the main pocket, then use T2 to machine all small-radius corners and narrow remaining regions. The target floor is Z=6.000 mm. Tool definitions: T1 is a clearing end mill; T2 is a smaller rest-machining end mill. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-28.nc.
```

## task-c/freecad-path/task-29

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/four_parts.step. Create four FreeCAD Path/CAM Jobs or equivalent work-coordinate offsets for four identical parts. The offsets must correspond to G54, G55, G56, and G57 or another evaluable coordinate scheme. Apply the same Face and Profile operations to each part. Tool definition: T1 is reused across G54, G55, G56, and G57 or equivalent offsets. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-29.nc.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/four_parts.step. Create four FreeCAD Path/CAM Jobs or equivalent work-coordinate offsets for four identical parts. The offsets must correspond to G54, G55, G56, and G57 or another evaluable coordinate scheme. Apply the same Face and Profile operations to each part. Tool definition: T1 is reused across G54, G55, G56, and G57 or equivalent offsets. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-29.nc.
```

## task-c/freecad-path/task-30

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/part.step, /home/user/Desktop/fixture.step. Use the fixture as check geometry in FreeCAD Path/CAM. While machining the top pocket, every low-level toolpath point must keep at least 3 mm clearance from the fixture. Tool definition: T1 is an end mill for the top pocket while respecting fixture clearance. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-30.nc.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/part.step, /home/user/Desktop/fixture.step. Use the fixture as check geometry in FreeCAD Path/CAM. While machining the top pocket, every low-level toolpath point must keep at least 3 mm clearance from the fixture. Tool definition: T1 is an end mill for the top pocket while respecting fixture clearance. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-30.nc.
```

## task-c/freecad-path/task-31

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/plate_A.step, /home/user/Desktop/plate_B.step, /home/user/Desktop/plate_C.step, /home/user/Desktop/text_table.csv. Create separate FreeCAD Path/CAM Engrave toolpaths for plate_A, plate_B, and plate_C. Each engraving must cut 0.3 mm deep according to its text, text height, and center coordinates in the CSV. Tool definition: T1 is an engraving cutter for the plate text jobs. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/plate_A.nc, /home/user/Desktop/plate_B.nc, /home/user/Desktop/plate_C.nc.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/plate_A.step, /home/user/Desktop/plate_B.step, /home/user/Desktop/plate_C.step, /home/user/Desktop/text_table.csv. Create separate FreeCAD Path/CAM Engrave toolpaths for plate_A, plate_B, and plate_C. Each engraving must cut 0.3 mm deep according to its text, text height, and center coordinates in the CSV. Tool definition: T1 is an engraving cutter for the plate text jobs. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/plate_A.nc, /home/user/Desktop/plate_B.nc, /home/user/Desktop/plate_C.nc.
```

## task-c/freecad-path/task-32

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/post_test_part.step, /home/user/Desktop/post_config.json. Create FreeCAD Path/CAM pocket and drilling operations, then post the NC program using the configured postprocessor, program number, metric units, and sequence-number policy. Valid G-code lines must carry increasing N numbers starting at N10 with increment 5. Tool and post settings come from /home/user/Desktop/post_config.json. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-32.nc.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/post_test_part.step, /home/user/Desktop/post_config.json. Create FreeCAD Path/CAM pocket and drilling operations, then post the NC program using the configured postprocessor, program number, metric units, and sequence-number policy. Valid G-code lines must carry increasing N numbers starting at N10 with increment 5. Tool and post settings come from /home/user/Desktop/post_config.json. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-32.nc.
```

## task-c/freecad-path/task-33

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/hole_group_part.step. Identify and group twenty-four holes into through holes, blind holes, counterbores, and threaded pilot holes. Create evaluable toolpaths for each group using spot drill, drill, bore/circle mill, and thread milling or helical approximation as needed. Tool definitions: use spot drill, drill, bore/circle mill, and thread mill or helical tools for the hole groups. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-33.nc.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/hole_group_part.step. Identify and group twenty-four holes into through holes, blind holes, counterbores, and threaded pilot holes. Create evaluable toolpaths for each group using spot drill, drill, bore/circle mill, and thread milling or helical approximation as needed. Tool definitions: use spot drill, drill, bore/circle mill, and thread mill or helical tools for the hole groups. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-33.nc.
```

## task-c/freecad-path/task-34

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/broken_boundary_pocket.step. Repair or rebuild the pocket boundary in FreeCAD so it can generate stable CAM pocket toolpaths. Remove the duplicate edge and close the 0.05 mm gap, then machine the pocket to floor Z=5.000 mm. Tool definition: T1 is an end mill for the repaired closed pocket boundary. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-34.nc.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/broken_boundary_pocket.step. Repair or rebuild the pocket boundary in FreeCAD so it can generate stable CAM pocket toolpaths. Remove the duplicate edge and close the 0.05 mm gap, then machine the pocket to floor Z=5.000 mm. Tool definition: T1 is an end mill for the repaired closed pocket boundary. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-34.nc.
```

## task-c/freecad-path/task-35

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/risky_setup.step. Machine all safe holes and maintain at least 3 mm clearance from fixtures. Tool definitions: use drilling tools sized for the safe holes, respect holder clearance, and skip collision-risk holes. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-35.nc.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/risky_setup.step. Machine all safe holes and maintain at least 3 mm clearance from fixtures. Tool definitions: use drilling tools sized for the safe holes, respect holder clearance, and skip collision-risk holes. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-35.nc.
```

## task-c/freecad-path/task-36

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/revision_A.step, /home/user/Desktop/revision_B.step. Compare the pocket-size and hole-position changes between revisions A and B. Generate the final FreeCAD Path/CAM Job and NC only for revision_B. Tool definitions: use the supplied end mill and drill to program revision_B only. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-36_B.nc.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/revision_A.step, /home/user/Desktop/revision_B.step. Compare the pocket-size and hole-position changes between revisions A and B. Generate the final FreeCAD Path/CAM Job and NC only for revision_B. Tool definitions: use the supplied end mill and drill to program revision_B only. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-36_B.nc.
```

## task-c/freecad-path/task-37

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/two_sided_part.step. Create A-side and B-side FreeCAD Path/CAM Jobs or independent machining coordinate systems. Side A machines the open pocket; side B machines the four counterbores. Tool definitions: use end mills, drills, and counterbore tools for side A and side B. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-37_A.nc, /home/user/Desktop/task-37_B.nc.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/two_sided_part.step. Create A-side and B-side FreeCAD Path/CAM Jobs or independent machining coordinate systems. Side A machines the open pocket; side B machines the four counterbores. Tool definitions: use end mills, drills, and counterbore tools for side A and side B. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-37_A.nc, /home/user/Desktop/task-37_B.nc.
```

## task-c/freecad-path/task-38

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/relief_surface.step. Create FreeCAD Path/CAM 3D roughing and finishing operations. Use T1 for 3D Pocket roughing with 0.5 mm stock, and T2 for 3D Surface finishing with stepover no larger than 1.5 mm. Tool definitions: T1 is for 3D Pocket roughing; T2 is for 3D Surface finishing with stepover <= 1.5 mm. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-38.nc.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/relief_surface.step. Create FreeCAD Path/CAM 3D roughing and finishing operations. Use T1 for 3D Pocket roughing with 0.5 mm stock, and T2 for 3D Surface finishing with stepover no larger than 1.5 mm. Tool definitions: T1 is for 3D Pocket roughing; T2 is for 3D Surface finishing with stepover <= 1.5 mm. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-38.nc.
```

## task-c/freecad-path/task-39

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/complex_pockets.step, /home/user/Desktop/tool_candidates.csv. Machine five pockets, twelve holes, and the outside contour. No selected tool diameter may exceed the corresponding pocket minimum width. Tool rule: choose no more than five tools from /home/user/Desktop/tool_candidates.csv. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-39.nc.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/complex_pockets.step, /home/user/Desktop/tool_candidates.csv. Machine five pockets, twelve holes, and the outside contour. No selected tool diameter may exceed the corresponding pocket minimum width. Tool rule: choose no more than five tools from /home/user/Desktop/tool_candidates.csv. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-39.nc.
```

## task-c/freecad-path/task-40

```diff
--- before
+++ after
@@ -1 +1 @@
-Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/final_benchmark.step, /home/user/Desktop/params.json. Complete the full FreeCAD Path/CAM delivery. Configure stock, Job origin, and fixture/check geometry; machine the outside profile, three pockets, sixteen through holes, two counterbores, and one surface region; use at least five tool classes. Tool rule: use at least five tool classes covering facing, pocketing, drilling, counterboring, surface finishing, and profiling. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-40.nc, /home/user/Desktop/post_log.txt.
+Use FreeCAD with the Path/CAM modules. Read the initial file(s) from the Desktop path(s): /home/user/Desktop/final_benchmark.step, /home/user/Desktop/params.json. Complete the full FreeCAD Path/CAM delivery. Configure stock, Job origin, and fixture/check geometry; machine the outside profile, three pockets, sixteen through holes, two counterbores, and one surface region; use at least five tool classes. Tool rule: use at least five tool classes covering facing, pocketing, drilling, counterboring, surface finishing, and profiling. Write the required output file(s) to the output folder using exactly these absolute file paths: /home/user/Desktop/task-40.nc, /home/user/Desktop/post_log.txt.
```

## task-c/fusion360/task-21

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\cli_plate.step, C:\Users\Administrator\Desktop\tools.csv. Using the CLI workflow, create a 3-axis milling setup for C:\Users\Administrator\Desktop\cli_plate.step. Face the top surface with T1, a 12 mm face mill. Put the WCS origin at the stock top-face center and use S6000 rpm and F750 mm/min. Export C:\Users\Administrator\Desktop\task-21.nc and C:\Users\Administrator\Desktop\task-21_setup.html. Tool definition: T1 is a 12 mm face mill, S6000 rpm, F750 mm/min. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-21.nc, C:\Users\Administrator\Desktop\task-21_setup.html.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\cli_plate.step, C:\Users\Administrator\Desktop\tools.csv. Create a 3-axis milling setup for C:\Users\Administrator\Desktop\cli_plate.step. Face the top surface with T1, a 12 mm face mill. Put the WCS origin at the stock top-face center and use S6000 rpm and F750 mm/min. Export C:\Users\Administrator\Desktop\task-21.nc and C:\Users\Administrator\Desktop\task-21_setup.html. Tool definition: T1 is a 12 mm face mill, S6000 rpm, F750 mm/min. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-21.nc, C:\Users\Administrator\Desktop\task-21_setup.html.
```

## task-c/fusion360/task-22

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\slot_plate.step, C:\Users\Administrator\Desktop\tools.csv. Using the CLI workflow, create a 2D Pocket or slot milling operation for C:\Users\Administrator\Desktop\slot_plate.step. Machine the centered 40 x 8 slot down to Z=0.000 mm with T1, a 6 mm flat end mill, at S8500 rpm and F500 mm/min. Export C:\Users\Administrator\Desktop\task-22.nc and C:\Users\Administrator\Desktop\task-22_summary.json. Tool definition: T1 is a 6 mm flat end mill, S8500 rpm, F500 mm/min. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-22.nc, C:\Users\Administrator\Desktop\task-22_summary.json.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\slot_plate.step, C:\Users\Administrator\Desktop\tools.csv. Create a 2D Pocket or slot milling operation for C:\Users\Administrator\Desktop\slot_plate.step. Machine the centered 40 x 8 slot down to Z=0.000 mm with T1, a 6 mm flat end mill, at S8500 rpm and F500 mm/min. Export C:\Users\Administrator\Desktop\task-22.nc and C:\Users\Administrator\Desktop\task-22_summary.json. Tool definition: T1 is a 6 mm flat end mill, S8500 rpm, F500 mm/min. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-22.nc, C:\Users\Administrator\Desktop\task-22_summary.json.
```

## task-c/fusion360/task-23

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\p1.step, C:\Users\Administrator\Desktop\p2.step, C:\Users\Administrator\Desktop\p3.step, C:\Users\Administrator\Desktop\tools.csv. Batch process the three STEP parts C:\Users\Administrator\Desktop\p1.step, C:\Users\Administrator\Desktop\p2.step, and C:\Users\Administrator\Desktop\p3.step. For each part, create a separate 2D Contour operation using that part's top-face center as the WCS. Export C:\Users\Administrator\Desktop\p1.nc, C:\Users\Administrator\Desktop\p2.nc, C:\Users\Administrator\Desktop\p3.nc, and C:\Users\Administrator\Desktop\batch_report.csv with a success row for each part. Tool definition: T1 is the contouring end mill reused for C:\Users\Administrator\Desktop\p1.step, C:\Users\Administrator\Desktop\p2.step, and C:\Users\Administrator\Desktop\p3.step. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\p1.nc, C:\Users\Administrator\Desktop\p2.nc, C:\Users\Administrator\Desktop\p3.nc, C:\Users\Administrator\Desktop\batch_report.csv.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\p1.step, C:\Users\Administrator\Desktop\p2.step, C:\Users\Administrator\Desktop\p3.step, C:\Users\Administrator\Desktop\tools.csv. Batch process the three STEP parts C:\Users\Administrator\Desktop\p1.step, C:\Users\Administrator\Desktop\p2.step, and C:\Users\Administrator\Desktop\p3.step. For each part, create a separate 2D Contour operation using that part's top-face center as the WCS. Export C:\Users\Administrator\Desktop\p1.nc, C:\Users\Administrator\Desktop\p2.nc, C:\Users\Administrator\Desktop\p3.nc, and C:\Users\Administrator\Desktop\batch_report.csv with a success row for each part. Tool definition: T1 is the contouring end mill reused for C:\Users\Administrator\Desktop\p1.step, C:\Users\Administrator\Desktop\p2.step, and C:\Users\Administrator\Desktop\p3.step. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\p1.nc, C:\Users\Administrator\Desktop\p2.nc, C:\Users\Administrator\Desktop\p3.nc, C:\Users\Administrator\Desktop\batch_report.csv.
```

## task-c/fusion360/task-24

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\hole_table_plate.step, C:\Users\Administrator\Desktop\hole_table.csv. Read C:\Users\Administrator\Desktop\hole_table.csv and machine all ten listed holes on C:\Users\Administrator\Desktop\hole_table_plate.step. Through holes must break through the bottom by 1 mm, and blind holes must follow the depth in the CSV. Export C:\Users\Administrator\Desktop\task-24.nc and C:\Users\Administrator\Desktop\hole_result.json with one record per hole containing x, y, diameter, depth, and type. Tool definitions: use the drilling tools needed for the diameters and through/blind depths listed in C:\Users\Administrator\Desktop\hole_table.csv. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-24.nc, C:\Users\Administrator\Desktop\hole_result.json.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\hole_table_plate.step, C:\Users\Administrator\Desktop\hole_table.csv. Read C:\Users\Administrator\Desktop\hole_table.csv and machine all ten listed holes on C:\Users\Administrator\Desktop\hole_table_plate.step. Through holes must break through the bottom by 1 mm, and blind holes must follow the depth in the CSV. Export C:\Users\Administrator\Desktop\task-24.nc and C:\Users\Administrator\Desktop\hole_result.json with one record per hole containing x, y, diameter, depth, and type. Tool definitions: use the drilling tools needed for the diameters and through/blind depths listed in C:\Users\Administrator\Desktop\hole_table.csv. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-24.nc, C:\Users\Administrator\Desktop\hole_result.json.
```

## task-c/fusion360/task-25

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\multi_feature.step, C:\Users\Administrator\Desktop\tool_library.csv. Use only the tools listed in C:\Users\Administrator\Desktop\tool_library.csv to machine C:\Users\Administrator\Desktop\multi_feature.step. Create Face, 2D Pocket, Drill, and 2D Contour operations without introducing any unlisted tool. Export C:\Users\Administrator\Desktop\task-25.nc, C:\Users\Administrator\Desktop\tools_used.csv, and C:\Users\Administrator\Desktop\task-25_setup.html. Tool rule: use only the tools listed in C:\Users\Administrator\Desktop\tool_library.csv and do not introduce any unlisted tool. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-25.nc, C:\Users\Administrator\Desktop\tools_used.csv, C:\Users\Administrator\Desktop\task-25_setup.html.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\multi_feature.step, C:\Users\Administrator\Desktop\tool_library.csv. Use only the tools listed in C:\Users\Administrator\Desktop\tool_library.csv to machine C:\Users\Administrator\Desktop\multi_feature.step. Create Face, 2D Pocket, Drill, and 2D Contour operations without introducing any unlisted tool. Export C:\Users\Administrator\Desktop\task-25.nc, C:\Users\Administrator\Desktop\tools_used.csv, and C:\Users\Administrator\Desktop\task-25_setup.html. Tool rule: use only the tools listed in C:\Users\Administrator\Desktop\tool_library.csv and do not introduce any unlisted tool. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-25.nc, C:\Users\Administrator\Desktop\tools_used.csv, C:\Users\Administrator\Desktop\task-25_setup.html.
```

## task-c/fusion360/task-26

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\job_input.step, C:\Users\Administrator\Desktop\tools.csv. Create a complete milling job for C:\Users\Administrator\Desktop\job_input.step containing pocket, drill, and outer-contour operations. Export C:\Users\Administrator\Desktop\task-26.nc, C:\Users\Administrator\Desktop\task-26_setup.html, and C:\Users\Administrator\Desktop\task-26_tools.csv. The setup sheet must list stock dimensions, WCS, operation names, and tool parameters, and the NC program must end normally. Tool definitions: use the supplied tool table for pocketing, drilling, and outer contouring. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-26.nc, C:\Users\Administrator\Desktop\task-26_setup.html, C:\Users\Administrator\Desktop\task-26_tools.csv.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\job_input.step, C:\Users\Administrator\Desktop\tools.csv. Create a complete milling job for C:\Users\Administrator\Desktop\job_input.step containing pocket, drill, and outer-contour operations. Export C:\Users\Administrator\Desktop\task-26.nc, C:\Users\Administrator\Desktop\task-26_setup.html, and C:\Users\Administrator\Desktop\task-26_tools.csv. The setup sheet must list stock dimensions, WCS, operation names, and tool parameters, and the NC program must end normally. Tool definitions: use the supplied tool table for pocketing, drilling, and outer contouring. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-26.nc, C:\Users\Administrator\Desktop\task-26_setup.html, C:\Users\Administrator\Desktop\task-26_tools.csv.
```

## task-c/fusion360/task-27

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\variant_template.step, C:\Users\Administrator\Desktop\variants.json. Generate five independent CAM results from C:\Users\Administrator\Desktop\variants.json for C:\Users\Administrator\Desktop\variant_template.step. Each variant must use its own pocket length, width, target floor Z, tool diameter, and program number. Export C:\Users\Administrator\Desktop\variant_01.nc through C:\Users\Administrator\Desktop\variant_05.nc and C:\Users\Administrator\Desktop\variants_report.json with five successful entries. Tool rule: each variant supplies its own tool diameter, pocket dimensions, floor Z, and program number in C:\Users\Administrator\Desktop\variants.json. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\variant_01.nc, C:\Users\Administrator\Desktop\variant_02.nc, C:\Users\Administrator\Desktop\variant_03.nc, C:\Users\Administrator\Desktop\variant_04.nc, C:\Users\Administrator\Desktop\variant_05.nc, C:\Users\Administrator\Desktop\variants_report.json.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\variant_template.step, C:\Users\Administrator\Desktop\variants.json. Generate five independent CAM results from C:\Users\Administrator\Desktop\variants.json for C:\Users\Administrator\Desktop\variant_template.step. Each variant must use its own pocket length, width, target floor Z, tool diameter, and program number. Export C:\Users\Administrator\Desktop\variant_01.nc through C:\Users\Administrator\Desktop\variant_05.nc and C:\Users\Administrator\Desktop\variants_report.json with five successful entries. Tool rule: each variant supplies its own tool diameter, pocket dimensions, floor Z, and program number in C:\Users\Administrator\Desktop\variants.json. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\variant_01.nc, C:\Users\Administrator\Desktop\variant_02.nc, C:\Users\Administrator\Desktop\variant_03.nc, C:\Users\Administrator\Desktop\variant_04.nc, C:\Users\Administrator\Desktop\variant_05.nc, C:\Users\Administrator\Desktop\variants_report.json.
```

## task-c/fusion360/task-28

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\rest_shape.step, C:\Users\Administrator\Desktop\tools.csv. Create rest-machining operations for C:\Users\Administrator\Desktop\rest_shape.step. Clear the main pocket with T1, a 12 mm end mill, then use T2, a 4 mm end mill, to machine all small-radius corners and narrow remaining regions. The target pocket floor is Z=6.000 mm. Export C:\Users\Administrator\Desktop\task-28.nc and C:\Users\Administrator\Desktop\rest_report.json. Tool definitions: T1 is a 12 mm end mill for main clearing; T2 is a 4 mm end mill for rest machining. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-28.nc, C:\Users\Administrator\Desktop\rest_report.json.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\rest_shape.step, C:\Users\Administrator\Desktop\tools.csv. Create rest-machining operations for C:\Users\Administrator\Desktop\rest_shape.step. Clear the main pocket with T1, a 12 mm end mill, then use T2, a 4 mm end mill, to machine all small-radius corners and narrow remaining regions. The target pocket floor is Z=6.000 mm. Export C:\Users\Administrator\Desktop\task-28.nc and C:\Users\Administrator\Desktop\rest_report.json. Tool definitions: T1 is a 12 mm end mill for main clearing; T2 is a 4 mm end mill for rest machining. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-28.nc, C:\Users\Administrator\Desktop\rest_report.json.
```

## task-c/fusion360/task-29

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\four_parts.step, C:\Users\Administrator\Desktop\tools.csv. Create a four-WCS manufacturing program for C:\Users\Administrator\Desktop\four_parts.step. Assign four offsets corresponding to G54, G55, G56, and G57 or equivalent offsets. Run the same Face and Contour operations on all four parts. Export C:\Users\Administrator\Desktop\task-29.nc and C:\Users\Administrator\Desktop\wcs_report.json. Tool definition: T1 is the end mill reused across G54, G55, G56, and G57. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-29.nc, C:\Users\Administrator\Desktop\wcs_report.json.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\four_parts.step, C:\Users\Administrator\Desktop\tools.csv. Create a four-WCS manufacturing program for C:\Users\Administrator\Desktop\four_parts.step. Assign four offsets corresponding to G54, G55, G56, and G57 or equivalent offsets. Run the same Face and Contour operations on all four parts. Export C:\Users\Administrator\Desktop\task-29.nc and C:\Users\Administrator\Desktop\wcs_report.json. Tool definition: T1 is the end mill reused across G54, G55, G56, and G57. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-29.nc, C:\Users\Administrator\Desktop\wcs_report.json.
```

## task-c/fusion360/task-30

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\part.step, C:\Users\Administrator\Desktop\fixture.step, C:\Users\Administrator\Desktop\tools.csv. Use C:\Users\Administrator\Desktop\fixture.step as the fixture definition while machining the pocket on C:\Users\Administrator\Desktop\part.step. All low-level tool positions below fixture top plus 2 mm must remain at least 3 mm clear of the fixture bounding boxes. Export C:\Users\Administrator\Desktop\task-30.nc and C:\Users\Administrator\Desktop\fixture_clearance.json. Tool definition: T1 machines the pocket while respecting the fixture clearance rule. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-30.nc, C:\Users\Administrator\Desktop\fixture_clearance.json.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\part.step, C:\Users\Administrator\Desktop\fixture.step, C:\Users\Administrator\Desktop\tools.csv. Use C:\Users\Administrator\Desktop\fixture.step as the fixture definition while machining the pocket on C:\Users\Administrator\Desktop\part.step. All low-level tool positions below fixture top plus 2 mm must remain at least 3 mm clear of the fixture bounding boxes. Export C:\Users\Administrator\Desktop\task-30.nc and C:\Users\Administrator\Desktop\fixture_clearance.json. Tool definition: T1 machines the pocket while respecting the fixture clearance rule. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-30.nc, C:\Users\Administrator\Desktop\fixture_clearance.json.
```

## task-c/fusion360/task-31

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\shaft_family.step, C:\Users\Administrator\Desktop\tools.csv. Create a turning setup for C:\Users\Administrator\Desktop\shaft_family.step with Z as the turning axis. Generate OD roughing, OD finishing, two grooving operations, and an end-face center drill operation. Export C:\Users\Administrator\Desktop\task-31.nc and C:\Users\Administrator\Desktop\turning_report.json with roughing allowance, finishing tool, and groove count. Tool definitions: use OD roughing, OD finishing, grooving, and center-drilling turning tools from C:\Users\Administrator\Desktop\tools.csv. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-31.nc, C:\Users\Administrator\Desktop\turning_report.json.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\shaft_family.step, C:\Users\Administrator\Desktop\tools.csv. Create a turning setup for C:\Users\Administrator\Desktop\shaft_family.step with Z as the turning axis. Generate OD roughing, OD finishing, two grooving operations, and an end-face center drill operation. Export C:\Users\Administrator\Desktop\task-31.nc and C:\Users\Administrator\Desktop\turning_report.json with roughing allowance, finishing tool, and groove count. Tool definitions: use OD roughing, OD finishing, grooving, and center-drilling turning tools from C:\Users\Administrator\Desktop\tools.csv. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-31.nc, C:\Users\Administrator\Desktop\turning_report.json.
```

## task-c/fusion360/task-32

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\quality_part.step, C:\Users\Administrator\Desktop\params.json. Machine C:\Users\Administrator\Desktop\quality_part.step according to C:\Users\Administrator\Desktop\params.json. Create the circular pocket, rectangular pocket, four holes, and outside contour, using the spindle speed and feed specified for each operation. Export C:\Users\Administrator\Desktop\task-32.nc, C:\Users\Administrator\Desktop\operation_report.json, and C:\Users\Administrator\Desktop\post_log.txt. Tool and cutting parameters are specified by C:\Users\Administrator\Desktop\params.json for each operation. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-32.nc, C:\Users\Administrator\Desktop\operation_report.json, C:\Users\Administrator\Desktop\post_log.txt.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\quality_part.step, C:\Users\Administrator\Desktop\params.json. Machine C:\Users\Administrator\Desktop\quality_part.step according to C:\Users\Administrator\Desktop\params.json. Create the circular pocket, rectangular pocket, four holes, and outside contour, using the spindle speed and feed specified for each operation. Export C:\Users\Administrator\Desktop\task-32.nc, C:\Users\Administrator\Desktop\operation_report.json, and C:\Users\Administrator\Desktop\post_log.txt. Tool and cutting parameters are specified by C:\Users\Administrator\Desktop\params.json for each operation. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-32.nc, C:\Users\Administrator\Desktop\operation_report.json, C:\Users\Administrator\Desktop\post_log.txt.
```

## task-c/fusion360/task-33

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\hole_recognition_part.step, C:\Users\Administrator\Desktop\tools.csv. Recognize and group all twenty-four holes in C:\Users\Administrator\Desktop\hole_recognition_part.step: eight through holes, eight blind holes, four counterbores, and four threaded holes. Create spot drilling, drilling, bore or circular pocket, and thread milling toolpaths for the groups. Export C:\Users\Administrator\Desktop\task-33.nc and C:\Users\Administrator\Desktop\hole_groups.json. Tool definitions: create spot drilling, drilling, boring/circular-pocket, and thread-milling tools for the recognized hole groups. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-33.nc, C:\Users\Administrator\Desktop\hole_groups.json.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\hole_recognition_part.step, C:\Users\Administrator\Desktop\tools.csv. Recognize and group all twenty-four holes in C:\Users\Administrator\Desktop\hole_recognition_part.step: eight through holes, eight blind holes, four counterbores, and four threaded holes. Create spot drilling, drilling, bore or circular pocket, and thread milling toolpaths for the groups. Export C:\Users\Administrator\Desktop\task-33.nc and C:\Users\Administrator\Desktop\hole_groups.json. Tool definitions: create spot drilling, drilling, boring/circular-pocket, and thread-milling tools for the recognized hole groups. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-33.nc, C:\Users\Administrator\Desktop\hole_groups.json.
```

## task-c/fusion360/task-34

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\post_test_part.step, C:\Users\Administrator\Desktop\post_config.json. Machine C:\Users\Administrator\Desktop\post_test_part.step and post the pocket and drilling program using C:\Users\Administrator\Desktop\post_config.json. The NC output must use program number 2034, metric units, and N sequence numbers starting at N10 with an increment of 5. Export C:\Users\Administrator\Desktop\task-34.nc and C:\Users\Administrator\Desktop\post_config_used.json. Tool definitions: use the post configuration from C:\Users\Administrator\Desktop\post_config.json and the pocket/drilling tools required by C:\Users\Administrator\Desktop\post_test_part.step. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-34.nc, C:\Users\Administrator\Desktop\post_config_used.json.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\post_test_part.step, C:\Users\Administrator\Desktop\post_config.json. Machine C:\Users\Administrator\Desktop\post_test_part.step and post the pocket and drilling program using C:\Users\Administrator\Desktop\post_config.json. The NC output must use program number 2034, metric units, and N sequence numbers starting at N10 with an increment of 5. Export C:\Users\Administrator\Desktop\task-34.nc and C:\Users\Administrator\Desktop\post_config_used.json. Tool definitions: use the post configuration from C:\Users\Administrator\Desktop\post_config.json and the pocket/drilling tools required by C:\Users\Administrator\Desktop\post_test_part.step. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-34.nc, C:\Users\Administrator\Desktop\post_config_used.json.
```

## task-c/fusion360/task-35

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\risky_setup.step, C:\Users\Administrator\Desktop\tools.csv. Plan drilling for sixteen candidate holes in C:\Users\Administrator\Desktop\risky_setup.step with fixtures present. Skip all holes with holder collision risk and do not include their coordinates in the final NC program. Machine all safe holes and keep low-level tool positions at least 3 mm clear of fixtures. Export C:\Users\Administrator\Desktop\task-35.nc and C:\Users\Administrator\Desktop\collision_filter.json. Tool definitions: use drilling tools that allow safe candidate holes and skip holes with holder collision risk. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-35.nc, C:\Users\Administrator\Desktop\collision_filter.json.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\risky_setup.step, C:\Users\Administrator\Desktop\tools.csv. Plan drilling for sixteen candidate holes in C:\Users\Administrator\Desktop\risky_setup.step with fixtures present. Skip all holes with holder collision risk and do not include their coordinates in the final NC program. Machine all safe holes and keep low-level tool positions at least 3 mm clear of fixtures. Export C:\Users\Administrator\Desktop\task-35.nc and C:\Users\Administrator\Desktop\collision_filter.json. Tool definitions: use drilling tools that allow safe candidate holes and skip holes with holder collision risk. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-35.nc, C:\Users\Administrator\Desktop\collision_filter.json.
```

## task-c/fusion360/task-36

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\revision_A.step, C:\Users\Administrator\Desktop\revision_B.step, C:\Users\Administrator\Desktop\tools.csv. Compare C:\Users\Administrator\Desktop\revision_A.step and C:\Users\Administrator\Desktop\revision_B.step, identify changes in pocket dimensions and hole positions, and generate the final CAM program only for revision_B. Export C:\Users\Administrator\Desktop\task-36_B.nc and C:\Users\Administrator\Desktop\change_report.json. The NC program must match revision_B geometry and not the old revision_A hole positions. Tool definitions: use the supplied tools to program only revision_B geometry. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-36_B.nc, C:\Users\Administrator\Desktop\change_report.json.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\revision_A.step, C:\Users\Administrator\Desktop\revision_B.step, C:\Users\Administrator\Desktop\tools.csv. Compare C:\Users\Administrator\Desktop\revision_A.step and C:\Users\Administrator\Desktop\revision_B.step, identify changes in pocket dimensions and hole positions, and generate the final CAM program only for revision_B. Export C:\Users\Administrator\Desktop\task-36_B.nc and C:\Users\Administrator\Desktop\change_report.json. The NC program must match revision_B geometry and not the old revision_A hole positions. Tool definitions: use the supplied tools to program only revision_B geometry. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-36_B.nc, C:\Users\Administrator\Desktop\change_report.json.
```

## task-c/fusion360/task-37

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\two_sided_part.step, C:\Users\Administrator\Desktop\tools.csv. Create A-side and B-side setups for C:\Users\Administrator\Desktop\two_sided_part.step. The A side machines the open pocket and the B side machines four counterbores. The setup WCS Z directions must be opposite. Export C:\Users\Administrator\Desktop\task-37_A.nc, C:\Users\Administrator\Desktop\task-37_B.nc, and C:\Users\Administrator\Desktop\two_setup_report.json. Tool definitions: T1 pockets the A side, T2 drills/counterbores the B side, and T3 finishes as needed. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-37_A.nc, C:\Users\Administrator\Desktop\task-37_B.nc, C:\Users\Administrator\Desktop\two_setup_report.json.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\two_sided_part.step, C:\Users\Administrator\Desktop\tools.csv. Create A-side and B-side setups for C:\Users\Administrator\Desktop\two_sided_part.step. The A side machines the open pocket and the B side machines four counterbores. The setup WCS Z directions must be opposite. Export C:\Users\Administrator\Desktop\task-37_A.nc, C:\Users\Administrator\Desktop\task-37_B.nc, and C:\Users\Administrator\Desktop\two_setup_report.json. Tool definitions: T1 pockets the A side, T2 drills/counterbores the B side, and T3 finishes as needed. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-37_A.nc, C:\Users\Administrator\Desktop\task-37_B.nc, C:\Users\Administrator\Desktop\two_setup_report.json.
```

## task-c/fusion360/task-38

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\impeller_test.step, C:\Users\Administrator\Desktop\tools.csv. Create a rotary or multi-axis toolpath for C:\Users\Administrator\Desktop\impeller_test.step. The simplified impeller has six blades, uses the Z axis as the rotary axis, and should be posted with a rotary A, B, or C axis coordinate. Export C:\Users\Administrator\Desktop\task-38.nc and C:\Users\Administrator\Desktop\rotary_report.json. Tool definition: T1 is the rotary/multi-axis tool for the six-blade impeller toolpath. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-38.nc, C:\Users\Administrator\Desktop\rotary_report.json.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\impeller_test.step, C:\Users\Administrator\Desktop\tools.csv. Create a rotary or multi-axis toolpath for C:\Users\Administrator\Desktop\impeller_test.step. The simplified impeller has six blades, uses the Z axis as the rotary axis, and should be posted with a rotary A, B, or C axis coordinate. Export C:\Users\Administrator\Desktop\task-38.nc and C:\Users\Administrator\Desktop\rotary_report.json. Tool definition: T1 is the rotary/multi-axis tool for the six-blade impeller toolpath. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-38.nc, C:\Users\Administrator\Desktop\rotary_report.json.
```

## task-c/fusion360/task-39

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\complex_pockets.step, C:\Users\Administrator\Desktop\tool_candidates.csv. Select no more than five tools from C:\Users\Administrator\Desktop\tool_candidates.csv to machine C:\Users\Administrator\Desktop\complex_pockets.step. Machine five pockets, twelve holes, and the outside contour. Do not choose a tool whose diameter is larger than the minimum width of the pocket it machines. Export C:\Users\Administrator\Desktop\task-39.nc, C:\Users\Administrator\Desktop\tool_selection.json, and C:\Users\Administrator\Desktop\tools_used.csv. Tool rule: choose no more than five tools from C:\Users\Administrator\Desktop\tool_candidates.csv and keep every selected tool diameter within the matching pocket width. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-39.nc, C:\Users\Administrator\Desktop\tool_selection.json, C:\Users\Administrator\Desktop\tools_used.csv.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\complex_pockets.step, C:\Users\Administrator\Desktop\tool_candidates.csv. Select no more than five tools from C:\Users\Administrator\Desktop\tool_candidates.csv to machine C:\Users\Administrator\Desktop\complex_pockets.step. Machine five pockets, twelve holes, and the outside contour. Do not choose a tool whose diameter is larger than the minimum width of the pocket it machines. Export C:\Users\Administrator\Desktop\task-39.nc, C:\Users\Administrator\Desktop\tool_selection.json, and C:\Users\Administrator\Desktop\tools_used.csv. Tool rule: choose no more than five tools from C:\Users\Administrator\Desktop\tool_candidates.csv and keep every selected tool diameter within the matching pocket width. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-39.nc, C:\Users\Administrator\Desktop\tool_selection.json, C:\Users\Administrator\Desktop\tools_used.csv.
```

## task-c/fusion360/task-40

```diff
--- before
+++ after
@@ -1 +1 @@
-Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\final_benchmark.step, C:\Users\Administrator\Desktop\tools.csv, C:\Users\Administrator\Desktop\params.json. Complete the full CAM delivery for C:\Users\Administrator\Desktop\final_benchmark.step. Configure stock, WCS, fixtures, outside contour, three pockets, sixteen through holes, two counterbores, one spherical finishing region, and at least five tool classes. Export C:\Users\Administrator\Desktop\task-40.nc, C:\Users\Administrator\Desktop\task-40_setup.html, C:\Users\Administrator\Desktop\tool_list.csv, C:\Users\Administrator\Desktop\validation.json, and C:\Users\Administrator\Desktop\post_log.txt with all checks passing. Tool rule: use at least five tool classes covering facing, pocketing, drilling, counterboring, spherical finishing, and contouring. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-40.nc, C:\Users\Administrator\Desktop\task-40_setup.html, C:\Users\Administrator\Desktop\tool_list.csv, C:\Users\Administrator\Desktop\validation.json, C:\Users\Administrator\Desktop\post_log.txt.
+Use Fusion 360 for CAM generation. Read the initial file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\final_benchmark.step, C:\Users\Administrator\Desktop\tools.csv, C:\Users\Administrator\Desktop\params.json. Complete the full CAM delivery for C:\Users\Administrator\Desktop\final_benchmark.step. Configure stock, WCS, fixtures, outside contour, three pockets, sixteen through holes, two counterbores, one spherical finishing region, and at least five tool classes. Export C:\Users\Administrator\Desktop\task-40.nc, C:\Users\Administrator\Desktop\task-40_setup.html, C:\Users\Administrator\Desktop\tool_list.csv, C:\Users\Administrator\Desktop\validation.json, and C:\Users\Administrator\Desktop\post_log.txt with all checks passing. Tool rule: use at least five tool classes covering facing, pocketing, drilling, counterboring, spherical finishing, and contouring. Write the output file(s) to the Desktop path(s) using exactly these absolute file paths: C:\Users\Administrator\Desktop\task-40.nc, C:\Users\Administrator\Desktop\task-40_setup.html, C:\Users\Administrator\Desktop\tool_list.csv, C:\Users\Administrator\Desktop\validation.json, C:\Users\Administrator\Desktop\post_log.txt.
```

## task-c/openfoam/task-01

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given an incomplete OpenFOAM case in `/home/user/Desktop/cavity_base/`.
-Complete a 2D incompressible laminar channel-flow analysis from the command line:
+Complete a 2D incompressible laminar channel-flow analysis:
 
@@ -16,2 +16 @@
 
-5. Do not use the ParaView GUI.
```

## task-c/openfoam/task-02

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given an incomplete cavity template `/home/user/Desktop/cavity_base/`.
-Complete a lid-driven cavity analysis from the command line:
+Complete a lid-driven cavity analysis:
 
```

## task-c/openfoam/task-03

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a backward-facing-step template `/home/user/Desktop/bfs_base/`.
-Complete a turbulent separation and reattachment analysis from the command line:
+Complete a turbulent separation and reattachment analysis:
 
```

## task-c/openfoam/task-04

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a pipe template `/home/user/Desktop/pipe_base/`.
-Complete a 3D fully developed laminar-flow analysis from the command line:
+Complete a 3D fully developed laminar-flow analysis:
 
```

## task-c/openfoam/task-05

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a pipe template `/home/user/Desktop/pipe_base/`.
-Complete a turbulent-flow analysis from the command line:
+Complete a turbulent-flow analysis:
 
```

## task-c/openfoam/task-06

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given an external-flow template `/home/user/Desktop/plate_base/`.
-Complete a flat-plate boundary-layer analysis from the command line:
+Complete a flat-plate boundary-layer analysis:
 
```

## task-c/openfoam/task-07

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a cylinder crossflow template `/home/user/Desktop/cylinder_base/`.
-Complete a transient vortex-shedding analysis from the command line:
+Complete a transient vortex-shedding analysis:
 
```

## task-c/openfoam/task-08

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given an airfoil template `/home/user/Desktop/airfoil_base/`.
-Complete a steady airfoil external-flow analysis from the command line:
+Complete a steady airfoil external-flow analysis:
 
```

## task-c/openfoam/task-09

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a heat-conduction template `/home/user/Desktop/heat_base/`.
-Complete a steady thermal analysis from the command line:
+Complete a steady thermal analysis:
 
```

## task-c/openfoam/task-10

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a buoyancy-driven template `/home/user/Desktop/buoyant_base/`.
-Complete a natural-convection cavity analysis from the command line:
+Complete a natural-convection cavity analysis:
 
```

## task-c/openfoam/task-11

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a cavity template `/home/user/Desktop/cavity_base/`.
-Complete a parametric Reynolds-number sweep from the command line:
+Complete a parametric Reynolds-number sweep:
 
```

## task-c/openfoam/task-12

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a pipe template `/home/user/Desktop/pipe_base/`.
-Complete a parallel-computing task from the command line:
+Complete a parallel-computing task:
 
```

## task-c/openfoam/task-13

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a cylinder crossflow template `/home/user/Desktop/cylinder_base/`.
-Implement online force-coefficient monitoring during the solve from the command line:
+Implement online force-coefficient monitoring during the solve:
 
```

## task-c/openfoam/task-14

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a `snappyHexMesh` template `/home/user/Desktop/snappy_base/`.
-Complete unstructured mesh generation and simulation from the command line:
+Complete unstructured mesh generation and simulation:
 
```

## task-c/openfoam/task-15

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a damBreak template `/home/user/Desktop/damBreak_base/`.
-Complete a tank sloshing analysis from the command line:
+Complete a tank sloshing analysis:
 
```

## task-c/openfoam/task-16

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a shock-tube template `/home/user/Desktop/shockTube_base/`.
-Complete a compressible shock-tube analysis from the command line:
+Complete a compressible shock-tube analysis:
 
```

## task-c/openfoam/task-18

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a cavity template `/home/user/Desktop/cavity_base/`.
-Complete field-data sampling from the command line:
+Complete field-data sampling:
 
```

## task-c/openfoam/task-19

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a porous-medium template `/home/user/Desktop/porous_base/`.
-Complete porous-zone flow analysis from the command line:
+Complete porous-zone flow analysis:
 
```

## task-c/openfoam/task-20

```diff
--- before
+++ after
@@ -1,3 +1,3 @@
 You are given a dynamic-mesh template `/home/user/Desktop/dynamic_base/`.
-Complete rigid-body-motion dynamic-mesh analysis from the command line:
+Complete rigid-body-motion dynamic-mesh analysis:
 
```

## task-c/openscad/task-21

```diff
--- before
+++ after
@@ -1 +1 @@
-In a command-line environment, operate on /home/user/Desktop/task-021_initial.scad. Use OpenSCAD command-line parameters or edit the source so width=90, depth=70, back_height=80, and slot_width=12. Export the modified CAD model as /home/user/Desktop/task-021_output.stl. The task is to generate the modified model, not to submit a new script file.
+Operate on /home/user/Desktop/task-021_initial.scad. Use OpenSCAD command-line parameters or edit the source so width=90, depth=70, back_height=80, and slot_width=12. Export the modified CAD model as /home/user/Desktop/task-021_output.stl. The task is to generate the modified model, not to submit a new script file.
```

## task-c/openscad/task-25

```diff
--- before
+++ after
@@ -1 +1 @@
-Edit /home/user/Desktop/task-025_initial.scad from the command line. Change $fn to 96 and ribs to 24. Keep outside diameter 38 mm, height 16 mm, and center hole diameter 6 mm unchanged. Export /home/user/Desktop/task-025_output.stl using the command line.
+Edit /home/user/Desktop/task-025_initial.scad. Change $fn to 96 and ribs to 24. Keep outside diameter 38 mm, height 16 mm, and center hole diameter 6 mm unchanged. Export /home/user/Desktop/task-025_output.stl using the command line.
```

## task-c/openscad/task-26

```diff
--- before
+++ after
@@ -1 +1 @@
-Use /home/user/Desktop/task-026_initial.scad and /home/user/Desktop/task-026_profile.dxf from the command line. Do not modify the DXF profile. In the SCAD file, import the profile and linear_extrude it to 6 mm thickness, then add one centered through hole of diameter 10 mm. Export /home/user/Desktop/task-026_output.stl.
+Use /home/user/Desktop/task-026_initial.scad and /home/user/Desktop/task-026_profile.dxf. Do not modify the DXF profile. In the SCAD file, import the profile and linear_extrude it to 6 mm thickness, then add one centered through hole of diameter 10 mm. Export /home/user/Desktop/task-026_output.stl.
```

## task-c/openscad/task-27

```diff
--- before
+++ after
@@ -1 +1 @@
-Process /home/user/Desktop/task-027_initial.scad from the command line. Import /home/user/Desktop/task-027_seed.stl, scale the imported mesh by x=1.5, y=1.0, and z=2.0, then subtract a centered vertical through hole of diameter 6 mm. Export /home/user/Desktop/task-027_output.stl.
+Process /home/user/Desktop/task-027_initial.scad. Import /home/user/Desktop/task-027_seed.stl, scale the imported mesh by x=1.5, y=1.0, and z=2.0, then subtract a centered vertical through hole of diameter 6 mm. Export /home/user/Desktop/task-027_output.stl.
```

## task-c/openscad/task-29

```diff
--- before
+++ after
@@ -1 +1 @@
-Edit /home/user/Desktop/task-029_initial.scad from the command line. On the side plate, add eight equally spaced snap tabs. Each tab must be 8 x 6 x 3 mm, distributed along X with first and last centers at x=-42 and x=42, y=23. Under each tab, use difference() to make a 5 x 2 mm release slot. Export /home/user/Desktop/task-029_output.stl.
+Edit /home/user/Desktop/task-029_initial.scad. On the side plate, add eight equally spaced snap tabs. Each tab must be 8 x 6 x 3 mm, distributed along X with first and last centers at x=-42 and x=42, y=23. Under each tab, use difference() to make a 5 x 2 mm release slot. Export /home/user/Desktop/task-029_output.stl.
```

## task-c/openscad/task-30

```diff
--- before
+++ after
@@ -1 +1 @@
-From the command line, set label_text to "A17", text size to 12 mm, and raised text height to 1.5 mm, while keeping the label plate 80 x 30 x 4 mm. You may use -D 'label_text="A17"' or edit the source directly. Export /home/user/Desktop/task-030_output.stl.
+Set label_text to "A17", text size to 12 mm, and raised text height to 1.5 mm, while keeping the label plate 80 x 30 x 4 mm. You may use -D 'label_text="A17"' or edit the source directly. Export /home/user/Desktop/task-030_output.stl.
```

## task-c/openscad/task-32

```diff
--- before
+++ after
@@ -1 +1 @@
-Modify /home/user/Desktop/task-032_initial.scad from the command line. Use hull() between two cylinders to create a smooth capsule-shaped mounting base. Subtract a through hole of diameter 5 mm at the center of each cylinder. Export /home/user/Desktop/task-032_output.stl.
+Modify /home/user/Desktop/task-032_initial.scad. Use hull() between two cylinders to create a smooth capsule-shaped mounting base. Subtract a through hole of diameter 5 mm at the center of each cylinder. Export /home/user/Desktop/task-032_output.stl.
```

## task-c/openscad/task-33

```diff
--- before
+++ after
@@ -1 +1 @@
-Modify /home/user/Desktop/task-033_initial.scad from the command line. Use minkowski() or an equivalent method to add about 3 mm outside corner rounding to the box, then subtract an internal cavity so the wall thickness is about 3 mm and the top remains open. Export /home/user/Desktop/task-033_output.stl.
+Modify /home/user/Desktop/task-033_initial.scad. Use minkowski() or an equivalent method to add about 3 mm outside corner rounding to the box, then subtract an internal cavity so the wall thickness is about 3 mm and the top remains open. Export /home/user/Desktop/task-033_output.stl.
```

## task-c/openscad/task-34

```diff
--- before
+++ after
@@ -1 +1 @@
-Edit /home/user/Desktop/task-034_initial.scad from the command line. Generate four coaxially stacked washers. Each washer must have outside diameter 24 mm, inside hole diameter 8 mm, and thickness 3 mm. Leave a 1 mm gap between adjacent washers. Export /home/user/Desktop/task-034_output.3mf.
+Edit /home/user/Desktop/task-034_initial.scad. Generate four coaxially stacked washers. Each washer must have outside diameter 24 mm, inside hole diameter 8 mm, and thickness 3 mm. Leave a 1 mm gap between adjacent washers. Export /home/user/Desktop/task-034_output.3mf.
```

## task-c/openscad/task-35

```diff
--- before
+++ after
@@ -1 +1 @@
-Modify /home/user/Desktop/task-035_initial.scad from the command line. Import /home/user/Desktop/task-035_logo.dxf, scale the logo to approximately 30 mm width, and cut it through the center of the nameplate to make a logo cutout. Export /home/user/Desktop/task-035_output.stl.
+Modify /home/user/Desktop/task-035_initial.scad. Import /home/user/Desktop/task-035_logo.dxf, scale the logo to approximately 30 mm width, and cut it through the center of the nameplate to make a logo cutout. Export /home/user/Desktop/task-035_output.stl.
```

## task-c/openscad/task-36

```diff
--- before
+++ after
@@ -1 +1 @@
-Edit /home/user/Desktop/task-036_initial.scad from the command line. On the base plate, create a centered 3 by 2 cylindrical boss array. Each boss must be diameter 14 mm and height 10 mm, and each boss must contain a centered through hole of diameter 4 mm. The X pitch is 40 mm, the Y pitch is 45 mm, and the array must be centered. Export /home/user/Desktop/task-036_output.stl.
+Edit /home/user/Desktop/task-036_initial.scad. On the base plate, create a centered 3 by 2 cylindrical boss array. Each boss must be diameter 14 mm and height 10 mm, and each boss must contain a centered through hole of diameter 4 mm. The X pitch is 40 mm, the Y pitch is 45 mm, and the array must be centered. Export /home/user/Desktop/task-036_output.stl.
```

## task-c/openscad/task-37

```diff
--- before
+++ after
@@ -1 +1 @@
-Edit /home/user/Desktop/task-037_initial.scad from the command line. Use rotate_extrude() or an equivalent method to generate a V-groove pulley. The pulley outside diameter is 50 mm, total width 16 mm, center hole diameter 8 mm, and the circumferential center groove is a 90 degree V groove about 4 mm deep. Export /home/user/Desktop/task-037_output.stl.
+Edit /home/user/Desktop/task-037_initial.scad. Use rotate_extrude() or an equivalent method to generate a V-groove pulley. The pulley outside diameter is 50 mm, total width 16 mm, center hole diameter 8 mm, and the circumferential center groove is a 90 degree V groove about 4 mm deep. Export /home/user/Desktop/task-037_output.stl.
```

## task-c/openscad/task-38

```diff
--- before
+++ after
@@ -1 +1 @@
-Edit /home/user/Desktop/task-038_initial.scad from the command line. Add five equally spaced triangular reinforcing ribs to the right-angle bracket. Each rib must be 3 mm thick, 32 mm high, and 28 mm deep, distributed along the X direction. Export /home/user/Desktop/task-038_output.stl.
+Edit /home/user/Desktop/task-038_initial.scad. Add five equally spaced triangular reinforcing ribs to the right-angle bracket. Each rib must be 3 mm thick, 32 mm high, and 28 mm deep, distributed along the X direction. Export /home/user/Desktop/task-038_output.stl.
```

## task-c/openscad/task-39

```diff
--- before
+++ after
@@ -1 +1 @@
-Modify /home/user/Desktop/task-039_initial.scad from the command line. Use difference() between guard_blank() and the imported motor shape /home/user/Desktop/task-039_motor.stl to create a protective cover that fits around the motor. Target wall thickness is 2.5 mm. Add six diameter 3 mm ventilation holes on the side. Export /home/user/Desktop/task-039_output.stl.
+Modify /home/user/Desktop/task-039_initial.scad. Use difference() between guard_blank() and the imported motor shape /home/user/Desktop/task-039_motor.stl to create a protective cover that fits around the motor. Target wall thickness is 2.5 mm. Add six diameter 3 mm ventilation holes on the side. Export /home/user/Desktop/task-039_output.stl.
```

## task-c/openscad/task-40

```diff
--- before
+++ after
@@ -1 +1 @@
-Complete the parametric adapter plate in /home/user/Desktop/task-040_initial.scad from the command line. The outside shape is a 96 x 72 x 8 mm rounded rectangle plate with corner radius 6 mm. Add a centered through hole of diameter 32 mm. Add one group of four diameter 5 mm holes on a 60 x 40 mm rectangular pitch pattern. Add a second group of four diameter 4 mm holes on a circular pitch diameter 54 mm at angles 45, 135, 225, and 315 degrees. Export /home/user/Desktop/task-040_output.stl.
+Complete the parametric adapter plate in /home/user/Desktop/task-040_initial.scad. The outside shape is a 96 x 72 x 8 mm rounded rectangle plate with corner radius 6 mm. Add a centered through hole of diameter 32 mm. Add one group of four diameter 5 mm holes on a 60 x 40 mm rectangular pitch pattern. Add a second group of four diameter 4 mm holes on a circular pitch diameter 54 mm at angles 45, 135, 225, and 315 degrees. Export /home/user/Desktop/task-040_output.stl.
```

## task-c/ptc-creo/task-21

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to call PTC Creo and open C:\Users\Administrator\Desktop\task-21_initial.step. Uniformly scale the entire solid by a factor of 1.2 about the model origin. Do not add or remove any features after scaling. Export the resulting STEP file as C:\Users\Administrator\Desktop\task-21_output.step.
+Use PTC Creo to open C:\Users\Administrator\Desktop\task-21_initial.step. Uniformly scale the entire solid by a factor of 1.2 about the model origin. Do not add or remove any features after scaling. Export the resulting STEP file as C:\Users\Administrator\Desktop\task-21_output.step.
```

## task-c/ptc-creo/task-22

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to open C:\Users\Administrator\Desktop\task-22_initial.step in Creo. Create a 4 column by 3 row through-hole pattern. The hole diameter must be 7 mm. The first hole center must be at (40 mm, 30 mm), with X pitch 40 mm and Y pitch 30 mm. Export C:\Users\Administrator\Desktop\task-22_output.step.
+Open C:\Users\Administrator\Desktop\task-22_initial.step in Creo. Create a 4 column by 3 row through-hole pattern. The hole diameter must be 7 mm. The first hole center must be at (40 mm, 30 mm), with X pitch 40 mm and Y pitch 30 mm. Export C:\Users\Administrator\Desktop\task-22_output.step.
```

## task-c/ptc-creo/task-23

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to open C:\Users\Administrator\Desktop\task-23_initial.step in Creo. On the top surface, create a 3 by 2 set of blind rectangular lightening pockets. Each pocket must be 30 x 20 mm and 6 mm deep. The first pocket center is at (45 mm, 40 mm), with X pitch 45 mm and Y pitch 40 mm. Export C:\Users\Administrator\Desktop\task-23_output.step.
+Open C:\Users\Administrator\Desktop\task-23_initial.step in Creo. On the top surface, create a 3 by 2 set of blind rectangular lightening pockets. Each pocket must be 30 x 20 mm and 6 mm deep. The first pocket center is at (45 mm, 40 mm), with X pitch 45 mm and Y pitch 40 mm. Export C:\Users\Administrator\Desktop\task-23_output.step.
```

## task-c/ptc-creo/task-24

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to open C:\Users\Administrator\Desktop\task-24_initial.step. Add R4 mm rounds to the four vertical edges of the lower outside outline. Add 2 mm equal-distance chamfers to the four outside edges of the upper step outline. Export C:\Users\Administrator\Desktop\task-24_output.step.
+Open C:\Users\Administrator\Desktop\task-24_initial.step. Add R4 mm rounds to the four vertical edges of the lower outside outline. Add 2 mm equal-distance chamfers to the four outside edges of the upper step outline. Export C:\Users\Administrator\Desktop\task-24_output.step.
```

## task-c/ptc-creo/task-25

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to open C:\Users\Administrator\Desktop\task-25_initial.step. Convert it into an open-top box by removing the top face and shelling to a uniform 4 mm wall thickness. Then create two diameter 8 mm drain holes through the bottom plate, with hole centers at X=40 mm and X=80 mm, Y=40 mm. Export C:\Users\Administrator\Desktop\task-25_output.step.
+Open C:\Users\Administrator\Desktop\task-25_initial.step. Convert it into an open-top box by removing the top face and shelling to a uniform 4 mm wall thickness. Then create two diameter 8 mm drain holes through the bottom plate, with hole centers at X=40 mm and X=80 mm, Y=40 mm. Export C:\Users\Administrator\Desktop\task-25_output.step.
```

## task-c/ptc-creo/task-26

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to open C:\Users\Administrator\Desktop\task-26_initial.step. Place three sliders on the top surface of the guide rail. Each slider bottom face must touch the guide rail top face. The slider center X coordinates must be 50, 110, and 170 mm, and each slider Y coordinate must align with the guide rail centerline. Export C:\Users\Administrator\Desktop\task-26_output.step.
+Open C:\Users\Administrator\Desktop\task-26_initial.step. Place three sliders on the top surface of the guide rail. Each slider bottom face must touch the guide rail top face. The slider center X coordinates must be 50, 110, and 170 mm, and each slider Y coordinate must align with the guide rail centerline. Export C:\Users\Administrator\Desktop\task-26_output.step.
```

## task-c/ptc-creo/task-27

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to open C:\Users\Administrator\Desktop\task-27_initial.step. Copy the locating pin and washer to create four locating assemblies. In each set, the washer must sit on the base plate top surface and the locating pin must pass through the washer center. The four set center points must be (40,25), (200,25), (40,65), and (200,65). Export C:\Users\Administrator\Desktop\task-27_output.step.
+Open C:\Users\Administrator\Desktop\task-27_initial.step. Copy the locating pin and washer to create four locating assemblies. In each set, the washer must sit on the base plate top surface and the locating pin must pass through the washer center. The four set center points must be (40,25), (200,25), (40,65), and (200,65). Export C:\Users\Administrator\Desktop\task-27_output.step.
```

## task-c/ptc-creo/task-28

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to open C:\Users\Administrator\Desktop\task-28_initial.step. Create a central diameter 40 mm through hole. Add a coaxial top circular counterbore or step with diameter 70 mm and depth 4 mm. Add ten diameter 8 mm through holes on PCD 120 mm. Add R2 mm rounds to the upper and lower outside circular edges. Export C:\Users\Administrator\Desktop\task-28_output.step.
+Open C:\Users\Administrator\Desktop\task-28_initial.step. Create a central diameter 40 mm through hole. Add a coaxial top circular counterbore or step with diameter 70 mm and depth 4 mm. Add ten diameter 8 mm through holes on PCD 120 mm. Add R2 mm rounds to the upper and lower outside circular edges. Export C:\Users\Administrator\Desktop\task-28_output.step.
```

## task-c/ptc-creo/task-29

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to open C:\Users\Administrator\Desktop\task-29_initial.step. Create an internal grid of reinforcing ribs: two ribs in the X direction and three ribs in the Y direction. Each rib must be 4 mm thick and 20 mm high. All rib bottom faces must connect to the base plate, and the rib tops must be 5 mm below the top of the surrounding frame. Export C:\Users\Administrator\Desktop\task-29_output.step.
+Open C:\Users\Administrator\Desktop\task-29_initial.step. Create an internal grid of reinforcing ribs: two ribs in the X direction and three ribs in the Y direction. Each rib must be 4 mm thick and 20 mm high. All rib bottom faces must connect to the base plate, and the rib tops must be 5 mm below the top of the surrounding frame. Export C:\Users\Administrator\Desktop\task-29_output.step.
```

## task-c/ptc-creo/task-30

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to open C:\Users\Administrator\Desktop\task-30_initial.step. Create a rectangular sealing groove on the bottom face, centered on the cover. The groove outside outline must be 100 x 60 mm, groove width 5 mm, groove depth 3 mm, and corner radius 8 mm. Export C:\Users\Administrator\Desktop\task-30_output.step.
+Open C:\Users\Administrator\Desktop\task-30_initial.step. Create a rectangular sealing groove on the bottom face, centered on the cover. The groove outside outline must be 100 x 60 mm, groove width 5 mm, groove depth 3 mm, and corner radius 8 mm. Export C:\Users\Administrator\Desktop\task-30_output.step.
```

## task-c/ptc-creo/task-31

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to open C:\Users\Administrator\Desktop\task-31_initial.step. Create six equally spaced shallow straight grooves on the outside cylindrical surface of the handle. Each groove is axial, 4 mm wide, 2 mm deep, and 100 mm long, starting 10 mm from the left end and ending 10 mm from the right end. The six grooves must be spaced every 60 degrees around the circumference. Export C:\Users\Administrator\Desktop\task-31_output.step.
+Open C:\Users\Administrator\Desktop\task-31_initial.step. Create six equally spaced shallow straight grooves on the outside cylindrical surface of the handle. Each groove is axial, 4 mm wide, 2 mm deep, and 100 mm long, starting 10 mm from the left end and ending 10 mm from the right end. The six grooves must be spaced every 60 degrees around the circumference. Export C:\Users\Administrator\Desktop\task-31_output.step.
```

## task-c/ptc-creo/task-32

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to open C:\Users\Administrator\Desktop\task-32_initial.step. Use the plate YZ mid-plane as the mirror plane and mirror the three holes from the left half to the right half, creating six total through holes. Keep the hole diameter D9 and keep the outside outline unchanged. Export C:\Users\Administrator\Desktop\task-32_output.step.
+Open C:\Users\Administrator\Desktop\task-32_initial.step. Use the plate YZ mid-plane as the mirror plane and mirror the three holes from the left half to the right half, creating six total through holes. Keep the hole diameter D9 and keep the outside outline unchanged. Export C:\Users\Administrator\Desktop\task-32_output.step.
```

## task-c/ptc-creo/task-33

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to open C:\Users\Administrator\Desktop\task-33_initial.step. Replace the original short spacers with spacer geometry of height 20 mm while keeping each spacer X/Y size and center position unchanged. Move the clamp plate upward so its bottom face contacts the top faces of the new spacers. Export C:\Users\Administrator\Desktop\task-33_output.step.
+Open C:\Users\Administrator\Desktop\task-33_initial.step. Replace the original short spacers with spacer geometry of height 20 mm while keeping each spacer X/Y size and center position unchanged. Move the clamp plate upward so its bottom face contacts the top faces of the new spacers. Export C:\Users\Administrator\Desktop\task-33_output.step.
```

## task-c/ptc-creo/task-34

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to open C:\Users\Administrator\Desktop\task-34_initial.step. Create four diameter 10 mm base mounting holes with each hole center 20 mm from the nearest plate corner. Create a centered diameter 25 mm through hole in the vertical plate. Add three triangular gusset ribs of 6 mm thickness, distributed evenly along the X direction. Add R4 mm rounds to the outside vertical edges of the base plate. Export C:\Users\Administrator\Desktop\task-34_output.step.
+Open C:\Users\Administrator\Desktop\task-34_initial.step. Create four diameter 10 mm base mounting holes with each hole center 20 mm from the nearest plate corner. Create a centered diameter 25 mm through hole in the vertical plate. Add three triangular gusset ribs of 6 mm thickness, distributed evenly along the X direction. Add R4 mm rounds to the outside vertical edges of the base plate. Export C:\Users\Administrator\Desktop\task-34_output.step.
```

## task-c/ptc-creo/task-35

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to open C:\Users\Administrator\Desktop\task-35_initial.step. Create sixteen equally spaced rectangular radial notches around the outside circumference. Each notch must be approximately 5 mm wide along the circumference, 6 mm deep radially, and cut through the full thickness. Keep the center hole diameter 20 mm unchanged. Export C:\Users\Administrator\Desktop\task-35_output.step.
+Open C:\Users\Administrator\Desktop\task-35_initial.step. Create sixteen equally spaced rectangular radial notches around the outside circumference. Each notch must be approximately 5 mm wide along the circumference, 6 mm deep radially, and cut through the full thickness. Keep the center hole diameter 20 mm unchanged. Export C:\Users\Administrator\Desktop\task-35_output.step.
```

## task-c/ptc-creo/task-36

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to open C:\Users\Administrator\Desktop\task-36_initial.step. Install the two bearing blocks at the left and right ends of the frame so the two bearing holes are coaxial. Insert the shaft through both bearing holes with the shaft axis coincident with the bearing-hole axis, and make the shaft extend 10 mm beyond the outside face of each bearing block. Export C:\Users\Administrator\Desktop\task-36_output.step.
+Open C:\Users\Administrator\Desktop\task-36_initial.step. Install the two bearing blocks at the left and right ends of the frame so the two bearing holes are coaxial. Insert the shaft through both bearing holes with the shaft axis coincident with the bearing-hole axis, and make the shaft extend 10 mm beyond the outside face of each bearing block. Export C:\Users\Administrator\Desktop\task-36_output.step.
```

## task-c/ptc-creo/task-37

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to open C:\Users\Administrator\Desktop\task-37_initial.step. Machine the cylinder into a three-step shaft: left segment diameter 50 mm and length 40 mm, middle segment diameter 36 mm and length 80 mm, and right segment diameter 24 mm and length 40 mm. All segments must be coaxial with flat end faces. Export C:\Users\Administrator\Desktop\task-37_output.step.
+Open C:\Users\Administrator\Desktop\task-37_initial.step. Machine the cylinder into a three-step shaft: left segment diameter 50 mm and length 40 mm, middle segment diameter 36 mm and length 80 mm, and right segment diameter 24 mm and length 40 mm. All segments must be coaxial with flat end faces. Export C:\Users\Administrator\Desktop\task-37_output.step.
```

## task-c/ptc-creo/task-38

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to open C:\Users\Administrator\Desktop\task-38_initial.step. Insert the inner shaft into the outer sleeve and place them coaxially. The inner shaft must extend 20 mm beyond each end of the sleeve, and the sleeve position must remain fixed. Export C:\Users\Administrator\Desktop\task-38_output.step.
+Open C:\Users\Administrator\Desktop\task-38_initial.step. Insert the inner shaft into the outer sleeve and place them coaxially. The inner shaft must extend 20 mm beyond each end of the sleeve, and the sleeve position must remain fixed. Export C:\Users\Administrator\Desktop\task-38_output.step.
```

## task-c/ptc-creo/task-39

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to open C:\Users\Administrator\Desktop\task-39_initial.step. Create a central diameter 52 mm bearing through hole. On the top surface, create a circular locating register with diameter 80 mm and depth 4 mm. Create four corner diameter 9 mm through mounting holes, each hole center 18 mm from the two adjacent outside edges. Add R2 mm rounds to all top outside-outline edges. Export C:\Users\Administrator\Desktop\task-39_output.step.
+Open C:\Users\Administrator\Desktop\task-39_initial.step. Create a central diameter 52 mm bearing through hole. On the top surface, create a circular locating register with diameter 80 mm and depth 4 mm. Create four corner diameter 9 mm through mounting holes, each hole center 18 mm from the two adjacent outside edges. Add R2 mm rounds to all top outside-outline edges. Export C:\Users\Administrator\Desktop\task-39_output.step.
```

## task-c/ptc-creo/task-40

```diff
--- before
+++ after
@@ -1 +1 @@
-Use the command-line evaluation workflow to open C:\Users\Administrator\Desktop\task-40_initial.step and complete the full assembly. Place the cover plate above the base and align their outside-outline centers. Place four screws into the four corner mounting holes, with each screw head bottom face touching the cover top surface. Insert two locating pins into the two side locating holes, with each pin axis coaxial with its hole and the lower pin end entering the base hole by 8 mm. Export C:\Users\Administrator\Desktop\task-40_output.step.
+Open C:\Users\Administrator\Desktop\task-40_initial.step and complete the full assembly. Place the cover plate above the base and align their outside-outline centers. Place four screws into the four corner mounting holes, with each screw head bottom face touching the cover top surface. Insert two locating pins into the two side locating holes, with each pin axis coaxial with its hole and the lower pin end entering the base hole by 8 mm. Export C:\Users\Administrator\Desktop\task-40_output.step.
```

## task-v/abaqus/task-01

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE through the graphical user interface to build and solve a 2D axisymmetric finite-element model of a circular plate.
+Use Abaqus/CAE to build and solve a 2D axisymmetric finite-element model of a circular plate.
 
```

## task-v/abaqus/task-02

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE through the graphical user interface to build and solve a 2D axisymmetric finite-element model of an internally pressurized thick-walled cylinder.
+Use Abaqus/CAE to build and solve a 2D axisymmetric finite-element model of an internally pressurized thick-walled cylinder.
 
```

## task-v/abaqus/task-03

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a tensile analysis of a thin rectangular shell plate with a central circular hole.
+Use Abaqus/CAE to perform a tensile analysis of a thin rectangular shell plate with a central circular hole.
 
```

## task-v/abaqus/task-04

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE in GUI mode to complete the following task.
+Use Abaqus/CAE to complete the following task.
 
```

## task-v/abaqus/task-05

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a tensile analysis of a rectangular solid block:
+Use Abaqus/CAE to perform a tensile analysis of a rectangular solid block:
 
```

## task-v/abaqus/task-06

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a steady-state heat conduction analysis:
+Use Abaqus/CAE to perform a steady-state heat conduction analysis:
 
```

## task-v/abaqus/task-07

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a torsion analysis of a circular shaft (Variant A):
+Use Abaqus/CAE to perform a torsion analysis of a circular shaft (Variant A):
 
```

## task-v/abaqus/task-08

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to build a contact analysis assembly from scratch:
+Use Abaqus/CAE to build a contact analysis assembly from scratch:
 
@@ -24,3 +24,3 @@
 
-6. Interaction (key GUI operations):
+6. Interaction:
    - Create a General Contact (Standard) or Surface-to-Surface Contact (Standard) interaction
```

## task-v/abaqus/task-09

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a simply supported beam analysis under a uniformly distributed load:
+Use Abaqus/CAE to perform a simply supported beam analysis under a uniformly distributed load:
 
```

## task-v/abaqus/task-10

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a torsion analysis of a circular shaft (Variant B):
+Use Abaqus/CAE to perform a torsion analysis of a circular shaft (Variant B):
 
```

## task-v/abaqus/task-11

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a simply supported beam analysis under a uniformly distributed load:
+Use Abaqus/CAE to perform a simply supported beam analysis under a uniformly distributed load:
 
```

## task-v/abaqus/task-12

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a linear buckling analysis of a thin plate (Variant A):
+Use Abaqus/CAE to perform a linear buckling analysis of a thin plate (Variant A):
 
```

## task-v/abaqus/task-13

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a modal analysis of a cantilever beam (Variant A):
+Use Abaqus/CAE to perform a modal analysis of a cantilever beam (Variant A):
 
```

## task-v/abaqus/task-14

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a constrained thermal stress analysis (Case A):
+Use Abaqus/CAE to perform a constrained thermal stress analysis (Case A):
 
```

## task-v/abaqus/task-15

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a constrained thermal stress analysis (Case B):
+Use Abaqus/CAE to perform a constrained thermal stress analysis (Case B):
 
```

## task-v/abaqus/task-16

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a transient heat-transfer analysis of a rectangular solid block (Variant A):
+Use Abaqus/CAE to perform a transient heat-transfer analysis of a rectangular solid block (Variant A):
 
```

## task-v/abaqus/task-17

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a thermal stress analysis:
+Use Abaqus/CAE to perform a thermal stress analysis:
 
```

## task-v/abaqus/task-18

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a modal analysis of a cantilever beam (Variant B):
+Use Abaqus/CAE to perform a modal analysis of a cantilever beam (Variant B):
 
```

## task-v/abaqus/task-19

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a linear buckling analysis of a thin plate (Variant B):
+Use Abaqus/CAE to perform a linear buckling analysis of a thin plate (Variant B):
 
```

## task-v/abaqus/task-20

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a static tensile analysis of a thin rectangular shell plate with a central circular hole (Variant A):
+Use Abaqus/CAE to perform a static tensile analysis of a thin rectangular shell plate with a central circular hole (Variant A):
 
```

## task-v/altium-designer/task-30

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-look at `C:\Users\Administrator\Desktop\base.SchDot` in Altium Designer's Schematic Template Editor. Starting from that template, create a custom title-block template with six auto-populated fields and save it as `C:\Users\Administrator\Desktop\custom.SchDot`.
+look at `C:\Users\Administrator\Desktop\base.SchDot` in Altium Designer. Starting from that template, create a custom title-block template with six auto-populated fields and save it as `C:\Users\Administrator\Desktop\custom.SchDot`.
 
```

## task-v/ansys/task-09

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the ANSYS Fluent GUI to complete a 2D lid-driven cavity flow analysis.
+Use ANSYS Fluent to complete a 2D lid-driven cavity flow analysis.
 
```

## task-v/ansys/task-10

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the ANSYS Fluent GUI to complete a 2D laminar channel-flow analysis.
+Use ANSYS Fluent to complete a 2D laminar channel-flow analysis.
 
```

## task-v/ansys/task-11

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the ANSYS Workbench GUI to complete a nonlinear Static Structural contact analysis.
+Use ANSYS Workbench to complete a nonlinear Static Structural contact analysis.
 
```

## task-v/ansys/task-12

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the ANSYS Workbench GUI to complete a Transient Structural analysis.
+Use ANSYS Workbench to complete a Transient Structural analysis.
 
```

## task-v/ansys/task-15

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the ANSYS Fluent GUI to complete a 3D laminar pipe-flow analysis.
+Use ANSYS Fluent to complete a 3D laminar pipe-flow analysis.
 
```

## task-v/ansys/task-16

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the ANSYS Fluent GUI to complete a 2D laminar channel-flow analysis.
+Use ANSYS Fluent to complete a 2D laminar channel-flow analysis.
 
```

## task-v/ansys/task-17

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the ANSYS Fluent GUI to complete a 2D laminar Couette-flow analysis.
+Use ANSYS Fluent to complete a 2D laminar Couette-flow analysis.
 
```

## task-v/ansys/task-18

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the ANSYS Workbench GUI to complete a Static Structural analysis.
+Use ANSYS Workbench to complete a Static Structural analysis.
 
```

## task-v/ansys/task-19

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the ANSYS Workbench GUI to complete a linear eigenvalue buckling analysis.
+Use ANSYS Workbench to complete a linear eigenvalue buckling analysis.
 
```

## task-v/ansys/task-20

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the ANSYS Workbench GUI to complete a Steady-State Thermal analysis.
+Use ANSYS Workbench to complete a Steady-State Thermal analysis.
 
```

## task-v/eagle/task-28

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Open `/home/user/Desktop/stackup_seed.brd` in the EAGLE board editor. The board currently carries a simple 2-layer design-rules setup.
+Open `/home/user/Desktop/stackup_seed.brd` in EAGLE. The board currently carries a simple 2-layer design-rules setup.
 
```

## task-v/eagle/task-34

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-look at `/home/user/Desktop/board.brd` in the EAGLE board editor. The board has one 8-pin IC (IC1) placed at coordinate (30, 15) mm with rotation R0, plus three 100 nF decoupling capacitors (C3, C4, C5) that are currently in dead space far from the IC. All three caps are already netted to the VCC signal (which terminates at IC1's pad 8). Your job: use the MOVE command in the board editor to drag C3, C4, and C5 so that each cap's origin (its <element x, y> coordinate) sits within 2 mm of IC1's VCC pad (pad 8), which lies at global coordinate (26.19, 18.81) mm. You may keep or change each cap's rotation - only the origin coordinate is checked.
+look at `/home/user/Desktop/board.brd` in EAGLE. The board has one 8-pin IC (IC1) placed at coordinate (30, 15) mm with rotation R0, plus three 100 nF decoupling capacitors (C3, C4, C5) that are currently in dead space far from the IC. All three caps are already netted to the VCC signal (which terminates at IC1's pad 8). Your job: use the MOVE command in the board editor to drag C3, C4, and C5 so that each cap's origin (its <element x, y> coordinate) sits within 2 mm of IC1's VCC pad (pad 8), which lies at global coordinate (26.19, 18.81) mm. You may keep or change each cap's rotation - only the origin coordinate is checked.
 
```

## task-v/eagle/task-42

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-look at `/home/user/Desktop/multi.sch` in EAGLE's schematic editor. It's a two-sheet project:
+look at `/home/user/Desktop/multi.sch` in EAGLE. It's a two-sheet project:
 - Sheet 1 contains U1 (part BLOCK2) whose VCC pin is currently unconnected.
```

## task-v/eagle/task-49

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-look at assign.sch in EAGLE's schematic editor. The <classes> block already defines HSPEED as class number 3. Five nets are present (VCC, GND, CLK, DATA, RESET), all initially at class="0".
+look at assign.sch in EAGLE. The <classes> block already defines HSPEED as class number 3. Five nets are present (VCC, GND, CLK, DATA, RESET), all initially at class="0".
 
```

## task-v/eagle/task-50

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-look at `/home/user/Desktop/vias.brd` in the EAGLE board editor. The board contains 8 vias, all drilled to `0.3 mm`. Shrink the three vias listed in `/home/user/Desktop/targets.txt` to `0.2 mm` drill and save the result as `/home/user/Desktop/answer.brd`.
+look at `/home/user/Desktop/vias.brd` in EAGLE. The board contains 8 vias, all drilled to `0.3 mm`. Shrink the three vias listed in `/home/user/Desktop/targets.txt` to `0.2 mm` drill and save the result as `/home/user/Desktop/answer.brd`.
 
```

## task-v/freecad/task-01

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-1_input.step in the FreeCAD GUI. Keep the rectangular plate outer size, thickness, and coordinate frame unchanged. Create one vertical through hole at the geometric center of the plate, centered at X=60 mm and Y=40 mm, with the hole axis along Z and diameter 20 mm through the full 10 mm thickness. Export only the final solid as freecad_task-1_output.step. Do not create images, PDFs, CSV files, JSON files, or other extra outputs.
+look at freecad_task-1_input.step in FreeCAD. Keep the rectangular plate outer size, thickness, and coordinate frame unchanged. Create one vertical through hole at the geometric center of the plate, centered at X=60 mm and Y=40 mm, with the hole axis along Z and diameter 20 mm through the full 10 mm thickness. Export only the final solid as freecad_task-1_output.step. Do not create images, PDFs, CSV files, JSON files, or other extra outputs.
```

## task-v/freecad/task-02

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-2_input.step in the FreeCAD GUI. Keep the L-shaped bracket base plate and vertical plate dimensions unchanged. Add two horizontal through holes in the vertical plate with axes along the Y direction. The hole centers must be (30 mm, 36 mm, 30 mm) and (70 mm, 36 mm, 30 mm), and both hole diameters must be 8 mm. Export the final bracket as freecad_task-2_output.step.
+look at freecad_task-2_input.step in FreeCAD. Keep the L-shaped bracket base plate and vertical plate dimensions unchanged. Add two horizontal through holes in the vertical plate with axes along the Y direction. The hole centers must be (30 mm, 36 mm, 30 mm) and (70 mm, 36 mm, 30 mm), and both hole diameters must be 8 mm. Export the final bracket as freecad_task-2_output.step.
```

## task-v/freecad/task-03

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-3_input.step in the FreeCAD GUI. Add four vertical cylindrical mounting posts on the top face of the base plate. Each post must have diameter 10 mm and height 16 mm, with its bottom face on Z=8 mm. The post center coordinates are (15,15), (75,15), (15,45), and (75,45). Fuse the posts with the existing base and center boss into one continuous solid, then export freecad_task-3_output.step.
+look at freecad_task-3_input.step in FreeCAD. Add four vertical cylindrical mounting posts on the top face of the base plate. Each post must have diameter 10 mm and height 16 mm, with its bottom face on Z=8 mm. The post center coordinates are (15,15), (75,15), (15,45), and (75,45). Fuse the posts with the existing base and center boss into one continuous solid, then export freecad_task-3_output.step.
```

## task-v/freecad/task-04

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-4_input.step in the FreeCAD GUI. Preserve the circular flange outside diameter, thickness, and existing center bore. On a bolt circle of radius 38 mm around the flange center, create six equally spaced vertical through holes of diameter 8 mm, with the first hole on the global +X direction and the others every 60 degrees. Export the resulting flange as freecad_task-4_output.step.
+look at freecad_task-4_input.step in FreeCAD. Preserve the circular flange outside diameter, thickness, and existing center bore. On a bolt circle of radius 38 mm around the flange center, create six equally spaced vertical through holes of diameter 8 mm, with the first hole on the global +X direction and the others every 60 degrees. Export the resulting flange as freecad_task-4_output.step.
```

## task-v/freecad/task-05

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-5_input.step in the FreeCAD GUI. Add 5 mm fillets or equivalent rounded edges to the four vertical outside edges of the rectangular base. Add 3 mm fillets or equivalent rounded edges to the upper outside edges of both square top bosses. Do not move the base or bosses and do not add holes. Export the final solid as freecad_task-5_output.step.
+look at freecad_task-5_input.step in FreeCAD. Add 5 mm fillets or equivalent rounded edges to the four vertical outside edges of the rectangular base. Add 3 mm fillets or equivalent rounded edges to the upper outside edges of both square top bosses. Do not move the base or bosses and do not add holes. Export the final solid as freecad_task-5_output.step.
```

## task-v/freecad/task-06

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-6_input.step in the FreeCAD GUI. Add two coaxial cylindrical collars to the shaft and fuse them to the original shaft. The left collar center is at X=30 mm, the right collar center is at X=90 mm, each collar is 10 mm wide along X, and each has outside diameter 40 mm. Keep the original 120 mm shaft length unchanged. Export freecad_task-6_output.step.
+look at freecad_task-6_input.step in FreeCAD. Add two coaxial cylindrical collars to the shaft and fuse them to the original shaft. The left collar center is at X=30 mm, the right collar center is at X=90 mm, each collar is 10 mm wide along X, and each has outside diameter 40 mm. Keep the original 120 mm shaft length unchanged. Export freecad_task-6_output.step.
```

## task-v/freecad/task-07

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-7_input.step in the FreeCAD GUI. Create four vertical through holes of diameter 6 mm in the thin cover plate. The hole centers must be 15 mm from the adjacent outside edges, at (15,15), (145,15), (15,85), and (145,85). Keep the 160 x 100 x 6 mm outside envelope unchanged and export freecad_task-7_output.step.
+look at freecad_task-7_input.step in FreeCAD. Create four vertical through holes of diameter 6 mm in the thin cover plate. The hole centers must be 15 mm from the adjacent outside edges, at (15,15), (145,15), (15,85), and (145,85). Keep the 160 x 100 x 6 mm outside envelope unchanged and export freecad_task-7_output.step.
```

## task-v/freecad/task-08

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-8_input.step in the FreeCAD GUI. From the top face, cut a centered rectangular pocket opening of size 80 x 40 mm. The pocket center is at (60,40), the cut depth is 45 mm, and the bottom floor must remain 5 mm thick. The outside size must remain 120 x 80 x 50 mm. Export the open box as freecad_task-8_output.step.
+look at freecad_task-8_input.step in FreeCAD. From the top face, cut a centered rectangular pocket opening of size 80 x 40 mm. The pocket center is at (60,40), the cut depth is 45 mm, and the bottom floor must remain 5 mm thick. The outside size must remain 120 x 80 x 50 mm. Export the open box as freecad_task-8_output.step.
```

## task-v/freecad/task-09

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-9_input.step in the FreeCAD GUI. Add three triangular reinforcing ribs on the top face of the base and fuse them to the base. Each rib is a right-triangular prism, 6 mm thick along Y, 30 mm high, and 24 mm long at the base. The rib center X positions are 35, 70, and 105 mm, the rib mid-plane is Y=15 mm, and the rib bottom touches Z=8 mm. Export freecad_task-9_output.step.
+look at freecad_task-9_input.step in FreeCAD. Add three triangular reinforcing ribs on the top face of the base and fuse them to the base. Each rib is a right-triangular prism, 6 mm thick along Y, 30 mm high, and 24 mm long at the base. The rib center X positions are 35, 70, and 105 mm, the rib mid-plane is Y=15 mm, and the rib bottom touches Z=8 mm. Export freecad_task-9_output.step.
```

## task-v/freecad/task-10

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-10_input.step in the FreeCAD GUI. In the annular ring, cut a rectangular side notch on the +X side. The notch is 18 mm wide along Y, extends from X=20 mm to X=40 mm, and cuts through the full 8 mm thickness. Preserve the center hole and remaining ring geometry. Export freecad_task-10_output.step.
+look at freecad_task-10_input.step in FreeCAD. In the annular ring, cut a rectangular side notch on the +X side. The notch is 18 mm wide along Y, extends from X=20 mm to X=40 mm, and cuts through the full 8 mm thickness. Preserve the center hole and remaining ring geometry. Export freecad_task-10_output.step.
```

## task-v/freecad/task-11

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-11_input.step in the FreeCAD GUI. Create one vertical through hole of diameter 18 mm at the center of the semicircular mounting ear. Create two additional vertical through holes of diameter 8 mm in the rectangular plate at centers (20,20) and (20,40). Export the final three-hole mounting ear as freecad_task-11_output.step.
+look at freecad_task-11_input.step in FreeCAD. Create one vertical through hole of diameter 18 mm at the center of the semicircular mounting ear. Create two additional vertical through holes of diameter 8 mm in the rectangular plate at centers (20,20) and (20,40). Export the final three-hole mounting ear as freecad_task-11_output.step.
```

## task-v/freecad/task-12

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-12_input.step in the FreeCAD GUI. Keep the original cube and create a 3 column by 2 row array of identical 12 mm cubes. The center spacing is 20 mm in X and 20 mm in Y, all cube bottom faces remain on the same Z plane, and the exported STEP may be a compound or separate solids. Export freecad_task-12_output.step.
+look at freecad_task-12_input.step in FreeCAD. Keep the original cube and create a 3 column by 2 row array of identical 12 mm cubes. The center spacing is 20 mm in X and 20 mm in Y, all cube bottom faces remain on the same Z plane, and the exported STEP may be a compound or separate solids. Export freecad_task-12_output.step.
```

## task-v/freecad/task-13

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-13_input.step in the FreeCAD GUI. Keep the first cylindrical pin fixed. Move the second pin by +25 mm along Y. Rotate the third pin 90 degrees about its own Z axis and move it so its center is at (50 mm, 25 mm, 0 mm). Export the three-pin compound as freecad_task-13_output.step.
+look at freecad_task-13_input.step in FreeCAD. Keep the first cylindrical pin fixed. Move the second pin by +25 mm along Y. Rotate the third pin 90 degrees about its own Z axis and move it so its center is at (50 mm, 25 mm, 0 mm). Export the three-pin compound as freecad_task-13_output.step.
```

## task-v/freecad/task-14

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-14_input.step in the FreeCAD GUI. Add a horizontal cylindrical crossbar between the tops of the two posts and fuse it with the posts. The crossbar axis is along X, its center height is Z=40 mm, its diameter is 10 mm, and its length is 50 mm. Export the single fused U-shaped handle as freecad_task-14_output.step.
+look at freecad_task-14_input.step in FreeCAD. Add a horizontal cylindrical crossbar between the tops of the two posts and fuse it with the posts. The crossbar axis is along X, its center height is Z=40 mm, its diameter is 10 mm, and its length is 50 mm. Export the single fused U-shaped handle as freecad_task-14_output.step.
```

## task-v/freecad/task-15

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-15_input.step in the FreeCAD GUI. Add one coaxial circular flange to each pipe end and fuse both flanges to the bent pipe. Each flange must have outside diameter 50 mm and thickness 8 mm, and each center opening must align with the pipe inside diameter. Export the double-flanged bent pipe as freecad_task-15_output.step.
+look at freecad_task-15_input.step in FreeCAD. Add one coaxial circular flange to each pipe end and fuse both flanges to the bent pipe. Each flange must have outside diameter 50 mm and thickness 8 mm, and each center opening must align with the pipe inside diameter. Export the double-flanged bent pipe as freecad_task-15_output.step.
```

## task-v/freecad/task-16

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-16_input.step in the FreeCAD GUI. For each support post, create one coaxial blind hole from the top face downward. Each blind hole has diameter 3 mm and depth 8 mm and must not pass through the base plate. Export the part with four blind holes as freecad_task-16_output.step.
+look at freecad_task-16_input.step in FreeCAD. For each support post, create one coaxial blind hole from the top face downward. Each blind hole has diameter 3 mm and depth 8 mm and must not pass through the base plate. Export the part with four blind holes as freecad_task-16_output.step.
```

## task-v/freecad/task-17

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-17_input.step in the FreeCAD GUI. Cut a rectangular keyway along the top of the shaft from X=20 mm to X=80 mm. The keyway is 8 mm wide along Y, 5 mm deep along Z, and centered on the shaft Y=0 plane. Export the keyed shaft as freecad_task-17_output.step.
+look at freecad_task-17_input.step in FreeCAD. Cut a rectangular keyway along the top of the shaft from X=20 mm to X=80 mm. The keyway is 8 mm wide along Y, 5 mm deep along Z, and centered on the shaft Y=0 plane. Export the keyed shaft as freecad_task-17_output.step.
```

## task-v/freecad/task-18

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-18_input.step in the FreeCAD GUI. Cut a dovetail slot through the full 80 mm length along X. The slot is centered at Y=20 mm on the top face, has top opening width 26 mm, bottom width 16 mm, and depth 10 mm. Export the dovetail block as freecad_task-18_output.step.
+look at freecad_task-18_input.step in FreeCAD. Cut a dovetail slot through the full 80 mm length along X. The slot is centered at Y=20 mm on the top face, has top opening width 26 mm, bottom width 16 mm, and depth 10 mm. Export the dovetail block as freecad_task-18_output.step.
```

## task-v/freecad/task-19

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-19_input.step in the FreeCAD GUI. Add two rectangular mounting ears to the two ends of the straight bottom edge of the guard and fuse them to the guard. Each ear is 20 x 18 x 6 mm and contains one centered vertical through hole of diameter 6 mm. Export freecad_task-19_output.step.
+look at freecad_task-19_input.step in FreeCAD. Add two rectangular mounting ears to the two ends of the straight bottom edge of the guard and fuse them to the guard. Each ear is 20 x 18 x 6 mm and contains one centered vertical through hole of diameter 6 mm. Export freecad_task-19_output.step.
```

## task-v/freecad/task-20

```diff
--- before
+++ after
@@ -1 +1 @@
-look at freecad_task-20_input.step in the FreeCAD GUI. Move the upright support to the center of the base plate top face so the support bottom touches the base top, with the support center at (60,30). Fuse the support and base into one solid. Cut one through hole of diameter 10 mm through the support along the Y direction. Export freecad_task-20_output.step.
+look at freecad_task-20_input.step in FreeCAD. Move the upright support to the center of the base plate top face so the support bottom touches the base top, with the support center at (60,30). Fuse the support and base into one solid. Cut one through hole of diameter 10 mm through the support along the Y direction. Export freecad_task-20_output.step.
```

## task-v/librecad/task-01

```diff
--- before
+++ after
@@ -1 +1 @@
-look at /home/user/Desktop/gui01_room_outline_seed.dxf in the LibreCAD graphical interface. Use the four guide corner points in the file to draw a 6000 mm by 4000 mm room outside outline as a closed rectangle on layer WALL. Draw one interior partition wall line on layer WALL from (3000,0) to (3000,4000). Leave a 900 mm door opening centered on the bottom wall by breaking or deleting the wall segment from x=2550 to x=3450. On layer DOOR, add a 900 mm door leaf line and a 90 degree door swing arc. Save the result as /home/user/Desktop/gui01_room_outline_completed.dxf.
+look at /home/user/Desktop/gui01_room_outline_seed.dxf in LibreCAD. Use the four guide corner points in the file to draw a 6000 mm by 4000 mm room outside outline as a closed rectangle on layer WALL. Draw one interior partition wall line on layer WALL from (3000,0) to (3000,4000). Leave a 900 mm door opening centered on the bottom wall by breaking or deleting the wall segment from x=2550 to x=3450. On layer DOOR, add a 900 mm door leaf line and a 90 degree door swing arc. Save the result as /home/user/Desktop/gui01_room_outline_completed.dxf.
```

## task-v/openscad/task-01

```diff
--- before
+++ after
@@ -1 +1 @@
-look at task-001_initial.scad in the OpenSCAD GUI editor. Change the base parameters to width=80, depth=50, and height=10, and keep the model centered at the origin. Press F5 to preview and confirm there is no syntax error, then press F6 to fully render. Use File -> Export -> Export as STL and save exactly task-001_output.stl. Do not create PNG, PDF, CSV, JSON, or any other extra output.
+look at task-001_initial.scad in OpenSCAD. Change the base parameters to width=80, depth=50, and height=10, and keep the model centered at the origin. Save as STL named task-001_output.stl. Do not create PNG, PDF, CSV, JSON, or any other extra output.
```

## task-v/openscad/task-09

```diff
--- before
+++ after
@@ -1 +1 @@
-look at task-009_initial.scad. In the 2D sketch, add two circular holes of diameter 8 mm centered at (-40,0) and (40,0). Add one centered rectangular window 60 mm by 20 mm. Do not use linear_extrude; keep the top-level object as a 2D model. Export a DXF from the GUI and save it as task-009_output.dxf.
+look at task-009_initial.scad. In the 2D sketch, add two circular holes of diameter 8 mm centered at (-40,0) and (40,0). Add one centered rectangular window 60 mm by 20 mm. Do not use linear_extrude; keep the top-level object as a 2D model. Save as DXF named task-009_output.dxf.
```

## task-v/sketchup/task-01

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Using SketchUp's GUI, build a dining table and export it as a COLLADA DAE. There is no initial file - model the table from scratch.
+Using SketchUp, build a dining table and export it as a COLLADA DAE. There is no initial file - model the table from scratch.
 
```

## task-v/sketchup/task-02

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Using SketchUp's GUI, build a curved wall and export it as a COLLADA DAE. There is no initial file - model the wall from scratch.
+Using SketchUp, build a curved wall and export it as a COLLADA DAE. There is no initial file - model the wall from scratch.
 
```

## task-v/sketchup/task-03

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Using SketchUp's GUI, build a ceiling-mounted pendant light fixture with three arms radiating from a central hub and export it as a COLLADA DAE. There is no initial file - model the fixture from scratch.
+Using SketchUp, build a ceiling-mounted pendant light fixture with three arms radiating from a central hub and export it as a COLLADA DAE. There is no initial file - model the fixture from scratch.
 
```

## task-v/sketchup/task-04

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Using SketchUp's GUI, build an L-shaped staircase with a mid-height landing and export it as a COLLADA DAE. There is no initial file - model the stair from scratch.
+Using SketchUp, build an L-shaped staircase with a mid-height landing and export it as a COLLADA DAE. There is no initial file - model the stair from scratch.
 
```

## task-v/sketchup/task-05

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Using SketchUp's GUI, model a chair frame and export it as COLLADA DAE (`C:\Users\Administrator\Desktop\output.dae`). No initial file is provided.
+Using SketchUp, model a chair frame and export it as COLLADA DAE (`C:\Users\Administrator\Desktop\output.dae`). No initial file is provided.
 
```

## task-v/sketchup/task-06

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Using SketchUp's GUI, model a hollow vase produced by revolving a smooth vase silhouette around the Z-axis and giving it a 5 mm wall thickness with an open top. Export the result as a binary STL. No initial file is provided.
+Using SketchUp, model a hollow vase produced by revolving a smooth vase silhouette around the Z-axis and giving it a 5 mm wall thickness with an open top. Export the result as a binary STL. No initial file is provided.
 
```

## task-v/sketchup/task-07

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Using SketchUp's GUI, model a flat perforated screen panel and export it as a binary STL. No initial file is provided.
+Using SketchUp, model a flat perforated screen panel and export it as a binary STL. No initial file is provided.
 
```

## task-v/sketchup/task-08

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Using SketchUp's GUI, lay out a run of 8 kitchen cabinets against a 3 m wall and export it as COLLADA DAE. No initial file is provided.
+Using SketchUp, lay out a run of 8 kitchen cabinets against a 3 m wall and export it as COLLADA DAE. No initial file is provided.
 
```

## task-v/sketchup/task-09

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Using SketchUp's GUI, build a single "OfficeSet" component and instance it four times in a 2x2 grid. No initial file is provided.
+Using SketchUp, build a single "OfficeSet" component and instance it four times in a 2x2 grid. No initial file is provided.
 
```

## task-v/sketchup/task-10

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Using SketchUp's GUI, model a straight stair with railings on both sides and export as COLLADA DAE. No initial file is provided.
+Using SketchUp, model a straight stair with railings on both sides and export as COLLADA DAE. No initial file is provided.
 
```

## task-v/sketchup/task-13

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Using SketchUp's GUI, model a brick wall and apply the provided brick texture with the correct real-world scale.
+Using SketchUp, model a brick wall and apply the provided brick texture with the correct real-world scale.
 
```

## task-v/sketchup/task-15

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Using SketchUp's GUI, build a small landscape scene and export it as a COLLADA DAE. There is no initial file.
+Using SketchUp, build a small landscape scene and export it as a COLLADA DAE. There is no initial file.
 
```

## task-v/sketchup/task-16

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Using SketchUp's GUI, model a terraced amphitheater carved into a hillside and export it as COLLADA DAE. No initial file is provided.
+Using SketchUp, model a terraced amphitheater carved into a hillside and export it as COLLADA DAE. No initial file is provided.
 
```

## task-v/sketchup/task-17

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Using SketchUp's GUI, model a 3-panel bay window projecting from an exterior wall and export it as COLLADA DAE. No initial file.
+Using SketchUp, model a 3-panel bay window projecting from an exterior wall and export it as COLLADA DAE. No initial file.
 
```

## task-v/sketchup/task-18

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Using SketchUp's GUI, model a small greenhouse and export it as COLLADA DAE. No initial file.
+Using SketchUp, model a small greenhouse and export it as COLLADA DAE. No initial file.
 
```

## task-v/sketchup/task-19

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Using SketchUp's GUI, model a raised deck covered by a pergola and export it as COLLADA DAE. No initial file.
+Using SketchUp, model a raised deck covered by a pergola and export it as COLLADA DAE. No initial file.
 
```

## task-v/sketchup/task-20

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Using SketchUp's GUI, model a classic mansard roof over a rectangular 10 m x 6 m building and export it as COLLADA DAE. No initial file.
+Using SketchUp, model a classic mansard roof over a rectangular 10 m x 6 m building and export it as COLLADA DAE. No initial file.
 
```

## task-v/sketchup/task-22

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Using SketchUp's GUI, build a simple hand-tool kit laid out on a wooden display board, and export it as a COLLADA DAE. There is no initial file - model the assembly from scratch.
+Using SketchUp, build a simple hand-tool kit laid out on a wooden display board, and export it as a COLLADA DAE. There is no initial file - model the assembly from scratch.
 
```

## task-v/sketchup/task-23

```diff
--- before
+++ after
@@ -2,3 +2,3 @@
 
-Using SketchUp's GUI, import the low-poly scan mesh `C:\Users\Administrator\Desktop\scan.obj`, soften nearly-coplanar edges, and export the result as `C:\Users\Administrator\Desktop\output.dae`, and write `C:\Users\Administrator\Desktop\softening_report.json`.
+Using SketchUp, import the low-poly scan mesh `C:\Users\Administrator\Desktop\scan.obj`, soften nearly-coplanar edges, and export the result as `C:\Users\Administrator\Desktop\output.dae`, and write `C:\Users\Administrator\Desktop\softening_report.json`.
 
```