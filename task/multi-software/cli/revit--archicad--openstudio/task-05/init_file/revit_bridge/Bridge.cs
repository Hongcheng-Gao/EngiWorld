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
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Events;
using BIM.IFC.Export.UI;

namespace EngiWorld.BimBridge;

public sealed class BridgeApplication : IExternalApplication
{
    private static UIControlledApplication? _controlledApplication;
    private static bool _started;

    public Result OnStartup(UIControlledApplication application)
    {
        if (!string.Equals(Environment.GetEnvironmentVariable("ENGIWORLD_BIM_STAGE"), "revit", StringComparison.OrdinalIgnoreCase))
            return Result.Succeeded;

        _controlledApplication = application;
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
        if (_started)
            return;
        _started = true;
        if (_controlledApplication is not null)
            _controlledApplication.Idling -= OnIdling;

        UIApplication? uiApplication = sender as UIApplication;
        if (uiApplication is null)
            return;

        string specPath = Environment.GetEnvironmentVariable("ENGIWORLD_BIM_JOB") ?? string.Empty;
        string desktop = Path.GetDirectoryName(specPath) ?? @"C:\Users\user\Desktop";
        string errorPath = Path.Combine(desktop, "revit_bridge_error.txt");
        try
        {
            File.Delete(errorPath);
            Execute(uiApplication, specPath, desktop);
        }
        catch (Exception exception)
        {
            File.WriteAllText(errorPath, exception.ToString(), new UTF8Encoding(false));
        }
        finally
        {
            TryExit(uiApplication);
        }
    }

    private static void Execute(UIApplication uiApplication, string specPath, string desktop)
    {
        if (!File.Exists(specPath))
            throw new FileNotFoundException("workflow_spec.json is missing", specPath);

        string inputPath = Path.Combine(desktop, "init.ifc");
        string outputPath = Path.Combine(desktop, "stage1.ifc");
        if (!File.Exists(inputPath))
            throw new FileNotFoundException("init.ifc is missing", inputPath);

        WorkflowSpec spec = WorkflowSpec.Load(specPath);
        if (!string.Equals(spec.CaseId, "multi-cli-3-revit-archicad-openstudio-task-05-windows", StringComparison.Ordinal))
            throw new InvalidDataException("This task-local bridge only accepts task-05.");

        Document? document = null;
        try
        {
            document = uiApplication.Application.OpenIFCDocument(inputPath);
            if (document is null || !document.IsValidObject || document.IsReadOnly)
                throw new InvalidOperationException("Revit did not return a writable document for init.ifc.");

            List<CreatedRoom> rooms;
            CreatedOpening opening;
            using (Transaction transaction = new(document, "EngiWorld EW3B05 two-storey space and stair-opening work"))
            {
                transaction.Start();
                SetProjectTokens(document, spec);
                IReadOnlyDictionary<string, Level> levels = FindLevels(document, spec);
                DeleteExistingRooms(document);
                DeleteGroundPartition(document, spec);
                EnsureRoomParameters(document, spec.ParameterNames);
                CreateUpperBoundaryLine(document, FindOrCreatePlan(document, levels["Level 2"]), levels["Level 2"], spec);
                rooms = CreateRooms(document, levels, spec);
                opening = CreateSlabOpening(document, spec);
                document.Regenerate();
                foreach (CreatedRoom room in rooms)
                {
                    room.AreaM2 = UnitUtils.ConvertFromInternalUnits(room.Room.Area, UnitTypeId.SquareMeters);
                    double expected = room.Spec.WidthM * room.Spec.DepthM;
                    if (room.AreaM2 <= 0 || Math.Abs(room.AreaM2 - expected) > 0.05)
                        throw new InvalidOperationException($"Room area mismatch for {room.Spec.Name}: {room.AreaM2:F6} m2, expected {expected:F6} m2.");
                    SetAreaParameter(room.Room.LookupParameter("Qto_SpaceBaseQuantities.GrossFloorArea"), room.Room.Area);
                    SetAreaParameter(room.Room.LookupParameter("Qto_SpaceBaseQuantities.NetFloorArea"), room.Room.Area);
                }
                FailureHandlingOptions failureOptions = transaction.GetFailureHandlingOptions();
                failureOptions.SetFailuresPreprocessor(new DeleteWarningsPreprocessor());
                transaction.SetFailureHandlingOptions(failureOptions);
                transaction.Commit();
            }

            string psetPath = Path.Combine(desktop, "EngiWorld_EnergyHandoff_psets.txt");
            WriteUserDefinedPset(psetPath, spec.ParameterNames);
            IFCExportOptions options = new()
            {
                FileVersion = IFCVersion.IFC4,
                SpaceBoundaryLevel = 2,
                WallAndColumnSplitting = false,
            };
            IFCExportConfiguration configuration = IFCExportConfiguration.CreateDefaultConfiguration();
            configuration.IFCVersion = IFCVersion.IFC4;
            configuration.SpaceBoundaries = 2;
            configuration.ExportBaseQuantities = true;
            configuration.ExportUserDefinedPsets = true;
            configuration.ExportUserDefinedPsetsFileName = psetPath;
            configuration.StoreIFCGUID = true;
            configuration.UpdateOptions(options, ElementId.InvalidElementId);
            options.AddOption("ExportBaseQuantities", "true");
            options.AddOption("ExportIFCCommonPropertySets", "true");
            options.AddOption("ExportRoomsInView", "true");
            options.AddOption("ExportUserDefinedPsets", "true");
            options.AddOption("ExportUserDefinedPsetsFileName", psetPath);
            options.AddOption("StoreIFCGUID", "true");
            options.AddOption("Use2DRoomBoundaryForVolume", "true");

            File.Delete(outputPath);
            using (Transaction exportTransaction = new(document, "EngiWorld EW3B05 IFC4 export"))
            {
                exportTransaction.Start();
                if (!document.Export(desktop, "stage1.ifc", options))
                    throw new InvalidOperationException("Revit IFC export returned false.");
                exportTransaction.Commit();
            }
            if (!File.Exists(outputPath) || new FileInfo(outputPath).Length == 0)
                throw new InvalidOperationException("Revit IFC export did not create stage1.ifc.");

            string ifcText = File.ReadAllText(outputPath);
            foreach (CreatedRoom room in rooms)
                room.IfcGuid = FindIfcSpaceGuid(ifcText, room.Spec.Name);
            opening.IfcGuid = FindIfcOpeningGuid(ifcText, spec);
            WriteHandoff(Path.Combine(desktop, "revit_handoff.json"), inputPath, outputPath, rooms, opening, spec);
        }
        finally
        {
            if (document is not null && document.IsValidObject)
                document.Close(false);
        }
    }

