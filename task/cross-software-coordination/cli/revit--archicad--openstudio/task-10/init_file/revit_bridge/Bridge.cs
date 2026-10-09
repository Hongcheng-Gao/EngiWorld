using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using Autodesk.Revit.DB.Structure;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Events;
using BIM.IFC.Export.UI;

namespace EngiWorld.BimBridge;

public sealed class BridgeApplication : IExternalApplication
{
    private static UIControlledApplication? _controlled;
    private static bool _started;

    public Result OnStartup(UIControlledApplication application)
    {
        if (!string.Equals(Environment.GetEnvironmentVariable("ENGIWORLD_BIM_STAGE"), "revit", StringComparison.OrdinalIgnoreCase))
            return Result.Succeeded;
        _controlled = application;
        application.Idling += OnIdling;
        return Result.Succeeded;
    }

    public Result OnShutdown(UIControlledApplication application)
    {
        application.Idling -= OnIdling;
        return Result.Succeeded;
    }

    private static void OnIdling(object? sender, IdlingEventArgs args)
    {
        if (_started) return;
        _started = true;
        if (_controlled is not null) _controlled.Idling -= OnIdling;
        if (sender is not UIApplication ui) return;
        string specPath = Environment.GetEnvironmentVariable("ENGIWORLD_BIM_JOB") ?? string.Empty;
        string desktop = Path.GetDirectoryName(specPath) ?? @"C:\Users\user\Desktop";
        string errorPath = Path.Combine(desktop, "revit_bridge_error.txt");
        try { File.Delete(errorPath); Execute(ui, specPath, desktop); }
        catch (Exception ex) { File.WriteAllText(errorPath, ex.ToString(), new UTF8Encoding(false)); }
        finally { TryExit(ui); }
    }

    private static void Execute(UIApplication ui, string specPath, string desktop)
    {
        string input = Path.Combine(desktop, "init.ifc");
        string output = Path.Combine(desktop, "stage1.ifc");
        if (!File.Exists(specPath) || !File.Exists(input)) throw new FileNotFoundException("Task-10 inputs are missing.");
        WorkflowSpec spec = WorkflowSpec.Load(specPath);
        if (spec.CaseId != "multi-cli-3-revit-archicad-openstudio-task-10-windows" || spec.Revision != "EW3B10")
            throw new InvalidDataException("This bridge only accepts task-10 EW3B10.");

        Document? document = null;
        try
        {
            document = ui.Application.OpenIFCDocument(input);
            if (document is null || document.IsReadOnly) throw new InvalidOperationException("Revit did not open a writable IFC document.");
            List<CreatedRoom> rooms;
            using (Transaction tx = new(document, "EngiWorld EW3B10 three-storey stack"))
            {
                tx.Start();
                SetProjectTokens(document, spec);
                Dictionary<string, Level> levels = FindLevels(document, spec);
                EnsureSharedParameters(document, spec.ParameterNames);
                VerifySeedSlabs(document, spec);
                DeleteImportedRooms(document, spec);
                List<Wall> walls = RebuildSeedWalls(document, levels, spec);
                rooms = CreateRooms(document, levels, spec);
                CreatePitchedRoof(document, spec);
                CreateHostedFillings(document, levels, walls, spec);
                document.Regenerate();
                foreach (CreatedRoom room in rooms)
                {
                    room.AreaM2 = UnitUtils.ConvertFromInternalUnits(room.Room.Area, UnitTypeId.SquareMeters);
                    double expected = room.Spec.WidthM * room.Spec.DepthM;
                    if (room.AreaM2 <= 0 || Math.Abs(room.AreaM2 - expected) > 0.05)
                        throw new InvalidOperationException($"Room area mismatch for {room.Spec.Name}: {room.AreaM2:F6} vs {expected:F6} m2.");
                    SetArea(room.Room.LookupParameter("Qto_SpaceBaseQuantities.GrossFloorArea"), room.Room.Area);
                    SetArea(room.Room.LookupParameter("Qto_SpaceBaseQuantities.NetFloorArea"), room.Room.Area);
                }
                FailureHandlingOptions failureOptions = tx.GetFailureHandlingOptions();
                failureOptions.SetFailuresPreprocessor(new DeleteWarningsPreprocessor());
                tx.SetFailureHandlingOptions(failureOptions);
                tx.Commit();
            }

            string pset = Path.Combine(desktop, "EngiWorld_EnergyHandoff_psets.txt");
            WriteUserDefinedPset(pset, spec.ParameterNames);
            IFCExportOptions export = new() { FileVersion = IFCVersion.IFC4, SpaceBoundaryLevel = 0, WallAndColumnSplitting = false };
            IFCExportConfiguration config = IFCExportConfiguration.CreateDefaultConfiguration();
            config.IFCVersion = IFCVersion.IFC4;
            config.SpaceBoundaries = 0;
            config.ExportBaseQuantities = true;
            config.ExportUserDefinedPsets = true;
            config.ExportUserDefinedPsetsFileName = pset;
            config.StoreIFCGUID = true;
            config.UpdateOptions(export, ElementId.InvalidElementId);
            foreach ((string key, string value) in new[] {
                ("ExportBaseQuantities","true"),("ExportIFCCommonPropertySets","true"),("ExportRoomsInView","true"),
                ("ExportUserDefinedPsets","true"),("ExportUserDefinedPsetsFileName",pset),("StoreIFCGUID","true"),
                ("Use2DRoomBoundaryForVolume","true") }) export.AddOption(key, value);
            File.Delete(output);
            using (Transaction tx = new(document, "EngiWorld EW3B10 IFC4 export"))
            {
                tx.Start();
                if (!document.Export(desktop, "stage1.ifc", export)) throw new InvalidOperationException("Revit IFC export returned false.");
                tx.Commit();
            }
            if (!File.Exists(output) || new FileInfo(output).Length == 0) throw new InvalidOperationException("stage1.ifc was not created.");
            string text = File.ReadAllText(output);
            foreach (CreatedRoom room in rooms)
            {
                room.IfcGuid = FindNamedGuid(text, "IFCSPACE", room.Spec.Name);
                if (room.IfcGuid != room.Spec.IfcGuid) throw new InvalidDataException($"Revit did not retain room GlobalId for {room.Spec.Name}.");
            }
            VerifyPreservedRoots(text, spec);
            FillingGraph graph = ParseFillingGraph(text, spec);
            if (graph.Doors.Count != 3 || graph.Windows.Count != 3 || graph.Openings.Count != 6 || graph.VoidRelations.Count != 6 || graph.FillRelations.Count != 6)
                throw new InvalidDataException($"Exported filling graph mismatch: doors={graph.Doors.Count}, windows={graph.Windows.Count}, openings={graph.Openings.Count}, voids={graph.VoidRelations.Count}, fills={graph.FillRelations.Count}.");
            WriteHandoff(Path.Combine(desktop, "revit_handoff.json"), input, output, rooms, graph, spec);
        }
        finally { if (document is not null && document.IsValidObject) document.Close(false); }
    }

