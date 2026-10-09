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
 'bbox': [120, 80, 6],
 'bbox_tol': 0.05,
 'bc_checks': [{'kind': 'constraint', 'name': 'BC-FixedHoles', 'region': 'FIXED_HOLES'}],
 'bc_names': ['BC-FixedHoles'],
 'cad_text': 'AutoCAD: draw a 120 x 80 mm rectangle on OUTLINE, D8 holes at (15,15), (105,15), '
             '(15,65), (105,65) on HOLE, and a centered 40 x 12 mm rounded slot on CUTOUT; save '
             'stage1_profile.dxf. SolidWorks: import it, extrude 6 mm, cut holes/slot through, add '
             '1 mm chamfers, export C:\\Users\\User\\Desktop\\stage2_geometry.step.',
 'cae_text': 'Import stage2_geometry.step. Create Steel E=210000 MPa nu=0.3. Create sets '
             'FIXED_HOLES and LOAD_HOLES, constrain the two left holes, apply 800 N tensile load '
             'to the two right holes, submit Job-PlateStatic.',
 'chain': 'three',
 'chain_evidence': {'cae_markers': ['EW_ACAD_SW_ABQ_01', 'IMPORTED_FROM_stage2_geometry.step'],
                    'dxf_markers': ['EW_ACAD_SW_ABQ_01', 'AUTOCAD_TO_SOLIDWORKS'],
                    'step_markers': ['EW_ACAD_SW_ABQ_01',
                                     'FROM_stage1_profile.dxf',
                                     'SOLIDWORKS_TO_ABAQUS']},
 'chain_token': 'EW_ACAD_SW_ABQ_01',
 'dxf_checks': {'bbox': [120, 80],
                'circles': [{'r': 4, 'x': 15, 'y': 15},
                            {'r': 4, 'x': 105, 'y': 15},
                            {'r': 4, 'x': 15, 'y': 65},
                            {'r': 4, 'x': 105, 'y': 65}],
                'layers': ['OUTLINE', 'HOLE', 'CUTOUT'],
                'tol': 0.05},
 'expected_step_volume_mm3': 53301.7110745,
 'step_volume_tol_mm3': 2.0,
 'expected_field_any': ['U', 'S'],
 'job_name': 'Job-PlateStatic',
 'load_checks': [{'kind': 'force',
                  'magnitude': 800.0,
                  'name': 'Load-RightHoles',
                  'region': 'LOAD_HOLES',
                  'rel_tol': 0.05,
                  'sign': 'positive'}],
 'load_names': ['Load-RightHoles'],
 'material': {'E': 210000, 'name': 'Steel', 'nu': 0.3},
 'min_elements': 1,
 'min_frames': 2,
 'model_name': 'Model-PlateStatic',
 'nonzero_odb_fields': ['U', 'S'],
 'required_files': ['stage1_profile.dxf',
                    'stage2_geometry.step',
                    'Job-PlateStatic.cae',
                    'Job-PlateStatic.odb'],
 'required_odb_fields': ['U', 'S', 'RF'],
 'required_sets': ['FIXED_HOLES', 'LOAD_HOLES'],
 'required_surfaces': [],
 'section_material': 'Steel',
 'stage_dxf': 'stage1_profile.dxf',
 'stage_step': 'stage2_geometry.step',
 'step_kind': 'STATIC',
 'step_name': 'Step-Static',
 'task_no': 1,
 'title': 'DXF Mounting Plate Static Analysis'}
DETAILS=[]
CAE_AUDIT={}
BC_AUDIT={}
LOAD_AUDIT={}
CAE_OPENED=False
STEP_AUDIT={}
FORBIDDEN=set(['.py','.pyw','.ipynb','.bat','.cmd','.ps1','.psm1','.vbs','.js','.mjs','.scr','.macro','.bas','.vba','.ahk','.sh'])
DELIVERABLE_EXTS=set(['.step','.stp','.dxf','.cae','.odb'])


def log(x): DETAILS.append(str(x))
def fail(x): log('[FAIL] '+str(x)); return False
def ok(x): log('[PASS] '+str(x)); return True
def warn(x): log('[WARN] '+str(x))
def ci(x): return '' if x is None else str(x).strip().upper()
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
    return os.path.join(base,'engiworld_eval_cae_task01')


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
            lower=name.lower(); prefix=SPEC['job_name'].lower()+'.'
            if lower.startswith(prefix):
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
    units=int(doc.header.get('$INSUNITS',0) or 0)
    layers=set(); points=[]; circles=[]; lines=[]; polylines=[]; arcs=[]; texts=[]; entities=[]; z_values=[]; normals=[]
    def z_value(value):
        try: return float(value.z)
        except Exception:
            try: return float(value)
            except Exception: return 0.0
    def layer_state(name):
        try:
            layer=doc.layers.get(name)
            return bool(layer.is_off()),bool(layer.is_frozen())
        except Exception: return False,False
    for entity in recursive_decompose(doc.modelspace()):
        kind=entity.dxftype().upper(); layer=str(entity.dxf.get('layer',''))
        layers.add(layer.upper())
        entities.append({'layer':layer,'type':kind})
        if kind in ('CIRCLE','ARC','LWPOLYLINE','POLYLINE'):
            extrusion=entity.dxf.get('extrusion',(0,0,1))
            try: normal=[float(extrusion.x),float(extrusion.y),float(extrusion.z)]
            except Exception: normal=[float(extrusion[0]),float(extrusion[1]),float(extrusion[2])]
            normals.append({'layer':layer,'normal':normal})
        if kind == 'CIRCLE':
            center=entity.dxf.center; radius=float(entity.dxf.radius)
            z_values.append(float(center.z))
            circles.append({'x':float(center.x),'y':float(center.y),'z':float(center.z),'r':radius,'layer':layer})
            points.extend([(float(center.x)-radius,float(center.y)),
                           (float(center.x)+radius,float(center.y)),
                           (float(center.x),float(center.y)-radius),
                           (float(center.x),float(center.y)+radius)])
        elif kind == 'LINE':
            start=entity.dxf.start; end=entity.dxf.end
            z_values.extend([float(start.z),float(end.z)])
            row={'layer':layer,'pts':[(float(start.x),float(start.y)),
                                     (float(end.x),float(end.y))],'type':kind}
            lines.append(row); points.extend(row['pts'])
        elif kind in ('LWPOLYLINE','POLYLINE'):
            vertices=[]
            if kind == 'LWPOLYLINE':
                elevation=z_value(entity.dxf.get('elevation',0.0)); z_values.append(elevation)
                source=entity.get_points('xyb')
                for value in source:
                    vertices.append({'x':float(value[0]),'y':float(value[1]),'z':elevation,'bulge':float(value[2])})
            else:
                for vertex in entity.vertices:
                    location=vertex.dxf.location
                    z_values.append(float(location.z))
                    vertices.append({'x':float(location.x),'y':float(location.y),
                                     'z':float(location.z),'bulge':float(vertex.dxf.get('bulge',0.0))})
            row={'layer':layer,'vertices':vertices,'closed':bool(entity.is_closed),'type':kind}
            polylines.append(row); points.extend([(v['x'],v['y']) for v in vertices])
        elif kind == 'ARC':
            center=entity.dxf.center
            z_values.append(float(center.z))
            arcs.append({'layer':layer,'x':float(center.x),'y':float(center.y),
                         'z':float(center.z),'r':float(entity.dxf.radius),'start':float(entity.dxf.start_angle)%360.0,
                         'end':float(entity.dxf.end_angle)%360.0})
        elif kind in ('TEXT','ATTRIB'):
            insert=entity.dxf.get('insert',(0,0,0)); off,frozen=layer_state(layer)
            texts.append({'layer':layer,'text':str(entity.dxf.text),'type':kind,
                          'height':float(entity.dxf.get('height',0.0) or 0.0),
                          'invisible':bool(int(entity.dxf.get('invisible',0) or 0)),
                          'layer_off':off,'layer_frozen':frozen,
                          'x':float(insert.x),'y':float(insert.y)})
        elif kind == 'MTEXT':
            insert=entity.dxf.get('insert',(0,0,0)); off,frozen=layer_state(layer)
            texts.append({'layer':layer,'text':str(entity.plain_text()),'type':kind,
                          'height':float(entity.dxf.get('char_height',0.0) or 0.0),
                          'invisible':bool(int(entity.dxf.get('invisible',0) or 0)),
                          'layer_off':off,'layer_frozen':frozen,
                          'x':float(insert.x),'y':float(insert.y)})
    out={'ok':True,'units':units,'layers':sorted(layers),'points':points,'circles':circles,'lines':lines,
         'polylines':polylines,'arcs':arcs,'texts':texts,'entities':entities,'z_values':z_values,
         'normals':normals}
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


def point_close(a, b, tol):
    return close(a[0],b[0],tol) and close(a[1],b[1],tol)


def point_set_matches(got, expected, tol):
    if len(got) != len(expected): return False
    unused=list(got)
    for req in expected:
        hit=None
        for i,p in enumerate(unused):
            if point_close(p,req,tol): hit=i; break
        if hit is None: return False
        unused.pop(hit)
    return not unused


def line_matches(line, a, b, tol):
    pts=line.get('pts',[])
    if len(pts) != 2: return False
    return ((point_close(pts[0],a,tol) and point_close(pts[1],b,tol)) or
            (point_close(pts[0],b,tol) and point_close(pts[1],a,tol)))


def cyclic_segments(vertices):
    out=[]
    for index,vertex in enumerate(vertices):
        nxt=vertices[(index+1)%len(vertices)]
        out.append(((float(vertex['x']),float(vertex['y'])),
                    (float(nxt['x']),float(nxt['y'])),float(vertex.get('bulge',0.0))))
    return out