    private static void SetProjectTokens(Document document, WorkflowSpec spec)
    {
        ProjectInfo info = document.ProjectInformation;
        SetParameter(info.get_Parameter(BuiltInParameter.PROJECT_NAME), spec.CaseId);
        SetParameter(info.get_Parameter(BuiltInParameter.PROJECT_NUMBER), spec.Revision);
        SetParameter(info.get_Parameter(BuiltInParameter.PROJECT_STATUS), "TWO-STOREY | GROUND-PUBLIC | UPPER-ACTIVITY | UPPER-READING | STAIR-OPENING");
    }

    private static IReadOnlyDictionary<string, Level> FindLevels(Document document, WorkflowSpec spec)
    {
        List<Level> all = new FilteredElementCollector(document)
            .OfClass(typeof(Level))
            .Cast<Level>()
            .ToList();
        Dictionary<string, Level> result = new(StringComparer.OrdinalIgnoreCase);
        foreach (StoreySpec storey in spec.Storeys)
        {
            Level? level = all.OrderBy(item => Math.Abs(UnitUtils.ConvertFromInternalUnits(item.Elevation, UnitTypeId.Meters) - storey.ZM)).FirstOrDefault();
            if (level is null || Math.Abs(UnitUtils.ConvertFromInternalUnits(level.Elevation, UnitTypeId.Meters) - storey.ZM) > 0.05)
                throw new InvalidOperationException($"The imported IFC did not create the configured Revit level at {storey.ZM:F3} m.");
            result[storey.Name] = level;
        }
        if (result.Values.Select(item => item.Id.Value).Distinct().Count() != spec.Storeys.Count)
            throw new InvalidOperationException("Configured storeys did not resolve to distinct Revit levels.");
        return result;
    }

    private static void DeleteExistingRooms(Document document)
    {
        List<ElementId> rooms = new FilteredElementCollector(document)
            .OfCategory(BuiltInCategory.OST_Rooms)
            .WhereElementIsNotElementType()
            .Select(element => element.Id)
            .ToList();
        if (rooms.Count > 0)
            document.Delete(rooms);
    }

