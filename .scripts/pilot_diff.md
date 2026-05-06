# Pilot instruction cleanup diff (DRY-RUN)


_Total: changed=80, unchanged=0, apply=NO (dry-run)_


## task-c/abaqus/task-01

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to build and solve a 2D axisymmetric finite-element model of a circular plate.
+Build and solve a 2D axisymmetric finite-element model of a circular plate.
 
```


## task-c/abaqus/task-02

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to build and solve a 2D axisymmetric finite-element model of an internally pressurized thick-walled cylinder.
+Build and solve a 2D axisymmetric finite-element model of an internally pressurized thick-walled cylinder.
 
```


## task-c/abaqus/task-03

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a tensile analysis of a thin rectangular shell plate with a central circular hole.
+Perform a tensile analysis of a thin rectangular shell plate with a central circular hole.
 
```


## task-c/abaqus/task-04

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to complete the following task.
+Complete the following task.
 
```


## task-c/abaqus/task-05

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a tensile analysis of a rectangular solid block:
+Perform a tensile analysis of a rectangular solid block:
 
```


## task-c/abaqus/task-06

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a steady-state heat conduction analysis:
+Perform a steady-state heat conduction analysis:
 
```


## task-c/abaqus/task-07

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a torsion analysis of a circular shaft (Variant A):
+Perform a torsion analysis of a circular shaft (Variant A):
 
```


## task-c/abaqus/task-08

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to build a contact analysis assembly from scratch:
+Build a contact analysis assembly from scratch:
 
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
+Perform a simply supported beam analysis under a uniformly distributed load:
 
```


## task-c/abaqus/task-10

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a torsion analysis of a circular shaft (Variant B):
+Perform a torsion analysis of a circular shaft (Variant B):
 
```


## task-c/abaqus/task-11

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a simply supported beam analysis under a uniformly distributed load:
+Perform a simply supported beam analysis under a uniformly distributed load:
 
```


## task-c/abaqus/task-12

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a linear buckling analysis of a thin plate (Variant A):
+Perform a linear buckling analysis of a thin plate (Variant A):
 
```


## task-c/abaqus/task-13

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a modal analysis of a cantilever beam (Variant A):
+Perform a modal analysis of a cantilever beam (Variant A):
 
```


## task-c/abaqus/task-14

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a constrained thermal stress analysis (Case A):
+Perform a constrained thermal stress analysis (Case A):
 
```


## task-c/abaqus/task-15

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a constrained thermal stress analysis (Case B):
+Perform a constrained thermal stress analysis (Case B):
 
```


## task-c/abaqus/task-16

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a transient heat-transfer analysis of a rectangular solid block (Variant A):
+Perform a transient heat-transfer analysis of a rectangular solid block (Variant A):
 
```


## task-c/abaqus/task-17

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a thermal stress analysis:
+Perform a thermal stress analysis:
 
```


## task-c/abaqus/task-18

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a modal analysis of a cantilever beam (Variant B):
+Perform a modal analysis of a cantilever beam (Variant B):
 
```


## task-c/abaqus/task-19

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a linear buckling analysis of a thin plate (Variant B):
+Perform a linear buckling analysis of a thin plate (Variant B):
 
```


## task-c/abaqus/task-20

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE via the Command Line Interface (CLI) to perform a static tensile analysis of a thin rectangular shell plate with a central circular hole (Variant A):
+Perform a static tensile analysis of a thin rectangular shell plate with a central circular hole (Variant A):
 
