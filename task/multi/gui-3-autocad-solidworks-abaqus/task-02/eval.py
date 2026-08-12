# -*- coding: utf-8 -*-
from __future__ import print_function
import os, sys, traceback, math, json, subprocess, re, shutil
try:
    from abaqus import mdb, openMdb
    from odbAccess import openOdb
    try:
        from abaqusConstants import THREE_D, DEFORMABLE_BODY
    except Exception:
        THREE_D = None; DEFORMABLE_BODY = None
except Exception:
    mdb = None; openMdb = None; openOdb = None; THREE_D = None; DEFORMABLE_BODY = None
SPEC = {'any_odb_fields': [],
 'bbox': [120, 120, 10],
 'bbox_tol': 0.1,
 'bc_checks': [{'kind': 'constraint', 'name': 'BC-BoltHoles', 'region': 'BOLT_HOLES'}],
 'bc_names': ['BC-BoltHoles'],
 'cad_text': 'AutoCAD: draw outside circle D120 on OUTLINE, centered D50 opening on CUTOUT, and '
             'eight D6 bolt holes on HOLE equally spaced on a 90 mm bolt circle; save '
             'stage1_profile.dxf. SolidWorks: import it, create a 10 mm thick flange cover with a '
             '2 mm deep central recess, export C:\\Users\\User\\Desktop\\stage2_geometry.step.',
 'cae_text': 'Import stage2_geometry.step. Create Steel E=210000 MPa nu=0.3. Create set BOLT_HOLES '
             'and surface PRESSURE_FACE, fix U1/U2/U3 on BOLT_HOLES, apply 1.0 MPa pressure to '
             'PRESSURE_FACE, submit Job-DxfFlangePressure.',
 'chain': 'three',
 'chain_evidence': {'cae_markers': ['EW_ACAD_SW_ABQ_02', 'IMPORTED_FROM_stage2_geometry.step'],
                    'dxf_markers': ['EW_ACAD_SW_ABQ_02', 'AUTOCAD_TO_SOLIDWORKS'],
                    'step_markers': ['EW_ACAD_SW_ABQ_02',
                                     'FROM_stage1_profile.dxf',
                                     'SOLIDWORKS_TO_ABAQUS']},
 'chain_token': 'EW_ACAD_SW_ABQ_02',
 'dxf_checks': {'bbox': [120, 120],
                'circle_radii': [{'count': 1, 'r': 60.0},
                                 {'count': 1, 'r': 25.0},
                                 {'count': 8, 'r': 3.0}],
                'layers': ['OUTLINE', 'HOLE', 'CUTOUT'],
                'min_circles': 10,
                'tol': 0.05},
 'expected_step_volume_mm3': 106908.398002,
 'step_volume_tol_mm3': 2.0,
 'expected_cae_surface_area_mm2': 27759.112687,
 'expected_pressure_area_mm2': 1963.495408,
 'expected_pressure_resultant_n': 1963.495408,
 'expected_field_any': ['U', 'S'],
 'job_name': 'Job-DxfFlangePressure',
 'load_checks': [{'kind': 'pressure', 'magnitude': 1.0, 'name': 'Pressure-1MPa',
                  'region': 'PRESSURE_FACE', 'sign': 'positive',
                  'abs_tol': 0.05, 'rel_tol': 0.1}],
 'load_names': ['Pressure-1MPa'],
 'material': {'E': 210000, 'name': 'Steel', 'nu': 0.3},
 'min_elements': 1,
 'max_nodes': 1000,
 'min_frames': 2,
 'model_name': 'Model-DxfFlangePressure',
 'nonzero_odb_fields': ['U', 'S'],
 'required_files': ['stage1_profile.dxf',
                    'stage2_geometry.step',
                    'Job-DxfFlangePressure.cae',
                    'Job-DxfFlangePressure.odb'],
 'required_odb_fields': ['U', 'S', 'RF', 'NFORC1', 'NFORC2', 'NFORC3'],
 'required_cae_output_variables': ['U', 'S', 'RF', 'NFORC', 'CF'],
 'required_sets': ['BOLT_HOLES'],
 'required_surfaces': ['PRESSURE_FACE'],
 'section_material': 'Steel',
 'stage_dxf': 'stage1_profile.dxf',
 'stage_step': 'stage2_geometry.step',
 'step_kind': 'STATIC',
 'step_name': 'Step-Pressure',
 'task_no': 2,
 'title': 'DXF Flange Cover Pressure Analysis'}
DETAILS=[]
DXF_AUDIT={}
STEP_AUDIT={}
CAE_AUDIT={}
CAE_OPENED=False
FORBIDDEN=set(['.py','.pyw','.ipynb','.bat','.cmd','.ps1','.psm1','.vbs','.js','.mjs','.scr','.macro','.bas','.vba','.ahk','.sh'])
DELIVERABLE_EXTS=set(['.step','.stp','.dxf','.cae','.odb'])


def log(x): DETAILS.append(str(x))
def fail(x): log('[FAIL] '+str(x)); return False
def ok(x): log('[PASS] '+str(x)); return True
def warn(x): log('[WARN] '+str(x))
def ci(x): return str('' if x is None else x).strip().upper()
def nn(x): return ci(x).replace('-','_').replace(' ','_')

def close(a,b,t):
    try: return abs(float(a)-float(b)) <= float(t)
    except Exception: return False

def close_rel(a,b,abs_tol=1.0e-6,rel_tol=1.0e-2):
    try:
        fa=float(a); fb=float(b)
        return abs(fa-fb) <= max(float(abs_tol), abs(fb)*float(rel_tol))
    except Exception: return False


def desktop():
    c=[]
    up=os.environ.get('USERPROFILE')
    if up: c.append(os.path.join(up,'Desktop'))
    c += [r'C:\Users\user\Desktop', r'C:\Users\User\Desktop']
    for p in c:
        if os.path.isdir(p): return p
    return c[0]

def dp(name): return os.path.join(desktop(), name)

def nonempty(path, n=1):
    try: return os.path.isfile(path) and os.path.getsize(path) >= n
    except Exception: return False


def eval_cae_dir():
    base=os.environ.get('TEMP') or os.environ.get('TMP') or desktop()
    return os.path.join(base,'engiworld_eval_cae_task02')


def eval_cae_path(): return os.path.join(eval_cae_dir(),SPEC['job_name']+'.cae')


def cleanup_eval_cae():
    global CAE_OPENED
    try:
        if CAE_OPENED and mdb is not None: mdb.close()
    except Exception: pass
    CAE_OPENED=False
    directory=eval_cae_dir()
    try:
        for name in os.listdir(directory):
            if name.lower().startswith(SPEC['job_name'].lower()+'.'):
                try: os.remove(os.path.join(directory,name))
                except Exception: pass
        os.rmdir(directory)
    except Exception: pass


def open_cae_for_eval():
    global CAE_OPENED
    if CAE_OPENED: return True
    source=dp(SPEC['job_name']+'.cae')
    if not nonempty(source,1024): return False
    cleanup_eval_cae()
    directory=eval_cae_dir()
    if not os.path.isdir(directory): os.makedirs(directory)
    target=eval_cae_path()
    shutil.copyfile(source,target)
    openMdb(pathName=target)
    CAE_OPENED=True
    return True


def write(path, text):
    try:
        f=open(path,'w'); f.write(text); f.close()
    except Exception: pass


def finish(v):
    text='True\n' if v else 'False\n'
    write(dp('eval_detail.txt'), '\n'.join(DETAILS)+'\n')
    write(dp('eval_result.txt'), text)
    cleanup_eval_inp()
    cleanup_eval_cae()
    try: sys.__stdout__.write(text); sys.__stdout__.flush()
    except Exception: sys.stdout.write(text); sys.stdout.flush()
    raise SystemExit(0)


def check_bypass():
    try: names=os.listdir(desktop())
    except Exception: return fail('Cannot list Desktop')
    for name in names:
        full=os.path.join(desktop(), name)
        if not os.path.isfile(full): continue
        lower=name.lower()
        if lower == 'eval.py': continue
        ext=os.path.splitext(lower)[1]
        if ext in FORBIDDEN: return fail('Forbidden script-like file on Desktop: '+name)
    return ok('No forbidden script artifacts')


def check_extra_deliverables():
    allowed=set([x.lower() for x in SPEC.get('required_files',[])])
    allowed.update(['eval.py','eval_detail.txt','eval_result.txt'])
    try: names=os.listdir(desktop())
    except Exception: return fail('Cannot list Desktop for deliverable audit')
    for name in names:
        full=os.path.join(desktop(), name)
        if not os.path.isfile(full): continue
        lower=name.lower()
        ext=os.path.splitext(lower)[1]
        if ext in DELIVERABLE_EXTS and lower not in allowed:
            return fail('Unexpected extra CAD/CAE deliverable on Desktop: '+name)
    return ok('No unexpected CAD/CAE deliverables')


def head(path, n=4000000):
    try:
        f=open(path,'rb'); data=f.read(n); f.close()
        try: return data.decode('utf-8','ignore')
        except Exception: return str(data)
    except Exception: return ''


def dxf_float(value):
    try: return float(value)
    except Exception: return None


def parse_dxf(path):
    code=r'''
import json, sys
try:
    import ezdxf
    from ezdxf.disassemble import recursive_decompose
    doc=ezdxf.readfile(sys.argv[1])
    circles=[]; texts=[]; layers=set()
    for entity in recursive_decompose(doc.modelspace()):
        kind=entity.dxftype().upper(); layer=str(entity.dxf.get('layer',''))
        layers.add(layer.upper())
        if kind == 'CIRCLE':
            center=entity.dxf.center
            circles.append({'x':float(center.x),'y':float(center.y),
                            'r':float(entity.dxf.radius),'layer':layer})
        elif kind == 'TEXT':
            texts.append({'layer':layer,'text':str(entity.dxf.text),
                          'height':float(entity.dxf.height),'type':kind})
        elif kind == 'MTEXT':
            texts.append({'layer':layer,'text':str(entity.plain_text()),
                          'height':float(entity.dxf.char_height),'type':kind})
    out={'ok':True,'layers':sorted(layers),'circles':circles,'texts':texts}
except Exception as exc:
    out={'ok':False,'error':repr(exc)}
sys.stdout.write('__DXF_METRICS__'+json.dumps(out))
'''
    errors=[]
    for exe in [r'C:\Program Files\Python311\python.exe','python']:
        try:
            if os.path.isabs(exe) and not os.path.isfile(exe):
                errors.append(exe+' not found'); continue
            env=dict(os.environ)
            for key in list(env.keys()):
                if key.upper().startswith('PYTHON'): env.pop(key,None)
            raw=subprocess.check_output([exe,'-E','-c',code,path],env=env)
            if not isinstance(raw,str): raw=raw.decode('utf-8','ignore')
            marker=raw.rfind('__DXF_METRICS__')
            if marker < 0:
                errors.append(exe+' produced no metrics marker: '+raw[-300:]); continue
            data=json.loads(raw[marker+len('__DXF_METRICS__'):].strip())
            if data.get('ok'): return data
            errors.append(exe+': '+str(data.get('error','unknown')))
        except Exception as exc: errors.append(exe+': '+str(exc))
    raise RuntimeError('; '.join(errors))


def check_dxf_chain_text(data):
    texts=[row for row in data['texts'] if ci(row.get('layer')) == 'CHAIN' and float(row.get('height') or 0.0) > 0.0]
    if not texts: return fail('DXF CHAIN layer has no readable native TEXT/MTEXT entity')
    blob='\n'.join(row.get('text','') for row in texts)
    for marker in SPEC.get('chain_evidence',{}).get('dxf_markers',[]):
        if not chain_contains(blob,marker): return fail('Missing native DXF chain text: '+marker)
    return True