    private static void DeleteGroundPartition(Document document, WorkflowSpec spec)
    {
        HashSet<string> removable = spec.RemovedSeedElementGlobalIds.ToHashSet(StringComparer.Ordinal);
        List<Element> candidates = new FilteredElementCollector(document)
            .OfCategory(BuiltInCategory.OST_Walls)
            .WhereElementIsNotElementType()
            .Where(item => removable.Contains(GetIfcGuid(item)))
            .ToList();
        if (candidates.Count != removable.Count)
            throw new InvalidOperationException($"Expected exactly {removable.Count} seed Ground Floor partition by IFC GlobalId, found {candidates.Count}.");
        foreach (Element wall in candidates)
            document.Delete(wall.Id);
    }

    private static string GetIfcGuid(Element element)
    {
        foreach (string name in new[] { "IfcGUID", "IFC GUID", "GlobalId" })
        {
            string? value = element.LookupParameter(name)?.AsString();
            if (!string.IsNullOrWhiteSpace(value))
                return value;
        }
        return string.Empty;
    }

    private static ViewPlan FindOrCreatePlan(Document document, Level level)
    {
        ViewPlan? plan = new FilteredElementCollector(document)
            .OfClass(typeof(ViewPlan))
            .Cast<ViewPlan>()
            .FirstOrDefault(view => !view.IsTemplate && view.GenLevel?.Id == level.Id);
        if (plan is not null)
            return plan;

        ViewFamilyType type = new FilteredElementCollector(document)
            .OfClass(typeof(ViewFamilyType))
            .Cast<ViewFamilyType>()
            .First(item => item.ViewFamily == ViewFamily.FloorPlan);
        return ViewPlan.Create(document, type.Id, level.Id);
    }