    private static double F(double metres) => UnitUtils.ConvertToInternalUnits(metres, UnitTypeId.Meters);

    private static void SetProjectTokens(Document document, WorkflowSpec spec)
    {
        ProjectInfo info = document.ProjectInformation;
        Set(info.get_Parameter(BuiltInParameter.PROJECT_NAME), spec.CaseId);
        Set(info.get_Parameter(BuiltInParameter.PROJECT_NUMBER), spec.Revision);
        Set(info.get_Parameter(BuiltInParameter.PROJECT_STATUS), "THREE-STOREY-STACK | GEOMETRIC-FILLINGS | PITCHED-ROOF");
    }

    private static Dictionary<string, Level> FindLevels(Document document, WorkflowSpec spec)
    {
        List<Level> all = new FilteredElementCollector(document).OfClass(typeof(Level)).Cast<Level>().ToList();
        Dictionary<string, Level> result = new(StringComparer.Ordinal);
        foreach (StoreySpec storey in spec.Storeys)
        {
            Level? level = all.OrderBy(item => Math.Abs(UnitUtils.ConvertFromInternalUnits(item.Elevation, UnitTypeId.Meters) - storey.ZM)).FirstOrDefault();
            if (level is null || Math.Abs(UnitUtils.ConvertFromInternalUnits(level.Elevation, UnitTypeId.Meters) - storey.ZM) > 0.02)
                throw new InvalidOperationException($"Missing imported level at {storey.ZM:F3} m.");
            string guid = GetIfcGuid(level);
            if (!string.IsNullOrEmpty(guid) && guid != storey.Guid)
                throw new InvalidOperationException($"Imported level GUID mismatch for {storey.Name}.");
            result[storey.Name] = level;
        }
        if (result.Values.Select(level => level.Id.Value).Distinct().Count() != 3) throw new InvalidOperationException("Storey mapping is not one-to-one.");
        return result;
    }

    private static void VerifySeedSlabs(Document document, WorkflowSpec spec)
    {
        HashSet<string> actual = new FilteredElementCollector(document).OfCategory(BuiltInCategory.OST_Floors)
            .WhereElementIsNotElementType().Select(GetIfcGuid).Where(value => !string.IsNullOrEmpty(value)).ToHashSet(StringComparer.Ordinal);
        foreach (string guid in spec.SlabGuids) if (!actual.Contains(guid)) throw new InvalidOperationException($"Seed slab missing: {guid}");
    }

    private static void DeleteImportedRooms(Document document, WorkflowSpec spec)
    {
        List<Element> rooms = new FilteredElementCollector(document).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToList();
        HashSet<string> expected = spec.Spaces.Select(space => space.IfcGuid).ToHashSet(StringComparer.Ordinal);
        HashSet<string> actual = rooms.Select(GetIfcGuid).Where(value => !string.IsNullOrEmpty(value)).ToHashSet(StringComparer.Ordinal);
        foreach (string guid in expected) if (!actual.Contains(guid)) throw new InvalidOperationException($"Seed room missing: {guid}");
        document.Delete(rooms.Select(room => room.Id).ToList());
    }

