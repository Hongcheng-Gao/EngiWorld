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
        if (!File.Exists(specPath) || !File.Exists(input)) throw new FileNotFoundException("Task-08 inputs are missing.");
        WorkflowSpec spec = WorkflowSpec.Load(specPath);
        if (spec.CaseId != "multi-cli-3-revit-archicad-openstudio-task-08-windows" || spec.Revision != "EW3B08")
            throw new InvalidDataException("This bridge only accepts task-08 EW3B08.");

        Document? document = null;
        try
        {
            document = ui.Application.OpenIFCDocument(input);
            if (document is null || document.IsReadOnly) throw new InvalidOperationException("Revit did not open a writable IFC document.");
            List<CreatedRoom> rooms;
            using (Transaction tx = new(document, "EngiWorld EW3B08 library annex"))
            {
                tx.Start();
                SetProjectTokens(document, spec);
                Dictionary<string, Level> levels = FindLevels(document);
                EnsureSharedParameters(document, spec.ParameterNames);
                DeleteImportedRooms(document);
                List<Wall> walls = RebuildSeedWalls(document, levels, spec);
                foreach (Level level in levels.Values)
                {
                    ViewPlan plan = FindOrCreatePlan(document, level);
                    CreateRoomSeparationLine(document, plan, level);
                }
                rooms = CreateRooms(document, levels, spec);
                CreatePitchedRoof(document, spec);
                CreateHostedFillings(document, levels, walls);
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
                FailureHandlingOptions options = tx.GetFailureHandlingOptions();
                options.SetFailuresPreprocessor(new DeleteWarningsPreprocessor());
                tx.SetFailureHandlingOptions(options);
                tx.Commit();
            }

            string pset = Path.Combine(desktop, "EngiWorld_EnergyHandoff_psets.txt");
            WriteUserDefinedPset(pset, spec.ParameterNames);
            IFCExportOptions export = new() { FileVersion = IFCVersion.IFC4, SpaceBoundaryLevel = 2, WallAndColumnSplitting = false };
            IFCExportConfiguration config = IFCExportConfiguration.CreateDefaultConfiguration();
            config.IFCVersion = IFCVersion.IFC4;
            config.SpaceBoundaries = 2;
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
            using (Transaction tx = new(document, "EngiWorld EW3B08 IFC4 export"))
            {
                tx.Start();
                if (!document.Export(desktop, "stage1.ifc", export)) throw new InvalidOperationException("Revit IFC export returned false.");
                tx.Commit();
            }
            if (!File.Exists(output) || new FileInfo(output).Length == 0) throw new InvalidOperationException("stage1.ifc was not created.");
            string text = File.ReadAllText(output);
            foreach (CreatedRoom room in rooms) room.IfcGuid = FindNamedGuid(text, "IFCSPACE", room.Spec.Name);
            FillingGraph graph = ParseFillingGraph(text);
            if (graph.Doors.Count != 4 || graph.Windows.Count != 4 || graph.Openings.Count != 8 || graph.VoidRelations.Count != 8 || graph.FillRelations.Count != 8)
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
        Set(info.get_Parameter(BuiltInParameter.PROJECT_STATUS), "FOUR-LAB-PREP-SPACES | TWO-LEVEL-GEOMETRY | GEOMETRIC-FILLINGS | PITCHED-ROOF");
    }

    private static Dictionary<string, Level> FindLevels(Document document)
    {
        List<Level> levels = new FilteredElementCollector(document).OfClass(typeof(Level)).Cast<Level>().OrderBy(x => x.Elevation).ToList();
        if (levels.Count != 2) throw new InvalidOperationException($"Expected two imported levels, found {levels.Count}.");
        return new Dictionary<string, Level>(StringComparer.Ordinal) { ["Level 1"] = levels[0], ["Level 2"] = levels[1] };
    }

    private static void DeleteImportedRooms(Document document)
    {
        List<ElementId> ids = new FilteredElementCollector(document).OfCategory(BuiltInCategory.OST_Rooms)
            .WhereElementIsNotElementType().Select(e => e.Id).ToList();
        if (ids.Count != 2) throw new InvalidOperationException($"Expected two seed Rooms, found {ids.Count}.");
        document.Delete(ids);
    }

    private static List<Wall> RebuildSeedWalls(Document document, IReadOnlyDictionary<string, Level> levels, WorkflowSpec spec)
    {
        List<Element> old = new FilteredElementCollector(document).OfCategory(BuiltInCategory.OST_Walls).WhereElementIsNotElementType().ToList();
        Dictionary<string, Element> byGuid = old.ToDictionary(GetIfcGuid, StringComparer.Ordinal);
        foreach (WallSeed seed in spec.Walls) if (!byGuid.ContainsKey(seed.Guid)) throw new InvalidOperationException($"Seed wall missing: {seed.Guid}");
        WallType baseType = new FilteredElementCollector(document).OfClass(typeof(WallType)).Cast<WallType>()
            .First(type => type.Kind == WallKind.Basic && type.GetCompoundStructure() is not null);
        WallType type = (WallType)baseType.Duplicate("EW3B08 Laboratory Wall");
        CompoundStructure sourceStructure = baseType.GetCompoundStructure()!;
        CompoundStructureLayer sourceLayer = sourceStructure.GetLayers().OrderByDescending(layer => layer.Width).First();
        type.SetCompoundStructure(CompoundStructure.CreateSingleLayerCompoundStructure(
            MaterialFunctionAssignment.Structure, F(0.2), sourceLayer.MaterialId));
        document.Delete(old.Select(e => e.Id).ToList());
        List<Wall> result = new();
        foreach (WallSeed seed in spec.Walls)
        {
            Level level = levels[seed.Storey];
            Line axis = Line.CreateBound(new XYZ(F(seed.X1), F(seed.Y1), level.Elevation), new XYZ(F(seed.X2), F(seed.Y2), level.Elevation));
            Wall wall = Wall.Create(document, axis, type.Id, level.Id, F(3.0), 0.0, false, false);
            SetIfcGuid(wall, seed.Guid);
            wall.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)?.Set("EW3B08 SEED WALL GUID AND GEOMETRY PRESERVED");
            result.Add(wall);
        }
        document.Regenerate();
        return result;
    }

    private static string GetIfcGuid(Element element)
    {
        foreach (string name in new[] { "IfcGUID", "IFC GUID", "GlobalId" })
        {
            string? value = element.LookupParameter(name)?.AsString();
            if (!string.IsNullOrWhiteSpace(value)) return value;
        }
        return string.Empty;
    }

    private static void SetIfcGuid(Element element, string guid)
    {
        foreach (string name in new[] { "IfcGUID", "IFC GUID", "GlobalId" })
        {
            Parameter? p = element.LookupParameter(name);
            if (p is not null && !p.IsReadOnly && p.StorageType == StorageType.String && p.Set(guid)) return;
        }
        throw new InvalidOperationException($"Could not restore IFC GlobalId {guid} on {element.Category?.Name}.");
    }

    private static ViewPlan FindOrCreatePlan(Document document, Level level)
    {
        ViewPlan? plan = new FilteredElementCollector(document).OfClass(typeof(ViewPlan)).Cast<ViewPlan>()
            .FirstOrDefault(view => !view.IsTemplate && view.GenLevel?.Id == level.Id);
        if (plan is not null) return plan;
        ViewFamilyType type = new FilteredElementCollector(document).OfClass(typeof(ViewFamilyType)).Cast<ViewFamilyType>()
            .First(item => item.ViewFamily == ViewFamily.FloorPlan);
        return ViewPlan.Create(document, type.Id, level.Id);
    }

    private static void CreateRoomSeparationLine(Document document, ViewPlan plan, Level level)
    {
        Plane plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, new XYZ(0, 0, level.Elevation));
        SketchPlane sketch = SketchPlane.Create(document, plane);
        CurveArray curves = new();
        curves.Append(Line.CreateBound(new XYZ(F(7.1), F(0.1), level.Elevation), new XYZ(F(7.1), F(6.9), level.Elevation)));
        document.Create.NewRoomBoundaryLines(sketch, curves, plan);
    }

    private static List<CreatedRoom> CreateRooms(Document document, IReadOnlyDictionary<string, Level> levels, WorkflowSpec spec)
    {
        List<CreatedRoom> result = new();
        for (int i = 0; i < spec.Spaces.Count; i++)
        {
            SpaceSpec item = spec.Spaces[i];
            Level level = levels[item.Storey];
            Room room = document.Create.NewRoom(level, new UV(F(item.XM + item.WidthM / 2.0), F(item.YM + item.DepthM / 2.0)))
                ?? throw new InvalidOperationException($"Could not create Room {item.Name}.");
            Set(room.get_Parameter(BuiltInParameter.ROOM_NAME), item.Name);
            Set(room.get_Parameter(BuiltInParameter.ROOM_NUMBER), (i + 1).ToString("00", CultureInfo.InvariantCulture));
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
        double x0=F(roof.XM), x1=F(roof.XM+roof.WidthM), y0=F(roof.YM), y1=F(roof.YM+roof.DepthM), ridge=(y0+y1)/2, z0=F(roof.BaseZM), z1=F(roof.BaseZM+roof.RidgeRiseM);
        List<GeometryObject> solids = new();
        foreach ((XYZ a,XYZ b,XYZ c,XYZ d) face in new[]{
            (new XYZ(x0,y0,z0),new XYZ(x1,y0,z0),new XYZ(x1,ridge,z1),new XYZ(x0,ridge,z1)),
            (new XYZ(x0,ridge,z1),new XYZ(x1,ridge,z1),new XYZ(x1,y1,z0),new XYZ(x0,y1,z0))})
        {
            CurveLoop loop=new(); loop.Append(Line.CreateBound(face.a,face.b)); loop.Append(Line.CreateBound(face.b,face.c)); loop.Append(Line.CreateBound(face.c,face.d)); loop.Append(Line.CreateBound(face.d,face.a));
            solids.Add(GeometryCreationUtilities.CreateExtrusionGeometry(new List<CurveLoop>{loop},XYZ.BasisZ,F(roof.ThicknessM)));
        }
        DirectShape shape=DirectShape.CreateElement(document,new ElementId(BuiltInCategory.OST_Roofs));
        shape.Name="EW3B08 PITCHED ROOF"; shape.ApplicationId=spec.CaseId; shape.ApplicationDataId=spec.Revision+"-ROOF"; shape.SetShape(solids);
        SetIfcGuid(shape, roof.IfcGuid);
    }

    private static void CreateHostedFillings(Document document, IReadOnlyDictionary<string, Level> levels, IReadOnlyList<Wall> walls)
    {
        string doorPath=@"C:\ProgramData\Autodesk\RVT 2025\Libraries\English\US\Doors\M_Door-Single-Panel.rfa";
        string windowPath=@"C:\ProgramData\Autodesk\RVT 2025\Libraries\English\US\Windows\M_Instance-Window-Fixed.rfa";
        if (!document.LoadFamily(doorPath, out Family doorFamily) || !document.LoadFamily(windowPath, out Family windowFamily)) throw new InvalidOperationException("Could not load task-08 hosted families.");
        FamilySymbol door=FirstSymbol(document,doorFamily); FamilySymbol window=FirstSymbol(document,windowFamily);
        SetTypeDimension(door,BuiltInParameter.DOOR_WIDTH,F(1.0)); SetTypeDimension(door,BuiltInParameter.DOOR_HEIGHT,F(2.1));
        SetTypeDimension(window,BuiltInParameter.WINDOW_WIDTH,F(2.0)); SetTypeDimension(window,BuiltInParameter.WINDOW_HEIGHT,F(1.2));
        if(!door.IsActive)door.Activate(); if(!window.IsActive)window.Activate(); document.Regenerate();
        foreach((string name,Wall host,Level level,double x,double y) in new[]{("D-L1-SOUTH",walls[0],levels["Level 1"],1.5,0.0),("D-L1-NORTH",walls[2],levels["Level 1"],8.5,7.0),("D-L2-SOUTH",walls[4],levels["Level 2"],1.5,0.0),("D-L2-NORTH",walls[6],levels["Level 2"],8.5,7.0)})
        {
            FamilyInstance instance=document.Create.NewFamilyInstance(new XYZ(F(x),F(y),level.Elevation),door,host,level,StructuralType.NonStructural);
            instance.get_Parameter(BuiltInParameter.ALL_MODEL_MARK)?.Set(name); instance.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)?.Set("GEOMETRIC-FILLINGS");
        }
        foreach((string name,Wall host,Level level,double x,double y) in new[]{("W-L1-SOUTH",walls[0],levels["Level 1"],5.0,0.0),("W-L1-NORTH",walls[2],levels["Level 1"],5.0,7.0),("W-L2-SOUTH",walls[4],levels["Level 2"],5.0,0.0),("W-L2-NORTH",walls[6],levels["Level 2"],5.0,7.0)})
        {
            FamilyInstance instance=document.Create.NewFamilyInstance(new XYZ(F(x),F(y),level.Elevation),window,host,level,StructuralType.NonStructural);
            Parameter? sill=instance.get_Parameter(BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM); if(sill is not null&&!sill.IsReadOnly)sill.Set(F(1.0));
            instance.get_Parameter(BuiltInParameter.ALL_MODEL_MARK)?.Set(name); instance.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)?.Set("GEOMETRIC-FILLINGS");
        }
    }

    private static FamilySymbol FirstSymbol(Document doc,Family family)=>family.GetFamilySymbolIds().Select(id=>doc.GetElement(id)).OfType<FamilySymbol>().First();
    private static void SetTypeDimension(FamilySymbol symbol,BuiltInParameter id,double value){Parameter? p=symbol.get_Parameter(id);if(p is not null&&!p.IsReadOnly)p.Set(value);}

    private static void EnsureSharedParameters(Document document,IReadOnlyList<string> names)
    {
        Application app=document.Application; string original=app.SharedParametersFilename; string temp=Path.Combine(Path.GetTempPath(),"EngiWorld_task08_params.txt");
        File.WriteAllText(temp,"# This is a Revit shared parameter file.\r\n*META\tVERSION\tMINVERSION\r\nMETA\t2\t1\r\n",new UTF8Encoding(false));
        try{app.SharedParametersFilename=temp;DefinitionFile file=app.OpenSharedParameterFile()??throw new InvalidOperationException("Shared parameter file failed.");DefinitionGroup group=file.Groups.get_Item("EngiWorld")??file.Groups.Create("EngiWorld");CategorySet cats=app.Create.NewCategorySet();cats.Insert(document.Settings.Categories.get_Item(BuiltInCategory.OST_Rooms));InstanceBinding binding=app.Create.NewInstanceBinding(cats);foreach(string name in names){Definition? existing=group.Definitions.get_Item(name);Definition d=existing??group.Definitions.Create(new ExternalDefinitionCreationOptions(name,SpecTypeId.String.Text));if(!document.ParameterBindings.Insert(d,binding,GroupTypeId.Data))document.ParameterBindings.ReInsert(d,binding,GroupTypeId.Data);}}
        finally{app.SharedParametersFilename=original;File.Delete(temp);}
        string builtIn=@"C:\Program Files\Autodesk\Revit 2025\IFC Shared Parameters-RevitIFCBuiltIn_ALL.txt";
        try{app.SharedParametersFilename=builtIn;DefinitionFile file=app.OpenSharedParameterFile()??throw new InvalidOperationException("IFC parameters failed.");CategorySet cats=app.Create.NewCategorySet();foreach(BuiltInCategory c in new[]{BuiltInCategory.OST_Rooms,BuiltInCategory.OST_Walls,BuiltInCategory.OST_Roofs})cats.Insert(document.Settings.Categories.get_Item(c));InstanceBinding binding=app.Create.NewInstanceBinding(cats);foreach(string name in new[]{"IfcGUID","Qto_SpaceBaseQuantities.GrossFloorArea","Qto_SpaceBaseQuantities.NetFloorArea"}){Definition? d=null;foreach(DefinitionGroup g in file.Groups){d=g.Definitions.get_Item(name);if(d is not null)break;}if(d is null)continue;if(!document.ParameterBindings.Insert(d,binding,GroupTypeId.Data))document.ParameterBindings.ReInsert(d,binding,GroupTypeId.Data);}}
        finally{app.SharedParametersFilename=original;}
    }

    private static void Set(Parameter? p,string value){if(p is null||p.IsReadOnly||!p.Set(value))throw new InvalidOperationException($"Could not set parameter to {value}.");}
    private static void SetArea(Parameter? p,double value){if(p is null||p.IsReadOnly||!p.Set(value))throw new InvalidOperationException("Could not set IFC area quantity.");}
    private static void WriteUserDefinedPset(string path,IReadOnlyList<string> names){StringBuilder s=new();s.AppendLine("PropertySet:\tEngiWorld_EnergyHandoff\tI\tIfcSpace");foreach(string n in names)s.Append('\t').Append(n).Append("\tText\t").AppendLine(n);File.WriteAllText(path,s.ToString(),new UTF8Encoding(false));}
    private static string FindNamedGuid(string text,string cls,string name){foreach(Match m in Regex.Matches(text,$@"{cls}\s*\(\s*'([^']+)'[^;]*;",RegexOptions.IgnoreCase|RegexOptions.Singleline))if(m.Value.IndexOf(name,StringComparison.OrdinalIgnoreCase)>=0)return m.Groups[1].Value;throw new InvalidDataException($"Missing {cls} named {name}.");}

    private static FillingGraph ParseFillingGraph(string text)
    {
        FillingGraph g=new();
        Dictionary<string,(string cls,string guid)> entities=new();
        foreach(Match m in Regex.Matches(text,@"#(\d+)\s*=\s*(IFC[A-Z0-9_]+)\s*\(\s*'([^']+)'",RegexOptions.IgnoreCase))entities[m.Groups[1].Value]=(m.Groups[2].Value.ToUpperInvariant(),m.Groups[3].Value);
        foreach(var pair in entities){if(pair.Value.cls=="IFCDOOR")g.Doors.Add(pair.Value.guid);else if(pair.Value.cls=="IFCWINDOW")g.Windows.Add(pair.Value.guid);else if(pair.Value.cls=="IFCOPENINGELEMENT")g.Openings.Add(pair.Value.guid);}
        foreach(Match m in Regex.Matches(text,@"IFCRELVOIDSELEMENT\s*\(\s*'([^']+)'[^;]*,#(\d+)\s*,\s*#(\d+)\s*\)\s*;",RegexOptions.IgnoreCase|RegexOptions.Singleline))if(entities.TryGetValue(m.Groups[2].Value,out var host)&&entities.TryGetValue(m.Groups[3].Value,out var opening))g.VoidRelations.Add(new Relation(m.Groups[1].Value,host.guid,opening.guid));
        foreach(Match m in Regex.Matches(text,@"IFCRELFILLSELEMENT\s*\(\s*'([^']+)'[^;]*,#(\d+)\s*,\s*#(\d+)\s*\)\s*;",RegexOptions.IgnoreCase|RegexOptions.Singleline))if(entities.TryGetValue(m.Groups[2].Value,out var opening)&&entities.TryGetValue(m.Groups[3].Value,out var filling))g.FillRelations.Add(new Relation(m.Groups[1].Value,opening.guid,filling.guid));
        return g;
    }

    private static void WriteHandoff(string path,string input,string output,IReadOnlyList<CreatedRoom> rooms,FillingGraph graph,WorkflowSpec spec)
    {
        string exe=@"C:\Program Files\Autodesk\Revit 2025\Revit.exe";FileVersionInfo v=FileVersionInfo.GetVersionInfo(exe);
        object payload=new{case_id=spec.CaseId,software_stage="revit",source_file="stage1.ifc",source_sha256=Sha256(output),input_seed_sha256=Sha256(input),
            spaces=rooms.Select(r=>new{name=r.Spec.Name,ifc_guid=r.IfcGuid,retained_seed_guid=r.Spec.RetainedGuid,area_m2=Math.Round(r.AreaM2,6),storey=r.Spec.Storey,thermal_zone=r.Spec.ThermalZone,schedule_category=r.Spec.ScheduleCategory,people_per_m2=r.Spec.PeoplePerM2,lighting_w_per_m2=r.Spec.LightingWPerM2,equipment_w_per_m2=r.Spec.EquipmentWPerM2,outdoor_air_l_per_s_person=r.Spec.OutdoorAirLPerSPerson,stage="revit"}).ToArray(),
            hosted_fillings=new{doors=graph.Doors,windows=graph.Windows,openings=graph.Openings,void_relations=graph.VoidRelations,fill_relations=graph.FillRelations},
            preserved_seed=new{wall_global_ids=spec.Walls.Select(w=>w.Guid).ToArray(),slab_global_ids=spec.SlabGuids.ToArray(),retained_space_global_ids=spec.Spaces.Where(s=>!string.IsNullOrEmpty(s.RetainedGuid)).Select(s=>s.RetainedGuid).ToArray()},
            stage1_tokens=spec.Stage1Tokens.Concat(new[]{spec.CaseId}).Distinct().ToArray(),downstream_consumer="archicad",native_provenance=new{exe,product_version=v.FileVersion,product_build=v.ProductVersion,automation="EngiWorld.BimBridge IExternalApplication executed from Revit 2025 Idling",completed_utc=DateTime.UtcNow.ToString("o",CultureInfo.InvariantCulture)}};
        File.WriteAllText(path,JsonSerializer.Serialize(payload,new JsonSerializerOptions{WriteIndented=true})+Environment.NewLine,new UTF8Encoding(false));
    }
    private static string Sha256(string path){using SHA256 a=SHA256.Create();using FileStream s=File.OpenRead(path);return Convert.ToHexString(a.ComputeHash(s)).ToLowerInvariant();}
    private static void TryExit(UIApplication app){try{RevitCommandId id=RevitCommandId.LookupPostableCommandId(PostableCommand.ExitRevit);if(app.CanPostCommand(id))app.PostCommand(id);}catch{}}
}