    private static void CreateUpperBoundaryLine(Document document, ViewPlan plan, Level level, WorkflowSpec spec)
    {
        SpaceSpec activity = spec.Spaces.Single(item => item.Name == "UPPER-ACTIVITY");
        SpaceSpec reading = spec.Spaces.Single(item => item.Name == "UPPER-READING");
        double minY = Math.Max(activity.YM, reading.YM);
        double maxY = Math.Min(activity.YM + activity.DepthM, reading.YM + reading.DepthM);
        double splitX = activity.XM + activity.WidthM;
        if (Math.Abs(splitX - reading.XM) > 0.001 || maxY <= minY)
            throw new InvalidDataException("UPPER-ACTIVITY and UPPER-READING do not share the configured boundary.");
        double f(double metres) => UnitUtils.ConvertToInternalUnits(metres, UnitTypeId.Meters);
        double z = level.Elevation;

        List<Line> lines = new()
        {
            Line.CreateBound(new XYZ(f(splitX), f(minY), z), new XYZ(f(splitX), f(maxY), z)),
        };

        Plane plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, new XYZ(0, 0, z));
        SketchPlane sketchPlane = SketchPlane.Create(document, plane);
        CurveArray curves = new();
        foreach (Line line in lines)
            curves.Append(line);
        document.Create.NewRoomBoundaryLines(sketchPlane, curves, plan);
    }

    private static CreatedOpening CreateSlabOpening(Document document, WorkflowSpec spec)
    {
        double f(double metres) => UnitUtils.ConvertToInternalUnits(metres, UnitTypeId.Meters);
        OpeningSpec item = spec.Opening;
        List<Element> importedHosts = new FilteredElementCollector(document)
            .OfCategory(BuiltInCategory.OST_Floors)
            .WhereElementIsNotElementType()
            .Where(element => string.Equals(GetIfcGuid(element), item.SourceHostSlabGlobalId, StringComparison.Ordinal))
            .ToList();
        if (importedHosts.Count != 1)
            throw new InvalidOperationException($"Expected one original Level 2 slab with IFC GlobalId {item.SourceHostSlabGlobalId}, found {importedHosts.Count}.");
        BoundingBoxXYZ importedBounds = importedHosts[0].get_BoundingBox(null)
            ?? throw new InvalidOperationException("The imported Level 2 slab has no Revit bounding box.");
        double expectedTop = f(item.ZM), expectedBottom = f(item.ZM - item.HostThicknessM);
        if (Math.Abs(importedBounds.Max.Z - expectedTop) > f(0.02) || Math.Abs(importedBounds.Min.Z - expectedBottom) > f(0.02))
            throw new InvalidOperationException("The imported Level 2 slab geometry does not match the workflow contract.");

        Level hostLevel = new FilteredElementCollector(document).OfClass(typeof(Level)).Cast<Level>()
            .OrderBy(level => Math.Abs(level.Elevation - expectedTop)).First();
        FloorType sourceFloorType = new FilteredElementCollector(document).OfClass(typeof(FloorType)).Cast<FloorType>()
            .First(type => type.GetCompoundStructure() is not null);
        FloorType floorType = (FloorType)sourceFloorType.Duplicate("EW3B05 300mm Opening Host Slab");
        CompoundStructure compound = floorType.GetCompoundStructure()
            ?? throw new InvalidOperationException("The duplicated Revit FloorType has no compound structure.");
        IList<CompoundStructureLayer> layers = compound.GetLayers();
        if (layers.Count == 0)
            throw new InvalidOperationException("The duplicated Revit FloorType has no material layers.");
        int adjustableLayer = Enumerable.Range(0, layers.Count).OrderByDescending(index => layers[index].Width).First();
        double otherWidth = layers.Where((_, index) => index != adjustableLayer).Sum(layer => layer.Width);
        double adjustedWidth = f(item.HostThicknessM) - otherWidth;
        if (adjustedWidth <= f(0.001))
            throw new InvalidOperationException("The Revit FloorType layers cannot be adjusted to the configured host thickness.");
        compound.SetLayerWidth(adjustableLayer, adjustedWidth);
        floorType.SetCompoundStructure(compound);
        CurveLoop floorProfile = new();
        XYZ fa = new(importedBounds.Min.X, importedBounds.Min.Y, expectedTop);
        XYZ fb = new(importedBounds.Max.X, importedBounds.Min.Y, expectedTop);
        XYZ fc = new(importedBounds.Max.X, importedBounds.Max.Y, expectedTop);
        XYZ fd = new(importedBounds.Min.X, importedBounds.Max.Y, expectedTop);
        floorProfile.Append(Line.CreateBound(fa, fb));
        floorProfile.Append(Line.CreateBound(fb, fc));
        floorProfile.Append(Line.CreateBound(fc, fd));
        floorProfile.Append(Line.CreateBound(fd, fa));
        document.Delete(importedHosts[0].Id);
        Floor host = Floor.Create(document, new List<CurveLoop> { floorProfile }, floorType.Id, hostLevel.Id);
        Parameter? heightOffset = host.get_Parameter(BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM);
        if (heightOffset is not null && !heightOffset.IsReadOnly)
            heightOffset.Set(expectedTop - hostLevel.Elevation);
        Parameter? ifcGuid = host.LookupParameter("IfcGUID") ?? host.LookupParameter("IFC GUID");
        if (ifcGuid is not null && !ifcGuid.IsReadOnly)
            ifcGuid.Set(item.SourceHostSlabGlobalId);
        host.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)?.Set("ORIGINAL-GLOBALID-PRESERVED | STAIR-OPENING-HOST");
        document.Regenerate();
        CurveArray profile = new();
        double x0 = f(item.XM), x1 = f(item.XM + item.WidthM), y0 = f(item.YM), y1 = f(item.YM + item.DepthM), z = f(item.ZM);
        XYZ a = new(x0, y0, z), b = new(x1, y0, z), c = new(x1, y1, z), d = new(x0, y1, z);
        profile.Append(Line.CreateBound(a, b));
        profile.Append(Line.CreateBound(b, c));
        profile.Append(Line.CreateBound(c, d));
        profile.Append(Line.CreateBound(d, a));
        Opening opening = document.Create.NewOpening(host, profile, false)
            ?? throw new InvalidOperationException("Revit failed to create the stair opening in the original Level 2 slab.");
        opening.LookupParameter("Comments")?.Set("STAIR-OPENING");
        return new CreatedOpening(opening, host, item);
    }

    private static List<CreatedRoom> CreateRooms(Document document, IReadOnlyDictionary<string, Level> levels, WorkflowSpec spec)
    {
        List<CreatedRoom> created = new();
        for (int index = 0; index < spec.Spaces.Count; index++)
        {
            SpaceSpec item = spec.Spaces[index];
            Level level = levels[item.Storey];
            double centreX = item.XM + item.WidthM / 2.0;
            double centreY = item.YM + item.DepthM / 2.0;
            Room room = document.Create.NewRoom(level, new UV(
                UnitUtils.ConvertToInternalUnits(centreX, UnitTypeId.Meters),
                UnitUtils.ConvertToInternalUnits(centreY, UnitTypeId.Meters)))
                ?? throw new InvalidOperationException($"Revit could not create room {item.Name}.");

            SetParameter(room.get_Parameter(BuiltInParameter.ROOM_NAME), item.Name);
            SetParameter(room.get_Parameter(BuiltInParameter.ROOM_NUMBER), (index + 1).ToString("00", CultureInfo.InvariantCulture));
            Parameter? upperLevel = room.get_Parameter(BuiltInParameter.ROOM_UPPER_LEVEL);
            if (upperLevel is not null && !upperLevel.IsReadOnly)
                upperLevel.Set(level.Id);
            Parameter? upperOffset = room.get_Parameter(BuiltInParameter.ROOM_UPPER_OFFSET);
            if (upperOffset is not null && !upperOffset.IsReadOnly)
                upperOffset.Set(UnitUtils.ConvertToInternalUnits(item.HeightM, UnitTypeId.Meters));

            SetParameter(room.LookupParameter("ThermalZone"), item.ThermalZone);
            SetParameter(room.LookupParameter("ScheduleCategory"), item.ScheduleCategory);
            SetParameter(room.LookupParameter("PeoplePerM2"), item.PeoplePerM2.ToString("R", CultureInfo.InvariantCulture));
            SetParameter(room.LookupParameter("LightingPowerDensityWPerM2"), item.LightingWPerM2.ToString("R", CultureInfo.InvariantCulture));
            SetParameter(room.LookupParameter("EquipmentPowerDensityWPerM2"), item.EquipmentWPerM2.ToString("R", CultureInfo.InvariantCulture));
            SetParameter(room.LookupParameter("OutdoorAirLPerSPerson"), item.OutdoorAirLPerSPerson.ToString("R", CultureInfo.InvariantCulture));
            created.Add(new CreatedRoom(room, item));
        }
        return created;
    }

    private static void EnsureRoomParameters(Document document, IReadOnlyList<string> names)
    {
        Application application = document.Application;
        string original = application.SharedParametersFilename;
        string file = Path.Combine(Path.GetTempPath(), "EngiWorld_task05_shared_parameters.txt");
        File.WriteAllText(file, "# This is a Revit shared parameter file.\r\n*META\tVERSION\tMINVERSION\r\nMETA\t2\t1\r\n", new UTF8Encoding(false));
        try
        {
            application.SharedParametersFilename = file;
            DefinitionFile definitions = application.OpenSharedParameterFile()
                ?? throw new InvalidOperationException("Could not open the task-local Revit shared parameter file.");
            DefinitionGroup group = definitions.Groups.get_Item("EngiWorld") ?? definitions.Groups.Create("EngiWorld");
            CategorySet categories = application.Create.NewCategorySet();
            categories.Insert(document.Settings.Categories.get_Item(BuiltInCategory.OST_Rooms));
            InstanceBinding binding = application.Create.NewInstanceBinding(categories);
            foreach (string name in names)
            {
                Definition? existing = group.Definitions.get_Item(name);
                Definition definition = existing ?? group.Definitions.Create(new ExternalDefinitionCreationOptions(name, SpecTypeId.String.Text));
                if (!document.ParameterBindings.Insert(definition, binding, GroupTypeId.Data))
                    document.ParameterBindings.ReInsert(definition, binding, GroupTypeId.Data);
            }
        }
        finally
        {
            application.SharedParametersFilename = original;
            File.Delete(file);
        }

        string builtInIfcParameters = @"C:\Program Files\Autodesk\Revit 2025\IFC Shared Parameters-RevitIFCBuiltIn_ALL.txt";
        try
        {
            application.SharedParametersFilename = builtInIfcParameters;
            DefinitionFile definitions = application.OpenSharedParameterFile()
                ?? throw new InvalidOperationException("Could not open Revit 2025 built-in IFC shared parameters.");
            CategorySet categories = application.Create.NewCategorySet();
            categories.Insert(document.Settings.Categories.get_Item(BuiltInCategory.OST_Rooms));
            InstanceBinding binding = application.Create.NewInstanceBinding(categories);
            foreach (string name in new[] { "Qto_SpaceBaseQuantities.GrossFloorArea", "Qto_SpaceBaseQuantities.NetFloorArea" })
            {
                Definition? definition = null;
                foreach (DefinitionGroup group in definitions.Groups)
                {
                    definition = group.Definitions.get_Item(name);
                    if (definition is not null)
                        break;
                }
                if (definition is null)
                    throw new InvalidOperationException($"Revit 2025 IFC shared parameter definition is missing: {name}");
                if (!document.ParameterBindings.Insert(definition, binding, GroupTypeId.Data))
                    document.ParameterBindings.ReInsert(definition, binding, GroupTypeId.Data);
            }
        }
        finally
        {
            application.SharedParametersFilename = original;
        }
    }

    private static void SetParameter(Parameter? parameter, string value)
    {
        if (parameter is null || parameter.IsReadOnly || !parameter.Set(value))
            throw new InvalidOperationException($"Could not set Revit parameter to '{value}'.");
    }

    private static void SetAreaParameter(Parameter? parameter, double internalSquareFeet)
    {
        if (parameter is null || parameter.IsReadOnly || !parameter.Set(internalSquareFeet))
            throw new InvalidOperationException("Could not set Revit IFC room quantity parameter.");
    }

    private static void WriteUserDefinedPset(string path, IReadOnlyList<string> names)
    {
        StringBuilder text = new();
        text.AppendLine("PropertySet:\tEngiWorld_EnergyHandoff\tI\tIfcSpace");
        foreach (string name in names)
            text.Append('\t').Append(name).Append("\tText\t").AppendLine(name);
        File.WriteAllText(path, text.ToString(), new UTF8Encoding(false));
    }

    private static string FindIfcSpaceGuid(string text, string spaceName)
    {
        foreach (Match match in Regex.Matches(text, @"IFCSPACE\s*\(\s*'([^']+)'[^;]*;", RegexOptions.IgnoreCase | RegexOptions.Singleline))
        {
            if (match.Value.IndexOf(spaceName, StringComparison.OrdinalIgnoreCase) >= 0)
                return match.Groups[1].Value;
        }
        throw new InvalidDataException($"The Revit IFC export does not contain an IfcSpace named {spaceName}.");
    }

    private static string FindIfcOpeningGuid(string text, WorkflowSpec spec)
    {
        MatchCollection openings = Regex.Matches(text, @"IFCOPENINGELEMENT\s*\(\s*'([^']+)'[^;]*;", RegexOptions.IgnoreCase | RegexOptions.Singleline);
        if (openings.Count != 1)
            throw new InvalidDataException($"The Revit IFC export must contain exactly one IfcOpeningElement, found {openings.Count}.");
        string guid = openings[0].Groups[1].Value;
        MatchCollection voids = Regex.Matches(text, @"IFCRELVOIDSELEMENT\s*\(", RegexOptions.IgnoreCase);
        if (voids.Count != 1)
            throw new InvalidDataException("The Revit IFC export does not contain exactly one slab-opening void relation.");
        return guid;
    }

    private static string FindIfcHostGuidForOpening(string text, string openingGuid)
    {
        Match openingEntity = Regex.Match(text, $@"#(\d+)\s*=\s*IFCOPENINGELEMENT\s*\(\s*'{Regex.Escape(openingGuid)}'[^;]*;", RegexOptions.IgnoreCase | RegexOptions.Singleline);
        if (!openingEntity.Success)
            throw new InvalidDataException("Could not resolve the exported IfcOpeningElement entity id.");
        Match relation = Regex.Match(text, $@"IFCRELVOIDSELEMENT\s*\([^;]*#(\d+)\s*,\s*#{openingEntity.Groups[1].Value}\s*\)\s*;", RegexOptions.IgnoreCase | RegexOptions.Singleline);
        if (!relation.Success)
            throw new InvalidDataException("Could not resolve the exported IfcRelVoidsElement host.");
        Match host = Regex.Match(text, $@"#{relation.Groups[1].Value}\s*=\s*IFCSLAB\s*\(\s*'([^']+)'", RegexOptions.IgnoreCase | RegexOptions.Singleline);
        if (!host.Success)
            throw new InvalidDataException("The opening host is not an exported IfcSlab.");
        return host.Groups[1].Value;
    }

    private static void WriteHandoff(string path, string inputPath, string outputPath, IReadOnlyList<CreatedRoom> rooms, CreatedOpening opening, WorkflowSpec spec)
    {
        string revitExe = @"C:\Program Files\Autodesk\Revit 2025\Revit.exe";
        FileVersionInfo versionInfo = FileVersionInfo.GetVersionInfo(revitExe);
        object payload = new
        {
            case_id = spec.CaseId,
            software_stage = "revit",
            source_file = "stage1.ifc",
            source_sha256 = Sha256(outputPath),
            input_seed_sha256 = Sha256(inputPath),
            spaces = rooms.Select(item => new
            {
                name = item.Spec.Name,
                ifc_guid = item.IfcGuid,
                area_m2 = Math.Round(item.AreaM2, 6),
                storey = item.Spec.Storey,
                thermal_zone = item.Spec.ThermalZone,
                schedule_category = item.Spec.ScheduleCategory,
                people_per_m2 = item.Spec.PeoplePerM2,
                lighting_w_per_m2 = item.Spec.LightingWPerM2,
                equipment_w_per_m2 = item.Spec.EquipmentWPerM2,
                outdoor_air_l_per_s_person = item.Spec.OutdoorAirLPerSPerson,
                stage = "revit",
            }).ToArray(),
            stair_opening = new
            {
                ifc_guid = opening.IfcGuid,
                source_host_slab_global_id = opening.Spec.SourceHostSlabGlobalId,
                host_slab_ifc_guid = FindIfcHostGuidForOpening(File.ReadAllText(outputPath), opening.IfcGuid),
                x_m = opening.Spec.XM,
                y_m = opening.Spec.YM,
                z_m = opening.Spec.ZM,
                width_m = opening.Spec.WidthM,
                depth_m = opening.Spec.DepthM,
                host_thickness_m = opening.Spec.HostThicknessM,
                revit_opening_element_id = opening.Opening.Id.Value,
                revit_host_element_id = opening.Host.Id.Value,
                relation = "IfcRelVoidsElement",
            },
            stage1_tokens = spec.Stage1Tokens.Concat(new[] { spec.CaseId }).Distinct().ToArray(),
            downstream_consumer = "archicad",
            native_provenance = new
            {
                exe = revitExe,
                product_version = versionInfo.FileVersion,
                product_build = versionInfo.ProductVersion,
                automation = "EngiWorld.BimBridge IExternalApplication loaded and executed from Revit 2025 Idling",
                completed_utc = DateTime.UtcNow.ToString("o", CultureInfo.InvariantCulture),
            },
        };
        File.WriteAllText(path, JsonSerializer.Serialize(payload, new JsonSerializerOptions { WriteIndented = true }) + Environment.NewLine, new UTF8Encoding(false));
    }

    private static string Sha256(string path)
    {
        using SHA256 algorithm = SHA256.Create();
        using FileStream stream = File.OpenRead(path);
        return Convert.ToHexString(algorithm.ComputeHash(stream)).ToLowerInvariant();
    }

    private static void TryExit(UIApplication application)
    {
        try
        {
            RevitCommandId command = RevitCommandId.LookupPostableCommandId(PostableCommand.ExitRevit);
            if (application.CanPostCommand(command))
                application.PostCommand(command);
        }
        catch
        {
            // The launcher will fail closed if Revit cannot exit or outputs are missing.
        }
    }
}