def check_dxf():
    global DXF_AUDIT
    DXF_AUDIT={}
    ds=SPEC.get('dxf_checks')
    if not ds: return ok('No DXF stage')
    path=dp(SPEC['stage_dxf'])
    if not nonempty(path,200): return fail('Missing DXF stage: '+path)
    data=parse_dxf(path); layers=data['layers']; circles=data['circles']
    for layer in ds.get('layers',[]):
        if ci(layer) not in layers: return fail('Missing DXF layer '+layer)
    tol=float(ds.get('tol',0.05))
    outline=[c for c in circles if ci(c.get('layer')) == 'OUTLINE']
    cutout=[c for c in circles if ci(c.get('layer')) == 'CUTOUT']
    holes=[c for c in circles if ci(c.get('layer')) == 'HOLE']
    if len(outline) != 1 or not close(outline[0]['r'],60.0,tol):
        return fail('DXF OUTLINE must contain exactly one D120 circle')
    if len(cutout) != 1 or not close(cutout[0]['r'],25.0,tol):
        return fail('DXF CUTOUT must contain exactly one D50 recess-boundary circle')
    center=(outline[0]['x'],outline[0]['y'])
    if not (close(cutout[0]['x'],center[0],tol) and close(cutout[0]['y'],center[1],tol)):
        return fail('DXF D50 recess boundary is not concentric with the D120 outline')
    if len(holes) != 8 or any(not close(hole['r'],3.0,tol) for hole in holes):
        return fail('DXF HOLE layer must contain exactly eight D6 circles')
    angles=[]
    for hole in holes:
        dx=hole['x']-center[0]; dy=hole['y']-center[1]
        radius=math.sqrt(dx*dx+dy*dy)
        if not close(radius,45.0,tol): return fail('DXF bolt hole is not on the 90 mm PCD')
        angles.append(math.atan2(dy,dx)%(2.0*math.pi))
    angles.sort()
    gaps=[(angles[(index+1)%8]-angles[index])%(2.0*math.pi) for index in range(8)]
    if any(abs(gap-math.pi/4.0) > 0.01 for gap in gaps):
        return fail('DXF eight-hole pattern is not evenly spaced at 45 degrees')
    if not check_dxf_chain_text(data): return False
    DXF_AUDIT={'center':center,'hole_centers':[(hole['x'],hole['y']) for hole in holes],
               'phase':angles[0] if angles else 0.0}
    return ok('DXF checks passed')


def dims_close(got, exp, tol):
    if len(got) != len(exp): return False
    g=sorted([abs(float(x)) for x in got]); e=sorted([abs(float(x)) for x in exp])
    return all(abs(a-b) <= tol for a,b in zip(g,e))


def external_cadquery_step_metrics(path):
    code = r'''
import json, sys, traceback
try:
    import cadquery as cq
    wp = cq.importers.importStep(sys.argv[1])
    solids = wp.solids().vals()
    if len(solids) != 1:
        out = {"ok": False, "error": "STEP must contain exactly one solid", "solid_count": len(solids)}
    else:
        solid = solids[0]
        box = solid.BoundingBox()
        faces = []
        for index, face in enumerate(solid.Faces()):
            row = {"index": index, "geom_type": str(face.geomType()),
                   "area": float(face.Area()), "center": [float(v) for v in face.Center().toTuple()]}
            if row["geom_type"].upper() == "CYLINDER":
                cylinder = face._geomAdaptor().Cylinder()
                row["radius"] = float(cylinder.Radius())
                row["axis_location"] = [float(v) for v in cylinder.Location().Coord()]
                row["axis_direction"] = [float(v) for v in cylinder.Axis().Direction().Coord()]
            faces.append(row)
        out = {"ok": True, "bbox": [box.xmin,box.ymin,box.zmin,box.xmax,box.ymax,box.zmax],
               "volume": float(solid.Volume()), "face_count": len(faces), "faces": faces}
except Exception as exc:
    out = {"ok": False, "error": repr(exc), "traceback": traceback.format_exc()}
sys.stdout.write("__CQ_METRICS__" + json.dumps(out))
'''
    errors = []
    for exe in [r'C:\Program Files\Python311\python.exe', 'python']:
        try:
            if os.path.isabs(exe) and not os.path.isfile(exe):
                errors.append(exe + ' not found')
                continue
            env = dict(os.environ)
            for key in list(env.keys()):
                if key.upper().startswith('PYTHON'):
                    env.pop(key, None)
            raw = subprocess.check_output([exe, '-E', '-c', code, path], env=env)
            if not isinstance(raw, str): raw = raw.decode('utf-8', 'ignore')
            marker = raw.rfind('__CQ_METRICS__')
            if marker < 0:
                errors.append(exe + ' produced no metrics marker: ' + raw[-300:])
                continue
            return json.loads(raw[marker + len('__CQ_METRICS__'):].strip())
        except Exception as exc:
            errors.append(exe + ': ' + str(exc))
    return {"ok": False, "error": '; '.join(errors)}


def strip_step_comments(text):
    return re.sub(r'/\*.*?\*/','',text,flags=re.S)


def step_native_strings(text):
    clean=strip_step_comments(text)
    data_index=clean.upper().find('DATA;')
    if data_index >= 0: clean=clean[data_index:]
    values=[]
    for match in re.findall(r"'(?:''|[^'])*'",clean):
        values.append(match[1:-1].replace("''", "'"))
    return values


def group_cylinders(faces, radius, axis, planar, tol=0.05):
    groups=[]
    for face in faces:
        if ci(face.get('geom_type')) != 'CYLINDER' or not close(face.get('radius'),radius,tol): continue
        direction=face.get('axis_direction') or []
        location=face.get('axis_location') or []
        if len(direction) != 3 or len(location) != 3 or abs(float(direction[axis])) < 0.99: continue
        key=(float(location[planar[0]]),float(location[planar[1]]))
        match=None
        for group in groups:
            if close(group['center'][0],key[0],0.1) and close(group['center'][1],key[1],0.1): match=group; break
        if match is None:
            match={'center':key,'area':0.0,'faces':0}; groups.append(match)
        match['area'] += float(face.get('area') or 0.0); match['faces'] += 1
    return groups


def evenly_spaced_centers(groups, center, radius, count):
    if len(groups) != count: return False
    angles=[]
    for group in groups:
        dx=group['center'][0]-center[0]; dy=group['center'][1]-center[1]
        if not close(math.sqrt(dx*dx+dy*dy),radius,0.1): return False
        angles.append(math.atan2(dy,dx)%(2.0*math.pi))
    angles.sort()
    return all(abs(((angles[(i+1)%count]-angles[i])%(2.0*math.pi))-2.0*math.pi/count) < 0.01 for i in range(count))


def bolt_pattern_phase(centers, center, count=8):
    if len(centers) != count: return None
    period=2.0*math.pi/float(count)
    phases=[]
    for point in centers:
        try: angle=math.atan2(float(point[1])-float(center[1]),float(point[0])-float(center[0]))
        except Exception: return None
        phases.append(angle%period)
    base=phases[0]
    if any(min(abs(value-base),period-abs(value-base)) > 0.01 for value in phases[1:]): return None
    return base


def bolt_pattern_phases_match(first, second, count=8, tolerance=0.01):
    if first is None or second is None: return False
    period=2.0*math.pi/float(count)
    def distance(a,b):
        delta=abs((a-b)%period)
        return min(delta,period-delta)
    # Swapping or reflecting the planar import axes reverses the angular phase.
    return min(distance(first,second),distance(first,(-second)%period)) <= tolerance


def check_step():
    global STEP_AUDIT
    STEP_AUDIT={}
    path=dp(SPEC['stage_step'])
    if not nonempty(path, 1): return fail('Missing STEP stage: '+path)
    text=head(path); h=text[:4096].upper()
    if 'ISO-10303' not in h and 'STEP' not in h: return fail('STEP header not recognized')
    clean_header=strip_step_comments(text[:12000]).upper()
    if 'SWSTEP' not in clean_header or 'SOLIDWORKS 2025' not in clean_header:
        return fail('STEP was not exported by native SOLIDWORKS 2025')
    native_strings=step_native_strings(text)
    for marker in SPEC.get('chain_evidence',{}).get('step_markers',[]):
        if not any(chain_contains(value,marker) for value in native_strings):
            return fail('STEP marker is missing from one quoted native DATA entity: '+marker)
    ext=external_cadquery_step_metrics(path)
    if not ext.get('ok'):
        if ext.get('solid_count') is not None: return fail('STEP must contain exactly one solid')
        return fail('STEP geometry could not be validated with CadQuery: '+str(ext.get('error','unknown')))
    bbox=ext.get('bbox') or []
    if len(bbox) != 6: return fail('STEP bounding box is unreadable')
    low=bbox[:3]; high=bbox[3:]; dims=[high[i]-low[i] for i in range(3)]
    if not dims_close(dims,SPEC['bbox'],SPEC.get('bbox_tol',0.1)):
        return fail('STEP bbox mismatch got %s expected %s'%(dims,SPEC['bbox']))
    volume=float(ext.get('volume') or 0.0)
    if not close(volume,SPEC['expected_step_volume_mm3'],SPEC['step_volume_tol_mm3']):
        return fail('STEP volume mismatch got %s expected %s'%(volume,SPEC['expected_step_volume_mm3']))
    axis=min(range(3),key=lambda index:dims[index]); planar=[index for index in range(3) if index != axis]
    center3=[(low[i]+high[i])/2.0 for i in range(3)]
    center=(center3[planar[0]],center3[planar[1]])
    faces=ext.get('faces') or []
    holes=group_cylinders(faces,3.0,axis,planar)
    if not evenly_spaced_centers(holes,center,45.0,8):
        return fail('STEP does not contain eight evenly spaced D6 through holes on a 90 mm PCD')
    step_phase=bolt_pattern_phase([group['center'] for group in holes],center)
    expected_hole_area=2.0*math.pi*3.0*10.0
    if any(not close(group['area'],expected_hole_area,0.5) for group in holes):
        return fail('STEP D6 holes are not through the full 10 mm thickness')
    recess=group_cylinders(faces,25.0,axis,planar)
    if len(recess) != 1 or not close(recess[0]['center'][0],center[0],0.1) or not close(recess[0]['center'][1],center[1],0.1):
        return fail('STEP lacks a centered D50 blind-recess wall')
    if not close(recess[0]['area'],2.0*math.pi*25.0*2.0,0.5):
        return fail('STEP D50 recess wall is not 2 mm deep')
    outer=group_cylinders(faces,60.0,axis,planar)
    if len(outer) != 1 or not close(outer[0]['area'],2.0*math.pi*60.0*10.0,1.0):
        return fail('STEP outer D120 wall is not 10 mm thick')
    pressure=[]
    for face in faces:
        if ci(face.get('geom_type')) != 'PLANE' or not close(face.get('area'),SPEC['expected_pressure_area_mm2'],1.0): continue
        fc=face.get('center') or []
        if len(fc) != 3: continue
        centered=close(fc[planar[0]],center[0],0.1) and close(fc[planar[1]],center[1],0.1)
        depth=close(fc[axis],low[axis]+2.0,0.1) or close(fc[axis],high[axis]-2.0,0.1)
        if centered and depth: pressure.append(face)
    if len(pressure) != 1: return fail('STEP lacks one centered D50 pressure floor 2 mm from an outer face')
    STEP_AUDIT={'axis':axis,'planar':planar,'center':center,'hole_centers':[group['center'] for group in holes],
                'phase':step_phase,'volume':volume}
    log('[PASS] STEP external CadQuery import and analytic geometry checks passed')
    return ok('STEP geometry, blind recess, provenance, and volume checks passed')



def chain_norm(value):
    out=[]
    for ch in ci(value):
        if ch.isalnum(): out.append(ch)
    return ''.join(out)


def chain_contains(blob, marker):
    return chain_norm(marker) in chain_norm(blob)


def check_chain_markers(blob, markers, context):
    for marker in markers:
        if not chain_contains(blob, marker):
            return fail('Missing chain evidence in %s: %s' % (context, marker))
    return True