def segment_matches(segment, a, b, bulge, tol):
    start,end,observed=segment
    return point_close(start,a,tol) and point_close(end,b,tol) and close(observed,bulge,0.01)


def unexpected_dxf_geometry(data, layer, allowed):
    text_types=set(['TEXT','MTEXT','ATTRIB'])
    return sorted(set(ci(row.get('type')) for row in data.get('entities',[])
                      if ci(row.get('layer')) == ci(layer) and
                      ci(row.get('type')) not in set(allowed) and
                      ci(row.get('type')) not in text_types))


def normalized_closed_vertices(vertices, tol):
    out=list(vertices or [])
    if len(out) > 1:
        first=(float(out[0]['x']),float(out[0]['y']))
        last=(float(out[-1]['x']),float(out[-1]['y']))
        if point_close(first,last,tol): out=out[:-1]
    return out


def arc_endpoints(arc):
    center=(float(arc['x']),float(arc['y'])); radius=float(arc['r'])
    start=math.radians(float(arc.get('start',0.0))%360.0)
    end=math.radians(float(arc.get('end',0.0))%360.0)
    return ((center[0]+radius*math.cos(start),center[1]+radius*math.sin(start)),
            (center[0]+radius*math.cos(end),center[1]+radius*math.sin(end)))


def segments_form_single_cycle(segments, tol):
    representatives=[]; edges=[]
    def node_index(point):
        for index,existing in enumerate(representatives):
            if point_close(point,existing,tol): return index
        representatives.append(point); return len(representatives)-1
    for start,end in segments:
        a=node_index(start); b=node_index(end)
        if a == b: return False
        edges.append((a,b))
    if not edges: return False
    degrees=[0 for item in representatives]; adjacency={}
    for a,b in edges:
        degrees[a] += 1; degrees[b] += 1
        adjacency.setdefault(a,set()).add(b); adjacency.setdefault(b,set()).add(a)
    if any(value != 2 for value in degrees): return False
    seen=set(); stack=[0]
    while stack:
        node=stack.pop()
        if node in seen: continue
        seen.add(node); stack.extend(adjacency.get(node,set())-seen)
    return len(seen) == len(representatives)


def line_arc_slot_matches(lines, arcs, tol):
    if not slot_straight_lines_match(lines,tol): return False
    sweeps={'left':0.0,'right':0.0}; segments=[]
    for line in lines: segments.append((line['pts'][0],line['pts'][1]))
    for arc in arcs:
        center=(float(arc['x']),float(arc['y'])); radius=float(arc['r'])
        if point_close(center,(46,40),tol): side='left'
        elif point_close(center,(74,40),tol): side='right'
        else: return False
        if not close(radius,6.0,tol): return False
        start=float(arc.get('start',0.0))%360.0; end=float(arc.get('end',0.0))%360.0
        sweep=(end-start)%360.0
        if sweep <= 0.0 or sweep > 180.0+0.05: return False
        middle=math.radians((start+sweep/2.0)%360.0)
        middle_x=center[0]+radius*math.cos(middle)
        if side == 'left' and middle_x > 46.0+tol: return False
        if side == 'right' and middle_x < 74.0-tol: return False
        sweeps[side] += sweep; segments.append(arc_endpoints(arc))
    return (close(sweeps['left'],180.0,0.05) and close(sweeps['right'],180.0,0.05) and
            segments_form_single_cycle(segments,tol))


def slot_straight_lines_match(lines, tol):
    totals={'bottom':0.0,'top':0.0}
    for line in lines:
        points=line.get('pts',[])
        if len(points) != 2: return False
        a=points[0]; b=points[1]
        if close(a[1],34.0,tol) and close(b[1],34.0,tol): key='bottom'
        elif close(a[1],46.0,tol) and close(b[1],46.0,tol): key='top'
        else: return False
        lo=min(a[0],b[0]); hi=max(a[0],b[0])
        if lo < 46.0-tol or hi > 74.0+tol or hi-lo <= tol: return False
        totals[key] += hi-lo
    return close(totals['bottom'],28.0,tol) and close(totals['top'],28.0,tol)


def bulge_polyline_slot_matches(vertices, tol):
    lines=[]; curves=[]; segments=[]
    for start,end,bulge in cyclic_segments(vertices):
        segments.append((start,end))
        if close(bulge,0.0,0.01):
            lines.append({'pts':[start,end]}); continue
        theta=4.0*math.atan(float(bulge)); chord_x=end[0]-start[0]; chord_y=end[1]-start[1]
        chord=math.sqrt(chord_x*chord_x+chord_y*chord_y)
        if chord <= tol or abs(math.sin(abs(theta)/2.0)) < 1.0e-9: return False
        radius=chord/(2.0*math.sin(abs(theta)/2.0))
        midpoint=((start[0]+end[0])/2.0,(start[1]+end[1])/2.0)
        left=(-chord_y/chord,chord_x/chord)
        offset=chord/(2.0*math.tan(theta/2.0))
        center=(midpoint[0]+left[0]*offset,midpoint[1]+left[1]*offset)
        start_angle=math.atan2(start[1]-center[1],start[0]-center[0])
        middle_angle=start_angle+theta/2.0
        curves.append({'center':center,'radius':radius,'sweep':abs(math.degrees(theta)),
                       'middle_x':center[0]+radius*math.cos(middle_angle)})
    if not slot_straight_lines_match(lines,tol) or not segments_form_single_cycle(segments,tol): return False
    sweeps={'left':0.0,'right':0.0}
    for curve in curves:
        center=curve['center']
        if point_close(center,(46,40),tol): side='left'
        elif point_close(center,(74,40),tol): side='right'
        else: return False
        if not close(curve['radius'],6.0,tol) or curve['sweep'] > 180.0+0.05: return False
        if side == 'left' and curve['middle_x'] > 46.0+tol: return False
        if side == 'right' and curve['middle_x'] < 74.0-tol: return False
        sweeps[side] += curve['sweep']
    return close(sweeps['left'],180.0,0.05) and close(sweeps['right'],180.0,0.05)


def line_outline_matches(lines, tol):
    totals={'bottom':0.0,'top':0.0,'left':0.0,'right':0.0}; segments=[]
    for line in lines:
        points=line.get('pts',[])
        if len(points) != 2: return False
        a=points[0]; b=points[1]; segments.append((a,b))
        if close(a[1],0.0,tol) and close(b[1],0.0,tol):
            key='bottom'; lo=min(a[0],b[0]); hi=max(a[0],b[0]); limit=120.0
        elif close(a[1],80.0,tol) and close(b[1],80.0,tol):
            key='top'; lo=min(a[0],b[0]); hi=max(a[0],b[0]); limit=120.0
        elif close(a[0],0.0,tol) and close(b[0],0.0,tol):
            key='left'; lo=min(a[1],b[1]); hi=max(a[1],b[1]); limit=80.0
        elif close(a[0],120.0,tol) and close(b[0],120.0,tol):
            key='right'; lo=min(a[1],b[1]); hi=max(a[1],b[1]); limit=80.0
        else: return False
        if lo < -tol or hi > limit+tol or hi-lo <= tol: return False
        totals[key] += hi-lo
    return (close(totals['bottom'],120.0,tol) and close(totals['top'],120.0,tol) and
            close(totals['left'],80.0,tol) and close(totals['right'],80.0,tol) and
            segments_form_single_cycle(segments,tol))


def check_dxf_outline(data, tol):
    unexpected=unexpected_dxf_geometry(data,'OUTLINE',['LINE','LWPOLYLINE','POLYLINE'])
    if unexpected: return fail('DXF OUTLINE has unexpected geometry entities: '+', '.join(unexpected))
    polys=[p for p in data['polylines'] if ci(p.get('layer')) == 'OUTLINE']
    poly_ok=False
    for poly in polys:
        vertices=normalized_closed_vertices(poly.get('vertices',[]),tol)
        if not poly.get('closed') or len(vertices) < 4: continue
        segments=cyclic_segments(vertices)
        if any(not close(segment[2],0.0,0.01) for segment in segments): continue
        poly_lines=[{'pts':[segment[0],segment[1]]} for segment in segments]
        if line_outline_matches(poly_lines,tol): poly_ok=True
    out_lines=[ln for ln in data['lines'] if ci(ln.get('layer')) == 'OUTLINE' and ln.get('type') == 'LINE']
    lines_ok=line_outline_matches(out_lines,tol)
    if not ((len(polys) == 1 and poly_ok and not out_lines) or (not polys and lines_ok)):
        return fail('DXF OUTLINE is not one connected closed 120 x 80 rectangle with straight edges')
    return True


def check_dxf_slot(data, tol):
    unexpected=unexpected_dxf_geometry(data,'CUTOUT',['LINE','ARC','LWPOLYLINE','POLYLINE','CIRCLE'])
    if unexpected: return fail('DXF CUTOUT has unexpected geometry entities: '+', '.join(unexpected))
    if [c for c in data['circles'] if ci(c.get('layer')) == 'CUTOUT']:
        return fail('DXF CUTOUT uses full circles instead of a closed rounded-slot boundary')
    cut_polys=[p for p in data['polylines'] if ci(p.get('layer')) == 'CUTOUT']
    poly_ok=False
    for poly in cut_polys:
        if not poly.get('closed'): continue
        verts=normalized_closed_vertices(poly.get('vertices',[]),tol)
        if len(verts) >= 4 and bulge_polyline_slot_matches(verts,tol): poly_ok=True
    cut_lines=[ln for ln in data['lines'] if ci(ln.get('layer')) == 'CUTOUT' and ln.get('type') == 'LINE']
    cut_arcs=[a for a in data['arcs'] if ci(a.get('layer')) == 'CUTOUT']
    line_arc_ok=line_arc_slot_matches(cut_lines,cut_arcs,tol)
    if not ((len(cut_polys) == 1 and poly_ok and not cut_lines and not cut_arcs) or
            (not cut_polys and line_arc_ok)):
        return fail('DXF CUTOUT is not one connected closed centered 40 x 12 rounded slot')
    return True