internal sealed class DeleteWarningsPreprocessor : IFailuresPreprocessor
{
    public FailureProcessingResult PreprocessFailures(FailuresAccessor failuresAccessor)
    {
        foreach (FailureMessageAccessor warning in failuresAccessor.GetFailureMessages())
        {
            if (warning.GetSeverity() == FailureSeverity.Warning)
                failuresAccessor.DeleteWarning(warning);
        }
        return FailureProcessingResult.Continue;
    }
}

internal sealed class CreatedRoom
{
    public CreatedRoom(Room room, SpaceSpec spec)
    {
        Room = room;
        Spec = spec;
    }

    public Room Room { get; }
    public SpaceSpec Spec { get; }
    public double AreaM2 { get; set; }
    public string IfcGuid { get; set; } = string.Empty;
}

internal sealed class CreatedOpening
{
    public CreatedOpening(Opening opening, Element host, OpeningSpec spec)
    {
        Opening = opening;
        Host = host;
        Spec = spec;
    }

    public Opening Opening { get; }
    public Element Host { get; }
    public OpeningSpec Spec { get; }
    public string IfcGuid { get; set; } = string.Empty;
}

internal sealed class WorkflowSpec
{
    public string CaseId { get; private set; } = string.Empty;
    public string Revision { get; private set; } = string.Empty;
    public List<SpaceSpec> Spaces { get; } = new();
    public List<StoreySpec> Storeys { get; } = new();
    public List<string> Stage1Tokens { get; } = new();
    public List<string> RemovedSeedElementGlobalIds { get; } = new();
    public OpeningSpec Opening { get; private set; } = new();
    public IReadOnlyList<string> ParameterNames { get; } = new[]
    {
        "ThermalZone", "ScheduleCategory", "PeoplePerM2", "LightingPowerDensityWPerM2",
        "EquipmentPowerDensityWPerM2", "OutdoorAirLPerSPerson",
    };