def cae_chain_blob(model):
    names=[]
    def add(value):
        if value is None: return
        try: names.append(str(value))
        except Exception: pass
    add(SPEC.get('model_name'))
    add(getattr(model, 'name', None))
    add(getattr(model, 'description', None))
    for mapping_name in ['parts','materials','sections','steps','loads','boundaryConditions','interactions']:
        mapping=getattr(model, mapping_name, None)
        if mapping is None: continue
        try: items=list(mapping.items())
        except Exception:
            try: items=[(k, mapping[k]) for k in mapping.keys()]
            except Exception: items=[]
        for key,obj in items:
            add(key); add(getattr(obj, 'name', None)); add(getattr(obj, 'description', None))
    try:
        asm=model.rootAssembly
        for mapping in [getattr(asm,'instances',{}), getattr(asm,'sets',{}), getattr(asm,'surfaces',{})]:
            try: keys=list(mapping.keys())
            except Exception: keys=[]
            for key in keys: add(key)
    except Exception: pass
    try:
        job=get_obj(mdb.jobs,SPEC['job_name'])
        if job is not None:
            add(SPEC['job_name']); add(getattr(job,'name',None)); add(getattr(job,'model',None)); add(getattr(job,'description',None))
    except Exception: pass
    return '\n'.join(names)


def check_chain_evidence():
    evidence=SPEC.get('chain_evidence') or {}
    token=SPEC.get('chain_token')
    if not token:
        return fail('Missing chain token in eval SPEC')
    dxf_markers=evidence.get('dxf_markers') or []
    if dxf_markers:
        dxf_name=SPEC.get('stage_dxf')
        if not dxf_name: return fail('DXF chain evidence requested but no stage_dxf in SPEC')
        dxf_path=dp(dxf_name)
        if not nonempty(dxf_path, 200): return fail('Missing DXF stage for chain evidence: '+dxf_path)
        try: data=parse_dxf(dxf_path)
        except Exception as e: return fail('Cannot parse DXF for chain evidence: '+str(e))
        if ci('CHAIN') not in data['layers']:
            return fail('DXF missing CHAIN layer for chain evidence')
        if not check_dxf_chain_text(data): return False
    step_markers=evidence.get('step_markers') or []
    if step_markers:
        step_name=SPEC.get('stage_step')
        if not step_name: return fail('STEP chain evidence requested but no stage_step in SPEC')
        step_path=dp(step_name)
        if not nonempty(step_path, 1): return fail('Missing STEP stage for chain evidence: '+step_path)
        values=step_native_strings(head(step_path))
        for marker in step_markers:
            if not any(chain_contains(value,marker) for value in values):
                return fail('Missing chain evidence in one STEP native DATA string: '+marker)
    cae_markers=evidence.get('cae_markers') or []
    if cae_markers:
        if openMdb is None: return fail('Run evaluator with Abaqus cae noGUI for CAE chain evidence')
        cae_path=dp(SPEC['job_name']+'.cae')
        if not nonempty(cae_path,1024): return fail('Missing CAE for chain evidence: '+cae_path)
        try:
            if not open_cae_for_eval(): return fail('Cannot prepare CAE copy for chain evidence')
        except Exception as e: return fail('Cannot open CAE for chain evidence: '+str(e))
        mk=find_key(mdb.models,SPEC['model_name'])
        if mk is None: return fail('Missing model for chain evidence '+SPEC['model_name'])
        blob=cae_chain_blob(mdb.models[mk])
        if not check_chain_markers(blob, cae_markers, 'CAE'):
            return False
    return ok('Chain evidence checks passed')

def find_key(repo, target):
    if repo is None: return None
    t=nn(target)
    try: keys=repo.keys()
    except Exception: return None
    for k in keys:
        nk=nn(k)
        if nk == t: return k
    return None


def has(repo,target): return find_key(repo,target) is not None


def get_obj(repo,target):
    k=find_key(repo,target)
    if k is None: return None
    try: return repo[k]
    except Exception: return None


def cls(o):
    try: return o.__class__.__name__
    except Exception: return ''


def step_kind(step, kind):
    blob=' '.join([cls(step),ci(getattr(step,'procedureType','')),ci(getattr(step,'analysis','')),ci(getattr(step,'response',''))])
    k=ci(kind)
    if k == 'STATIC': return 'STATIC' in blob and 'HEAT' not in blob
    if k == 'HEAT_TRANSFER': return 'HEAT' in blob or 'THERMAL' in blob
    if k == 'BUCKLE': return 'BUCKLE' in blob or 'BUCKLING' in blob
    return k in blob


def collect_sets(model):
    out=set()
    try:
        for k in model.rootAssembly.sets.keys(): out.add(nn(k))
        for k in model.rootAssembly.nodeSets.keys(): out.add(nn(k))
    except Exception: pass
    try:
        for pk in model.parts.keys():
            p=model.parts[pk]
            for k in p.sets.keys(): out.add(nn(k))
            try:
                for k in p.nodeSets.keys(): out.add(nn(k))
            except Exception: pass
    except Exception: pass
    return out


def collect_surfaces(model):
    out=set()
    try:
        for k in model.rootAssembly.surfaces.keys(): out.add(nn(k))
    except Exception: pass
    try:
        for pk in model.parts.keys():
            p=model.parts[pk]
            for k in p.surfaces.keys(): out.add(nn(k))
    except Exception: pass
    return out


def mesh_info(part):
    coords=[]; elements=[]; types=[]
    try:
        for node in part.nodes: coords.append(tuple(float(value) for value in node.coordinates))
    except Exception: pass
    try:
        elements=[element for element in part.elements]
        types=sorted(set(ci(element.type) for element in elements))
    except Exception: pass
    return coords,elements,types


def check_material(model):
    m=SPEC.get('material',{}); name=m.get('name')
    if name and not has(model.materials,name): return fail('Missing material '+name)
    key=find_key(model.materials,name)
    if not key: return fail('Required material not found: '+str(name))
    mat=model.materials[key]
    if 'E' in m:
        try:
            e=float(mat.elastic.table[0][0]); nu=float(mat.elastic.table[0][1])
        except Exception as ex: return fail('Could not inspect elastic table: '+str(ex))
        if abs(e-float(m['E'])) > max(1.0,0.01*float(m['E'])): return fail('Elastic E mismatch')
        if abs(nu-float(m['nu'])) > 0.02: return fail('Poisson ratio mismatch')
    if 'conductivity' in m:
        try:
            kval=float(mat.conductivity.table[0][0])
        except Exception as ex: return fail('Could not inspect conductivity table: '+str(ex))
        if abs(kval-float(m['conductivity'])) > max(5.0,0.15*float(m['conductivity'])): return fail('Conductivity mismatch')
    return ok('Material checks passed')


def check_section_assignment(model):
    mat_name=SPEC.get('section_material') or SPEC.get('material',{}).get('name')
    if not mat_name: return True
    matching_sections=set()
    try:
        for sk in model.sections.keys():
            sec=model.sections[sk]
            if ci(getattr(sec,'material','')) == ci(mat_name): matching_sections.add(nn(sk))
    except Exception as e: return fail('Cannot inspect section repository: '+str(e))
    if not matching_sections: return fail('No section uses material '+str(mat_name))
    assigned=False
    try:
        for pk in model.parts.keys():
            p=model.parts[pk]
            try: assigns=p.sectionAssignments
            except Exception: continue
            for a in assigns:
                sname=nn(getattr(a,'sectionName',''))
                if sname in matching_sections: assigned=True
    except Exception as e: return fail('Cannot inspect section assignments: '+str(e))
    if not assigned: return fail('No section assignment uses material '+str(mat_name))
    return ok('Section assignment checks passed')


def is_set_value(v):
    vu=ci(v)
    if vu in ('','NONE','UNSET','UNCHANGED','FREED','OFF'): return False
    return True


INP_CACHE={}


def inp_tmp_dir():
    base=os.environ.get('TEMP') or os.environ.get('TMP') or desktop()
    return os.path.join(base, 'engiworld_eval_inp')


def cleanup_eval_inp():
    tmp=inp_tmp_dir()
    try:
        if not os.path.isdir(tmp): return
        for name in os.listdir(tmp):
            lower=name.lower()
            if lower.startswith('evalinp') or lower.startswith('__eval'):
                try: os.remove(os.path.join(tmp,name))
                except Exception: pass
        os.rmdir(tmp)
    except Exception: pass


def model_job_name(model):
    try:
        return str(model.name)
    except Exception:
        return SPEC['model_name']


def write_eval_inp(model):
    if mdb is None: return None
    tmp=inp_tmp_dir()
    cleanup_eval_inp()
    if not os.path.isdir(tmp): os.makedirs(tmp)
    job_name='EvalInp%s'%str(SPEC.get('task_no',0))
    try:
        if job_name in mdb.jobs.keys(): del mdb.jobs[job_name]
    except Exception: pass
    old=os.getcwd()
    try:
        os.chdir(tmp)
        job=mdb.Job(name=job_name, model=model_job_name(model))
        try: job.writeInput(consistencyChecking=False)
        except TypeError: job.writeInput()
    finally:
        try: os.chdir(old)
        except Exception: pass
    path=os.path.join(tmp, job_name+'.inp')
    if os.path.isfile(path): return path
    try:
        for name in os.listdir(tmp):
            if name.lower().endswith('.inp'): return os.path.join(tmp,name)
    except Exception: pass
    return None


def parse_float_token(text):
    try:
        return float(str(text).strip().replace('D','E').replace('d','E'))
    except Exception: return None


def parse_int_token(text):
    v=parse_float_token(text)
    if v is None: return None
    try: return int(v)
    except Exception: return None


def normalize_region_name(text):
    return nn(str(text).replace('.', '_').replace('"','').replace("'",''))


def token_matches_region(token, region):
    if not token or not region: return False
    raw=str(token).strip().replace('"','').replace("'",'')
    t=normalize_region_name(raw); r=normalize_region_name(region)
    if not t or not r: return False
    if t == r: return True
    # Abaqus qualifies part-level sets and surfaces as INSTANCE.REGION in INP files.
    return '.' in raw and normalize_region_name(raw.rsplit('.',1)[-1]) == r


def object_region_matches(token, region):
    return bool(token and region and normalize_region_name(token) == normalize_region_name(region))


def inp_token_matches_model_region(model, token, region):
    if not token or not region: return False
    raw=str(token).strip().replace('"','').replace("'",'')
    if object_region_matches(raw,region): return True
    if '.' not in raw or not object_region_matches(raw.rsplit('.',1)[-1],region): return False
    prefix=raw.rsplit('.',1)[0]
    try: return find_key(model.rootAssembly.instances,prefix) is not None
    except Exception: return False


def object_region_name(obj):
    try: region=getattr(obj,'region')
    except Exception: return ''
    for attr in ['name','setName','surfaceName']:
        try:
            value=str(getattr(region,attr))
            if value: return value
        except Exception: pass
    rep=repr(region)
    for quote in ["'", '"']:
        i=rep.find(quote)
        if i >= 0:
            j=rep.find(quote, i+1)
            if j > i: return rep[i+1:j]
    try: return rep.strip('()').split(',')[0].strip()
    except Exception: return ''