    private static List<Wall> RebuildSeedWalls(Document document, IReadOnlyDictionary<string, Level> levels, WorkflowSpec spec)
    {
        List<Element> old = new FilteredElementCollector(document).OfCategory(BuiltInCategory.OST_Walls).WhereElementIsNotElementType().ToList();
        HashSet<string> actual = old.Select(GetIfcGuid).Where(value => !string.IsNullOrEmpty(value)).ToHashSet(StringComparer.Ordinal);
        foreach (WallSeed seed in spec.Walls) if (!actual.Contains(seed.Guid)) throw new InvalidOperationException($"Seed wall missing: {seed.Guid}");
        WallType baseType = new FilteredElementCollector(document).OfClass(typeof(WallType)).Cast<WallType>()
            .First(type => type.Kind == WallKind.Basic && type.GetCompoundStructure() is not null);
        WallType type = (WallType)baseType.Duplicate("EW3B10 200mm Stack Wall");
        CompoundStructureLayer sourceLayer = baseType.GetCompoundStructure()!.GetLayers().OrderByDescending(layer => layer.Width).First();
        type.SetCompoundStructure(CompoundStructure.CreateSingleLayerCompoundStructure(MaterialFunctionAssignment.Structure, F(0.2), sourceLayer.MaterialId));
        document.Delete(old.Select(element => element.Id).ToList());
        List<Wall> result = new();
        foreach (WallSeed seed in spec.Walls)
        {
            Level level = levels[seed.Storey];
            Line axis = Line.CreateBound(new XYZ(F(seed.X1), F(seed.Y1), level.Elevation), new XYZ(F(seed.X2), F(seed.Y2), level.Elevation));
            Wall wall = Wall.Create(document, axis, type.Id, level.Id, F(3.0), 0.0, false, false);
            SetIfcGuid(wall, seed.Guid);
            wall.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)?.Set("EW3B10 ORIGINAL WALL GUID AND GEOMETRY PRESERVED");
            result.Add(wall);
        }
        document.Regenerate();
        return result;
    }

    private static List<CreatedRoom> CreateRooms(Document document, IReadOnlyDictionary<string, Level> levels, WorkflowSpec spec)
    {
        List<CreatedRoom> result = new();
        for (int index = 0; index < spec.Spaces.Count; index++)
        {
            SpaceSpec item = spec.Spaces[index];
            Level level = levels[item.Storey];
            Room room = document.Create.NewRoom(level, new UV(F(item.XM + item.WidthM / 2.0), F(item.YM + item.DepthM / 2.0)))
                ?? throw new InvalidOperationException($"Could not create Room {item.Name}.");
            Set(room.get_Parameter(BuiltInParameter.ROOM_NAME), item.Name);
            Set(room.get_Parameter(BuiltInParameter.ROOM_NUMBER), (index + 1).ToString("00", CultureInfo.InvariantCulture));
            Parameter? upperLevel = room.get_Parameter(BuiltInParameter.ROOM_UPPER_LEVEL); if (upperLevel is not null && !upperLevel.IsReadOnly) upperLevel.Set(level.Id);
            Parameter? upperOffset = room.get_Parameter(BuiltInParameter.ROOM_UPPER_OFFSET); if (upperOffset is not null && !upperOffset.IsReadOnly) upperOffset.Set(F(item.HeightM));
            Set(room.LookupParameter("ThermalZone"), item.ThermalZone);
            Set(room.LookupParameter("ScheduleCategory"), item.ScheduleCategory);
            Set(room.LookupParameter("PeoplePerM2"), item.PeoplePerM2.ToString("R", CultureInfo.InvariantCulture));
            Set(room.LookupParameter("LightingPowerDensityWPerM2"), item.LightingWPerM2.ToString("R", CultureInfo.InvariantCulture));
            Set(room.LookupParameter("EquipmentPowerDensityWPerM2"), item.EquipmentWPerM2.ToString("R", CultureInfo.InvariantCulture));
            Set(room.LookupParameter("OutdoorAirLPerSPerson"), item.OutdoorAirLPerSPerson.ToString("R", CultureInfo.InvariantCulture));
            SetIfcGuid(room, item.IfcGuid);
            result.Add(new CreatedRoom(room, item));
        }
        return result;
    }

    private static void CreatePitchedRoof(Document document, WorkflowSpec spec)
    {
        RoofSpec roof = spec.Roof;
        double x0 = F(roof.XM), x1 = F(roof.XM + roof.WidthM), y0 = F(roof.YM), y1 = F(roof.YM + roof.DepthM);
        double ridge = (y0 + y1) / 2.0, z0 = F(roof.BaseZM), z1 = F(roof.BaseZM + roof.RidgeRiseM);
        List<GeometryObject> solids = new();
        foreach ((XYZ a, XYZ b, XYZ c, XYZ d) face in new[] {
            (new XYZ(x0,y0,z0),new XYZ(x1,y0,z0),new XYZ(x1,ridge,z1),new XYZ(x0,ridge,z1)),
            (new XYZ(x0,ridge,z1),new XYZ(x1,ridge,z1),new XYZ(x1,y1,z0),new XYZ(x0,y1,z0)) })
        {
            CurveLoop loop = new(); loop.Append(Line.CreateBound(face.a, face.b)); loop.Append(Line.CreateBound(face.b, face.c));
            loop.Append(Line.CreateBound(face.c, face.d)); loop.Append(Line.CreateBound(face.d, face.a));
            solids.Add(GeometryCreationUtilities.CreateExtrusionGeometry(new List<CurveLoop> { loop }, XYZ.BasisZ, F(roof.ThicknessM)));
        }
        DirectShape shape = DirectShape.CreateElement(document, new ElementId(BuiltInCategory.OST_Roofs));
        shape.Name = "EW3B10 LEVEL 3 PITCHED ROOF"; shape.ApplicationId = spec.CaseId; shape.ApplicationDataId = spec.Revision + "-ROOF"; shape.SetShape(solids);
        SetIfcGuid(shape, roof.IfcGuid);
    }

    private static void CreateHostedFillings(Document document, IReadOnlyDictionary<string, Level> levels, IReadOnlyList<Wall> walls, WorkflowSpec spec)
    {
        string doorPath = @"C:\ProgramData\Autodesk\RVT 2025\Libraries\English\US\Doors\M_Door-Single-Panel.rfa";
        string windowPath = @"C:\ProgramData\Autodesk\RVT 2025\Libraries\English\US\Windows\M_Instance-Window-Fixed.rfa";
        if (!document.LoadFamily(doorPath, out Family doorFamily) || !document.LoadFamily(windowPath, out Family windowFamily))
            throw new InvalidOperationException("Could not load task-10 hosted families.");
        FamilySymbol baseDoor = FirstSymbol(document, doorFamily), baseWindow = FirstSymbol(document, windowFamily);
        foreach (FillingSpec item in spec.Doors)
        {
            Level level = levels[item.Storey];
            FamilySymbol symbol = (FamilySymbol)baseDoor.Duplicate($"EW3B10 {item.Name} {item.OverallWidthM * 1000:0} x {item.HeightM * 1000:0}");
            SetTypeDimension(symbol, BuiltInParameter.DOOR_WIDTH, F(item.OverallWidthM)); SetTypeDimension(symbol, BuiltInParameter.DOOR_HEIGHT, F(item.HeightM));
            if (!symbol.IsActive) symbol.Activate(); document.Regenerate();
            XYZ centre = new(F(item.XM + item.WidthM / 2.0), F(item.YM + item.DepthM / 2.0), level.Elevation + F(item.ZM));
            FamilyInstance instance = document.Create.NewFamilyInstance(centre, symbol, walls[item.HostWallIndex], level, StructuralType.NonStructural);
            instance.get_Parameter(BuiltInParameter.ALL_MODEL_MARK)?.Set(item.Name); instance.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)?.Set("GEOMETRIC-FILLINGS");
        }
        foreach (FillingSpec item in spec.Windows)
        {
            Level level = levels[item.Storey];
            FamilySymbol symbol = (FamilySymbol)baseWindow.Duplicate($"EW3B10 {item.Name} {item.OverallWidthM * 1000:0} x {item.HeightM * 1000:0}");
            SetTypeDimension(symbol, BuiltInParameter.WINDOW_WIDTH, F(item.OverallWidthM)); SetTypeDimension(symbol, BuiltInParameter.WINDOW_HEIGHT, F(item.HeightM));
            if (!symbol.IsActive) symbol.Activate(); document.Regenerate();
            XYZ centre = new(F(item.XM + item.WidthM / 2.0), F(item.YM + item.DepthM / 2.0), level.Elevation);
            FamilyInstance instance = document.Create.NewFamilyInstance(centre, symbol, walls[item.HostWallIndex], level, StructuralType.NonStructural);
            Parameter? sill = instance.get_Parameter(BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM); if (sill is not null && !sill.IsReadOnly) sill.Set(F(item.ZM));
            instance.get_Parameter(BuiltInParameter.ALL_MODEL_MARK)?.Set(item.Name); instance.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)?.Set("GEOMETRIC-FILLINGS");
        }
    }

    private static FamilySymbol FirstSymbol(Document document, Family family) => family.GetFamilySymbolIds().Select(id => document.GetElement(id)).OfType<FamilySymbol>().First();
    private static void SetTypeDimension(FamilySymbol symbol, BuiltInParameter id, double value) { Parameter? p = symbol.get_Parameter(id); if (p is not null && !p.IsReadOnly) p.Set(value); }

    private static void EnsureSharedParameters(Document document, IReadOnlyList<string> names)
    {
        Application app = document.Application; string original = app.SharedParametersFilename; string temp = Path.Combine(Path.GetTempPath(), "EngiWorld_task10_params.txt");
        File.WriteAllText(temp, "# This is a Revit shared parameter file.\r\n*META\tVERSION\tMINVERSION\r\nMETA\t2\t1\r\n", new UTF8Encoding(false));
        try
        {
            app.SharedParametersFilename = temp; DefinitionFile file = app.OpenSharedParameterFile() ?? throw new InvalidOperationException("Shared parameter file failed.");
            DefinitionGroup group = file.Groups.get_Item("EngiWorld") ?? file.Groups.Create("EngiWorld"); CategorySet categories = app.Create.NewCategorySet(); categories.Insert(document.Settings.Categories.get_Item(BuiltInCategory.OST_Rooms));
            InstanceBinding binding = app.Create.NewInstanceBinding(categories);
            foreach (string name in names) { Definition? existing = group.Definitions.get_Item(name); Definition definition = existing ?? group.Definitions.Create(new ExternalDefinitionCreationOptions(name, SpecTypeId.String.Text)); if (!document.ParameterBindings.Insert(definition, binding, GroupTypeId.Data)) document.ParameterBindings.ReInsert(definition, binding, GroupTypeId.Data); }
        }
        finally { app.SharedParametersFilename = original; File.Delete(temp); }
        string builtIn = @"C:\Program Files\Autodesk\Revit 2025\IFC Shared Parameters-RevitIFCBuiltIn_ALL.txt";
        try
        {
            app.SharedParametersFilename = builtIn; DefinitionFile file = app.OpenSharedParameterFile() ?? throw new InvalidOperationException("IFC parameters failed.");
            CategorySet categories = app.Create.NewCategorySet(); foreach (BuiltInCategory category in new[] { BuiltInCategory.OST_Rooms, BuiltInCategory.OST_Walls, BuiltInCategory.OST_Roofs }) categories.Insert(document.Settings.Categories.get_Item(category));
            InstanceBinding binding = app.Create.NewInstanceBinding(categories);
            foreach (string name in new[] { "IfcGUID", "Qto_SpaceBaseQuantities.GrossFloorArea", "Qto_SpaceBaseQuantities.NetFloorArea" })
            {
                Definition? definition = null; foreach (DefinitionGroup group in file.Groups) { definition = group.Definitions.get_Item(name); if (definition is not null) break; }
                if (definition is null) continue; if (!document.ParameterBindings.Insert(definition, binding, GroupTypeId.Data)) document.ParameterBindings.ReInsert(definition, binding, GroupTypeId.Data);
            }
        }
        finally { app.SharedParametersFilename = original; }
    }

    private static string GetIfcGuid(Element element)
    {
        foreach (string name in new[] { "IfcGUID", "IFC GUID", "GlobalId" }) { string? value = element.LookupParameter(name)?.AsString(); if (!string.IsNullOrWhiteSpace(value)) return value; }
        return string.Empty;
    }
    private static void SetIfcGuid(Element element, string guid)
    {
        foreach (string name in new[] { "IfcGUID", "IFC GUID", "GlobalId" }) { Parameter? p = element.LookupParameter(name); if (p is not null && !p.IsReadOnly && p.StorageType == StorageType.String && p.Set(guid)) return; }
        throw new InvalidOperationException($"Could not restore IFC GlobalId {guid} on {element.Category?.Name}.");
    }
    private static void Set(Parameter? p, string value) { if (p is null || p.IsReadOnly || !p.Set(value)) throw new InvalidOperationException($"Could not set parameter to {value}."); }
    private static void SetArea(Parameter? p, double value) { if (p is null || p.IsReadOnly || !p.Set(value)) throw new InvalidOperationException("Could not set IFC area quantity."); }
    private static void WriteUserDefinedPset(string path, IReadOnlyList<string> names) { StringBuilder s = new(); s.AppendLine("PropertySet:\tEngiWorld_EnergyHandoff\tI\tIfcSpace"); foreach (string name in names) s.Append('\t').Append(name).Append("\tText\t").AppendLine(name); File.WriteAllText(path, s.ToString(), new UTF8Encoding(false)); }
    private static string FindNamedGuid(string text, string cls, string name) { foreach (Match m in Regex.Matches(text, $@"{cls}\s*\(\s*'([^']+)'[^;]*;", RegexOptions.IgnoreCase | RegexOptions.Singleline)) if (m.Value.IndexOf(name, StringComparison.OrdinalIgnoreCase) >= 0) return m.Groups[1].Value; throw new InvalidDataException($"Missing {cls} named {name}."); }

    private static void VerifyPreservedRoots(string text, WorkflowSpec spec)
    {
        foreach (string guid in spec.Storeys.Select(s => s.Guid).Concat(spec.Walls.Select(w => w.Guid)).Concat(spec.SlabGuids).Concat(spec.Spaces.Select(s => s.IfcGuid)).Append(spec.Roof.IfcGuid))
            if (text.IndexOf("'" + guid + "'", StringComparison.Ordinal) < 0) throw new InvalidDataException($"Exported IFC lost required GlobalId {guid}.");
    }

    private static FillingGraph ParseFillingGraph(string text, WorkflowSpec spec)
    {
        FillingGraph graph = new(); Dictionary<string, EntityRow> entities = new();
        foreach (Match m in Regex.Matches(text, @"#(\d+)\s*=\s*(IFC[A-Z0-9_]+)\s*\(\s*'([^']+)'([^;]*);", RegexOptions.IgnoreCase | RegexOptions.Singleline))
            entities[m.Groups[1].Value] = new EntityRow(m.Groups[2].Value.ToUpperInvariant(), m.Groups[3].Value, m.Value);
        foreach (FillingSpec item in spec.Doors.Concat(spec.Windows))
        {
            string expectedClass = spec.Doors.Contains(item) ? "IFCDOOR" : "IFCWINDOW";
            List<KeyValuePair<string, EntityRow>> matches = entities.Where(pair => pair.Value.ClassName == expectedClass && pair.Value.StepText.IndexOf(item.Name, StringComparison.OrdinalIgnoreCase) >= 0).ToList();
            if (matches.Count != 1) throw new InvalidDataException($"Expected one exported {expectedClass} for {item.Name}, found {matches.Count}.");
            if (expectedClass == "IFCDOOR") graph.Doors.Add(new FillingRow(item.Name, matches[0].Value.Guid, item.Storey, spec.Walls[item.HostWallIndex].Guid));
            else graph.Windows.Add(new FillingRow(item.Name, matches[0].Value.Guid, item.Storey, spec.Walls[item.HostWallIndex].Guid));
        }
        foreach (KeyValuePair<string, EntityRow> pair in entities) if (pair.Value.ClassName == "IFCOPENINGELEMENT") graph.Openings.Add(pair.Value.Guid);
        foreach (Match m in Regex.Matches(text, @"IFCRELVOIDSELEMENT\s*\(\s*'([^']+)'[^;]*,#(\d+)\s*,\s*#(\d+)\s*\)\s*;", RegexOptions.IgnoreCase | RegexOptions.Singleline))
            if (entities.TryGetValue(m.Groups[2].Value, out EntityRow? host) && entities.TryGetValue(m.Groups[3].Value, out EntityRow? opening)) graph.VoidRelations.Add(new Relation(m.Groups[1].Value, host.Guid, opening.Guid));
        foreach (Match m in Regex.Matches(text, @"IFCRELFILLSELEMENT\s*\(\s*'([^']+)'[^;]*,#(\d+)\s*,\s*#(\d+)\s*\)\s*;", RegexOptions.IgnoreCase | RegexOptions.Singleline))
            if (entities.TryGetValue(m.Groups[2].Value, out EntityRow? opening) && entities.TryGetValue(m.Groups[3].Value, out EntityRow? filling)) graph.FillRelations.Add(new Relation(m.Groups[1].Value, opening.Guid, filling.Guid));
        HashSet<string> fillingGuids = graph.Doors.Select(x => x.ifc_guid).Concat(graph.Windows.Select(x => x.ifc_guid)).ToHashSet(StringComparer.Ordinal);
        HashSet<string> filled = graph.FillRelations.Select(x => x.second_guid).ToHashSet(StringComparer.Ordinal);
        if (!fillingGuids.SetEquals(filled)) throw new InvalidDataException("Every task filling must have exactly one exported fill relation.");
        foreach (Relation fill in graph.FillRelations)
        {
            Relation? voidRelation = graph.VoidRelations.SingleOrDefault(x => x.second_guid == fill.first_guid);
            FillingRow filling = graph.Doors.Concat(graph.Windows).Single(x => x.ifc_guid == fill.second_guid);
            if (voidRelation is null || voidRelation.first_guid != filling.host_wall_guid) throw new InvalidDataException($"Hosted opening graph mismatch for {filling.name}.");
        }
        return graph;
    }

    private static void WriteHandoff(string path, string input, string output, IReadOnlyList<CreatedRoom> rooms, FillingGraph graph, WorkflowSpec spec)
    {
        string exe = @"C:\Program Files\Autodesk\Revit 2025\Revit.exe"; FileVersionInfo version = FileVersionInfo.GetVersionInfo(exe);
        object payload = new
        {
            case_id = spec.CaseId, software_stage = "revit", source_file = "stage1.ifc", source_sha256 = Sha256(output), input_seed_sha256 = Sha256(input),
            spaces = rooms.Select(r => new { name = r.Spec.Name, ifc_guid = r.IfcGuid, retained_seed_guid = r.Spec.IfcGuid, area_m2 = Math.Round(r.AreaM2, 6), storey = r.Spec.Storey, thermal_zone = r.Spec.ThermalZone, schedule_category = r.Spec.ScheduleCategory, people_per_m2 = r.Spec.PeoplePerM2, lighting_w_per_m2 = r.Spec.LightingWPerM2, equipment_w_per_m2 = r.Spec.EquipmentWPerM2, outdoor_air_l_per_s_person = r.Spec.OutdoorAirLPerSPerson, stage = "revit" }).ToArray(),
            hosted_fillings = new { doors = graph.Doors, windows = graph.Windows, openings = graph.Openings, void_relations = graph.VoidRelations, fill_relations = graph.FillRelations },
            preserved_seed = new { storey_global_ids = spec.Storeys.ToDictionary(s => s.Name, s => s.Guid), wall_global_ids = spec.Walls.Select(w => w.Guid).ToArray(), slab_global_ids = spec.SlabGuids.ToArray(), retained_space_global_ids = spec.Spaces.Select(s => s.IfcGuid).ToArray() },
            space_boundaries = new { policy = "observe_validate_and_preserve_native_export_state", relationship_count = Regex.Matches(File.ReadAllText(output), @"\bIFCRELSPACEBOUNDARY\s*\(", RegexOptions.IgnoreCase).Count, second_level_count = Regex.Matches(File.ReadAllText(output), @"\bIFCRELSPACEBOUNDARY2NDLEVEL\s*\(", RegexOptions.IgnoreCase).Count },
            stage1_tokens = spec.Stage1Tokens.Concat(new[] { spec.CaseId }).Distinct().ToArray(), downstream_consumer = "archicad",
            native_provenance = new { exe, product_version = version.FileVersion, product_build = version.ProductVersion, automation = "EngiWorld.BimBridge IExternalApplication executed from Revit 2025 Idling", completed_utc = DateTime.UtcNow.ToString("o", CultureInfo.InvariantCulture) }
        };
        File.WriteAllText(path, JsonSerializer.Serialize(payload, new JsonSerializerOptions { WriteIndented = true }) + Environment.NewLine, new UTF8Encoding(false));
    }
    private static string Sha256(string path) { using SHA256 algorithm = SHA256.Create(); using FileStream stream = File.OpenRead(path); return Convert.ToHexString(algorithm.ComputeHash(stream)).ToLowerInvariant(); }
    private static void TryExit(UIApplication app) { try { RevitCommandId id = RevitCommandId.LookupPostableCommandId(PostableCommand.ExitRevit); if (app.CanPostCommand(id)) app.PostCommand(id); } catch { } }
}