internal sealed class DeleteWarningsPreprocessor:IFailuresPreprocessor{public FailureProcessingResult PreprocessFailures(FailuresAccessor a){foreach(FailureMessageAccessor w in a.GetFailureMessages())if(w.GetSeverity()==FailureSeverity.Warning)a.DeleteWarning(w);return FailureProcessingResult.Continue;}}
internal sealed class CreatedRoom{public CreatedRoom(Room room,SpaceSpec spec){Room=room;Spec=spec;}public Room Room{get;}public SpaceSpec Spec{get;}public double AreaM2{get;set;}public string IfcGuid{get;set;}="";}
internal sealed record Relation(string relation_guid,string first_guid,string second_guid);
internal sealed class FillingGraph{public List<string> Doors{get;}=new();public List<string> Windows{get;}=new();public List<string> Openings{get;}=new();public List<Relation> VoidRelations{get;}=new();public List<Relation> FillRelations{get;}=new();}

internal sealed class WorkflowSpec
{
    public string CaseId{get;private set;}="";public string Revision{get;private set;}="";public List<string> SlabGuids{get;}=new();public List<SpaceSpec> Spaces{get;}=new();public List<WallSeed> Walls{get;}=new();public List<string> Stage1Tokens{get;}=new();public RoofSpec Roof{get;private set;}=new();
    public IReadOnlyList<string> ParameterNames{get;}=new[]{"ThermalZone","ScheduleCategory","PeoplePerM2","LightingPowerDensityWPerM2","EquipmentPowerDensityWPerM2","OutdoorAirLPerSPerson"};
    public static WorkflowSpec Load(string path){using JsonDocument j=JsonDocument.Parse(File.ReadAllText(path));JsonElement r=j.RootElement;WorkflowSpec s=new(){CaseId=r.GetProperty("case_id").GetString()??"",Revision=r.GetProperty("revision").GetString()??""};foreach(JsonElement id in r.GetProperty("seed_preservation").GetProperty("slab_global_ids").EnumerateArray())s.SlabGuids.Add(id.GetString()??"");foreach(JsonElement t in r.GetProperty("revit_stage").GetProperty("required_tokens").EnumerateArray())s.Stage1Tokens.Add(t.GetString()??"");foreach(JsonElement e in r.GetProperty("spaces").EnumerateArray())s.Spaces.Add(SpaceSpec.Load(e));foreach(JsonElement e in r.GetProperty("seed_preservation").GetProperty("walls").EnumerateArray())s.Walls.Add(WallSeed.Load(e));s.Roof=RoofSpec.Load(r.GetProperty("roof_geometry"));if(s.Spaces.Count!=4||s.Walls.Count!=8||s.SlabGuids.Count!=2)throw new InvalidDataException("Task-08 requires four spaces, eight seed walls and two seed slabs.");return s;}
}
internal sealed class WallSeed{public string Guid{get;private set;}="";public string Storey{get;private set;}="";public double X1{get;private set;}public double Y1{get;private set;}public double X2{get;private set;}public double Y2{get;private set;}public static WallSeed Load(JsonElement e)=>new(){Guid=e.GetProperty("global_id").GetString()??"",Storey=e.GetProperty("storey").GetString()??"",X1=e.GetProperty("x1_m").GetDouble(),Y1=e.GetProperty("y1_m").GetDouble(),X2=e.GetProperty("x2_m").GetDouble(),Y2=e.GetProperty("y2_m").GetDouble()};}
internal sealed class RoofSpec{public string IfcGuid{get;private set;}="";public double XM{get;private set;}public double YM{get;private set;}public double WidthM{get;private set;}public double DepthM{get;private set;}public double BaseZM{get;private set;}public double RidgeRiseM{get;private set;}public double ThicknessM{get;private set;}public static RoofSpec Load(JsonElement e)=>new(){IfcGuid=e.GetProperty("ifc_guid").GetString()??"",XM=e.GetProperty("x_m").GetDouble(),YM=e.GetProperty("y_m").GetDouble(),WidthM=e.GetProperty("width_m").GetDouble(),DepthM=e.GetProperty("depth_m").GetDouble(),BaseZM=e.GetProperty("base_z_m").GetDouble(),RidgeRiseM=e.GetProperty("ridge_rise_m").GetDouble(),ThicknessM=e.GetProperty("thickness_m").GetDouble()};}
internal sealed class SpaceSpec
{
    public string Name{get;private set;}="";public string IfcGuid{get;private set;}="";public string ThermalZone{get;private set;}="";public string Storey{get;private set;}="";public string RetainedGuid{get;private set;}="";public double XM{get;private set;}public double YM{get;private set;}public double WidthM{get;private set;}public double DepthM{get;private set;}public double HeightM{get;private set;}public string ScheduleCategory{get;private set;}="";public double PeoplePerM2{get;private set;}public double LightingWPerM2{get;private set;}public double EquipmentWPerM2{get;private set;}public double OutdoorAirLPerSPerson{get;private set;}
    public static SpaceSpec Load(JsonElement e){JsonElement g=e.GetProperty("energy_geometry"),s=e.GetProperty("energy_semantics");return new(){Name=e.GetProperty("name").GetString()??"",IfcGuid=e.GetProperty("ifc_guid").GetString()??"",ThermalZone=e.GetProperty("thermal_zone").GetString()??"",Storey=e.GetProperty("storey").GetString()??"",RetainedGuid=e.TryGetProperty("retained_seed_global_id",out JsonElement id)?id.GetString()??"":"",XM=g.GetProperty("x_m").GetDouble(),YM=g.GetProperty("y_m").GetDouble(),WidthM=g.GetProperty("width_m").GetDouble(),DepthM=g.GetProperty("depth_m").GetDouble(),HeightM=g.GetProperty("height_m").GetDouble(),ScheduleCategory=s.GetProperty("schedule_category").GetString()??"",PeoplePerM2=s.GetProperty("people_per_m2").GetDouble(),LightingWPerM2=s.GetProperty("lighting_w_per_m2").GetDouble(),EquipmentWPerM2=s.GetProperty("equipment_w_per_m2").GetDouble(),OutdoorAirLPerSPerson=s.GetProperty("outdoor_air_l_per_s_person").GetDouble()};}
}