def parse_inp(path):
    data={'boundary':[], 'cload':[], 'pressure':[], 'flux':[], 'film':[], 'couplings':[],
          'raw_cards':[], 'keyword_cards':[], 'field_output_variables_by_step':{},
          'step_order':['INITIAL']}
    if not path or not os.path.isfile(path): return data
    card=''; current_step='INITIAL'; card_id=0; card_params={}; field_output_active=False
    try:
        f=open(path,'r')
        lines=f.readlines()
        f.close()
    except Exception:
        return data
    for raw in lines:
        line=raw.strip()
        if not line or line.startswith('**'): continue
        if line.startswith('*'):
            pieces=[piece.strip() for piece in line.split(',')]
            card=pieces[0].lower()
            card_id += 1
            params={}
            for piece in pieces[1:]:
                if '=' in piece:
                    key,value=piece.split('=',1); params[ci(key)]=value.strip()
            card_params=params
            data['raw_cards'].append(line)
            if card == '*step':
                current_step=params.get('NAME','__UNNAMED_STEP__')
                if nn(current_step) not in [nn(value) for value in data['step_order']]:
                    data['step_order'].append(current_step)
            elif card == '*end step': current_step=None
            if card == '*output': field_output_active='FIELD' in ci(line)
            elif card == '*end step': field_output_active=False
            if field_output_active and ci(params.get('VARIABLE','')) == 'PRESELECT':
                variables=[]
                if card == '*node output': variables=['U','RF','CF']
                elif card == '*element output': variables=['S']
                observed=data['field_output_variables_by_step'].setdefault(nn(current_step or ''),[])
                for variable in variables:
                    if variable not in observed: observed.append(variable)
            if card == '*coupling':
                data['couplings'].append({'name':params.get('CONSTRAINT NAME',''),
                                          'control':params.get('REF NODE',''),
                                          'surface':params.get('SURFACE',''),
                                          'step':current_step,'card_id':card_id})
            data['keyword_cards'].append({'name':card,'params':params,'step':current_step,
                                          'card_id':card_id})
            continue
        parts=[p.strip() for p in line.split(',')]
        if not parts or not parts[0]: continue
        target=parts[0]
        if field_output_active:
            variables=data['field_output_variables_by_step'].setdefault(nn(current_step or ''),[])
            for value in parts:
                token=ci(value)
                if re.match(r'^[A-Z][A-Z0-9_]*$',token) and token not in variables:
                    variables.append(token)
        if card == '*boundary':
            d1=parse_int_token(parts[1]) if len(parts)>1 else None
            d2=parse_int_token(parts[2]) if len(parts)>2 else d1
            val=parse_float_token(parts[3]) if len(parts)>3 else 0.0
            boundary_type=ci(parts[1]) if len(parts)>1 and d1 is None else ''
            data['boundary'].append({'target':target,'dof1':d1,'dof2':d2,'value':val,
                                     'type':boundary_type,'step':current_step,
                                     'op':ci(card_params.get('OP','MOD')),'card_id':card_id})
        elif card == '*cload':
            dof=parse_int_token(parts[1]) if len(parts)>1 else None
            val=parse_float_token(parts[2]) if len(parts)>2 else None
            data['cload'].append({'target':target,'dof':dof,'value':val,'step':current_step,
                                  'op':ci(card_params.get('OP','MOD')),'card_id':card_id})
        elif card in ('*dload','*dsload'):
            vals=[parse_float_token(p) for p in parts[1:]]
            vals=[v for v in vals if v is not None]
            data['pressure'].append({'target':target,'load_type':ci(parts[1]) if len(parts)>1 else '',
                                     'values':vals,'card':card,'parts':parts,'step':current_step,
                                     'op':ci(card_params.get('OP','MOD')),'card_id':card_id})
        elif card in ('*cflux','*dflux','*dsflux'):
            vals=[parse_float_token(p) for p in parts[1:]]
            vals=[v for v in vals if v is not None]
            data['flux'].append({'target':target,'values':vals,'card':card,'parts':parts,'step':current_step,
                                 'op':ci(card_params.get('OP','MOD')),'card_id':card_id})
        elif card == '*film':
            vals=[parse_float_token(p) for p in parts[1:]]
            vals=[v for v in vals if v is not None]
            data['film'].append({'target':target,'values':vals,'parts':parts,'step':current_step,
                                 'op':ci(card_params.get('OP','MOD')),'card_id':card_id})
        elif card in ('*node output','*element output'):
            step_key=nn(current_step or '')
            variables=data['field_output_variables_by_step'].setdefault(step_key,[])
            for value in parts:
                token=ci(value)
                if token and token not in variables: variables.append(token)
    return data


def get_inp_data(model):
    key=SPEC.get('job_name','__default__')
    if key in INP_CACHE: return INP_CACHE[key]
    data={'boundary':[], 'cload':[], 'pressure':[], 'flux':[], 'film':[], 'couplings':[],
          'raw_cards':[], 'keyword_cards':[], 'field_output_variables_by_step':{},
          'step_order':['INITIAL']}
    try:
        path=write_eval_inp(model)
        if not path or not os.path.isfile(path):
            warn('CAE INP export produced no input file')
        else:
            data=parse_inp(path)
            log('[PASS] CAE temporary INP export parsed')
    except Exception as e:
        warn('CAE INP export/parse unavailable: '+str(e))
    finally:
        cleanup_eval_inp()
    INP_CACHE[key]=data
    return data


def inp_entries_for(data, kind, region, step=None):
    out=[]
    for entry in data.get(kind,[]):
        if step is not None and nn(entry.get('step')) != nn(step): continue
        if token_matches_region(entry.get('target',''), region): out.append(entry)
    return out


def inp_card_names_for_kind(kind):
    return {'boundary':set(['*boundary']), 'cload':set(['*cload']),
            'pressure':set(['*dload','*dsload']),
            'flux':set(['*cflux','*dflux','*dsflux']),
            'film':set(['*film'])}.get(kind,set())


def effective_inp_entries(data, kind, step):
    entries=data.get(kind,[])
    valid_names=inp_card_names_for_kind(kind)
    order=[nn(value) for value in data.get('step_order',['INITIAL'])]
    target_index=order.index(nn(step)) if nn(step) in order else len(order)-1
    allowed_steps=set(order[:target_index+1])
    cards=[row for row in data.get('keyword_cards',[])
           if row.get('name') in valid_names and nn(row.get('step') or 'INITIAL') in allowed_steps]
    cards.sort(key=lambda row:int(row.get('card_id') or 0))
    effective={}
    for row in cards:
        if ci((row.get('params') or {}).get('OP','MOD')) == 'NEW': effective=[]
        card_id=row.get('card_id')
        if isinstance(effective,list): effective={}
        for entry in entries:
            if entry.get('card_id') != card_id: continue
            target=normalize_region_name(entry.get('target',''))
            if kind == 'boundary':
                symbolic=ci(entry.get('type',''))
                if symbolic in ('ENCASTRE','PINNED'):
                    for dof in (1,2,3):
                        effective[(target,dof)]={'target':entry.get('target'),'dof1':dof,'dof2':dof,
                                                'value':0.0,'type':'','step':entry.get('step'),
                                                'op':entry.get('op'),'card_id':card_id}
                else:
                    d1=entry.get('dof1'); d2=entry.get('dof2') if entry.get('dof2') is not None else d1
                    if d1 is None: continue
                    for dof in range(int(d1),int(d2)+1):
                        effective[(target,dof)]=dict(entry,dof1=dof,dof2=dof)
            elif kind == 'cload':
                effective[(target,entry.get('dof'))]=entry
            elif kind == 'pressure':
                effective[(target,ci(entry.get('load_type','')))]=entry
            else:
                effective[(target,ci(entry.get('card',kind)))]=entry
    return list(effective.values())


def numeric_attr(obj, name):
    try:
        v=getattr(obj,name)
        if not is_set_value(v): return None
        return float(v)
    except Exception: return None


def numeric_values(obj):
    vals=[]
    for attr in ['cf1','cf2','cf3','cm1','cm2','cm3','u1','u2','u3','ur1','ur2','ur3','magnitude']:
        v=numeric_attr(obj, attr)
        if v is not None: vals.append((attr,v))
    return vals


def target_step_state_repository(model, repository_name):
    key=find_key(model.steps,SPEC['step_name'])
    if key is None: return None
    try: return getattr(model.steps[key],repository_name)
    except Exception: return None


def target_step_state(model, repository_name, name):
    repository=target_step_state_repository(model,repository_name)
    key=find_key(repository,name)
    if key is None: return None
    try: return repository[key]
    except Exception: return None


def state_is_active(state):
    if state is None: return False
    status=ci(getattr(state,'status',''))
    if not status: return False
    inactive=['DEACTIVATED','INACTIVE','NOT_YET_ACTIVE','NO_LONGER_ACTIVE','INSTANCE_NOT_APPLICABLE',
              'TYPE_NOT_APPLICABLE','SUPPRESSED']
    return not any(token in status for token in inactive)


def extra_active_state_names(model, repository_name, expected_names):
    repository=target_step_state_repository(model,repository_name)
    if repository is None: return None
    expected=set(nn(name) for name in expected_names)
    out=[]
    try:
        for key in repository.keys():
            if nn(key) in expected: continue
            if state_is_active(repository[key]): out.append(str(key))
    except Exception: return None
    return out


def state_fixed_translations(state):
    fixed=set()
    for attr in ['u1','u2','u3']:
        component_state=ci(getattr(state,attr+'State',''))
        if component_state in ('UNSET','FREED'): continue
        try: value=getattr(state,attr)
        except Exception: continue
        if not is_set_value(value): continue
        try:
            if abs(float(value)) <= 1.0e-9: fixed.add(int(attr[-1]))
        except Exception:
            if ci(value) in ('SET','FIXED'): fixed.add(int(attr[-1]))
    return fixed


def object_fixed_translations(obj):
    fixed=set()
    for attr in ['u1','u2','u3']:
        try: value=getattr(obj,attr)
        except Exception: continue
        if not is_set_value(value): continue
        try:
            if abs(float(value)) <= 1.0e-9: fixed.add(int(attr[-1]))
        except Exception:
            if ci(value) in ('SET','FIXED'): fixed.add(int(attr[-1]))
    return fixed


def object_is_suppressed(obj):
    for attr in ['suppressed','isSuppressed']:
        try:
            value=getattr(obj,attr)
            if callable(value): value=value()
        except Exception: continue
        if isinstance(value,bool): return value
        text=ci(value)
        if text in ('TRUE','YES','ON','1','SUPPRESSED'): return True
        if text in ('FALSE','NO','OFF','0','ACTIVE'): return False
    return False


def active_constraint_names(model):
    try: repository=model.constraints
    except AttributeError: return []
    except Exception: return None
    if repository is None: return []
    out=[]
    try:
        for key in repository.keys():
            if not object_is_suppressed(repository[key]): out.append(str(key))
    except Exception: return None
    return out


def active_state_backed_names(model, object_repository_name, state_repository_name):
    repository=getattr(model,object_repository_name,None)
    if repository is None: return []
    states=target_step_state_repository(model,state_repository_name)
    out=[]
    try:
        for key in repository.keys():
            obj=repository[key]
            if object_is_suppressed(obj): continue
            state_key=find_key(states,key)
            if states is None or state_key is None or state_is_active(states[state_key]): out.append(str(key))
    except Exception: return None
    return out


def check_no_active_constraints(model):
    names=active_constraint_names(model)
    if names is None: return fail('Cannot inspect Abaqus constraint/coupling repository')
    if names: return fail('Unexpected active constraint/coupling objects: '+', '.join(names))
    for object_repo,state_repo,label in [
            ('interactions','interactionStates','interaction'),
            ('predefinedFields','predefinedFieldStates','predefined field')]:
        active=active_state_backed_names(model,object_repo,state_repo)
        if active is None: return fail('Cannot inspect active Abaqus '+label+' objects')
        if active: return fail('Unexpected active '+label+' objects: '+', '.join(active))
    try:
        if len(model.rootAssembly.elements) > 0:
            return fail('Unexpected connector or assembly-level elements are active')
    except Exception: pass
    couplings=get_inp_data(model).get('couplings',[])
    if couplings: return fail('Unexpected active coupling cards in job input: '+repr(couplings))
    return ok('No unexpected active constraints, interactions, predefined fields, or assembly elements')