```


## task-c/autocad/task-21

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\cli_blank_seed.dxf. Recreate the target 2D CAD drawing for task 21 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\cli_blank_seed.dxf. Recreate the target 2D CAD drawing for task 21 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-c/autocad/task-22

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\inspect_me.dxf. Recreate the target 2D CAD drawing for task 22 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\inspect_me.dxf. Recreate the target 2D CAD drawing for task 22 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-c/autocad/task-23

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\plate_raw.dxf. Recreate the target 2D CAD drawing for task 23 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\plate_raw.dxf. Recreate the target 2D CAD drawing for task 23 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-c/autocad/task-24

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\inch_valve.dxf. Recreate the target 2D CAD drawing for task 24 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\inch_valve.dxf. Recreate the target 2D CAD drawing for task 24 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-c/autocad/task-25

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\bracket_seed.dxf. Recreate the target 2D CAD drawing for task 25 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\bracket_seed.dxf. Recreate the target 2D CAD drawing for task 25 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-c/autocad/task-26

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\base.dxf, C:\Users\Administrator\Desktop\slider.dxf, C:\Users\Administrator\Desktop\pin.dxf, C:\Users\Administrator\Desktop\cover.dxf. Recreate the target 2D CAD drawing for task 26 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\base.dxf, C:\Users\Administrator\Desktop\slider.dxf, C:\Users\Administrator\Desktop\pin.dxf, C:\Users\Administrator\Desktop\cover.dxf. Recreate the target 2D CAD drawing for task 26 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-c/autocad/task-27

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\surface_leak.dxf. Recreate the target 2D CAD drawing for task 27 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\surface_leak.dxf. Recreate the target 2D CAD drawing for task 27 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-c/autocad/task-28

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\profile_seed.dxf. Recreate the target 2D CAD drawing for task 28 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\profile_seed.dxf. Recreate the target 2D CAD drawing for task 28 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-c/autocad/task-29

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\segmented_flange.dxf. Recreate the target 2D CAD drawing for task 29 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\segmented_flange.dxf. Recreate the target 2D CAD drawing for task 29 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-c/autocad/task-30

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\nozzle_seed.dxf. Recreate the target 2D CAD drawing for task 30 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\nozzle_seed.dxf. Recreate the target 2D CAD drawing for task 30 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-c/autocad/task-31

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\housing.dxf. Recreate the target 2D CAD drawing for task 31 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\housing.dxf. Recreate the target 2D CAD drawing for task 31 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-c/autocad/task-32

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\family_seed.dxf. Recreate the target 2D CAD drawing for task 32 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\family_seed.dxf. Recreate the target 2D CAD drawing for task 32 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-c/autocad/task-33

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\base.dxf, C:\Users\Administrator\Desktop\arm.dxf, C:\Users\Administrator\Desktop\bracket.dxf, C:\Users\Administrator\Desktop\pin.dxf, C:\Users\Administrator\Desktop\cap.dxf. Recreate the target 2D CAD drawing for task 33 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\base.dxf, C:\Users\Administrator\Desktop\arm.dxf, C:\Users\Administrator\Desktop\bracket.dxf, C:\Users\Administrator\Desktop\pin.dxf, C:\Users\Administrator\Desktop\cap.dxf. Recreate the target 2D CAD drawing for task 33 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-c/autocad/task-34

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\base_mm.dxf, C:\Users\Administrator\Desktop\cover_inch.dxf, C:\Users\Administrator\Desktop\pin_mirrored.dxf. Recreate the target 2D CAD drawing for task 34 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\base_mm.dxf, C:\Users\Administrator\Desktop\cover_inch.dxf, C:\Users\Administrator\Desktop\pin_mirrored.dxf. Recreate the target 2D CAD drawing for task 34 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-c/autocad/task-35

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\volume_seed.dxf. Recreate the target 2D CAD drawing for task 35 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\volume_seed.dxf. Recreate the target 2D CAD drawing for task 35 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-c/autocad/task-36

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\cast_part.dxf. Recreate the target 2D CAD drawing for task 36 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\cast_part.dxf. Recreate the target 2D CAD drawing for task 36 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-c/autocad/task-37

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\panel_layout.dxf. Recreate the target 2D CAD drawing for task 37 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\panel_layout.dxf. Recreate the target 2D CAD drawing for task 37 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-c/autocad/task-38

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\base.dxf, C:\Users\Administrator\Desktop\slider.dxf, C:\Users\Administrator\Desktop\stop1.dxf, C:\Users\Administrator\Desktop\stop2.dxf, C:\Users\Administrator\Desktop\pin.dxf. Recreate the target 2D CAD drawing for task 38 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\base.dxf, C:\Users\Administrator\Desktop\slider.dxf, C:\Users\Administrator\Desktop\stop1.dxf, C:\Users\Administrator\Desktop\stop2.dxf, C:\Users\Administrator\Desktop\pin.dxf. Recreate the target 2D CAD drawing for task 38 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-c/autocad/task-39

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\part1.dxf, C:\Users\Administrator\Desktop\part2.dxf, C:\Users\Administrator\Desktop\part3.dxf, C:\Users\Administrator\Desktop\part4.dxf. Recreate the target 2D CAD drawing for task 39 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\part1.dxf, C:\Users\Administrator\Desktop\part2.dxf, C:\Users\Administrator\Desktop\part3.dxf, C:\Users\Administrator\Desktop\part4.dxf. Recreate the target 2D CAD drawing for task 39 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-c/autocad/task-40

```diff
--- before
+++ after
@@ -1 +1 @@
-Use AutoCAD command line, Core Console, or an AutoCAD automation script. Open only the DXF file(s) from the Desktop path(s): C:\Users\Administrator\Desktop\base_bad.dxf, C:\Users\Administrator\Desktop\arm_bad.dxf, C:\Users\Administrator\Desktop\pin_bad.dxf, C:\Users\Administrator\Desktop\cap_bad.dxf. Recreate the target 2D CAD drawing for task 40 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
+Read the DXF input file(s): C:\Users\Administrator\Desktop\base_bad.dxf, C:\Users\Administrator\Desktop\arm_bad.dxf, C:\Users\Administrator\Desktop\pin_bad.dxf, C:\Users\Administrator\Desktop\cap_bad.dxf. Recreate the target 2D CAD drawing for task 40 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named C:\Users\Administrator\Desktop\autocad_result.dxf to the output folder.
```


## task-v/abaqus/task-01

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE through the graphical user interface to build and solve a 2D axisymmetric finite-element model of a circular plate.
+Build and solve a 2D axisymmetric finite-element model of a circular plate.
 
```