    public static WorkflowSpec Load(string path)
    {
        using JsonDocument json = JsonDocument.Parse(File.ReadAllText(path));
        JsonElement root = json.RootElement;
        WorkflowSpec spec = new()
        {
            CaseId = root.GetProperty("case_id").GetString() ?? string.Empty,
            Revision = root.GetProperty("revision").GetString() ?? string.Empty,
        };
        foreach (JsonElement token in root.GetProperty("revit_stage").GetProperty("required_tokens").EnumerateArray())
            spec.Stage1Tokens.Add(token.GetString() ?? string.Empty);
        foreach (JsonElement item in root.GetProperty("spaces").EnumerateArray())
            spec.Spaces.Add(SpaceSpec.Load(item));
        foreach (JsonElement item in root.GetProperty("storeys").EnumerateArray())
            spec.Storeys.Add(StoreySpec.Load(item));
        foreach (JsonElement item in root.GetProperty("revit_stage").GetProperty("removed_seed_element_global_ids").EnumerateArray())
            spec.RemovedSeedElementGlobalIds.Add(item.GetString() ?? string.Empty);
        spec.Opening = OpeningSpec.Load(root.GetProperty("opening_geometry"));
        if (spec.Spaces.Count != 3 || spec.Storeys.Count != 2 || spec.RemovedSeedElementGlobalIds.Count != 1)
            throw new InvalidDataException("task-05 must define exactly three spaces, two storeys, and one removable seed partition.");
        return spec;
    }
}