def check_inp_action_whitelist(model):
    data=get_inp_data(model)
    forbidden_cards=set(['*equation','*rigid body','*tie','*mpc','*coupling',
                         '*initial conditions','*temperature','*field','*predefined field',
                         '*foundation','*connector load','*base motion','*incident wave',
                         '*submodel','*contact','*contact pair','*model change','*bolt load',
                         '*pre-tension section','*mass flow rate'])
    observed=set(row.get('name','') for row in data.get('keyword_cards',[])
                 if nn(row.get('step') or 'INITIAL') in (nn('INITIAL'),nn(SPEC['step_name'])))
    extra_cards=sorted(observed & forbidden_cards)
    if extra_cards: return fail('Unexpected active action cards in job input: '+', '.join(extra_cards))
    boundary=effective_inp_entries(data,'boundary',SPEC['step_name'])
    for entry in boundary:
        if not inp_token_matches_model_region(model,entry.get('target'),'BOLT_HOLES'):
            return fail('Unexpected boundary-condition target in job input: '+repr(entry))
        if entry.get('type') == 'ENCASTRE': continue
        d1=entry.get('dof1'); d2=entry.get('dof2') if entry.get('dof2') is not None else d1
        value=entry.get('value')
        if d1 is None or d2 is None or int(d1) < 1 or int(d2) > 3 or (value is not None and abs(float(value)) > 1.0e-9):
            return fail('Unexpected BOLT_HOLES boundary card in job input: '+repr(entry))
    pressure=effective_inp_entries(data,'pressure',SPEC['step_name'])
    if len(pressure) != 1:
        return fail('Job input must contain exactly one active pressure card; got '+repr(pressure))
    entry=pressure[0]
    expected_req=SPEC['load_checks'][0]
    if (nn(entry.get('step')) != nn(SPEC['step_name']) or
            not inp_token_matches_model_region(model,entry.get('target'),'PRESSURE_FACE') or
            not re.match(r'^P[1-6]?$',entry.get('load_type','')) or
            not any(inp_value_matches(value,expected_req) for value in entry.get('values',[]))):
        return fail('Unexpected pressure card in job input: '+repr(entry))
    for kind in ['cload','flux','film']:
        effective=effective_inp_entries(data,kind,SPEC['step_name'])
        if effective: return fail('Unexpected active '+kind+' cards in job input: '+repr(effective))
    return ok('Job input contains only the specified support and pressure actions')


def inp_boundary_has_constraint(model, region):
    data=get_inp_data(model)
    constrained=set()
    for entry in effective_inp_entries(data,'boundary',SPEC['step_name']):
        if not inp_token_matches_model_region(model,entry.get('target',''),region): continue
        if entry.get('type') == 'ENCASTRE': constrained.update([1,2,3]); continue
        d1=entry.get('dof1'); d2=entry.get('dof2') if entry.get('dof2') is not None else d1
        if d1 is None: continue
        if d2 is None: d2=d1
        if abs(float(entry.get('value') or 0.0)) > 1.0e-9: continue
        for dof in range(max(int(d1),1),min(int(d2),3)+1): constrained.add(dof)
    if constrained != set([1,2,3]): log('[AUDIT] Effective boundary entries: '+repr(
        effective_inp_entries(data,'boundary',SPEC['step_name'])))
    return constrained == set([1,2,3])


def check_constraint_bc(model, name, expected_region):
    bc=get_obj(model.boundaryConditions, name)
    if bc is None: return fail('Missing BC '+name)
    state=target_step_state(model,'boundaryConditionStates',name)
    if not state_is_active(state): return fail('BC '+name+' is not active in '+SPEC['step_name'])
    extras=extra_active_state_names(model,'boundaryConditionStates',[name])
    if extras is None: return fail('Cannot inspect active boundary conditions in '+SPEC['step_name'])
    if extras: return fail('Unexpected additional active boundary conditions: '+', '.join(extras))
    region=object_region_name(bc)
    if not object_region_matches(region,expected_region):
        return fail('BC '+name+' is not bound to '+expected_region)
    state_exposes_components=False
    for attr in ['u1','u2','u3']:
        try: getattr(state,attr); state_exposes_components=True
        except Exception: pass
    fixed=state_fixed_translations(state) if state_exposes_components else object_fixed_translations(bc)
    if fixed != set([1,2,3]) and inp_boundary_has_constraint(model,expected_region):
        fixed.update([1,2,3])
    if fixed == set([1,2,3]):
        return ok('BC '+name+' constrains translations 1-3 on '+expected_region)
    return fail('BC '+name+' does not constrain translations 1-3 on '+expected_region)


def check_convection(model, name):
    if has(model.boundaryConditions, name): return ok('Convection boundary condition found '+name)
    try:
        if has(model.interactions, name): return ok('Convection interaction found '+name)
    except Exception: pass
    data=get_inp_data(model)
    if inp_entries_for(data, 'film', name): return ok('Convection film card found '+name)
    return fail('Missing convection interaction or boundary condition '+name)


def check_bc_specs(model):
    for req in SPEC.get('bc_checks',[]):
        kind=req.get('kind','constraint')
        name=req.get('name')
        if kind == 'convection':
            if not check_convection(model,name): return False
        else:
            if not check_constraint_bc(model,name,req.get('region') or name): return False
    return True


def close_magnitude(v, target, req):
    return close_rel(abs(v), abs(float(target)), abs_tol=float(req.get('abs_tol', max(1.0, abs(float(target))*0.02))), rel_tol=float(req.get('rel_tol',0.20)))


def inp_value_matches(value, req):
    if value is None: return False
    sign=req.get('sign')
    mag=req.get('magnitude')
    if mag is not None and not close_magnitude(value, mag, req): return False
    if sign == 'positive' and value <= 0.0: return False
    if sign == 'negative' and value >= 0.0: return False
    return True


def force_like_ok(obj, req, model=None):
    vals=numeric_values(obj)
    if vals:
        sign=req.get('sign')
        mag=req.get('magnitude')
        for attr,v in vals:
            if mag is not None and not close_magnitude(v, mag, req):
                continue
            if sign == 'positive' and v <= 0.0: continue
            if sign == 'negative' and v >= 0.0: continue
            return True
        if mag is None:
            for attr,v in vals:
                if abs(v) > 1.0e-9: return True
    if model is not None and obj is not None:
        region=object_region_name(obj)
        data=get_inp_data(model)
        for entry in inp_entries_for(data, 'cload', region):
            v=entry.get('value')
            if req.get('magnitude') is None:
                if v is not None and abs(v) > 1.0e-9: return True
            elif inp_value_matches(v, req): return True
    return False


def displacement_ok(obj, req, model=None):
    vals=[]
    for attr in ['u1','u2','u3']:
        v=numeric_attr(obj, attr)
        if v is not None: vals.append((attr,v))
    if vals:
        disp=req.get('disp_magnitude')
        if disp is None:
            return any(abs(v) > 1.0e-9 for attr,v in vals)
        for attr,v in vals:
            if close_magnitude(v, disp, req): return True
    if model is not None and obj is not None:
        region=object_region_name(obj)
        data=get_inp_data(model)
        for entry in inp_entries_for(data, 'boundary', region):
            v=entry.get('value')
            if v is None: continue
            disp=req.get('disp_magnitude')
            if disp is None and abs(v) > 1.0e-9: return True
            if disp is not None and close_magnitude(v, disp, req): return True
    return False


def inp_card_has_value(model, kind, region, req=None, require_nonzero=True, step=None):
    data=get_inp_data(model)
    entries=(effective_inp_entries(data,kind,step) if step is not None else data.get(kind,[]))
    for entry in entries:
        if not inp_token_matches_model_region(model,entry.get('target',''),region): continue
        for v in entry.get('values',[]):
            if v is None: continue
            if req is not None and req.get('magnitude') is not None:
                if inp_value_matches(v,req): return True
            elif (not require_nonzero) or abs(v) > 1.0e-12:
                return True
    return False


def check_field_output_requests(model):
    required=set(ci(value) for value in SPEC.get('required_cae_output_variables',[]))
    observed=set(ci(value) for value in get_inp_data(model).get(
        'field_output_variables_by_step',{}).get(nn(SPEC['step_name']),[]))
    if not observed: return fail('Cannot inspect active field output in '+SPEC['step_name'])
    # CAE uses semantic family names; the ODB exposes NFORC as scalar components.
    if 'NFORC' in observed: observed.update(['NFORC1','NFORC2','NFORC3'])
    if any(token.startswith('NFORC') for token in observed): observed.add('NFORC')
    missing=sorted(required-observed)
    if missing: return fail('Field-output request is missing: '+', '.join(missing))
    return ok('CAE requests U, S, RF, NFORC1/2/3, and CF field output')


def check_load_specs(model):
    for req in SPEC.get('load_checks',[]):
        name=req.get('name'); kind=req.get('kind')
        load=get_obj(model.loads, name)
        bc=get_obj(model.boundaryConditions, name)
        if kind == 'pressure':
            if load is None: return fail('Missing pressure load '+name)
            if 'PRESSURE' not in ci(cls(load)): return fail('Load '+name+' is not a pressure object')
            state=target_step_state(model,'loadStates',name)
            if not state_is_active(state): return fail('Pressure load '+name+' is not active in '+SPEC['step_name'])
            extras=extra_active_state_names(model,'loadStates',[name])
            if extras is None: return fail('Cannot inspect active loads in '+SPEC['step_name'])
            if extras: return fail('Unexpected additional active loads: '+', '.join(extras))
            expected_region=req.get('region') or 'PRESSURE_FACE'
            region=object_region_name(load)
            if not object_region_matches(region,expected_region):
                return fail('Pressure load '+name+' is not bound to '+expected_region)
            distribution=ci(getattr(load,'distributionType',''))
            if distribution != 'UNIFORM':
                return fail('Pressure load '+name+' must use a uniform 1.0 MPa distribution')
            state_mag=numeric_attr(state,'magnitude'); object_mag=numeric_attr(load,'magnitude')
            effective_mag=state_mag if state_mag is not None else object_mag
            inp_ok=inp_card_has_value(model,'pressure',expected_region,req=req,step=SPEC['step_name'])
            magnitude_ok=(effective_mag is None and inp_ok) or (
                effective_mag is not None and inp_value_matches(effective_mag,req))
            if not magnitude_ok or not inp_ok:
                return fail('Pressure '+name+' must have magnitude 1.0 and target '+expected_region+
                            '; object_region=%s state_magnitude=%s object_magnitude=%s INP=%s'%
                            (region,state_mag,object_mag,repr(get_inp_data(model).get('pressure',[]))))
        elif kind == 'heat_flux':
            if load is None: return fail('Missing heat flux load '+name)
            vals=numeric_values(load)
            if vals and any(abs(v) > 1.0e-12 for attr,v in vals): continue
            region=object_region_name(load) or name
            if not inp_card_has_value(model, 'flux', region, req=req): return fail('Heat flux load '+name+' has no readable magnitude')
        elif kind == 'force_or_displacement':
            matched=False
            if load is not None and force_like_ok(load, req, model): matched=True
            if bc is not None and displacement_ok(bc, req, model): matched=True
            if not matched: return fail('Missing acceptable force or displacement action '+name)
        else:
            if load is None: return fail('Missing load '+name)
            if not force_like_ok(load, req, model): return fail('Load magnitude/sign mismatch for '+name)
    return ok('Load/action checks passed')


def object_bbox(obj):
    try: box=obj.faces.getBoundingBox()
    except Exception: return None
    try:
        low=tuple(float(value) for value in box['low']); high=tuple(float(value) for value in box['high'])
        return low,high,[high[index]-low[index] for index in range(3)]
    except Exception: return None


def find_analysis_part(model):
    matches=[]
    for key in model.parts.keys():
        part=model.parts[key]
        try:
            if len(part.cells) < 1: continue
        except Exception: continue
        bbox=object_bbox(part)
        if bbox and dims_close(bbox[2],SPEC['bbox'],SPEC.get('bbox_tol',0.1)):
            matches.append((key,part,bbox))
    return matches[0] if len(matches) == 1 else (None,None,None)


def part_volume(part):
    try:
        value=part.getMassProperties().get('volume')
        return float(value)
    except Exception: return None


def part_surface_area(part):
    try:
        properties=part.getMassProperties()
        for key in ['area','surfaceArea']:
            value=properties.get(key)
            if value is not None: return float(value)
    except Exception: pass
    try:
        if len(part.cells) != 1: return None
        total=0.0
        for face in part.faces:
            try: total += float(face.getSize(printResults=False))
            except TypeError: total += float(face.getSize())
        return total
    except Exception: return None