def check_dxf_chain_text(data):
    visible=[]
    for row in data['texts']:
        if ci(row.get('layer')) != 'CHAIN': continue
        if row.get('invisible') or row.get('layer_off') or row.get('layer_frozen'): continue
        if float(row.get('height',0.0)) < 0.5: continue
        if not (-10.0 <= float(row.get('x',0.0)) <= 130.0 and -10.0 <= float(row.get('y',0.0)) <= 90.0): continue
        visible.append(row)
    texts=[t.get('text','') for t in visible]
    if not texts: return fail('DXF CHAIN layer has no native TEXT/MTEXT entity')
    blob='\n'.join(texts)
    for marker in SPEC.get('chain_evidence',{}).get('dxf_markers',[]):
        if not chain_contains(blob,marker): return fail('Missing native DXF chain text: '+marker)
    return True


def check_dxf():
    ds=SPEC.get('dxf_checks')
    if not ds: return ok('No DXF stage')
    path=dp(SPEC['stage_dxf'])
    if not nonempty(path,200): return fail('Missing DXF stage: '+path)
    data=parse_dxf(path); layers=data['layers']; circles=data['circles']
    if int(data.get('units',0)) not in (0,4):
        return fail('DXF insertion units must be unitless/mm, not a conflicting physical unit')
    if any(abs(float(value)) > 0.05 for value in data.get('z_values',[])):
        return fail('DXF profile geometry must lie in the Z=0 plane')
    for row in data.get('normals',[]):
        if ci(row.get('layer')) not in ('OUTLINE','HOLE','CUTOUT'): continue
        normal=row.get('normal') or [0,0,0]
        if (len(normal) != 3 or abs(float(normal[0])) > 1.0e-6 or
                abs(float(normal[1])) > 1.0e-6 or abs(abs(float(normal[2]))-1.0) > 1.0e-6):
            return fail('DXF profile geometry must use an XY-plane extrusion normal')
    for layer in ds.get('layers',[]):
        if ci(layer) not in layers: return fail('Missing DXF layer '+layer)
    tol=ds.get('tol',1.0)
    if not check_dxf_outline(data,tol): return False
    if not check_dxf_slot(data,tol): return False
    if not check_dxf_chain_text(data): return False
    unexpected=unexpected_dxf_geometry(data,'HOLE',['CIRCLE'])
    if unexpected: return fail('DXF HOLE has unexpected geometry entities: '+', '.join(unexpected))
    if ds.get('min_circles') is not None and len(circles) < int(ds['min_circles']): return fail('Too few DXF circles')
    for req in ds.get('circles',[]):
        found=False
        for c in circles:
            if ci(c.get('layer')) == 'HOLE' and close(c['x'],req['x'],tol) and close(c['y'],req['y'],tol) and close(c['r'],req['r'],tol): found=True
        if not found: return fail('Missing required DXF circle near (%s,%s)'%(req['x'],req['y']))
    for req in ds.get('circle_radii',[]):
        cnt=0
        for c in circles:
            if close(c['r'], req['r'], ds.get('tol',1.0)): cnt += 1
        if cnt < int(req.get('count',1)): return fail('Too few DXF circles with radius %s: got %s'%(req['r'],cnt))
    hole_circles=[c for c in circles if ci(c.get('layer')) == 'HOLE']
    if len(hole_circles) != len(ds.get('circles',[])): return fail('DXF HOLE layer must contain exactly four circles')
    for layer, min_count in ds.get('layer_line_min',{}).items():
        cnt=len([ln for ln in data['lines'] if ci(ln.get('layer')) == ci(layer)])
        if cnt < int(min_count): return fail('Too few DXF line/polyline entities on layer %s: got %s'%(layer,cnt))
    return ok('DXF checks passed')


def dims_close(got, exp, tol):
    if len(got) != len(exp): return False
    g=sorted([abs(float(x)) for x in got]); e=sorted([abs(float(x)) for x in exp])
    return all(abs(a-b) <= tol for a,b in zip(g,e))


def abaqus_step_bbox(path):
    if mdb is None or THREE_D is None or DEFORMABLE_BODY is None: return None
    model_name='__eval_step_import__'
    part_name='__eval_step_part__'
    try:
        if model_name in mdb.models.keys(): del mdb.models[model_name]
    except Exception: pass
    try:
        model=mdb.Model(name=model_name)
        try: geom=mdb.openStep(fileName=path)
        except Exception: geom=mdb.openStep(path)
        part=model.PartFromGeometryFile(name=part_name, geometryFile=geom, combine=False, dimensionality=THREE_D, type=DEFORMABLE_BODY)
        bb=part.vertices.getBoundingBox()
        low=bb.get('low', None); high=bb.get('high', None)
        if low is None or high is None: return None
        return [float(high[i])-float(low[i]) for i in range(3)]
    except Exception as e:
        warn('Abaqus STEP fallback failed: '+str(e))
        return None
    finally:
        try:
            if model_name in mdb.models.keys(): del mdb.models[model_name]
        except Exception: pass


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
        probes = {}
        points = {
            "hole_15_15_low": (15.0,15.0,0.5), "hole_15_15_mid": (15.0,15.0,3.0), "hole_15_15_high": (15.0,15.0,5.5),
            "hole_105_15": (105.0,15.0,3.0), "hole_15_65": (15.0,65.0,3.0), "hole_105_65": (105.0,65.0,3.0),
            "hole_15_15_outside": (19.5,15.0,3.0), "hole_105_15_outside": (100.5,15.0,3.0),
            "slot_low": (60.0,40.0,0.5), "slot_mid": (60.0,40.0,3.0), "slot_high": (60.0,40.0,5.5),
            "slot_left_end": (40.5,40.0,3.0), "slot_right_end": (79.5,40.0,3.0),
            "slot_bottom_inside": (60.0,34.5,3.0), "slot_top_inside": (60.0,45.5,3.0),
            "slot_left_corner_material": (40.5,34.5,3.0), "slot_right_corner_material": (79.5,45.5,3.0),
            "slot_below_material": (60.0,33.5,3.0), "slot_above_material": (60.0,46.5,3.0),
            "chamfer_left_bottom": (0.25,40.0,0.25), "chamfer_right_bottom": (119.75,40.0,0.25),
            "chamfer_front_bottom": (30.0,0.25,0.25), "chamfer_back_bottom": (30.0,79.75,0.25),
            "chamfer_left_top": (0.25,40.0,5.75), "chamfer_right_top": (119.75,40.0,5.75),
            "chamfer_front_top": (30.0,0.25,5.75), "chamfer_back_top": (30.0,79.75,5.75),
            "chamfer_left_material": (1.25,40.0,0.25), "chamfer_right_material": (118.75,40.0,5.75),
            "chamfer_front_material": (30.0,1.25,0.25), "chamfer_back_material": (30.0,78.75,5.75)
        }
        for name, point in points.items():
            probes[name] = bool(solid.isInside(cq.Vector(*point), 1.0e-5))
        faces = solid.Faces()
        out = {"ok": True, "bbox": [box.xlen, box.ylen, box.zlen],
               "volume": float(solid.Volume()),
               "surface_area": float(sum(face.Area() for face in faces)),
               "face_count": len(faces), "edge_count": len(solid.Edges()), "probes": probes}
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


def check_step():
    global STEP_AUDIT
    STEP_AUDIT={}
    path=dp(SPEC['stage_step'])
    if not nonempty(path, 1): return fail('Missing STEP stage: '+path)
    h=head(path,4096).upper()
    if 'ISO-10303' not in h and 'STEP' not in h: return fail('STEP header not recognized')
    ext=external_cadquery_step_metrics(path)
    if not ext.get('ok'):
        if ext.get('solid_count') is not None: return fail('STEP must contain exactly one solid')
        return fail('STEP geometry could not be validated with CadQuery: '+str(ext.get('error','unknown')))
    got=ext.get('bbox')
    if not dims_close(got, SPEC['bbox'], SPEC.get('bbox_tol',8.0)): return fail('STEP bbox mismatch got %s expected %s'%(got,SPEC['bbox']))
    volume=ext.get('volume')
    if not close(volume,SPEC['expected_step_volume_mm3'],SPEC['step_volume_tol_mm3']):
        return fail('STEP volume mismatch got %s expected %s'%(volume,SPEC['expected_step_volume_mm3']))
    log('[PASS] STEP imported topology has %s faces and %s edges'%(ext.get('face_count'),ext.get('edge_count')))
    probes=ext.get('probes') or {}
    expected_void=['hole_15_15_low','hole_15_15_mid','hole_15_15_high','hole_105_15','hole_15_65','hole_105_65',
                   'slot_low','slot_mid','slot_high','slot_left_end','slot_right_end','slot_bottom_inside','slot_top_inside',
                   'chamfer_left_bottom','chamfer_right_bottom','chamfer_front_bottom','chamfer_back_bottom',
                   'chamfer_left_top','chamfer_right_top','chamfer_front_top','chamfer_back_top']
    expected_solid=['hole_15_15_outside','hole_105_15_outside','slot_left_corner_material','slot_right_corner_material',
                    'slot_below_material','slot_above_material','chamfer_left_material','chamfer_right_material',
                    'chamfer_front_material','chamfer_back_material']
    for name in expected_void:
        if name not in probes or probes[name]: return fail('STEP missing required hole/slot/chamfer void at '+name)
    for name in expected_solid:
        if name not in probes or not probes[name]: return fail('STEP removes required material at '+name)
    STEP_AUDIT={'volume':float(volume),'surface_area':float(ext.get('surface_area'))}
    return ok('STEP solid, volume, through holes, rounded slot, and eight outer chamfers passed')



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


