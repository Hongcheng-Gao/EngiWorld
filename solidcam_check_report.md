# SolidCAM task check report

Scope: `task/task-v/solidcam/task-01` through `task-20`, then `task/task-c/solidcam/task-21` through `task-40`, checked sequentially.

Verification standard for every task: ground truth positive = true, seed negative = false, instruction-compliant sample = true.

Update: `.csv`, `.txt`, `.json`, and `.pdf` are not required as task outputs. Existing `.csv`/`.json` files under `init_file` remain only as input data when the instruction needs tool tables, hole tables, parameters, or variants.

## Records

- task-01: fixed init STEP to the instructed 100 x 60 x 12 plate; eval checks T1, S6000, F800, Z12, and top-face 100 x 60 coverage. Verification passed.
- task-02: init outer plate matches outside contour task; eval checks T1, S9000, F650, Z0, and outside boundary points. Verification passed.
- task-03: init includes four marked hole locations; eval checks T1/T2, S/F values, four hole coordinates, and through depth. Verification passed.
- task-04: init includes centered 50 x 30 pocket; eval checks pocket operation, T1, S8000, F600, Z8, and pocket boundary. Verification passed.
- task-05: init includes outside contour and four hole mouths; eval checks T2 chamfer coverage on contour and holes. Verification passed.
- task-06: init includes drill/profile features; eval checks Face, Drill, Profile, and T1/T2 usage. Verification passed.
- task-07: init rebuilt as dual-pocket bracket; eval checks rough/finish/contour terms, T1/T2, two pockets, Z6 and Z0. Verification passed.
- task-08: init includes four through holes and two stepped holes; eval checks T1/T2/T3, six positions, Z-1 and Z9. Verification passed.
- task-09: init rebuilt as cross rest pocket; eval checks rest machining, T1/T2, and Z8. Verification passed.
- task-10: init rebuilt as sheet panel with inner windows and holes; eval checks gcode, T1, inside/outside profile points, and Z0. Verification passed.
- task-11: init rebuilt as part plus vise jaws; eval checks T1, pocket points, and 3 mm fixture clearance. Verification passed.
- task-12: init includes pocket and holes for manual tool table workflow; eval checks T1-T4 and Face/Drill/Profile requirements. Verification passed.
- task-13: init rebuilt as two-part fixture for G54/G55; eval checks T1, Face/Profile, and G54/G55. Verification passed.
- task-14: init includes 12 candidate holes and risk markers; eval checks ten safe holes are present and two risky holes are absent. Verification passed.
- task-15: init includes pocket and spherical region; eval checks rough/finish, T1/T2, and required Z range. Verification passed.
- task-16: init rebuilt as stepped turning shaft with groove; eval checks turning X/Z motion and OD rough/finish/groove/center operations. Verification passed.
- task-17: init rebuilt as central pocket with four fixtures; eval checks T1/T2, Z5, and 4 mm fixture clearance. Verification passed.
- task-18: init includes six M8 pilot holes; eval checks T1/T2, six positions, Z0, and arc/helical thread milling. Verification passed.
- task-19: init remains a rotary shaft; eval checks T1, A-axis motion, and sufficient rotary toolpath moves. Verification passed.
- task-20: init rebuilt as two-sided housing with side-A holes/pocket and side-B counterbores; eval checks both side NC files. Verification passed.
- task-21: init plate and tools.csv corrected to 12 mm face mill; eval checks only the NC output. Verification passed.
- task-22: init includes centered 40 x 8 slot and 6 mm tool; eval checks only the NC output for T1, S8500, F500, Z0, and slot bounds. Verification passed.
- task-23: init uses three distinct STEP parts; eval checks only the p1/p2/p3 NC outputs. Verification passed.
- task-24: init STEP and hole table now agree on ten holes; eval checks only the NC output for coordinates and through depth. Verification passed.
- task-25: init rebuilt as multi-feature part with matching input tool library; eval checks only the NC output. Verification passed.
- task-26: init and input tools table align with pocket/drill/profile job; eval checks only the NC output. Verification passed.
- task-27: input variants file expanded from placeholder into five variants; eval checks only the five NC outputs. Verification passed.
- task-28: init rebuilt for rest machining geometry; eval checks only the NC output for T1/T2, Z6, and rest operation. Verification passed.
- task-29: init rebuilt as four-part fixture; eval checks only the NC output for G54-G57. Verification passed.
- task-30: init split into part.step and fixture.step; eval checks only the NC output. Verification passed.
- task-31: init rebuilt as 150 mm shaft family with grooves and turning tools; eval checks only the NC output. Verification passed.
- task-32: input params file expanded with operation tools/spindles/feeds; eval checks only the NC output parameters. Verification passed.
- task-33: init rebuilt with through, blind, counterbore, and threaded holes; eval checks only the NC output for required tools and arc/thread behavior. Verification passed.
- task-34: input post config expanded with program and sequence rules; eval checks only the NC output sequence numbers and program 2034. Verification passed.
- task-35: init rebuilt with 16 candidate holes and three fixture risk zones; eval checks only the NC output. Verification passed.
- task-36: revision_A and revision_B now differ in pocket size and hole positions; eval checks only the revision_B NC output. Verification passed.
- task-37: init rebuilt as two-sided part with A pocket and B counterbores; eval checks only A/B NC outputs. Verification passed.
- task-38: init rebuilt as mill-turn shaft with live milling slot and matching tools; eval checks only the NC output for C/Y-axis motion. Verification passed.
- task-39: init rebuilt as simplified six-blade impeller; eval checks only the NC output for A-axis multi-axis motion. Verification passed.
- task-40: init rebuilt as final benchmark assembly with fixtures, pockets, holes, counterbores, and spherical region; eval checks only the NC output. Verification passed.

Final audit: 40/40 ground-truth positives passed; no `.csv`, `.txt`, `.json`, or `.pdf` files remain as ground-truth outputs; no `eval-windows.py`, `eval-ubuntu.py`, `*-windows.json`, or `*-ubuntu.json` files remain in the SolidCAM task directories.