def find_analysis_instance(model,part_key):
    matches=[]
    for key in model.rootAssembly.instances.keys():
        instance=model.rootAssembly.instances[key]
        try:
            if nn(getattr(instance,'partName','')) == nn(part_key): matches.append((key,instance))
        except Exception: pass
    return matches[0] if len(matches) == 1 else (None,None)


def faces_at_indices(face_array,points):
    queries=tuple((tuple(float(value) for value in point),) for point in points)
    try: found=face_array.findAt(*queries)
    except Exception: return set()
    try: return set(int(face.index) for face in found)
    except Exception:
        try: return set([int(found.index)])
        except Exception: return set()


def task02_expected_faces(face_array,bbox):
    if not STEP_AUDIT: return set(),set(),{}
    low,high,dims=bbox
    axis=min(range(3),key=lambda index:dims[index])
    planar=[index for index in range(3) if index != axis]
    part_center=[(low[index]+high[index])/2.0 for index in range(3)]
    source_center=STEP_AUDIT['center']
    hole_centers=[]
    for hx,hy in STEP_AUDIT['hole_centers']:
        point=list(part_center)
        point[planar[0]] += hx-source_center[0]
        point[planar[1]] += hy-source_center[1]
        hole_centers.append(tuple(point))
    bolt=set(); pressure_by_depth={low[axis]+2.0:set(),high[axis]-2.0:set()}
    for face in face_array:
        point=face_point(face)
        if point is None: continue
        for center in hole_centers:
            dx=point[planar[0]]-center[planar[0]]
            dy=point[planar[1]]-center[planar[1]]
            if close(math.sqrt(dx*dx+dy*dy),3.0,0.1): bolt.add(int(face.index)); break
        radial=math.sqrt((point[planar[0]]-part_center[planar[0]])**2+
                         (point[planar[1]]-part_center[planar[1]])**2)
        for depth in pressure_by_depth.keys():
            if close(point[axis],depth,0.05) and radial <= 25.1:
                pressure_by_depth[depth].add(int(face.index))
    pressure=set(); pressure_depth=None; best_error=None
    for depth,indices in pressure_by_depth.items():
        area=face_indices_area(face_array,indices)
        error=abs(area-float(SPEC['expected_pressure_area_mm2']))
        if indices and (best_error is None or error < best_error):
            pressure=indices; pressure_depth=depth; best_error=error
    return bolt,pressure,{'axis':axis,'center':tuple(part_center),'hole_centers':hole_centers,
                           'pressure_depth':pressure_depth,'low':low,'high':high}


def face_point(face):
    try: value=face.pointOn
    except Exception: return None
    try:
        if len(value) == 3 and not hasattr(value[0],'__iter__'):
            return tuple(float(item) for item in value)
        if value and len(value[0]) >= 3: return tuple(float(item) for item in value[0][:3])
    except Exception: pass
    return None


def face_indices_area(face_array,indices):
    total=0.0
    for face in face_array:
        try:
            if int(face.index) not in indices: continue
            try: total += float(face.getSize(printResults=False))
            except TypeError: total += float(face.getSize())
        except Exception: continue
    return total


def face_indices_node_labels(face_array,indices):
    labels=set()
    for face in face_array:
        try:
            if int(face.index) in indices: labels.update(collect_entity_labels(face.getNodes()))
        except Exception: pass
    return labels


def named_region_candidates(model,name,repository_name):
    candidates=[]
    repo=getattr(model.rootAssembly,repository_name,None)
    key=find_key(repo,name)
    if key is not None:
        try: candidates.append(('assembly',repo[key]))
        except Exception: pass
    for part_key in model.parts.keys():
        part=model.parts[part_key]; repo=getattr(part,repository_name,None); key=find_key(repo,name)
        if key is not None:
            try: candidates.append((str(part_key),repo[key]))
            except Exception: pass
    return candidates


def region_face_indices(region):
    try: return set(int(face.index) for face in region.faces)
    except Exception: return set()


def region_area(region):
    total=0.0; observed=False
    try:
        for face in region.faces:
            try: total += float(face.getSize(printResults=False))
            except Exception: total += float(face.getSize())
            observed=True
        return total if observed else None
    except Exception: return None


def collect_entity_labels(value):
    labels=set()
    try:
        label=getattr(value,'label')
        labels.add(int(label)); return labels
    except Exception: pass
    try:
        for item in value: labels.update(collect_entity_labels(item))
    except Exception: pass
    return labels


def region_node_labels(region):
    labels=set()
    try: labels.update(collect_entity_labels(region.nodes))
    except Exception: pass
    if labels: return labels
    try:
        for face in region.faces:
            try: labels.update(collect_entity_labels(face.getNodes()))
            except Exception: pass
    except Exception: pass
    return labels


def require_face_region(model,name,expected,repository_name,expected_nodes=None,allow_nodes=False):
    candidates=named_region_candidates(model,name,repository_name)
    if not candidates: return None,fail('Missing native '+repository_name[:-1]+' '+name)
    for owner,region in candidates:
        if region_face_indices(region) == expected and expected: return region,True
        if allow_nodes and not region_face_indices(region):
            observed=region_node_labels(region)
            if observed and expected_nodes and observed == set(expected_nodes): return region,True
    return None,fail(name+' does not contain the required spatial faces')


def vector_subtract(first,second):
    return tuple(float(first[index])-float(second[index]) for index in range(3))


def vector_add(first,second):
    return tuple(float(first[index])+float(second[index]) for index in range(3))


def vector_scale(value,factor):
    return tuple(float(component)*float(factor) for component in value)


def vector_dot(first,second):
    return (float(first[0])*float(second[0])+
            float(first[1])*float(second[1])+
            float(first[2])*float(second[2]))


def vector_cross(first,second):
    return (first[1]*second[2]-first[2]*second[1],
            first[2]*second[0]-first[0]*second[2],
            first[0]*second[1]-first[1]*second[0])


def vector_length(value):
    return math.sqrt(vector_dot(value,value))


def vector_unit(value):
    length=vector_length(value)
    if length <= 1.0e-12: return None
    return vector_scale(value,1.0/length)


def mesh_node_coordinates(nodes):
    out={}
    for node in nodes:
        try: out[int(node.label)]=tuple(float(value) for value in node.coordinates)
        except Exception: pass
    return out


def mesh_rigid_transform(part_nodes,instance_nodes):
    source=mesh_node_coordinates(part_nodes); target=mesh_node_coordinates(instance_nodes)
    labels=sorted(set(source.keys()) & set(target.keys()))
    if len(labels) < 4: return None
    p0=source[labels[0]]; q0=target[labels[0]]
    label1=max(labels[1:],key=lambda label:vector_length(vector_subtract(source[label],p0)))
    a=vector_subtract(source[label1],p0)
    remaining=[label for label in labels if label not in (labels[0],label1)]
    label2=max(remaining,key=lambda label:vector_length(vector_cross(a,vector_subtract(source[label],p0))))
    b=vector_subtract(source[label2],p0); normal=vector_cross(a,b)
    remaining=[label for label in remaining if label != label2]
    label3=max(remaining,key=lambda label:abs(vector_dot(normal,vector_subtract(source[label],p0))))
    c=vector_subtract(source[label3],p0); determinant=vector_dot(a,vector_cross(b,c))
    if abs(determinant) <= 1.0e-9: return None
    return {'source_origin':p0,'target_origin':q0,'source_basis':(a,b,c),
            'target_basis':(vector_subtract(target[label1],q0),
                            vector_subtract(target[label2],q0),
                            vector_subtract(target[label3],q0)),'determinant':determinant}


def apply_mesh_transform(transform,point):
    a,b,c=transform['source_basis']; qa,qb,qc=transform['target_basis']
    value=vector_subtract(point,transform['source_origin']); det=float(transform['determinant'])
    weights=(vector_dot(value,vector_cross(b,c))/det,
             vector_dot(a,vector_cross(value,c))/det,
             vector_dot(a,vector_cross(b,value))/det)
    result=transform['target_origin']
    result=vector_add(result,vector_scale(qa,weights[0]))
    result=vector_add(result,vector_scale(qb,weights[1]))
    return vector_add(result,vector_scale(qc,weights[2]))


def check_part_section_assignment(model,part):
    material=ci(SPEC.get('section_material'))
    sections=set()
    for key in model.sections.keys():
        if ci(getattr(model.sections[key],'material','')) == material: sections.add(nn(key))
    if not sections: return fail('No solid section uses Steel')
    covered=set()
    try:
        for assignment in part.sectionAssignments:
            if nn(getattr(assignment,'sectionName','')) not in sections: continue
            region=getattr(assignment,'region',None); regions=[]
            if region is not None: regions.append(region)
            if isinstance(region,(tuple,list)):
                regions=[]
                for item in region:
                    if hasattr(item,'cells'): regions.append(item)
                    else:
                        key=find_key(part.sets,str(item))
                        if key is not None: regions.append(part.sets[key])
            for candidate in regions:
                try:
                    for cell in candidate.cells: covered.add(int(cell.index))
                except Exception: pass
    except Exception as e: return fail('Cannot inspect target-part section coverage: '+str(e))
    expected=set(int(cell.index) for cell in part.cells)
    if covered != expected: return fail('Steel section is not assigned to every flange cell')
    return ok('Steel solid section covers the complete flange')