def step_quoted_data(path):
    raw=head(path,4000000)
    upper=raw.upper(); marker=upper.find('DATA;')
    if marker < 0: return ''
    data=raw[marker+len('DATA;'):]
    data=re.sub(r'/\*.*?\*/','',data,flags=re.S)
    data=re.sub(r'--[^\r\n]*','',data)
    return '\n'.join(re.findall(r"'(?:[^']|'')*'",data))


def cae_chain_items(model):
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
        job=get_obj(mdb.jobs,SPEC.get('job_name'))
        if job is not None and nn(getattr(job,'model','')) == nn(SPEC.get('model_name')):
            add(getattr(job,'name',None)); add(getattr(job,'model',None)); add(getattr(job,'description',None))
    except Exception: pass
    return names


def cae_chain_blob(model): return '\n'.join(cae_chain_items(model))


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
        try:
            data=parse_dxf(dxf_path)
        except Exception as e:
            return fail('Cannot parse DXF for chain evidence: '+str(e))
        if ci('CHAIN') not in data['layers']:
            return fail('DXF missing CHAIN layer for chain evidence')
        native_text='\n'.join(t.get('text','') for t in data['texts'] if ci(t.get('layer')) == 'CHAIN')
        if not check_chain_markers(native_text, dxf_markers, 'DXF native TEXT/MTEXT'): return False
    step_markers=evidence.get('step_markers') or []
    if step_markers:
        step_name=SPEC.get('stage_step')
        if not step_name: return fail('STEP chain evidence requested but no stage_step in SPEC')
        step_path=dp(step_name)
        if not nonempty(step_path, 1): return fail('Missing STEP stage for chain evidence: '+step_path)
        header=head(step_path,8192)
        if 'SWSTEP' not in ci(header) or 'SOLIDWORKS 2025' not in ci(header):
            return fail('STEP lacks native SOLIDWORKS 2025 exporter identity')
        if not check_chain_markers(step_quoted_data(step_path), step_markers, 'quoted STEP DATA entities'):
            return False
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
        items=cae_chain_items(mdb.models[mk])
        if not any(all(chain_contains(item,marker) for marker in cae_markers) for item in items):
            return fail('No single native CAE name/description contains all chain markers')
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


def entity_indices(sequence):
    out=set()
    try:
        for item in sequence: out.add(int(item.index))
    except Exception: pass
    return out


def region_face_indices(region):
    try: return entity_indices(region.faces)
    except Exception: return set()


def bbox_dims(vertices):
    try:
        bb=vertices.getBoundingBox(); low=bb['low']; high=bb['high']
        return [float(high[i])-float(low[i]) for i in range(3)]
    except Exception: return None


def find_analysis_part(model):
    matches=[]
    try:
        for key in model.parts.keys():
            part=model.parts[key]
            dims=bbox_dims(part.vertices)
            if dims and dims_close(dims,SPEC['bbox'],SPEC.get('bbox_tol',0.05)) and len(part.cells) == 1:
                matches.append((key,part,dims))
    except Exception as e:
        return None,None,None
    if len(matches) != 1: return None,None,None
    return matches[0]


def part_volume(part):
    try: return float(part.getMassProperties().get('volume'))
    except Exception: return None


def part_surface_area(part):
    total=0.0
    try:
        for face in part.faces:
            try: total += float(face.getSize(printResults=False))
            except TypeError: total += float(face.getSize())
        return total
    except Exception: return None


def find_analysis_instance(model, part_key):
    matches=[]
    try:
        for key in model.rootAssembly.instances.keys():
            inst=model.rootAssembly.instances[key]
            if ci(getattr(inst,'partName','')) == ci(part_key): matches.append((key,inst))
    except Exception: pass
    if len(matches) == 1: return matches[0]
    return None,None


def expected_hole_face_indices(faces, centers):
    all_faces=set()
    for x,y in centers:
        center_faces=set()
        for z in (1.5,3.0,4.5):
            for index in range(32):
                angle=2.0*math.pi*(float(index)+0.37)/32.0
                point=(x+4.0*math.cos(angle),y+4.0*math.sin(angle),z)
                try: found=faces.findAt((point,))
                except Exception: continue
                center_faces.update(entity_indices(found))
        if not center_faces: return set()
        all_faces.update(center_faces)
    return all_faces


def named_region_candidates(model, name, repository_name):
    out=[]
    try:
        repo=getattr(model.rootAssembly,repository_name)
        key=find_key(repo,name)
        if key is not None: out.append(('assembly',repo[key]))
    except Exception: pass
    try:
        for ik in model.rootAssembly.instances.keys():
            repo=getattr(model.rootAssembly.instances[ik],repository_name)
            key=find_key(repo,name)
            if key is not None: out.append(('instance:'+str(ik),repo[key]))
    except Exception: pass
    try:
        for pk in model.parts.keys():
            repo=getattr(model.parts[pk],repository_name)
            key=find_key(repo,name)
            if key is not None: out.append(('part:'+str(pk),repo[key]))
    except Exception: pass
    return out


def region_node_coordinates(region):
    out=[]
    try:
        for node in region.nodes:
            out.append(tuple(float(value) for value in node.coordinates))
    except Exception: pass
    return out


def region_node_labels(region):
    out=set()
    try:
        for node in region.nodes: out.add(int(node.label))
    except Exception: pass
    return out


def region_instance_names(region):
    out=set()
    for attr in ('faces','nodes','elements'):
        try: sequence=getattr(region,attr)
        except Exception: continue
        try:
            for entity in sequence:
                name=ci(getattr(entity,'instanceName',''))
                if name: out.add(name)
        except Exception: pass
    return out


def expected_hole_node_labels(nodes, centers, radius=4.0):
    out=set(); hits=[0 for center in centers]
    try: source=list(nodes)
    except Exception: source=[]
    for node in source:
        try:
            point=tuple(float(value) for value in node.coordinates)
            label=int(node.label)
        except Exception: continue
        if len(point) < 3 or point[2] < -0.1 or point[2] > 6.1: continue
        for index,(x,y) in enumerate(centers):
            distance=math.sqrt((point[0]-x)**2+(point[1]-y)**2)
            if close(distance,radius,0.1):
                out.add(label); hits[index] += 1; break
    if not all(count >= 2 for count in hits): return set()
    return out


def hole_region_matches(region, expected_faces, expected_nodes, expected_instance=None):
    faces=region_face_indices(region)
    nodes=region_node_labels(region)
    if not expected_nodes or nodes != expected_nodes: return False
    names=region_instance_names(region)
    if expected_instance and names and names != set([ci(expected_instance)]): return False
    if faces:
        area=surface_area(region)
        if area is None or not close_rel(area,301.5928947,abs_tol=0.5,rel_tol=0.01): return False
    return True


def require_hole_set(model, name, expected_faces, expected_nodes, expected_instance=None):
    candidates=named_region_candidates(model,name,'sets')
    if not candidates: return None,fail('Missing native set '+name)
    assembly=[item for item in candidates if item[0] == 'assembly']
    tested=assembly if assembly else candidates
    for owner,region in tested:
        if hole_region_matches(region,expected_faces,expected_nodes,expected_instance): return region,True
    return None,fail('%s does not identify exactly the two required hole boundaries'%name)


def require_face_region(model, name, expected, repository_name):
    candidates=named_region_candidates(model,name,repository_name)
    if not candidates: return None,fail('Missing native face region '+name)
    assembly=[item for item in candidates if item[0] == 'assembly']
    tested=assembly if assembly else candidates
    for owner,region in tested:
        got=region_face_indices(region)
        if got == expected: return region,True
    return None,fail('%s membership does not equal the required hole faces'%name)


def mesh_info(part):
    coords=[]
    try:
        for node in part.nodes: coords.append(tuple(node.coordinates))
    except Exception: pass
    try: elems=list(part.elements)
    except Exception: elems=[]
    types=sorted(set(ci(getattr(element,'type','')) for element in elems))
    return coords, elems, types


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


def check_plate_section_assignment(model, part):
    mat_name=SPEC.get('section_material')
    valid_sections=set()
    for key in model.sections.keys():
        if ci(getattr(model.sections[key],'material','')) == ci(mat_name): valid_sections.add(nn(key))
    required=entity_indices(part.cells)
    covered=set()
    try:
        for assignment in part.sectionAssignments:
            if nn(getattr(assignment,'sectionName','')) not in valid_sections: continue
            try:
                covered.update(entity_indices(assignment.region.cells))
            except Exception:
                region_name=object_region_name(assignment)
                for owner,region in named_region_candidates(model,region_name,'sets'):
                    if owner == 'part:'+str(part.name): covered.update(entity_indices(region.cells))
    except Exception as e: return fail('Cannot inspect target plate section coverage: '+str(e))
    if not required or covered != required: return fail('Steel section does not cover every cell of the target plate')
    return ok('Steel section covers the target plate')


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
            job_prefix=ci(SPEC.get('job_name','')).lower()
            if lower.startswith('evalinp') or lower.startswith('__eval') or (job_prefix and lower.startswith(job_prefix+'.')):
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
    job_name=SPEC.get('job_name')
    job=get_obj(mdb.jobs,job_name)
    if job is None: raise RuntimeError('Required native job not found for INP inspection: '+str(job_name))
    old=os.getcwd()
    try:
        os.chdir(tmp)
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
    t=normalize_region_name(token); r=normalize_region_name(region)
    if not t or not r: return False
    return t == r or t.endswith('_'+r) or r.endswith('_'+t)


def object_region_name(obj):
    try: rep=repr(getattr(obj,'region'))
    except Exception: return ''
    for quote in ["'", '"']:
        i=rep.find(quote)
        if i >= 0:
            j=rep.find(quote, i+1)
            if j > i: return rep[i+1:j]
    try: return rep.strip('()').split(',')[0].strip()
    except Exception: return ''


