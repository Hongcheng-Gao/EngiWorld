# Task-10 instance cleanup

Cleanup was performed after native generation and Windows validation on the
`cli3-revit2025-archicad27-openstudio310-win` instance.

Removed task-created paths:

- `C:\Users\user\Desktop\EW3B10-work`
- `C:\Users\user\Documents\EngiWorld-task-10-work`
- `C:\Users\user\Documents\EngiWorld-task-10-build`
- `C:\Users\user\Documents\EW3B10-validation`
- `C:\Users\user\Documents\EW3B10-neg-osm`
- `C:\Users\user\Documents\EW3B10-neg-sql`
- `C:\Users\user\Documents\EW3B10-neg-log`
- `C:\EW3B10DB`
- `C:\EW3B10PROBE`
- `C:\EW3B10-server-out.txt`
- `C:\EW3B10-server-err.txt`
- the temporary Revit add-in manifest/directory under
  `C:\ProgramData\Autodesk\Revit\Addins\2025`

The final structured check returned empty arrays for remaining paths, matching
TEMP entries, Revit/Archicad/IFCCommandServer/OpenStudio/EnergyPlus processes,
and TCP listeners on port 19740.