internal sealed class StoreySpec
{
    public string Name { get; private set; } = string.Empty;
    public double ZM { get; private set; }

    public static StoreySpec Load(JsonElement item) => new()
    {
        Name = item.GetProperty("name").GetString() ?? string.Empty,
        ZM = item.GetProperty("z_m").GetDouble(),
    };
}

internal sealed class OpeningSpec
{
    public string Storey { get; private set; } = string.Empty;
    public string SourceHostSlabGlobalId { get; private set; } = string.Empty;
    public double XM { get; private set; }
    public double YM { get; private set; }
    public double ZM { get; private set; }
    public double WidthM { get; private set; }
    public double DepthM { get; private set; }
    public double HostThicknessM { get; private set; }

    public static OpeningSpec Load(JsonElement item) => new()
    {
        Storey = item.GetProperty("storey").GetString() ?? string.Empty,
        SourceHostSlabGlobalId = item.GetProperty("source_host_slab_global_id").GetString() ?? string.Empty,
        XM = item.GetProperty("x_m").GetDouble(),
        YM = item.GetProperty("y_m").GetDouble(),
        ZM = item.GetProperty("z_m").GetDouble(),
        WidthM = item.GetProperty("width_m").GetDouble(),
        DepthM = item.GetProperty("depth_m").GetDouble(),
        HostThicknessM = item.GetProperty("host_thickness_m").GetDouble(),
    };
}