def parse_inp(path):
    data={'boundary':[], 'cload':[], 'pressure':[], 'flux':[], 'film':[], 'couplings':[],
          'field_output_variables':[], 'field_output_variables_by_step':{},
          'constraint_cards':[], 'raw_cards':[]}
    if not path or not os.path.isfile(path): return data
    card=''; field_output_active=False; current_step=''
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
            card=line.lower().split(',')[0].strip()
            data['raw_cards'].append(line)
            if card == '*step':
                current_step=''
                for token in line.split(',')[1:]:
                    if '=' in token:
                        key,value=token.split('=',1)
                        if ci(key) == 'NAME': current_step=nn(value.strip())
            if card == '*output':
                field_output_active='FIELD' in ci(line)
            elif card == '*end step':
                field_output_active=False
            if field_output_active and 'VARIABLE=PRESELECT' in ci(line):
                if card == '*node output':
                    variables=['U','RF','CF']
                elif card == '*element output':
                    variables=['S']
                else:
                    variables=[]
                data['field_output_variables'].extend(variables)
                data['field_output_variables_by_step'].setdefault(current_step,[]).extend(variables)
            if card in ('*equation','*mpc','*rigid body','*tie','*embedded element',
                        '*shell to solid coupling'):
                data['constraint_cards'].append(line)
            if card == '*coupling':
                params={}
                for token in line.split(',')[1:]:
                    if '=' in token:
                        key,value=token.split('=',1); params[ci(key)]=value.strip()
                data['couplings'].append({'name':params.get('CONSTRAINT NAME',''),
                                          'control':params.get('REF NODE',''),
                                          'surface':params.get('SURFACE',''),'mode':'','dofs':[]})
            elif card == '*distributing' and data['couplings']:
                data['couplings'][-1]['mode']='distributing'
            elif card == '*kinematic' and data['couplings']:
                data['couplings'][-1]['mode']='kinematic'
            if card == '*end step': current_step=''
            continue
        parts=[p.strip() for p in line.split(',')]
        if not parts or not parts[0]: continue
        target=parts[0]
        if field_output_active:
            for token in parts:
                variable=ci(token)
                if re.match(r'^[A-Z][A-Z0-9_]*$',variable):
                    data['field_output_variables'].append(variable)
                    data['field_output_variables_by_step'].setdefault(current_step,[]).append(variable)
        if card == '*boundary':
            symbolic=ci(parts[1]) if len(parts)>1 else ''
            if symbolic == 'ENCASTRE':
                d1=1; d2=6; val=0.0
            elif symbolic == 'PINNED':
                d1=1; d2=3; val=0.0
            else:
                d1=parse_int_token(parts[1]) if len(parts)>1 else None
                d2=parse_int_token(parts[2]) if len(parts)>2 else d1
                val=parse_float_token(parts[3]) if len(parts)>3 else 0.0
            data['boundary'].append({'target':target,'dof1':d1,'dof2':d2,'value':val,
                                     'step':current_step})
        elif card == '*cload':
            dof=parse_int_token(parts[1]) if len(parts)>1 else None
            val=parse_float_token(parts[2]) if len(parts)>2 else None
            data['cload'].append({'target':target,'dof':dof,'value':val,'step':current_step})
        elif card in ('*dload','*dsload'):
            vals=[parse_float_token(p) for p in parts[1:]]
            vals=[v for v in vals if v is not None]
            data['pressure'].append({'target':target,'values':vals,'card':card,'parts':parts,
                                     'step':current_step})
        elif card in ('*cflux','*dflux','*dsflux'):
            vals=[parse_float_token(p) for p in parts[1:]]
            vals=[v for v in vals if v is not None]
            data['flux'].append({'target':target,'values':vals,'card':card,'parts':parts,
                                 'step':current_step})
        elif card == '*film':
            vals=[parse_float_token(p) for p in parts[1:]]
            vals=[v for v in vals if v is not None]
            data['film'].append({'target':target,'values':vals,'parts':parts,'step':current_step})
        elif card in ('*distributing','*kinematic') and data['couplings']:
            d1=parse_int_token(parts[0]) if len(parts)>0 else None
            d2=parse_int_token(parts[1]) if len(parts)>1 else d1
            if d1 is not None:
                if d2 is None: d2=d1
                for dof in range(int(d1),int(d2)+1):
                    if dof not in data['couplings'][-1]['dofs']:
                        data['couplings'][-1]['dofs'].append(dof)
    return data


def get_inp_data(model):
    key=SPEC.get('job_name','__default__')
    if key in INP_CACHE: return INP_CACHE[key]
    data={'boundary':[], 'cload':[], 'pressure':[], 'flux':[], 'film':[], 'couplings':[],
          'field_output_variables':[], 'field_output_variables_by_step':{},
          'constraint_cards':[], 'raw_cards':[]}
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


def inp_entries_for(data, kind, region, step_name=None):
    out=[]
    for entry in data.get(kind,[]):
        if step_name is not None and nn(entry.get('step','')) != nn(step_name): continue
        if token_matches_region(entry.get('target',''), region): out.append(entry)
    return out


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
    inactive=['DEACTIVATED','NOT_YET_ACTIVE','NO_LONGER_ACTIVE','INSTANCE_NOT_APPLICABLE',
              'TYPE_NOT_APPLICABLE','SUPPRESSED']
    return not any(token in status for token in inactive)


def extra_active_state_names(model, repository_name, expected_name):
    repository=target_step_state_repository(model,repository_name)
    if repository is None: return None
    out=[]
    try:
        for key in repository.keys():
            if nn(key) == nn(expected_name): continue
            if state_is_active(repository[key]): out.append(str(key))
    except Exception: return None
    return out


def inp_boundary_translations(model, region):
    data=get_inp_data(model)
    entries=inp_entries_for(data,'boundary',region,SPEC['step_name'])
    if not entries: entries=inp_entries_for(data,'boundary',region)
    fixed=set()
    for entry in entries:
        d1=entry.get('dof1'); d2=entry.get('dof2') if entry.get('dof2') is not None else d1
        if d1 is None: continue
        if d2 is None: d2=d1
        value=entry.get('value')
        if value is not None and abs(float(value)) > 1.0e-9: continue
        for dof in range(max(int(d1),1),min(int(d2),3)+1): fixed.add(dof)
    return fixed


def constraint_fixed_translations(model, bc, region_name):
    fixed=set()
    for attr in ['u1','u2','u3','ur1','ur2','ur3']:
        try:
            value=getattr(bc,attr)
            if attr in ('u1','u2','u3') and is_set_value(value):
                try:
                    if abs(float(value)) <= 1.0e-9: fixed.add(int(attr[-1]))
                except Exception:
                    if ci(value) in ('SET','FIXED'): fixed.add(int(attr[-1]))
        except Exception: pass
    fixed.update(inp_boundary_translations(model,region_name))
    return fixed


def state_fixed_translations(state):
    fixed=set(); exposed=False
    for attr in ['u1','u2','u3']:
        try: value=getattr(state,attr); exposed=True
        except Exception: continue
        if not is_set_value(value): continue
        try:
            if abs(float(value)) <= 1.0e-9: fixed.add(int(attr[-1]))
        except Exception:
            if ci(value) in ('SET','FIXED'): fixed.add(int(attr[-1]))
    return exposed,fixed


def check_constraint_bc(model, name, expected_region=None):
    bc=get_obj(model.boundaryConditions, name)
    if bc is None: return fail('Missing BC '+name)
    region=object_region_name(bc)
    if expected_region and not token_matches_region(region,expected_region):
        return fail('BC '+name+' is not bound to '+expected_region)
    fixed=constraint_fixed_translations(model,bc,expected_region or region or name)
    if fixed >= set([1,2,3]): return ok('BC '+name+' fixes translations on '+str(expected_region or region))
    return fail('BC '+name+' does not fix U1, U2, and U3 to zero')


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
            if not check_constraint_bc(model,name,req.get('region')): return False
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


def named_attr_region(obj, attr):
    try: rep=repr(getattr(obj,attr))
    except Exception: return ''
    for quote in ["'",'"']:
        i=rep.find(quote)
        if i >= 0:
            j=rep.find(quote,i+1)
            if j > i: return rep[i+1:j]
    return ''


def preferred_named_region(model, name, repository_name):
    candidates=named_region_candidates(model,name,repository_name)
    for owner,region in candidates:
        if owner == 'assembly': return region
    return candidates[0][1] if candidates else None


def preferred_region_by_token(model, token, repository_name):
    repositories=[]
    try: repositories.append(getattr(model.rootAssembly,repository_name))
    except Exception: pass
    try:
        for key in model.rootAssembly.instances.keys():
            repositories.append(getattr(model.rootAssembly.instances[key],repository_name))
    except Exception: pass
    try:
        for key in model.parts.keys(): repositories.append(getattr(model.parts[key],repository_name))
    except Exception: pass
    for repo in repositories:
        try:
            for key in repo.keys():
                if token_matches_region(key,token): return repo[key]
        except Exception: pass
    return None


def region_entity_counts(region):
    counts={'referencePoints':0,'nodes':0,'faces':0}
    if region is None: return counts
    for attr in counts.keys():
        try: counts[attr]=len(getattr(region,attr))
        except Exception: pass
    return counts


def region_control_ids(region):
    out=set()
    if region is None: return out
    try:
        for point in region.referencePoints:
            out.add(('RP',int(getattr(point,'id'))))
    except Exception: pass
    try:
        for node in region.nodes: out.add(('NODE',int(node.label)))
    except Exception: pass
    return out