## task-v/abaqus/task-02

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE through the graphical user interface to build and solve a 2D axisymmetric finite-element model of an internally pressurized thick-walled cylinder.
+Build and solve a 2D axisymmetric finite-element model of an internally pressurized thick-walled cylinder.
 
```


## task-v/abaqus/task-03

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a tensile analysis of a thin rectangular shell plate with a central circular hole.
+Perform a tensile analysis of a thin rectangular shell plate with a central circular hole.
 
```


## task-v/abaqus/task-04

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use Abaqus/CAE in GUI mode to complete the following task.
+Complete the following task.
 
```


## task-v/abaqus/task-05

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a tensile analysis of a rectangular solid block:
+Perform a tensile analysis of a rectangular solid block:
 
```


## task-v/abaqus/task-06

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a steady-state heat conduction analysis:
+Perform a steady-state heat conduction analysis:
 
```


## task-v/abaqus/task-07

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a torsion analysis of a circular shaft (Variant A):
+Perform a torsion analysis of a circular shaft (Variant A):
 
```


## task-v/abaqus/task-08

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to build a contact analysis assembly from scratch:
+Build a contact analysis assembly from scratch:
 
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
+Perform a simply supported beam analysis under a uniformly distributed load:
 
```


## task-v/abaqus/task-10

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a torsion analysis of a circular shaft (Variant B):
+Perform a torsion analysis of a circular shaft (Variant B):
 
```


## task-v/abaqus/task-11

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a simply supported beam analysis under a uniformly distributed load:
+Perform a simply supported beam analysis under a uniformly distributed load:
 
```


## task-v/abaqus/task-12

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a linear buckling analysis of a thin plate (Variant A):
+Perform a linear buckling analysis of a thin plate (Variant A):
 
```


## task-v/abaqus/task-13

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a modal analysis of a cantilever beam (Variant A):
+Perform a modal analysis of a cantilever beam (Variant A):
 
```


## task-v/abaqus/task-14

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a constrained thermal stress analysis (Case A):
+Perform a constrained thermal stress analysis (Case A):
 
```


## task-v/abaqus/task-15

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a constrained thermal stress analysis (Case B):
+Perform a constrained thermal stress analysis (Case B):
 
```


## task-v/abaqus/task-16

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a transient heat-transfer analysis of a rectangular solid block (Variant A):
+Perform a transient heat-transfer analysis of a rectangular solid block (Variant A):
 
```


## task-v/abaqus/task-17

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a thermal stress analysis:
+Perform a thermal stress analysis:
 
```


## task-v/abaqus/task-18

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a modal analysis of a cantilever beam (Variant B):
+Perform a modal analysis of a cantilever beam (Variant B):
 
```


## task-v/abaqus/task-19

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a linear buckling analysis of a thin plate (Variant B):
+Perform a linear buckling analysis of a thin plate (Variant B):
 
```


## task-v/abaqus/task-20

```diff
--- before
+++ after
@@ -1,2 +1,2 @@
-Use the Abaqus/CAE GUI to perform a static tensile analysis of a thin rectangular shell plate with a central circular hole (Variant A):
+Perform a static tensile analysis of a thin rectangular shell plate with a central circular hole (Variant A):
 