internal sealed class SpaceSpec
{
    public string Name { get; private set; } = string.Empty;
    public string ThermalZone { get; private set; } = string.Empty;
    public string Storey { get; private set; } = string.Empty;
    public double XM { get; private set; }
    public double YM { get; private set; }
    public double WidthM { get; private set; }
    public double DepthM { get; private set; }
    public double HeightM { get; private set; }
    public string ScheduleCategory { get; private set; } = string.Empty;
    public double PeoplePerM2 { get; private set; }
    public double LightingWPerM2 { get; private set; }
    public double EquipmentWPerM2 { get; private set; }
    public double OutdoorAirLPerSPerson { get; private set; }

    public static SpaceSpec Load(JsonElement item)
    {
        JsonElement geometry = item.GetProperty("energy_geometry");
        JsonElement semantics = item.GetProperty("energy_semantics");
        return new SpaceSpec
        {
            Name = item.GetProperty("name").GetString() ?? string.Empty,
            ThermalZone = item.GetProperty("thermal_zone").GetString() ?? string.Empty,
            Storey = item.GetProperty("storey").GetString() ?? string.Empty,
            XM = geometry.GetProperty("x_m").GetDouble(),
            YM = geometry.GetProperty("y_m").GetDouble(),
            WidthM = geometry.GetProperty("width_m").GetDouble(),
            DepthM = geometry.GetProperty("depth_m").GetDouble(),
            HeightM = geometry.GetProperty("height_m").GetDouble(),
            ScheduleCategory = semantics.GetProperty("schedule_category").GetString() ?? string.Empty,
            PeoplePerM2 = semantics.GetProperty("people_per_m2").GetDouble(),
            LightingWPerM2 = semantics.GetProperty("lighting_w_per_m2").GetDouble(),
            EquipmentWPerM2 = semantics.GetProperty("equipment_w_per_m2").GetDouble(),
            OutdoorAirLPerSPerson = semantics.GetProperty("outdoor_air_l_per_s_person").GetDouble(),
        };
    }
}