def coupling_surface_regions(model, control_name=None, required_dofs=None):
    linked=[]; seen=set()
    required=set(required_dofs or [1,2,3])
    for coupling in get_inp_data(model).get('couplings',[]):
        if control_name and not token_matches_region(coupling.get('control'),control_name): continue
        if not required.issubset(set(coupling.get('dofs',[]))): continue
        surface=preferred_region_by_token(model,coupling.get('surface'),'surfaces')
        token=normalize_region_name(coupling.get('surface',''))
        if surface is not None and token not in seen:
            linked.append(surface); seen.add(token)
    return linked


def combined_hole_surfaces_match(regions, expected_nodes, expected_instance=None):
    if not regions or not expected_nodes: return False
    nodes=set(); faces={}; names=set()
    for region in regions:
        nodes.update(region_node_labels(region))
        names.update(region_instance_names(region))
        try:
            for face in region.faces:
                key=(ci(getattr(face,'instanceName','')),int(face.index))
                faces[key]=face
        except Exception: pass
    if nodes != expected_nodes: return False
    if expected_instance and names and names != set([ci(expected_instance)]): return False
    area=0.0
    try:
        for face in faces.values():
            try: area += float(face.getSize(printResults=False))
            except TypeError: area += float(face.getSize())
    except Exception: return False
    return close_rel(area,301.5928947,abs_tol=0.5,rel_tol=0.01)


def coupling_links_holes(model, control_name, expected_nodes, expected_instance, required_dofs):
    regions=coupling_surface_regions(model,control_name,required_dofs)
    return combined_hole_surfaces_match(regions,expected_nodes,expected_instance)


def surface_area(region):
    area=0.0
    try:
        for face in region.faces: area += float(face.getSize(printResults=False))
    except Exception: return None
    return area


def traction_direction_is_positive_x(load):
    try:
        points=getattr(load,'directionVector')
        try:
            vector=[float(points[index]) for index in range(3)]
        except Exception:
            a=points[0]; b=points[1]
            vector=[float(b[i])-float(a[i]) for i in range(3)]
        length=math.sqrt(vector[0]*vector[0]+vector[1]*vector[1]+vector[2]*vector[2])
        return length > 0.0 and vector[0]/length > 0.99 and abs(vector[1]/length) < 0.02 and abs(vector[2]/length) < 0.02
    except Exception: return False


def check_task01_field_outputs(model):
    by_step=get_inp_data(model).get('field_output_variables_by_step',{})
    variables=set(ci(value) for value in by_step.get(nn(SPEC['step_name']),[]))
    required=set(['U','S','RF','NFORC'])
    if LOAD_AUDIT.get('mode') in ('concentrated_reference_point','concentrated_direct'):
        required.add('CF')
    missing=sorted(required-variables)
    if missing: return fail('CAE active field output request is missing: '+', '.join(missing))
    return ok('CAE active field output request covers '+', '.join(sorted(required)))


def check_task01_extra_constraints(model):
    data=get_inp_data(model)
    extra_cards=data.get('constraint_cards',[])
    if extra_cards:
        return fail('Unexpected active constraint cards in Step-Static: '+', '.join(extra_cards))
    allowed_controls=[]
    if BC_AUDIT.get('mode') == 'coupled':
        allowed_controls.append(BC_AUDIT.get('control_region_name'))
    if LOAD_AUDIT.get('mode') == 'concentrated_reference_point':
        allowed_controls.append(LOAD_AUDIT.get('load_region_name'))
    unexpected=[]
    for coupling in data.get('couplings',[]):
        if not any(token_matches_region(coupling.get('control'),name) for name in allowed_controls):
            unexpected.append(coupling.get('name') or coupling.get('control') or '<unnamed>')
    if unexpected:
        return fail('Unexpected active couplings in Step-Static: '+', '.join(unexpected))
    return ok('No unrelated active constraints or couplings')


def check_task01_bc(model, expected_faces, expected_nodes, expected_instance):
    global BC_AUDIT
    BC_AUDIT={}
    name='BC-FixedHoles'
    bc=get_obj(model.boundaryConditions,name)
    if bc is None: return fail('Missing BC '+name)
    state=target_step_state(model,'boundaryConditionStates',name)
    if not state_is_active(state): return fail('BC-FixedHoles is not active in Step-Static')
    extras=extra_active_state_names(model,'boundaryConditionStates',name)
    if extras is None: return fail('Cannot inspect active boundary conditions in Step-Static')
    if extras: return fail('Unexpected additional active boundary conditions: '+', '.join(extras))
    region_name=object_region_name(bc)
    exposed,state_fixed=state_fixed_translations(state)
    inp_fixed=inp_boundary_translations(model,region_name or name)
    effective_fixed=(state_fixed & inp_fixed) if exposed else inp_fixed
    if effective_fixed < set([1,2,3]):
        return fail('BC-FixedHoles does not fix U1, U2, and U3 to zero')
    region=preferred_region_by_token(model,region_name,'sets')
    if region is not None and hole_region_matches(region,expected_faces,expected_nodes,expected_instance):
        BC_AUDIT={'control_region_name':region_name or name,'hole_region_name':'FIXED_HOLES','mode':'direct'}
        return ok('BC-FixedHoles directly fixes the two left-hole boundaries')
    counts=region_entity_counts(region)
    if ((counts['referencePoints'] or counts['nodes']) and
            coupling_links_holes(model,region_name,expected_nodes,expected_instance,[1,2,3])):
        BC_AUDIT={'control_region_name':region_name or name,'hole_region_name':'FIXED_HOLES','mode':'coupled'}
        return ok('BC-FixedHoles fixes control points coupled to the two left holes')
    return fail('BC-FixedHoles is not connected to exactly the two left holes')


def check_task01_load(model, expected_faces, expected_nodes, expected_instance):
    global LOAD_AUDIT
    LOAD_AUDIT={}
    load=get_obj(model.loads,'Load-RightHoles')
    if load is None: return fail('Missing load Load-RightHoles')
    state=target_step_state(model,'loadStates','Load-RightHoles')
    if not state_is_active(state): return fail('Load-RightHoles is not active in Step-Static')
    extras=extra_active_state_names(model,'loadStates','Load-RightHoles')
    if extras is None: return fail('Cannot inspect active loads in Step-Static')
    if extras: return fail('Unexpected additional active loads: '+', '.join(extras))
    region_name=object_region_name(load)
    class_name=ci(cls(load))
    if 'CONCENTRATEDFORCE' in class_name:
        cf1=numeric_attr(state,'cf1')
        if cf1 is None: cf1=numeric_attr(load,'cf1')
        if cf1 is None:
            entries=[entry for entry in inp_entries_for(
                get_inp_data(model),'cload',region_name,SPEC['step_name']) if entry.get('dof') == 1]
            if len(entries) == 1: cf1=entries[0].get('value')
        if cf1 is None or cf1 <= 0.0: return fail('Load-RightHoles must have positive CF1')
        for attr in ['cf2','cf3','cm1','cm2','cm3']:
            value=numeric_attr(state,attr)
            if value is None: value=numeric_attr(load,attr)
            if value is not None and abs(value) > 1.0e-9: return fail('Load-RightHoles has an unintended force/moment component '+attr)
        region=preferred_named_region(model,region_name,'sets')
        counts=region_entity_counts(region)
        count=counts['referencePoints'] or counts['nodes']
        if count < 1: return fail('Load-RightHoles is not applied to native points/nodes')
        total=cf1*float(count)
        if not close_rel(total,800.0,abs_tol=1.0,rel_tol=0.05):
            return fail('Load-RightHoles total concentrated load is %s N, expected 800 N'%total)
        if counts['referencePoints']:
            if not coupling_links_holes(model,region_name,expected_nodes,expected_instance,[1]):
                return fail('Load reference point is not coupled to exactly the two right-hole faces')
            mode='concentrated_reference_point'
        elif not hole_region_matches(region,expected_faces,expected_nodes,expected_instance):
            return fail('Direct nodal Load-RightHoles is not bound to the two right-hole boundaries')
        else:
            mode='concentrated_direct'
        LOAD_AUDIT={'mode':mode,'load_region_name':region_name,'hole_region_name':'LOAD_HOLES'}
        return ok('Total +800 N load is bound to the two right holes')
    if 'SURFACETRACTION' in class_name:
        surface=preferred_region_by_token(model,region_name,'surfaces')
        if surface is None or not hole_region_matches(
                surface,expected_faces,expected_nodes,expected_instance):
            return fail('Surface traction is not bound to the two right-hole faces')
        magnitude=numeric_attr(state,'magnitude')
        if magnitude is None: magnitude=numeric_attr(load,'magnitude')
        area=surface_area(surface)
        if magnitude is None or area is None or not close_rel(magnitude*area,800.0,abs_tol=1.0,rel_tol=0.05):
            return fail('Integrated surface traction does not total 800 N')
        if not traction_direction_is_positive_x(load): return fail('Surface traction is not tensile in +X')
        LOAD_AUDIT={'mode':'surface_traction','load_region_name':region_name,'hole_region_name':'LOAD_HOLES'}
        return ok('Integrated +X surface traction totals 800 N on the two right holes')
    return fail('Load-RightHoles is neither a defensible concentrated-force coupling nor surface traction')


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


def inp_card_has_value(model, kind, region, req=None, require_nonzero=True):
    data=get_inp_data(model)
    for entry in inp_entries_for(data, kind, region):
        for v in entry.get('values',[]):
            if v is None: continue
            if req is not None and req.get('magnitude') is not None:
                if close_magnitude(v, req.get('magnitude'), req): return True
            elif (not require_nonzero) or abs(v) > 1.0e-12:
                return True
    return False


def check_load_specs(model):
    for req in SPEC.get('load_checks',[]):
        name=req.get('name'); kind=req.get('kind')
        load=get_obj(model.loads, name)
        bc=get_obj(model.boundaryConditions, name)
        if kind == 'pressure':
            if load is None: return fail('Missing pressure load '+name)
            if 'PRESSURE' not in ci(cls(load)): return fail('Load '+name+' is not a pressure object')
            mag=numeric_attr(load,'magnitude')
            if mag is not None and close_magnitude(mag, req.get('magnitude'), req): continue
            region=object_region_name(load) or name
            if not inp_card_has_value(model, 'pressure', region, req=req): return fail('Pressure magnitude mismatch for '+name)
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