internal sealed class DeleteWarningsPreprocessor : IFailuresPreprocessor { public FailureProcessingResult PreprocessFailures(FailuresAccessor accessor) { foreach (FailureMessageAccessor warning in accessor.GetFailureMessages()) if (warning.GetSeverity() == FailureSeverity.Warning) accessor.DeleteWarning(warning); return FailureProcessingResult.Continue; } }
internal sealed class CreatedRoom { public CreatedRoom(Room room, SpaceSpec spec) { Room = room; Spec = spec; } public Room Room { get; } public SpaceSpec Spec { get; } public double AreaM2 { get; set; } public string IfcGuid { get; set; } = string.Empty; }
internal sealed record EntityRow(string ClassName, string Guid, string StepText);
internal sealed record Relation(string relation_guid, string first_guid, string second_guid);
internal sealed record FillingRow(string name, string ifc_guid, string storey, string host_wall_guid);
internal sealed class FillingGraph { public List<FillingRow> Doors { get; } = new(); public List<FillingRow> Windows { get; } = new(); public List<string> Openings { get; } = new(); public List<Relation> VoidRelations { get; } = new(); public List<Relation> FillRelations { get; } = new(); }

internal sealed class WorkflowSpec
{
    public string CaseId { get; private set; } = ""; public string Revision { get; private set; } = ""; public List<StoreySpec> Storeys { get; } = new(); public List<string> SlabGuids { get; } = new(); public List<SpaceSpec> Spaces { get; } = new(); public List<WallSeed> Walls { get; } = new(); public List<FillingSpec> Doors { get; } = new(); public List<FillingSpec> Windows { get; } = new(); public List<string> Stage1Tokens { get; } = new(); public RoofSpec Roof { get; private set; } = new();
    public IReadOnlyList<string> ParameterNames { get; } = new[] { "ThermalZone", "ScheduleCategory", "PeoplePerM2", "LightingPowerDensityWPerM2", "EquipmentPowerDensityWPerM2", "OutdoorAirLPerSPerson" };
    public static WorkflowSpec Load(string path)
    {
        using JsonDocument json = JsonDocument.Parse(File.ReadAllText(path)); JsonElement root = json.RootElement; WorkflowSpec spec = new() { CaseId = root.GetProperty("case_id").GetString() ?? "", Revision = root.GetProperty("revision").GetString() ?? "" };
        foreach (JsonElement token in root.GetProperty("revit_stage").GetProperty("required_tokens").EnumerateArray()) spec.Stage1Tokens.Add(token.GetString() ?? "");
        Dictionary<string, string> storeyGuids = root.GetProperty("seed_preservation").GetProperty("storey_global_ids").EnumerateObject().ToDictionary(p => p.Name, p => p.Value.GetString() ?? "", StringComparer.Ordinal);
        foreach (JsonElement item in root.GetProperty("storeys").EnumerateArray()) spec.Storeys.Add(StoreySpec.Load(item, storeyGuids));
        foreach (JsonElement id in root.GetProperty("seed_preservation").GetProperty("slab_global_ids").EnumerateArray()) spec.SlabGuids.Add(id.GetString() ?? "");
        foreach (JsonElement item in root.GetProperty("seed_preservation").GetProperty("walls").EnumerateArray()) spec.Walls.Add(WallSeed.Load(item));
        foreach (JsonElement item in root.GetProperty("spaces").EnumerateArray()) spec.Spaces.Add(SpaceSpec.Load(item));
        foreach (JsonElement item in root.GetProperty("door_geometries").EnumerateArray()) spec.Doors.Add(FillingSpec.Load(item));
        foreach (JsonElement item in root.GetProperty("window_geometries").EnumerateArray()) spec.Windows.Add(FillingSpec.Load(item));
        spec.Roof = RoofSpec.Load(root.GetProperty("roof_geometry"));
        if (spec.Storeys.Count != 3 || spec.Spaces.Count != 3 || spec.Walls.Count != 12 || spec.SlabGuids.Count != 3 || spec.Doors.Count != 3 || spec.Windows.Count != 3) throw new InvalidDataException("Task-10 requires three storeys/spaces/slabs/doors/windows and twelve walls.");
        return spec;
    }
}
internal sealed class StoreySpec { public string Name { get; private set; } = ""; public string SourceName { get; private set; } = ""; public string Guid { get; private set; } = ""; public double ZM { get; private set; } public static StoreySpec Load(JsonElement item, IReadOnlyDictionary<string, string> guids) { string name = item.GetProperty("name").GetString() ?? ""; return new() { Name = name, SourceName = item.GetProperty("source_name").GetString() ?? "", Guid = guids[name], ZM = item.GetProperty("z_m").GetDouble() }; } }
internal sealed class WallSeed { public string Guid { get; private set; } = ""; public string Storey { get; private set; } = ""; public double X1 { get; private set; } public double Y1 { get; private set; } public double X2 { get; private set; } public double Y2 { get; private set; } public static WallSeed Load(JsonElement item) => new() { Guid = item.GetProperty("global_id").GetString() ?? "", Storey = item.GetProperty("storey").GetString() ?? "", X1 = item.GetProperty("x1_m").GetDouble(), Y1 = item.GetProperty("y1_m").GetDouble(), X2 = item.GetProperty("x2_m").GetDouble(), Y2 = item.GetProperty("y2_m").GetDouble() }; }
internal sealed class RoofSpec { public string IfcGuid { get; private set; } = ""; public double XM { get; private set; } public double YM { get; private set; } public double WidthM { get; private set; } public double DepthM { get; private set; } public double BaseZM { get; private set; } public double RidgeRiseM { get; private set; } public double ThicknessM { get; private set; } public static RoofSpec Load(JsonElement item) => new() { IfcGuid = item.GetProperty("ifc_guid").GetString() ?? "", XM = item.GetProperty("x_m").GetDouble(), YM = item.GetProperty("y_m").GetDouble(), WidthM = item.GetProperty("width_m").GetDouble(), DepthM = item.GetProperty("depth_m").GetDouble(), BaseZM = item.GetProperty("base_z_m").GetDouble(), RidgeRiseM = item.GetProperty("ridge_rise_m").GetDouble(), ThicknessM = item.GetProperty("thickness_m").GetDouble() }; }
internal sealed class FillingSpec { public string Name { get; private set; } = ""; public string Storey { get; private set; } = ""; public int HostWallIndex { get; private set; } public double OverallWidthM { get; private set; } public bool IsExternal { get; private set; } public double XM { get; private set; } public double YM { get; private set; } public double ZM { get; private set; } public double WidthM { get; private set; } public double DepthM { get; private set; } public double HeightM { get; private set; } public static FillingSpec Load(JsonElement item) { JsonElement geometry = item.GetProperty("geometry"); return new() { Name = item.GetProperty("name").GetString() ?? "", Storey = item.GetProperty("storey").GetString() ?? "", HostWallIndex = item.GetProperty("host_wall_index").GetInt32(), OverallWidthM = item.GetProperty("overall_width_m").GetDouble(), IsExternal = item.GetProperty("is_external").GetBoolean(), XM = geometry.GetProperty("x_m").GetDouble(), YM = geometry.GetProperty("y_m").GetDouble(), ZM = geometry.GetProperty("z_m").GetDouble(), WidthM = geometry.GetProperty("width_m").GetDouble(), DepthM = geometry.GetProperty("depth_m").GetDouble(), HeightM = geometry.GetProperty("height_m").GetDouble() }; } }
internal sealed class SpaceSpec
{
    public string Name { get; private set; } = ""; public string IfcGuid { get; private set; } = ""; public string ThermalZone { get; private set; } = ""; public string Storey { get; private set; } = ""; public double XM { get; private set; } public double YM { get; private set; } public double WidthM { get; private set; } public double DepthM { get; private set; } public double HeightM { get; private set; } public string ScheduleCategory { get; private set; } = ""; public double PeoplePerM2 { get; private set; } public double LightingWPerM2 { get; private set; } public double EquipmentWPerM2 { get; private set; } public double OutdoorAirLPerSPerson { get; private set; }
    public static SpaceSpec Load(JsonElement item) { JsonElement geometry = item.GetProperty("energy_geometry"), semantics = item.GetProperty("energy_semantics"); return new() { Name = item.GetProperty("name").GetString() ?? "", IfcGuid = item.GetProperty("retained_seed_global_id").GetString() ?? "", ThermalZone = item.GetProperty("thermal_zone").GetString() ?? "", Storey = item.GetProperty("storey").GetString() ?? "", XM = geometry.GetProperty("x_m").GetDouble(), YM = geometry.GetProperty("y_m").GetDouble(), WidthM = geometry.GetProperty("width_m").GetDouble(), DepthM = geometry.GetProperty("depth_m").GetDouble(), HeightM = geometry.GetProperty("height_m").GetDouble(), ScheduleCategory = semantics.GetProperty("schedule_category").GetString() ?? "", PeoplePerM2 = semantics.GetProperty("people_per_m2").GetDouble(), LightingWPerM2 = semantics.GetProperty("lighting_w_per_m2").GetDouble(), EquipmentWPerM2 = semantics.GetProperty("equipment_w_per_m2").GetDouble(), OutdoorAirLPerSPerson = semantics.GetProperty("outdoor_air_l_per_s_person").GetDouble() }; }
}