def check_cae():
    global CAE_AUDIT
    CAE_AUDIT={}
    if openMdb is None: return fail('Run evaluator with Abaqus cae noGUI')
    path=dp(SPEC['job_name']+'.cae')
    if not nonempty(path,1024): return fail('Missing CAE '+path)
    try:
        if not open_cae_for_eval(): return fail('Cannot prepare CAE copy for evaluation')
    except Exception as e: return fail('Cannot open CAE: '+str(e))
    mk=find_key(mdb.models,SPEC['model_name'])
    if mk is None: return fail('Missing model '+SPEC['model_name'])
    model=mdb.models[mk]
    if not check_material(model): return False
    part_key,part,bbox=find_analysis_part(model)
    if part is None: return fail('CAE must contain exactly one 120 x 120 x 10 flange analysis part')
    volume=part_volume(part)
    if volume is None or not close(volume,SPEC['expected_step_volume_mm3'],SPEC['step_volume_tol_mm3']):
        return fail('CAE flange volume mismatch got %s expected %s'%(volume,SPEC['expected_step_volume_mm3']))
    area=part_surface_area(part)
    if area is not None and not close(area,SPEC['expected_cae_surface_area_mm2'],5.0):
        return fail('CAE flange surface-area mismatch got %s expected %s'%(area,SPEC['expected_cae_surface_area_mm2']))
    log('[PASS] CAE flange volume matches the validated STEP geometry'+
        (' and exterior area matches' if area is not None else ' (partition-safe area check deferred to named faces)'))
    instance_key,instance=find_analysis_instance(model,part_key)
    if instance is None: return fail('CAE must contain exactly one instance of the flange part')
    transform=mesh_rigid_transform(part.nodes,instance.nodes)
    if transform is None: return fail('Cannot derive the flange instance rigid transform from the CAE mesh')
    if not check_part_section_assignment(model,part): return False
    sk=find_key(model.steps,SPEC['step_name'])
    if sk is None: return fail('Missing step '+SPEC['step_name'])
    step_obj=model.steps[sk]
    if not step_kind(step_obj, SPEC['step_kind']): return fail('Step kind mismatch')
    if SPEC.get('step_num_eigen') is not None:
        try: obs=int(getattr(step_obj,'numEigen'))
        except Exception as e: return fail('Step numEigen unreadable: '+str(e))
        if obs != int(SPEC['step_num_eigen']): return fail('Step numEigen mismatch got %s expected %s'%(obs,SPEC['step_num_eigen']))
    part_bolt,part_pressure,part_spatial=task02_expected_faces(part.faces,bbox)
    bolt_expected=part_bolt; pressure_expected=part_pressure
    if (not bolt_expected or not pressure_expected or
            not close(face_indices_area(part.faces,bolt_expected),8.0*2.0*math.pi*3.0*10.0,2.0) or
            not close(face_indices_area(part.faces,pressure_expected),SPEC['expected_pressure_area_mm2'],1.0)):
        return fail('CAE imported part does not expose eight complete bolt holes and the D50 recess floor')
    expected_bolt_nodes=face_indices_node_labels(part.faces,bolt_expected)
    bolt_region,bolt_ok=require_face_region(model,'BOLT_HOLES',bolt_expected,'sets',
                                            expected_nodes=expected_bolt_nodes,allow_nodes=True)
    if not bolt_ok: return False
    pressure_region,pressure_ok=require_face_region(model,'PRESSURE_FACE',pressure_expected,'surfaces')
    if not pressure_ok: return False
    bolt_area=region_area(bolt_region); pressure_area=region_area(pressure_region)
    if bolt_area is not None and not close(bolt_area,8.0*2.0*math.pi*3.0*10.0,2.0):
        return fail('BOLT_HOLES does not cover all eight complete bore walls; area=%s expected=%s'%(bolt_area,8.0*2.0*math.pi*3.0*10.0))
    if pressure_area is None or not close(pressure_area,SPEC['expected_pressure_area_mm2'],1.0):
        return fail('PRESSURE_FACE is not the centered D50 recess floor')
    pre_coords,pre_elements,pre_types=mesh_info(part)
    if not pre_elements or not pre_types or not set(pre_types).issubset(set(['C3D4','C3D8R'])):
        return fail('CAE mesh must use only first-order C3D4/C3D8R; got %s'%pre_types)
    if len(part.nodes) > int(SPEC.get('max_nodes',1000)):
        return fail('CAE mesh is too dense for the Learning Edition: %s nodes'%len(part.nodes))
    if not check_no_active_constraints(model): return False
    if not check_bc_specs(model): return False
    if not check_load_specs(model): return False
    if not check_inp_action_whitelist(model): return False
    if not check_field_output_requests(model): return False
    job=get_obj(mdb.jobs,SPEC['job_name'])
    if job is None: return fail('Missing job '+SPEC['job_name'])
    if nn(getattr(job,'model','')) != nn(SPEC['model_name']):
        return fail(SPEC['job_name']+' is not bound to '+SPEC['model_name'])
    coords,elements,element_types=mesh_info(part)
    if len(elements) < int(SPEC.get('min_elements',1)): return fail('CAE flange has no mesh elements')
    allowed=set(['C3D4','C3D8R'])
    if not element_types or not set(element_types).issubset(allowed):
        return fail('CAE mesh must use only first-order C3D4/C3D8R; got %s'%element_types)
    if len(part.nodes) > int(SPEC.get('max_nodes',1000)):
        return fail('CAE mesh is too dense for the Learning Edition: %s nodes'%len(part.nodes))
    nodes=mesh_node_coordinates(instance.nodes)
    if len(nodes) != len(part.nodes): return fail('Cannot build complete CAE instance node signature')
    element_signature={}
    try:
        for element in instance.elements:
            labels=[]
            for value in element.connectivity:
                index=int(value)
                try: labels.append(int(instance.nodes[index].label))
                except Exception: labels.append(index)
            element_signature[int(element.label)]=(ci(element.type),tuple(labels))
    except Exception as e: return fail('Cannot build CAE element signature: '+str(e))
    local_axis=int(part_spatial.get('axis',2))
    local_center=part_spatial.get('center'); local_pressure_depth=part_spatial.get('pressure_depth')
    center=apply_mesh_transform(transform,local_center)
    bolt_centers=[apply_mesh_transform(transform,point) for point in part_spatial.get('hole_centers',[])]
    local_normal=[0.0,0.0,0.0]
    local_normal[local_axis]=1.0 if local_pressure_depth > local_center[local_axis] else -1.0
    axis_point=apply_mesh_transform(transform,vector_add(local_center,local_normal))
    normal=vector_unit(vector_subtract(axis_point,center))
    local_pressure_point=list(local_center); local_pressure_point[local_axis]=local_pressure_depth
    pressure_point=apply_mesh_transform(transform,tuple(local_pressure_point))
    CAE_AUDIT={'instance_name':str(instance_key),'node_count':len(part.nodes),'element_count':len(elements),
               'element_types':element_types,'nodes':nodes,'elements':element_signature,
               'bolt_node_labels':region_node_labels(bolt_region),
               'pressure_node_labels':region_node_labels(pressure_region),
               'bolt_centers':bolt_centers,'normal':normal,'center':center,
               'pressure_point':pressure_point}
    return ok('CAE geometry, regions, pressure, material, job, and first-order mesh checks passed')


def data_nonzero(data):
    try:
        if hasattr(data, '__iter__') and not isinstance(data, (str, bytes)):
            for x in data:
                if abs(float(x)) > 1.0e-12: return True
            return False
        return abs(float(data)) > 1.0e-12
    except Exception: return False


def field_nonzero(field):
    try:
        n=0
        for v in field.values:
            if data_nonzero(getattr(v,'data',None)): return True
            n += 1
            if n > 5000: break
    except Exception: return False
    return False


def odb_frame(frames, idx):
    n=len(frames)
    if idx < 0: idx=n+idx
    return frames[idx]


def odb_frames_from(frames, start):
    return [frames[i] for i in range(start, len(frames))]


def parse_frame_eigenvalue(frame):
    desc=''
    try: desc=frame.description or ''
    except Exception: desc=''
    try:
        tokens=desc.replace(',',' ').replace(':',' ').replace('=',' ').split()
        for i,tok in enumerate(tokens):
            if tok.lower().startswith('eigen') and i+1 < len(tokens):
                try: return float(tokens[i+1])
                except Exception: pass
    except Exception: pass
    try:
        val=float(frame.frameValue)
        if val > 0.0: return val
    except Exception: pass
    return None


def field_subset(field, region):
    try: return field.getSubset(region=region)
    except Exception: return None


def field_max_value(field, attribute=None):
    maximum=0.0; observed_any=False
    try:
        for value in field.values:
            try:
                if attribute:
                    observed=float(getattr(value,attribute))
                else:
                    data=getattr(value,'data',())
                    if hasattr(data,'__iter__') and not isinstance(data,(str,bytes)):
                        observed=math.sqrt(float(data[0])*float(data[0])+
                                           float(data[1])*float(data[1])+
                                           float(data[2])*float(data[2]))
                    else: observed=abs(float(data))
                maximum=max(maximum,abs(observed)); observed_any=True
            except Exception: continue
    except Exception: return None
    return maximum if observed_any else None


def odb_node_set(odb, instance, name):
    try:
        key=find_key(odb.rootAssembly.nodeSets,name)
        if key is not None: return odb.rootAssembly.nodeSets[key]
    except Exception: pass
    try:
        key=find_key(instance.nodeSets,name)
        if key is not None: return instance.nodeSets[key]
    except Exception: pass
    return None


def odb_surface(odb, instance, name):
    try:
        key=find_key(odb.rootAssembly.surfaces,name)
        if key is not None: return odb.rootAssembly.surfaces[key]
    except Exception: pass
    try:
        key=find_key(instance.surfaces,name)
        if key is not None: return instance.surfaces[key]
    except Exception: pass
    return None


def odb_instance_uses_material(odb, instance, material_name):
    expected=set(int(element.label) for element in instance.elements); covered=set()
    if not expected: return False
    try: assignments=instance.sectionAssignments
    except Exception: return False
    for assignment in assignments:
        try:
            labels=collect_entity_labels(assignment.region.elements)
            section_key=find_key(odb.sections,assignment.sectionName)
            if section_key is None: return False
            if nn(getattr(odb.sections[section_key],'material','')) != nn(material_name): return False
            covered.update(labels)
        except Exception: return False
    return covered == expected


def value_instance_name(value):
    try: return str(value.instance.name)
    except Exception: return ''


def field_values_for_nodes(field, instance_name, labels):
    out=[]; expected=set(int(label) for label in labels)
    try:
        for value in field.values:
            try: label=int(value.nodeLabel)
            except Exception: continue
            if label not in expected: continue
            observed_instance=value_instance_name(value)
            if observed_instance and nn(observed_instance) != nn(instance_name): continue
            out.append(value)
    except Exception: return []
    return out


def values_nonzero(values):
    for value in values:
        if data_nonzero(getattr(value,'data',None)): return True
    return False


def vector_sum_values(values):
    total=[0.0,0.0,0.0]
    for value in values:
        data=getattr(value,'data',())
        for index in range(min(3,len(data))): total[index] += float(data[index])
    return total


def vector_magnitude(values):
    return math.sqrt(float(values[0])*float(values[0])+
                     float(values[1])*float(values[1])+
                     float(values[2])*float(values[2]))


def max_vector_magnitude(values):
    maximum=0.0
    for value in values:
        data=getattr(value,'data',())
        maximum=max(maximum,vector_magnitude(data[:3]))
    return maximum


def reaction_sums_by_centers(values, instance, labels, centers, normal):
    if len(centers) != 8: return None
    coords={int(node.label):tuple(float(value) for value in node.coordinates) for node in instance.nodes}
    normal=vector_unit(normal)
    if normal is None: return None
    groups=[[] for ignored in centers]
    for value in values:
        try: label=int(value.nodeLabel)
        except Exception: continue
        if label not in labels: continue
        observed_instance=value_instance_name(value)
        if observed_instance and nn(observed_instance) != nn(instance.name): continue
        point=coords.get(label)
        if point is None: return None
        distances=[]
        for center in centers:
            delta=vector_subtract(point,center)
            planar=vector_subtract(delta,vector_scale(normal,vector_dot(delta,normal)))
            distances.append(vector_dot(planar,planar))
        index=min(range(len(distances)),key=lambda item:distances[item])
        if distances[index] > 3.3*3.3: return None
        groups[index].append(value)
    if any(not group for group in groups): return None
    return [vector_sum_values(group) for group in groups]


def odb_region_nodes_match_pressure(instance, labels, audit):
    if not labels: return False
    coords={int(node.label):tuple(float(value) for value in node.coordinates) for node in instance.nodes}
    center=audit.get('center') or (0.0,0.0,0.0)
    pressure_point=audit.get('pressure_point')
    normal=vector_unit(audit.get('normal'))
    if pressure_point is None or normal is None: return False
    radii=[]
    for label in labels:
        point=coords.get(int(label))
        if point is None or abs(vector_dot(vector_subtract(point,pressure_point),normal)) > 0.2: return False
        delta=vector_subtract(point,center)
        planar=vector_subtract(delta,vector_scale(normal,vector_dot(delta,normal)))
        radius=vector_length(planar)
        if radius > 25.2: return False
        radii.append(radius)
    return bool(radii) and max(radii) >= 20.0


def scalar_field_sum_for_nodes(field, instance_name, labels):
    total=0.0; observed=False; expected=set(int(label) for label in labels)
    try:
        for value in field.values:
            try: label=int(value.nodeLabel)
            except Exception: continue
            if label not in expected: continue
            value_instance=value_instance_name(value)
            if value_instance and nn(value_instance) != nn(instance_name): continue
            data=getattr(value,'data',0.0)
            if hasattr(data,'__iter__') and not isinstance(data,(str,bytes)):
                data=list(data)[0] if data else 0.0
            total += float(data); observed=True
    except Exception: return None
    return total if observed else None


def nforc_sum_for_nodes(frame, instance_name, labels):
    total=[]
    for component in ['NFORC1','NFORC2','NFORC3']:
        key=find_key(frame.fieldOutputs,component)
        if key is None: return None
        value=scalar_field_sum_for_nodes(frame.fieldOutputs[key],instance_name,labels)
        if value is None: return None
        total.append(value)
    return total