def check_cae():
    global CAE_AUDIT,BC_AUDIT,LOAD_AUDIT
    CAE_AUDIT={}; BC_AUDIT={}; LOAD_AUDIT={}
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
    if not check_section_assignment(model): return False
    part_key,part,part_dims=find_analysis_part(model)
    if part is None: return fail('CAE must contain exactly one one-cell 120 x 80 x 6 analysis part')
    volume=part_volume(part); area=part_surface_area(part)
    if (not STEP_AUDIT or volume is None or
            not close(volume,STEP_AUDIT.get('volume'),SPEC['step_volume_tol_mm3'])):
        return fail('CAE plate volume does not match the validated STEP geometry: %s'%volume)
    if area is None or not close(area,STEP_AUDIT.get('surface_area'),2.0):
        return fail('CAE plate surface area does not match the validated STEP geometry: %s'%area)
    log('[PASS] CAE volume and surface area match the validated STEP geometry')
    try: instance_count=len(model.rootAssembly.instances)
    except Exception: instance_count=0
    if instance_count != 1: return fail('CAE assembly must contain exactly one analysis instance')
    instance_key,instance=find_analysis_instance(model,part_key)
    if instance is None: return fail('CAE must contain exactly one instance of the analysis part')
    if not check_plate_section_assignment(model,part): return False
    sk=find_key(model.steps,SPEC['step_name'])
    if sk is None: return fail('Missing step '+SPEC['step_name'])
    step_obj=model.steps[sk]
    if not step_kind(step_obj, SPEC['step_kind']): return fail('Step kind mismatch')
    if SPEC.get('step_num_eigen') is not None:
        try: obs=int(getattr(step_obj,'numEigen'))
        except Exception as e: return fail('Step numEigen unreadable: '+str(e))
        if obs != int(SPEC['step_num_eigen']): return fail('Step numEigen mismatch got %s expected %s'%(obs,SPEC['step_num_eigen']))
    fixed_centers=[(15.0,15.0),(15.0,65.0)]
    load_centers=[(105.0,15.0),(105.0,65.0)]
    fixed_expected=expected_hole_face_indices(instance.faces,fixed_centers)
    load_expected=expected_hole_face_indices(instance.faces,load_centers)
    fixed_expected_nodes=expected_hole_node_labels(instance.nodes,fixed_centers)
    load_expected_nodes=expected_hole_node_labels(instance.nodes,load_centers)
    if (not fixed_expected or not load_expected or fixed_expected & load_expected or
            not fixed_expected_nodes or not load_expected_nodes or fixed_expected_nodes & load_expected_nodes):
        return fail('CAE imported geometry does not expose the required distinct left/right hole faces')
    fixed_region,fixed_ok=require_hole_set(
        model,'FIXED_HOLES',fixed_expected,fixed_expected_nodes,instance_key)
    if not fixed_ok: return False
    load_region,load_ok=require_hole_set(
        model,'LOAD_HOLES',load_expected,load_expected_nodes,instance_key)
    if not load_ok: return False
    for name,region in [('FIXED_HOLES',fixed_region),('LOAD_HOLES',load_region)]:
        if region_face_indices(region):
            area=surface_area(region)
            if area is None or not close_rel(area,301.5928947,abs_tol=0.5,rel_tol=0.01):
                return fail('%s cylindrical area mismatch: %s'%(name,area))
    pre_coords,pre_elements,pre_types=mesh_info(part)
    if not pre_types or not set(pre_types).issubset(set(['C3D4','C3D8R'])):
        return fail('CAE mesh must use only first-order C3D4/C3D8R; got %s'%pre_types)
    if not check_task01_bc(model,fixed_expected,fixed_expected_nodes,instance_key): return False
    if not check_task01_load(model,load_expected,load_expected_nodes,instance_key): return False
    if not check_task01_field_outputs(model): return False
    if not check_task01_extra_constraints(model): return False
    job=get_obj(mdb.jobs,SPEC['job_name'])
    if job is None: return fail('Missing job '+SPEC['job_name'])
    if nn(getattr(job,'model','')) != nn(SPEC['model_name']): return fail('Job-PlateStatic is not bound to Model-PlateStatic')
    coords, elements, element_types = mesh_info(part)
    if len(elements) < int(SPEC.get('min_elements',1)): return fail('CAE plate has no mesh elements')
    if not element_types or not set(element_types).issubset(set(['C3D4','C3D8R'])):
        return fail('CAE mesh must use only first-order C3D4/C3D8R; got %s'%element_types)
    try: node_count=len(part.nodes)
    except Exception: node_count=len(coords)
    if coords:
        spans=[]
        for ax in range(3):
            vals=[float(c[ax]) for c in coords if len(c)>ax]
            if vals: spans.append(max(vals)-min(vals))
        if len(spans) == 3 and not dims_close(spans, SPEC['bbox'], SPEC.get('bbox_tol',8.0)): return fail('CAE mesh bbox mismatch got %s expected %s'%(spans,SPEC['bbox']))
    node_signature={}
    try:
        for node in part.nodes: node_signature[int(node.label)]=tuple(float(x) for x in node.coordinates)
    except Exception as e: return fail('Cannot build CAE node signature: '+str(e))
    element_signature={}
    try:
        for element in part.elements:
            labels=[]
            for value in element.connectivity:
                index=int(value)
                try: labels.append(int(part.nodes[index].label))
                except Exception: labels.append(index)
            element_signature[int(element.label)]=(ci(element.type),tuple(labels))
    except Exception as e: return fail('Cannot build CAE element signature: '+str(e))
    fixed_groups=[expected_hole_node_labels(instance.nodes,[center]) for center in fixed_centers]
    load_groups=[expected_hole_node_labels(instance.nodes,[center]) for center in load_centers]
    CAE_AUDIT={'instance_name':str(instance_key),'node_count':node_count,'element_count':len(elements),
               'element_types':element_types,'node_signature':node_signature,'element_signature':element_signature,
               'fixed_node_labels':set(fixed_expected_nodes),'load_node_labels':set(load_expected_nodes),
               'fixed_node_groups':fixed_groups,'load_node_groups':load_groups}
    return ok('CAE checks passed')


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
                        observed=math.sqrt(sum(float(item)*float(item) for item in data))
                    else: observed=abs(float(data))
                maximum=max(maximum,abs(observed)); observed_any=True
            except Exception: continue
    except Exception: return None
    return maximum if observed_any else None


def field_component_sums(frame, region, vector_name, component_names):
    key=find_key(frame.fieldOutputs,vector_name)
    if key is not None:
        subset=field_subset(frame.fieldOutputs[key],region)
        if subset is None: return None
        totals=[0.0,0.0,0.0]; observed=False
        try:
            for value in subset.values:
                data=getattr(value,'data',())
                for index in range(min(3,len(data))): totals[index] += float(data[index])
                observed=True
        except Exception: return None
        return totals if observed else None
    totals=[]
    for component_name in component_names:
        component_key=find_key(frame.fieldOutputs,component_name)
        if component_key is None: return None
        subset=field_subset(frame.fieldOutputs[component_key],region)
        if subset is None: return None
        total=0.0; observed=False
        try:
            for value in subset.values:
                total += float(value.data); observed=True
        except Exception: return None
        if not observed: return None
        totals.append(total)
    return totals


def odb_region_node_keys(region, default_instance=None):
    keys=set()
    def visit(value):
        try:
            label=int(value.label)
            instance_name=ci(getattr(value,'instanceName','') or default_instance or '')
            keys.add((instance_name,label)); return
        except Exception: pass
        try:
            for item in value: visit(item)
        except Exception: pass
    try: visit(region.nodes)
    except Exception: pass
    return keys


def odb_set_matches_cae_nodes(region, instance_name, expected_labels):
    expected=set((ci(instance_name),int(label)) for label in expected_labels)
    observed=odb_region_node_keys(region,instance_name)
    return bool(expected) and observed == expected


def field_x_sums_by_node_groups(frame, region, vector_name, component_name, node_groups):
    key=find_key(frame.fieldOutputs,vector_name)
    vector=True
    if key is None:
        key=find_key(frame.fieldOutputs,component_name); vector=False
    if key is None: return None
    subset=field_subset(frame.fieldOutputs[key],region)
    if subset is None: return None
    groups=[set(int(label) for label in group) for group in node_groups]
    totals=[0.0 for group in groups]; observed=[False for group in groups]
    try:
        for value in subset.values:
            label=int(value.nodeLabel)
            data=value.data
            x_value=float(data[0]) if vector else float(data)
            for index,group in enumerate(groups):
                if label in group:
                    totals[index] += x_value; observed[index]=True; break
    except Exception: return None
    return totals if all(observed) else None


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