```


## task-v/autocad/task-01

```diff
--- before
+++ after
@@ -1 +1 @@
-look at blank_seed.dxf. Recreate the target 2D CAD drawing for task 01 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) blank_seed.dxf. Recreate the target 2D CAD drawing for task 01 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```


## task-v/autocad/task-02

```diff
--- before
+++ after
@@ -1 +1 @@
-look at blank_seed.dxf. Recreate the target 2D CAD drawing for task 02 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) blank_seed.dxf. Recreate the target 2D CAD drawing for task 02 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```


## task-v/autocad/task-03

```diff
--- before
+++ after
@@ -1 +1 @@
-look at plate_base.dxf. Recreate the target 2D CAD drawing for task 03 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) plate_base.dxf. Recreate the target 2D CAD drawing for task 03 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```


## task-v/autocad/task-04

```diff
--- before
+++ after
@@ -1 +1 @@
-look at tilted_block.dxf. Recreate the target 2D CAD drawing for task 04 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) tilted_block.dxf. Recreate the target 2D CAD drawing for task 04 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```


## task-v/autocad/task-05

```diff
--- before
+++ after
@@ -1 +1 @@
-look at bracket_input.dxf. Recreate the target 2D CAD drawing for task 05 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) bracket_input.dxf. Recreate the target 2D CAD drawing for task 05 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```


## task-v/autocad/task-06

```diff
--- before
+++ after
@@ -1 +1 @@
-look at blank_seed.dxf. Recreate the target 2D CAD drawing for task 06 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) blank_seed.dxf. Recreate the target 2D CAD drawing for task 06 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```


## task-v/autocad/task-07

```diff
--- before
+++ after
@@ -1 +1 @@
-look at support.dxf. Recreate the target 2D CAD drawing for task 07 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) support.dxf. Recreate the target 2D CAD drawing for task 07 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```


## task-v/autocad/task-08

```diff
--- before
+++ after
@@ -1 +1 @@
-look at unit_inch_geometry.dxf. Recreate the target 2D CAD drawing for task 08 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) unit_inch_geometry.dxf. Recreate the target 2D CAD drawing for task 08 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```


## task-v/autocad/task-09

```diff
--- before
+++ after
@@ -1 +1 @@
-look at open_shell_box.dxf. Recreate the target 2D CAD drawing for task 09 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) open_shell_box.dxf. Recreate the target 2D CAD drawing for task 09 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```


## task-v/autocad/task-10

```diff
--- before
+++ after
@@ -1 +1 @@
-look at split_box.dxf. Recreate the target 2D CAD drawing for task 10 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) split_box.dxf. Recreate the target 2D CAD drawing for task 10 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```


## task-v/autocad/task-11

```diff
--- before
+++ after
@@ -1 +1 @@
-look at base.dxf, pin.dxf, cover.dxf. Recreate the target 2D CAD drawing for task 11 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) base.dxf, pin.dxf, cover.dxf. Recreate the target 2D CAD drawing for task 11 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```


## task-v/autocad/task-12

```diff
--- before
+++ after
@@ -1 +1 @@
-look at blank_seed.dxf. Recreate the target 2D CAD drawing for task 12 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) blank_seed.dxf. Recreate the target 2D CAD drawing for task 12 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```


## task-v/autocad/task-13

```diff
--- before
+++ after
@@ -1 +1 @@
-look at housing_simple.dxf. Recreate the target 2D CAD drawing for task 13 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) housing_simple.dxf. Recreate the target 2D CAD drawing for task 13 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```


## task-v/autocad/task-14

```diff
--- before
+++ after
@@ -1 +1 @@
-look at counterbore_plate.dxf. Recreate the target 2D CAD drawing for task 14 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) counterbore_plate.dxf. Recreate the target 2D CAD drawing for task 14 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```


## task-v/autocad/task-15

```diff
--- before
+++ after
@@ -1 +1 @@
-look at valve_body.dxf. Recreate the target 2D CAD drawing for task 15 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) valve_body.dxf. Recreate the target 2D CAD drawing for task 15 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```


## task-v/autocad/task-16

```diff
--- before
+++ after
@@ -1 +1 @@
-look at blank_seed.dxf. Recreate the target 2D CAD drawing for task 16 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) blank_seed.dxf. Recreate the target 2D CAD drawing for task 16 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```


## task-v/autocad/task-17

```diff
--- before
+++ after
@@ -1 +1 @@
-look at clamp_input.dxf. Recreate the target 2D CAD drawing for task 17 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) clamp_input.dxf. Recreate the target 2D CAD drawing for task 17 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```


## task-v/autocad/task-18

```diff
--- before
+++ after
@@ -1 +1 @@
-look at bracket.dxf, shaft.dxf, spacer.dxf, cap.dxf. Recreate the target 2D CAD drawing for task 18 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) bracket.dxf, shaft.dxf, spacer.dxf, cap.dxf. Recreate the target 2D CAD drawing for task 18 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```


## task-v/autocad/task-19

```diff
--- before
+++ after
@@ -1 +1 @@
-look at segmented_flange_gui.dxf. Recreate the target 2D CAD drawing for task 19 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) segmented_flange_gui.dxf. Recreate the target 2D CAD drawing for task 19 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```


## task-v/autocad/task-20

```diff
--- before
+++ after
@@ -1 +1 @@
-look at pump_housing_rotated.dxf. Recreate the target 2D CAD drawing for task 20 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
+Read the DXF input file(s) pump_housing_rotated.dxf. Recreate the target 2D CAD drawing for task 20 from the provided DXF input. Preserve the task's main geometry intent from the source case: outlines, holes, slots, alignment, symmetry, dimensions, and labels should be represented as clean DXF entities on sensible layers. Export exactly one DXF deliverable named autocad_result.dxf to the output folder.
```
