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
        if (!string.Equals(spec.CaseId, "multi-cli-3-revit-archicad-openstudio-task-06-windows", StringComparison.Ordinal))
            throw new InvalidDataException("This task-local bridge only accepts task-06.");

        Document? document = null;
        try
        {
            document = uiApplication.Application.OpenIFCDocument(inputPath);
            if (document is null || !document.IsValidObject || document.IsReadOnly)
                throw new InvalidOperationException("Revit did not return a writable document for init.ifc.");

            List<CreatedRoom> rooms;
            using (Transaction transaction = new(document, "EngiWorld EW3B06 workshop room subdivision"))
            {
                transaction.Start();
                SetProjectTokens(document, spec);
                Level level = FindLevel(document);
                DeleteExistingRooms(document);
                EnsureRoomParameters(document, spec.ParameterNames);
                ViewPlan plan = FindOrCreatePlan(document, level);
                CreateBoundaryLines(document, plan, level.Elevation, spec);
                rooms = CreateRooms(document, level, spec);
                document.Regenerate();
                foreach (CreatedRoom room in rooms)
                {
                    room.AreaM2 = UnitUtils.ConvertFromInternalUnits(room.Room.Area, UnitTypeId.SquareMeters);
                    double expected = room.Spec.WidthM * room.Spec.DepthM;
                    if (room.AreaM2 <= 0 || Math.Abs(room.AreaM2 - expected) > 0.50)
                        throw new InvalidOperationException($"Room area mismatch for {room.Spec.Name}: {room.AreaM2:F6} m2, expected {expected:F6} m2.");
                    SetAreaParameter(room.Room.LookupParameter("Qto_SpaceBaseQuantities.GrossFloorArea"), room.Room.Area);
                    SetAreaParameter(room.Room.LookupParameter("Qto_SpaceBaseQuantities.NetFloorArea"), room.Room.Area);
                }
                double actualTotalArea = rooms.Sum(room => room.AreaM2);
                double expectedTotalArea = spec.Spaces.Sum(space => space.WidthM * space.DepthM);
                if (Math.Abs(actualTotalArea - expectedTotalArea) > 0.02)
                    throw new InvalidOperationException($"Task-06 room areas do not conserve the seed workshop area: {actualTotalArea:F6} m2, expected {expectedTotalArea:F6} m2.");
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
            using (Transaction exportTransaction = new(document, "EngiWorld EW3B06 IFC4 export"))
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
            ValidateSeedPreservation(ifcText, spec);
            WriteHandoff(Path.Combine(desktop, "revit_handoff.json"), inputPath, outputPath, rooms, spec);
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
        SetParameter(info.get_Parameter(BuiltInParameter.PROJECT_STATUS), "SIX-COLUMN-LAYOUT-PRESERVED | MAKER-WORKSHOP | OFFICE | TOOL-ROOM");
    }

    private static Level FindLevel(Document document)
    {
        Level? level = new FilteredElementCollector(document)
            .OfClass(typeof(Level))
            .Cast<Level>()
            .OrderBy(item => Math.Abs(item.Elevation))
            .FirstOrDefault();
        return level ?? throw new InvalidOperationException("The imported IFC did not create a Revit level.");
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

    private static void DeleteExistingRooms(Document document)
    {
        List<ElementId> rooms = new FilteredElementCollector(document)
            .OfCategory(BuiltInCategory.OST_Rooms)
            .WhereElementIsNotElementType()
            .Select(element => element.Id)
            .ToList();
        if (rooms.Count != 1)
            throw new InvalidOperationException($"The task-06 seed must import as exactly one Revit Room, found {rooms.Count}.");
        document.Delete(rooms);
    }

    private static void CreateBoundaryLines(Document document, ViewPlan plan, double elevation, WorkflowSpec spec)
    {
        SpaceSpec maker = spec.Spaces.Single(item => item.Name == "MAKER-WORKSHOP");
        SpaceSpec office = spec.Spaces.Single(item => item.Name == "OFFICE");
        SpaceSpec tool = spec.Spaces.Single(item => item.Name == "TOOL-ROOM");
        double minY = maker.YM + 0.1;
        double maxY = maker.YM + maker.DepthM + 0.1;
        double firstSplitX = maker.XM + maker.WidthM + 0.1;
        double secondSplitX = office.XM + office.WidthM + 0.1;
        if (Math.Abs(firstSplitX - (office.XM + 0.1)) > 0.001 ||
            Math.Abs(secondSplitX - (tool.XM + 0.1)) > 0.001 ||
            Math.Abs(office.DepthM - maker.DepthM) > 0.001 ||
            Math.Abs(tool.DepthM - maker.DepthM) > 0.001)
            throw new InvalidDataException("The three task-06 spaces do not form the configured contiguous workshop subdivision.");
        double f(double metres) => UnitUtils.ConvertToInternalUnits(metres, UnitTypeId.Meters);
        double z = elevation;

        List<Line> lines = new()
        {
            Line.CreateBound(new XYZ(f(firstSplitX), f(minY), z), new XYZ(f(firstSplitX), f(maxY), z)),
            Line.CreateBound(new XYZ(f(secondSplitX), f(minY), z), new XYZ(f(secondSplitX), f(maxY), z)),
        };

        Plane plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, new XYZ(0, 0, z));
        SketchPlane sketchPlane = SketchPlane.Create(document, plane);
        CurveArray curves = new();
        foreach (Line line in lines)
            curves.Append(line);
        document.Create.NewRoomBoundaryLines(sketchPlane, curves, plan);
    }

    private static List<CreatedRoom> CreateRooms(Document document, Level level, WorkflowSpec spec)
    {
        List<CreatedRoom> created = new();
        for (int index = 0; index < spec.Spaces.Count; index++)
        {
            SpaceSpec item = spec.Spaces[index];
            double centreX = item.XM + item.WidthM / 2.0 + 0.1;
            double centreY = item.YM + item.DepthM / 2.0 + 0.1;
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
        string file = Path.Combine(Path.GetTempPath(), "EngiWorld_task04_shared_parameters.txt");
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

    private static void ValidateSeedPreservation(string ifcText, WorkflowSpec spec)
    {
        foreach (string guid in spec.PreservedGlobalIds)
        {
            int occurrences = Regex.Matches(ifcText, Regex.Escape("'" + guid + "'"), RegexOptions.CultureInvariant).Count;
            if (occurrences != 1)
                throw new InvalidDataException($"The Revit export did not preserve seed IfcRoot GlobalId {guid} exactly once.");
        }
        if (Regex.Matches(ifcText, @"\bIFCCOLUMN\s*\(", RegexOptions.IgnoreCase).Count != 6)
            throw new InvalidDataException("The Revit export must retain exactly the six seed IfcColumn entities.");
        if (Regex.Matches(ifcText, @"\bIFCWALL\s*\(", RegexOptions.IgnoreCase).Count != 4)
            throw new InvalidDataException("The Revit export must retain exactly the four seed IfcWall entities.");
        if (Regex.Matches(ifcText, @"\bIFCSLAB\s*\(", RegexOptions.IgnoreCase).Count != 1)
            throw new InvalidDataException("The Revit export must retain exactly the seed IfcSlab entity.");
        if (Regex.Matches(ifcText, @"\bIFCSPACE\s*\(", RegexOptions.IgnoreCase).Count != 3)
            throw new InvalidDataException("The Revit export must contain exactly three task-06 IfcSpace entities.");
        if (Regex.IsMatch(ifcText, @"\bIFCGRID(?:AXIS)?\s*\(", RegexOptions.IgnoreCase))
            throw new InvalidDataException("The seed has no IFC grid entities; task-06 must not fabricate any.");
    }

    private static void WriteHandoff(string path, string inputPath, string outputPath, IReadOnlyList<CreatedRoom> rooms, WorkflowSpec spec)
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

internal sealed class WorkflowSpec
{
    public string CaseId { get; private set; } = string.Empty;
    public string Revision { get; private set; } = string.Empty;
    public List<SpaceSpec> Spaces { get; } = new();
    public List<string> Stage1Tokens { get; } = new();
    public List<string> PreservedGlobalIds { get; } = new();
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
        JsonElement preservation = root.GetProperty("seed_preservation");
        foreach (string key in new[] { "project_global_id", "site_global_id", "building_global_id", "storey_global_id", "slab_global_id" })
            spec.PreservedGlobalIds.Add(preservation.GetProperty(key).GetString() ?? string.Empty);
        foreach (JsonElement value in preservation.GetProperty("wall_global_ids").EnumerateArray())
            spec.PreservedGlobalIds.Add(value.GetString() ?? string.Empty);
        foreach (JsonElement value in preservation.GetProperty("column_global_ids").EnumerateArray())
            spec.PreservedGlobalIds.Add(value.GetString() ?? string.Empty);
        if (spec.Spaces.Count != 3)
            throw new InvalidDataException("task-06 must define exactly three spaces.");
        return spec;
    }
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