def odb_instance_uses_material(odb, instance, material_name):
    expected=set(int(element.label) for element in instance.elements); covered=set()
    if not expected: return False
    try: assignments=instance.sectionAssignments
    except Exception: return False
    for assignment in assignments:
        try:
            labels=set(int(element.label) for element in assignment.region.elements)
            section_key=find_key(odb.sections,assignment.sectionName)
            if section_key is None: return False
            if nn(getattr(odb.sections[section_key],'material','')) != nn(material_name): return False
            covered.update(labels)
        except Exception: return False
    return covered == expected


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
        mesh_instances=[]
        unexpected_instances=[]
        try:
            for candidate_key in odb.rootAssembly.instances.keys():
                candidate=odb.rootAssembly.instances[candidate_key]
                if (nn(candidate_key) not in (nn('ASSEMBLY'),nn(instance_name)) and
                        len(candidate.elements) > 0):
                    unexpected_instances.append(str(candidate_key))
                if (len(candidate.nodes) == CAE_AUDIT.get('node_count') and
                        len(candidate.elements) == CAE_AUDIT.get('element_count')):
                    mesh_instances.append(str(candidate_key))
        except Exception: mesh_instances=[]
        if unexpected_instances:
            return fail('ODB contains unexpected additional meshed instances: '+', '.join(unexpected_instances))
        if len(mesh_instances) != 1 or nn(mesh_instances[0]) != nn(instance_name):
            return fail('ODB must contain exactly one meshed analysis instance matching CAE: %s vs %s'%
                        (mesh_instances,instance_name))
        ik=find_key(odb.rootAssembly.instances,instance_name)
        if ik is None: return fail('ODB missing CAE analysis instance '+str(instance_name))
        odb_instance=odb.rootAssembly.instances[ik]
        for f in SPEC.get('nonzero_odb_fields',[]):
            key=find_key(last_frame.fieldOutputs, f)
            if key is None: return fail('Required nonzero ODB field missing: '+str(f))
            subset=field_subset(last_frame.fieldOutputs[key],odb_instance)
            if subset is None or not field_nonzero(subset):
                return fail('ODB field is zero on the target plate instance: '+str(f))
        material_key=find_key(getattr(odb,'materials',{}),SPEC['material']['name'])
        if material_key is None: return fail('ODB is missing material '+SPEC['material']['name'])
        try:
            elastic=odb.materials[material_key].elastic.table[0]
            odb_e=float(elastic[0]); odb_nu=float(elastic[1])
        except Exception as e: return fail('Cannot inspect ODB elastic material: '+str(e))
        if not close_rel(odb_e,SPEC['material']['E'],abs_tol=1.0,rel_tol=0.01) or not close(odb_nu,SPEC['material']['nu'],0.02):
            return fail('ODB Steel elastic properties do not match CAE requirements')
        u_key=find_key(last_frame.fieldOutputs,'U'); s_key=find_key(last_frame.fieldOutputs,'S')
        max_u=field_max_value(field_subset(last_frame.fieldOutputs[u_key],odb_instance),'magnitude')
        max_s=field_max_value(field_subset(last_frame.fieldOutputs[s_key],odb_instance),'mises')
        if max_u is None or max_u < 1.0e-5 or max_u > 0.05:
            return fail('ODB target-instance displacement is not physically consistent with the specified plate/load: '+str(max_u))
        if max_s is None or max_s < 0.01 or max_s > 100.0:
            return fail('ODB target-instance stress is not physically consistent with the specified plate/load: '+str(max_s))
        if not odb_instance_uses_material(odb,odb_instance,SPEC['material']['name']):
            return fail('ODB target plate elements are not fully assigned to Steel sections')
        rf_key=find_key(last_frame.fieldOutputs,'RF')
        rf1=0.0
        try:
            for value in last_frame.fieldOutputs[rf_key].values: rf1 += float(value.data[0])
        except Exception as e: return fail('Cannot sum ODB RF1 reactions: '+str(e))
        if rf1 >= 0.0 or not close_rel(abs(rf1),800.0,abs_tol=1.0,rel_tol=0.05):
            return fail('ODB RF1 equilibrium mismatch got %s N expected approximately -800 N'%rf1)
        if not BC_AUDIT: return fail('CAE fixed-region audit unavailable before ODB check')
        fixed_hole_set=odb_node_set(odb,odb_instance,BC_AUDIT.get('hole_region_name'))
        if fixed_hole_set is None: return fail('ODB is missing the canonical fixed-hole node set')
        if not odb_set_matches_cae_nodes(
                fixed_hole_set,instance_name,CAE_AUDIT.get('fixed_node_labels',set())):
            return fail('ODB fixed-hole instance/node membership does not match the validated CAE')
        fixed_control_set=odb_node_set(
            odb,odb_instance,BC_AUDIT.get('control_region_name'))
        if fixed_control_set is None: return fail('ODB is missing the active fixed-control node set')
        fixed_rf=field_subset(last_frame.fieldOutputs[rf_key],fixed_control_set)
        fixed_rf1=0.0
        try:
            for value in fixed_rf.values: fixed_rf1 += float(value.data[0])
        except Exception as e: return fail('Cannot sum ODB RF1 on the fixed region: '+str(e))
        if fixed_rf1 >= 0.0 or not close_rel(abs(fixed_rf1),800.0,abs_tol=1.0,rel_tol=0.05):
            return fail('ODB fixed-region RF1 mismatch got %s N expected approximately -800 N'%fixed_rf1)
        if BC_AUDIT.get('mode') == 'direct':
            fixed_group_rf=field_x_sums_by_node_groups(
                last_frame,fixed_hole_set,'RF','RF1',CAE_AUDIT.get('fixed_node_groups',[]))
            if (fixed_group_rf is None or len(fixed_group_rf) != 2 or
                    any(value >= 0.0 or abs(value) < 40.0 for value in fixed_group_rf)):
                return fail('ODB RF1 does not show both left holes carrying the reaction: %s'%fixed_group_rf)
        else:
            fixed_group_nforc=field_x_sums_by_node_groups(
                last_frame,fixed_hole_set,'NFORC','NFORC1',CAE_AUDIT.get('fixed_node_groups',[]))
            if (fixed_group_nforc is None or len(fixed_group_nforc) != 2 or
                    any(value <= 0.0 or abs(value) < 40.0 for value in fixed_group_nforc)):
                return fail('ODB NFORC1 does not show both coupled left holes carrying the reaction: %s'%fixed_group_nforc)
        if not LOAD_AUDIT: return fail('CAE load-region audit unavailable before ODB check')
        load_hole_set=odb_node_set(odb,odb_instance,LOAD_AUDIT.get('hole_region_name'))
        if load_hole_set is None: return fail('ODB is missing the active right-hole load node set')
        if not odb_set_matches_cae_nodes(
                load_hole_set,instance_name,CAE_AUDIT.get('load_node_labels',set())):
            return fail('ODB right-hole load-set instance/node membership does not match the validated CAE')
        hole_nforc=field_component_sums(
            last_frame,load_hole_set,'NFORC',('NFORC1','NFORC2','NFORC3'))
        if hole_nforc is None:
            return fail('ODB is missing readable NFORC output on the active right-hole load set')
        if (hole_nforc[0] >= 0.0 or
                not close_rel(abs(hole_nforc[0]),800.0,abs_tol=1.0,rel_tol=0.05) or
                abs(hole_nforc[1]) > 1.0 or abs(hole_nforc[2]) > 1.0):
            return fail('ODB right-hole NFORC resultant mismatch got %s N expected approximately [-800,0,0] N'%hole_nforc)
        load_group_nforc=field_x_sums_by_node_groups(
            last_frame,load_hole_set,'NFORC','NFORC1',CAE_AUDIT.get('load_node_groups',[]))
        if (load_group_nforc is None or len(load_group_nforc) != 2 or
                any(value >= 0.0 or abs(value) < 40.0 for value in load_group_nforc)):
            return fail('ODB NFORC1 does not show both right holes carrying the tensile load: %s'%load_group_nforc)
        if LOAD_AUDIT.get('mode') in ('concentrated_reference_point','concentrated_direct'):
            load_point_set=odb_node_set(odb,odb_instance,LOAD_AUDIT.get('load_region_name'))
            if load_point_set is None: return fail('ODB is missing the active concentrated-force node set')
            applied_cf=field_component_sums(last_frame,load_point_set,'CF',('CF1','CF2','CF3'))
            if applied_cf is None:
                return fail('ODB is missing readable CF output on the active concentrated-force set')
            if (applied_cf[0] <= 0.0 or
                    not close_rel(applied_cf[0],800.0,abs_tol=1.0,rel_tol=0.05) or
                    abs(applied_cf[1]) > 1.0 or abs(applied_cf[2]) > 1.0):
                return fail('ODB applied CF resultant mismatch got %s N expected approximately [800,0,0] N'%applied_cf)
        if len(odb_instance.nodes) != CAE_AUDIT.get('node_count') or len(odb_instance.elements) != CAE_AUDIT.get('element_count'):
            return fail('ODB mesh counts do not match CAE')
        odb_types=sorted(set(ci(element.type) for element in odb_instance.elements))
        if odb_types != CAE_AUDIT.get('element_types'):
            return fail('ODB element types do not match CAE: %s vs %s'%(odb_types,CAE_AUDIT.get('element_types')))
        cae_nodes=CAE_AUDIT.get('node_signature',{})
        for node in odb_instance.nodes:
            expected=cae_nodes.get(int(node.label))
            if expected is None or len(expected) != len(node.coordinates): return fail('ODB node labels do not match CAE')
            if any(abs(float(node.coordinates[i])-float(expected[i])) > 1.0e-5 for i in range(len(expected))):
                return fail('ODB node coordinates do not match CAE at label %s'%node.label)
        cae_elements=CAE_AUDIT.get('element_signature',{})
        for element in odb_instance.elements:
            observed=(ci(element.type),tuple(int(value) for value in element.connectivity))
            if cae_elements.get(int(element.label)) != observed:
                return fail('ODB element connectivity/type does not match CAE at label %s'%element.label)
        any_nonzero=SPEC.get('nonzero_odb_any_fields',[])
        if any_nonzero:
            matched=False
            for f in any_nonzero:
                key=find_key(last_frame.fieldOutputs, f)
                if key is not None and field_nonzero(last_frame.fieldOutputs[key]): matched=True
            if not matched: return fail('No required heat-flow ODB field is nonzero: '+str(any_nonzero))
        if SPEC.get('nonzero_odb_fields') or SPEC.get('nonzero_odb_any_fields'):
            return ok('ODB completed, fields are nonzero, load/reaction regions are balanced, and mesh matches CAE')
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