def check_odb():
    if openOdb is None: return fail('Run evaluator with Abaqus cae noGUI')
    path=dp(SPEC['job_name']+'.odb')
    if not nonempty(path,1024): return fail('Missing ODB '+path)
    odb=None
    try:
        odb=openOdb(path=path, readOnly=True)
        status=ci(getattr(odb.diagnosticData,'jobStatus',''))
        if 'COMPLETED' not in status or 'SUCCESS' not in status:
            return fail('ODB job did not complete successfully: '+status)
        try:
            if int(getattr(odb.diagnosticData,'numberOfAnalysisErrors')) != 0:
                return fail('ODB reports analysis errors')
        except Exception: pass
        try:
            odb_job_name=str(getattr(odb.jobData,'name',''))
            if odb_job_name and nn(os.path.splitext(os.path.basename(odb_job_name))[0]) != nn(SPEC['job_name']):
                return fail('ODB job identity does not match '+SPEC['job_name'])
        except Exception: pass
        sk=find_key(odb.steps,SPEC['step_name'])
        if sk is None: return fail('Missing ODB step')
        st=odb.steps[sk]
        if len(st.frames) < int(SPEC.get('min_frames',1)): return fail('Too few ODB frames')
        if SPEC.get('min_mode_frames') is not None:
            modes=odb_frames_from(st.frames, 1)
            if len(modes) < int(SPEC['min_mode_frames']): return fail('Too few buckle mode frames')
            vals=[parse_frame_eigenvalue(fr) for fr in modes]
            vals=[v for v in vals if v is not None and v > 0.0]
            if len(vals) < int(SPEC['min_mode_frames']): return fail('Could not parse required positive buckle eigenvalues')
        last_frame=odb_frame(st.frames, -1)
        fields=set([ci(k) for k in last_frame.fieldOutputs.keys()])
        for f in SPEC.get('required_odb_fields',[]):
            if ci(f) not in fields: return fail('Required ODB field output missing: '+str(f))
        any_fields=SPEC.get('any_odb_fields',[])
        if any_fields and not (fields & set([ci(x) for x in any_fields])): return fail('Expected one of ODB field outputs missing: '+str(any_fields))
        if not CAE_AUDIT: return fail('CAE mesh signature unavailable before ODB check')
        instance_name=CAE_AUDIT.get('instance_name')
        unexpected_instances=[]
        try:
            for candidate_key in odb.rootAssembly.instances.keys():
                candidate=odb.rootAssembly.instances[candidate_key]
                if nn(candidate_key) not in (nn('ASSEMBLY'),nn(instance_name)) and len(candidate.elements) > 0:
                    unexpected_instances.append(str(candidate_key))
        except Exception: return fail('Cannot enumerate ODB analysis instances')
        if unexpected_instances:
            return fail('ODB contains unexpected additional meshed instances: '+', '.join(unexpected_instances))
        ik=find_key(odb.rootAssembly.instances,instance_name)
        if ik is None: return fail('ODB missing CAE flange instance '+str(instance_name))
        instance=odb.rootAssembly.instances[ik]
        for f in SPEC.get('nonzero_odb_fields',[]):
            key=find_key(last_frame.fieldOutputs, f)
            if key is None: return fail('Required nonzero ODB field missing: '+str(f))
            subset=field_subset(last_frame.fieldOutputs[key],instance)
            if subset is None or not field_nonzero(subset):
                return fail('ODB field is zero on the target flange instance: '+str(f))
        material_name=SPEC['material']['name']
        material_key=find_key(getattr(odb,'materials',{}),material_name)
        if material_key is None: return fail('ODB is missing material '+material_name)
        try:
            elastic=odb.materials[material_key].elastic.table[0]
            odb_e=float(elastic[0]); odb_nu=float(elastic[1])
        except Exception as e: return fail('Cannot inspect ODB Steel elastic properties: '+str(e))
        if not close_rel(odb_e,SPEC['material']['E'],abs_tol=1.0,rel_tol=0.01) or not close(odb_nu,SPEC['material']['nu'],0.02):
            return fail('ODB Steel elastic properties do not match the specified material')
        if not odb_instance_uses_material(odb,instance,material_name):
            return fail('ODB target flange elements are not fully assigned to Steel sections')
        u_key=find_key(last_frame.fieldOutputs,'U'); s_key=find_key(last_frame.fieldOutputs,'S')
        target_u=field_subset(last_frame.fieldOutputs[u_key],instance)
        target_s=field_subset(last_frame.fieldOutputs[s_key],instance)
        max_u=field_max_value(target_u,'magnitude'); max_s=field_max_value(target_s,'mises')
        if max_u is None or max_u < 1.0e-5 or max_u > 0.05:
            return fail('ODB target-instance displacement is not physically consistent with the 1 MPa recess pressure: '+str(max_u))
        if max_s is None or max_s < 0.05 or max_s > 100.0:
            return fail('ODB target-instance stress is not physically consistent with the 1 MPa recess pressure: '+str(max_s))
        bolt_set=odb_node_set(odb,instance,'BOLT_HOLES')
        if bolt_set is None: return fail('ODB is missing the BOLT_HOLES support node set')
        bolt_labels=region_node_labels(bolt_set)
        if not bolt_labels: return fail('ODB BOLT_HOLES node set is empty')
        cae_bolt_labels=CAE_AUDIT.get('bolt_node_labels') or set()
        if cae_bolt_labels and bolt_labels != set(cae_bolt_labels):
            return fail('ODB BOLT_HOLES nodes do not match the active CAE support region')
        pressure_surface=odb_surface(odb,instance,'PRESSURE_FACE')
        if pressure_surface is None: return fail('ODB is missing the PRESSURE_FACE surface')
        pressure_labels=region_node_labels(pressure_surface)
        cae_pressure_labels=CAE_AUDIT.get('pressure_node_labels') or set()
        if cae_pressure_labels and pressure_labels != set(cae_pressure_labels):
            return fail('ODB PRESSURE_FACE nodes do not match the CAE pressure region')
        if not odb_region_nodes_match_pressure(instance,pressure_labels,CAE_AUDIT):
            return fail('ODB PRESSURE_FACE is not located on the centered D50 recess floor')
        pressure_u=field_values_for_nodes(last_frame.fieldOutputs[u_key],instance_name,pressure_labels)
        if not pressure_u or not values_nonzero(pressure_u):
            return fail('ODB displacement response is zero on PRESSURE_FACE')
        pressure_max_u=max_vector_magnitude(pressure_u)
        if pressure_max_u < 0.5*max_u:
            return fail('ODB maximum displacement is not localized to PRESSURE_FACE')
        pressure_nforc=nforc_sum_for_nodes(last_frame,instance_name,pressure_labels)
        if pressure_nforc is None:
            return fail('ODB NFORC1/2/3 are unavailable on PRESSURE_FACE')
        expected=float(SPEC['expected_pressure_resultant_n'])
        pressure_nforc_resultant=vector_magnitude(pressure_nforc)
        if not close_rel(pressure_nforc_resultant,expected,abs_tol=2.0,rel_tol=0.05):
            return fail('ODB PRESSURE_FACE NFORC mismatch got %s N expected %s N'%
                        (pressure_nforc_resultant,expected))
        normal=vector_unit(CAE_AUDIT.get('normal'))
        nforc_projection=vector_dot(pressure_nforc,normal)
        if pressure_nforc_resultant <= 0.0 or nforc_projection/pressure_nforc_resultant < 0.99:
            return fail('ODB PRESSURE_FACE NFORC sign is inconsistent with positive pressure: '+repr(pressure_nforc))
        cf_key=find_key(last_frame.fieldOutputs,'CF')
        if cf_key is not None:
            target_cf=field_subset(last_frame.fieldOutputs[cf_key],instance)
            if target_cf is None: return fail('ODB CF cannot be restricted to the target flange instance')
            if field_nonzero(target_cf):
                return fail('ODB contains nonzero concentrated-force output on the target flange')
        rf_key=find_key(last_frame.fieldOutputs,'RF')
        try:
            reaction=vector_sum_values(last_frame.fieldOutputs[rf_key].values)
            bolt_rf_values=field_values_for_nodes(last_frame.fieldOutputs[rf_key],instance_name,bolt_labels)
            bolt_reaction=vector_sum_values(bolt_rf_values)
        except Exception as e: return fail('Cannot sum ODB reaction-force vectors: '+str(e))
        resultant=vector_magnitude(reaction); bolt_resultant=vector_magnitude(bolt_reaction)
        if not close_rel(resultant,expected,abs_tol=2.0,rel_tol=0.05):
            return fail('ODB reaction equilibrium mismatch got %s N expected %s N'%(resultant,expected))
        if not bolt_rf_values or not close_rel(bolt_resultant,expected,abs_tol=2.0,rel_tol=0.05):
            return fail('ODB BOLT_HOLES reaction mismatch got %s N expected %s N'%(bolt_resultant,expected))
        group_reactions=reaction_sums_by_centers(
            bolt_rf_values,instance,bolt_labels,CAE_AUDIT.get('bolt_centers',[]),normal)
        if (group_reactions is None or
                any(vector_magnitude(group) < 0.03*expected for group in group_reactions)):
            return fail('ODB reaction force is not carried by all eight BOLT_HOLES')
        outside=[reaction[index]-bolt_reaction[index] for index in range(3)]
        if vector_magnitude(outside) > max(2.0,0.01*expected):
            return fail('ODB has material reaction force outside BOLT_HOLES: '+repr(outside))
        reaction_projection=vector_dot(reaction,normal)
        if (resultant <= 0.0 or reaction_projection/resultant < 0.99 or
                vector_dot(reaction,pressure_nforc)/(resultant*pressure_nforc_resultant) < 0.99):
            return fail('ODB reaction and PRESSURE_FACE NFORC are not aligned on the pressure-face axis')
        if len(instance.nodes) != CAE_AUDIT.get('node_count') or len(instance.elements) != CAE_AUDIT.get('element_count'):
            return fail('ODB mesh counts do not match CAE')
        odb_types=sorted(set(ci(element.type) for element in instance.elements))
        if odb_types != CAE_AUDIT.get('element_types'):
            return fail('ODB element types do not match CAE: %s vs %s'%(odb_types,CAE_AUDIT.get('element_types')))
        cae_nodes=CAE_AUDIT.get('nodes',{})
        for node in instance.nodes:
            expected_coords=cae_nodes.get(int(node.label))
            if expected_coords is None or len(expected_coords) != len(node.coordinates):
                return fail('ODB node labels do not match CAE')
            if any(abs(float(node.coordinates[i])-float(expected_coords[i])) > 1.0e-5 for i in range(len(expected_coords))):
                return fail('ODB node coordinates do not match CAE at label %s'%node.label)
        cae_elements=CAE_AUDIT.get('elements',{})
        for element in instance.elements:
            expected_element=cae_elements.get(int(element.label))
            observed=(ci(element.type),tuple(int(value) for value in element.connectivity))
            if expected_element != observed:
                return fail('ODB element connectivity/type does not match CAE at label %s'%element.label)
        any_nonzero=SPEC.get('nonzero_odb_any_fields',[])
        if any_nonzero:
            matched=False
            for f in any_nonzero:
                key=find_key(last_frame.fieldOutputs, f)
                if key is not None and field_nonzero(last_frame.fieldOutputs[key]): matched=True
            if not matched: return fail('No required heat-flow ODB field is nonzero: '+str(any_nonzero))
        if SPEC.get('nonzero_odb_fields') or SPEC.get('nonzero_odb_any_fields'):
            return ok('ODB target Steel flange, pressure-face response, bolt reactions, and mesh match CAE')
    except Exception as e: return fail('Cannot inspect ODB: '+str(e))
    finally:
        try:
            if odb: odb.close()
        except Exception: pass
    return ok('ODB checks passed')


def check_files():
    for f in SPEC.get('required_files',[]):
        if not nonempty(dp(f),1): return fail('Missing required output '+f)
    return ok('Required files exist')


def main():
    return check_bypass() and check_files() and check_extra_deliverables() and check_dxf() and check_step() and check_chain_evidence() and check_cae() and check_odb()
try:
    finish(main())
except SystemExit:
    raise
except Exception:
    log('[EXCEPTION] '+traceback.format_exc()); finish(False)
