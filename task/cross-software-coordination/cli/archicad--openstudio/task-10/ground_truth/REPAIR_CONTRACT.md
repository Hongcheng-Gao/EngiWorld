# Task-10 repair contract

This task is evaluated as a two-stage native workflow. The BIM targets are derived from the supplied IFC, not from the former ground truth. The formal mapping is:

| Required record | Seed IfcSpace | GlobalId | IFC area (m2) |
|---|---|---|---:|
| CONSULT | CONSULT-1 | 0p_GCOHqL9O8Orvi_YQmfp | 14 |
| EQUIPMENT | LAB | 38jEfacSPBCBtDO38Sa4ab | 16 |
| ISO-CONSULT | CONSULT-2 | 2donn1s$15fQstYK6K7bhA | 14 |
| PPE-DONNING | CLEAN | 3h$isFwRP5_hw8nERq6D$D | 8 |
| CONTAMINATED-SUPPORT | DIRTY | 25gwD9sn52YxBd1q5pXbvc | 8 |

All 94 seed IfcRoot identities and all 12 spaces remain present. The five mapped spaces receive the required names, zone identity, revision, and one-way flow semantics through successful Archicad 27 IFC Command Server transactions. OpenStudio 3.10 then consumes the handoff, creates five closed spaces and distinct zones/schedules/loads, assigns outdoor air and Ideal Loads, translates to EnergyPlus 25.1 IDF, runs an annual real-weather simulation, and derives the CSV from SQLite hourly series.

CONSULT and ISO-CONSULT may instead bind distinct members of the three seed consultation spaces when the candidate's own Archicad transactions and handoff consistently declare that choice. A full alternate native run using CONSULT-3 and CONSULT-1 was accepted. The evaluator reads each target's `Pset_EngiWorld.Area` from the submitted IFC. Because the seed contains no `IfcRelSpaceBoundary` or `IfcOpeningElement` relationships and its doors/windows have no authoritative target-space containment, per-space and target-total door/window attribution is zero.

Reasonable alternate closed geometry, weather, and clinical assumptions remain valid. Fresh simulation replay uses the same OpenStudio 3.10 workflow path as generation, verifies its pre-preprocess IDF against the submitted canonical translation, and compares all 30 chronological hourly sequences, the Errors table, and completion flags.

Official references:

- https://archicadapi.graphisoft.com/JSONInterfaceDocumentation/
- https://archicadapi.graphisoft.com/archicadPythonPackage/archicad.html
- https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcSpace.htm
- https://openstudio-sdk-documentation.s3.amazonaws.com/cpp/OpenStudio-3.10.0-doc/model/html/classopenstudio_1_1model_1_1_space.html
- https://openstudio-sdk-documentation.s3.amazonaws.com/cpp/OpenStudio-3.10.0-doc/model/html/classopenstudio_1_1model_1_1_zone_h_v_a_c_ideal_loads_air_system.html
- https://nrel.github.io/OpenStudio-user-documentation/reference/command_line_interface/
- https://bigladdersoftware.com/epx/docs/25-1/input-output-reference/group-zone-forced-air-units.html#zonehvacidealloadsairsystem
- https://www.ashrae.org/technical-resources/standards-and-guidelines/standards-addenda/standard-170-2021-ventilation-of-health-care-facilities
