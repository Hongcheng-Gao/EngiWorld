# -*- coding: utf-8 -*-
from __future__ import print_function
import os, sys, traceback, math, json, subprocess
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
 'bbox': [160, 40, 6],
 'bbox_tol': 8.0,
 'bc_checks': [{'kind': 'constraint', 'name': 'BC-LeftEye'}],
 'bc_names': ['BC-LeftEye'],
 'cad_text': 'Slotted Link Tension Analysis',
 'cae_text': 'Slotted Link Tension Analysis',
 'chain': 'two',
 'chain_evidence': {'cae_markers': ['EW_SW_ABQ_07', 'IMPORTED_FROM_stage1_geometry.step'],
                    'step_markers': ['EW_SW_ABQ_07', 'SOLIDWORKS_TO_ABAQUS']},
 'chain_token': 'EW_SW_ABQ_07',
 'dxf_checks': None,
 'expected_field_any': ['U', 'S'],
 'job_name': 'Job-SlottedLinkTension',
 'load_checks': [{'kind': 'force_or_displacement',
                  'magnitude': 1200.0,
                  'name': 'Load-RightTension',
                  'rel_tol': 0.35,
                  'sign': 'positive'}],
 'load_names': ['Load-RightTension'],
 'material': {'E': 210000, 'name': 'Steel', 'nu': 0.3},
 'min_elements': 90,
 'min_frames': 2,
 'model_name': 'Model-SlottedLinkTension',
 'nonzero_odb_fields': ['U', 'S'],
 'required_files': ['stage1_geometry.step',
                    'Job-SlottedLinkTension.cae',
                    'Job-SlottedLinkTension.odb'],
 'required_odb_fields': ['U', 'S'],
 'required_sets': ['LEFT_EYE', 'RIGHT_EYE', 'SLOT_EDGE'],
 'required_surfaces': [],
 'section_material': 'Steel',
 'stage_step': 'stage1_geometry.step',
 'step_kind': 'STATIC',
 'step_name': 'Step-Tension',
 'task_no': 7,
 'title': 'Slotted Link Tension Analysis'}
DETAILS=[]
FORBIDDEN=set(['.py','.pyw','.ipynb','.bat','.cmd','.ps1','.psm1','.vbs','.js','.mjs','.scr','.macro','.bas','.vba','.ahk','.sh'])
DELIVERABLE_EXTS=set(['.step','.stp','.dxf','.cae','.odb'])


def log(x): DETAILS.append(str(x))
def fail(x): log('[FAIL] '+str(x)); return False
def ok(x): log('[PASS] '+str(x)); return True
def warn(x): log('[WARN] '+str(x))
def ci(x): return str(x or '').strip().upper()
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


def write(path, text):
    try:
        f=open(path,'w'); f.write(text); f.close()
    except Exception: pass


def finish(v):
    text='True\n' if v else 'False\n'
    write(dp('eval_detail.txt'), '\n'.join(DETAILS)+'\n')
    write(dp('eval_result.txt'), text)
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


def parse_dxf(path):
    raw=[x.rstrip('\r') for x in head(path).splitlines()]
    pairs=[]; i=0
    while i+1 < len(raw): pairs.append((raw[i].strip(), raw[i+1].strip())); i += 2
    ents=[]; cur=None
    for code,val in pairs:
        if code == '0':
            if cur: ents.append(cur)
            cur={'type':val.upper(),'raw':[]}
        if cur: cur['raw'].append((code,val))
    if cur: ents.append(cur)
    layers=set(); pts=[]; circles=[]; lines=[]
    for e in ents:
        layer=''; xs=[]; ys=[]; rad=None
        for code,val in e['raw']:
            if code == '8': layer=val; layers.add(ci(val))
            elif code in ('10','11'):
                try: xs.append(float(val))
                except Exception: pass
            elif code in ('20','21'):
                try: ys.append(float(val))
                except Exception: pass
            elif code == '40':
                try: rad=float(val)
                except Exception: pass
        if e['type'] not in ('LINE','LWPOLYLINE','POLYLINE','CIRCLE','ARC'):
            continue
        local_pts=[]
        for j in range(min(len(xs),len(ys))):
            p=(xs[j],ys[j]); pts.append(p); local_pts.append(p)
        if e['type'] == 'CIRCLE' and xs and ys and rad is not None:
            circles.append({'x':xs[0],'y':ys[0],'r':rad,'layer':layer})
            pts += [(xs[0]-rad,ys[0]),(xs[0]+rad,ys[0]),(xs[0],ys[0]-rad),(xs[0],ys[0]+rad)]
        if e['type'] in ('LINE','LWPOLYLINE','POLYLINE') and len(local_pts) >= 2:
            lines.append({'layer':layer,'pts':local_pts,'type':e['type']})
    return layers, pts, circles, lines


def check_dxf():
    ds=SPEC.get('dxf_checks')
    if not ds: return ok('No DXF stage')
    path=dp(SPEC['stage_dxf'])
    if not nonempty(path,200): return fail('Missing DXF stage: '+path)
    layers, pts, circles, lines = parse_dxf(path)
    for layer in ds.get('layers',[]):
        if ci(layer) not in layers: return fail('Missing DXF layer '+layer)
    if ds.get('bbox'):
        if len(pts) < 2: return fail('Not enough DXF geometry points for bbox check')
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        got=[max(xs)-min(xs), max(ys)-min(ys)]; exp=ds['bbox']; tol=ds.get('tol',1.0)
        if not (close(got[0],exp[0],tol) and close(got[1],exp[1],tol)): return fail('DXF bbox mismatch got %s expected %s'%(got,exp))
    if ds.get('min_circles') is not None and len(circles) < int(ds['min_circles']): return fail('Too few DXF circles')
    for req in ds.get('circles',[]):
        found=False
        for c in circles:
            if close(c['x'],req['x'],ds.get('tol',1.0)) and close(c['y'],req['y'],ds.get('tol',1.0)) and close(c['r'],req['r'],ds.get('tol',1.0)): found=True
        if not found: return fail('Missing required DXF circle near (%s,%s)'%(req['x'],req['y']))
    for req in ds.get('circle_radii',[]):
        cnt=0
        for c in circles:
            if close(c['r'], req['r'], ds.get('tol',1.0)): cnt += 1
        if cnt < int(req.get('count',1)): return fail('Too few DXF circles with radius %s: got %s'%(req['r'],cnt))
    for layer, min_count in ds.get('layer_line_min',{}).items():
        cnt=len([ln for ln in lines if ci(ln.get('layer')) == ci(layer)])
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
        bb=part.getBoundingBox()
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


def external_cadquery_step_bbox(path):
    code = r'''
import json, sys, traceback
try:
    import cadquery as cq
    wp = cq.importers.importStep(sys.argv[1])
    solids = wp.solids().vals()
    if len(solids) != 1:
        out = {"ok": False, "error": "STEP must contain exactly one solid", "solid_count": len(solids)}
    else:
        box = solids[0].BoundingBox()
        out = {"ok": True, "bbox": [box.xlen, box.ylen, box.zlen]}
except Exception as exc:
    out = {"ok": False, "error": repr(exc), "traceback": traceback.format_exc()}
sys.stdout.write("__CQ_BBOX__" + json.dumps(out))
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
            marker = raw.rfind('__CQ_BBOX__')
            if marker < 0:
                errors.append(exe + ' produced no bbox marker: ' + raw[-300:])
                continue
            return json.loads(raw[marker + len('__CQ_BBOX__'):].strip())
        except Exception as exc:
            errors.append(exe + ': ' + str(exc))
    return {"ok": False, "error": '; '.join(errors)}


def check_step():
    path=dp(SPEC['stage_step'])
    if not nonempty(path, 1): return fail('Missing STEP stage: '+path)
    h=head(path,4096).upper()
    if 'ISO-10303' not in h and 'STEP' not in h: return fail('STEP header not recognized')
    got=None
    try:
        import cadquery as cq
        wp=cq.importers.importStep(path); solids=wp.solids().vals()
        if len(solids) != 1: return fail('STEP must contain exactly one solid')
        box=solids[0].BoundingBox(); got=[box.xlen,box.ylen,box.zlen]
        log('[PASS] STEP cadquery import succeeded')
    except Exception as e:
        warn('Abaqus Python cadquery STEP check unavailable; trying external Python CadQuery: '+str(e))
        ext=external_cadquery_step_bbox(path)
        if ext.get('ok'):
            got=ext.get('bbox')
            log('[PASS] STEP external cadquery import succeeded')
        elif ext.get('solid_count') is not None:
            return fail('STEP must contain exactly one solid')
        else:
            warn('external cadquery STEP check failed; trying Abaqus STEP import: '+str(ext.get('error','unknown')))
            got=abaqus_step_bbox(path)
    if got is None: return fail('STEP geometry could not be validated')
    if not dims_close(got, SPEC['bbox'], SPEC.get('bbox_tol',8.0)): return fail('STEP bbox mismatch got %s expected %s'%(got,SPEC['bbox']))
    return ok('STEP geometry checks passed')



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
        for key,job in mdb.jobs.items():
            add(key); add(getattr(job,'name',None)); add(getattr(job,'model',None)); add(getattr(job,'description',None))
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
        try:
            layers, pts, circles, lines = parse_dxf(dxf_path)
        except Exception as e:
            return fail('Cannot parse DXF for chain evidence: '+str(e))
        if ci('CHAIN') not in layers:
            return fail('DXF missing CHAIN layer for chain evidence')
        if not check_chain_markers(head(dxf_path), dxf_markers, 'DXF'):
            return False
    step_markers=evidence.get('step_markers') or []
    if step_markers:
        step_name=SPEC.get('stage_step')
        if not step_name: return fail('STEP chain evidence requested but no stage_step in SPEC')
        step_path=dp(step_name)
        if not nonempty(step_path, 1): return fail('Missing STEP stage for chain evidence: '+step_path)
        if not check_chain_markers(head(step_path), step_markers, 'STEP'):
            return False
    cae_markers=evidence.get('cae_markers') or []
    if cae_markers:
        if openMdb is None: return fail('Run evaluator with Abaqus cae noGUI for CAE chain evidence')
        cae_path=dp(SPEC['job_name']+'.cae')
        if not nonempty(cae_path,1024): return fail('Missing CAE for chain evidence: '+cae_path)
        try: openMdb(pathName=cae_path)
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
        if nk == t or nk.endswith('_'+t) or nk.endswith('.'+t): return k
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


def mesh_info(model):
    coords=[]; elems=0
    try:
        for pk in model.parts.keys():
            p=model.parts[pk]
            try: elems += len(p.elements)
            except Exception: pass
            try:
                for n in p.nodes: coords.append(tuple(n.coordinates))
            except Exception: pass
    except Exception: pass
    try:
        for ik in model.rootAssembly.instances.keys():
            inst=model.rootAssembly.instances[ik]
            try: elems += len(inst.elements)
            except Exception: pass
            try:
                for n in inst.nodes: coords.append(tuple(n.coordinates))
            except Exception: pass
    except Exception: pass
    return coords, elems


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
    except Exception: pass


def model_job_name(model):
    try:
        return str(model.name)
    except Exception:
        return SPEC['model_name']


def write_eval_inp(model):
    if mdb is None: return None
    tmp=inp_tmp_dir()
    if not os.path.isdir(tmp): os.makedirs(tmp)
    cleanup_eval_inp()
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
    t=normalize_region_name(token); r=normalize_region_name(region)
    if not t or not r: return False
    return t == r or t.endswith('_'+r) or r.endswith('_'+t) or r in t


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
    data={'boundary':[], 'cload':[], 'pressure':[], 'flux':[], 'film':[], 'raw_cards':[]}
    if not path or not os.path.isfile(path): return data
    card=''
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
            continue
        parts=[p.strip() for p in line.split(',')]
        if not parts or not parts[0]: continue
        target=parts[0]
        if card == '*boundary':
            d1=parse_int_token(parts[1]) if len(parts)>1 else None
            d2=parse_int_token(parts[2]) if len(parts)>2 else d1
            val=parse_float_token(parts[3]) if len(parts)>3 else 0.0
            data['boundary'].append({'target':target,'dof1':d1,'dof2':d2,'value':val})
        elif card == '*cload':
            dof=parse_int_token(parts[1]) if len(parts)>1 else None
            val=parse_float_token(parts[2]) if len(parts)>2 else None
            data['cload'].append({'target':target,'dof':dof,'value':val})
        elif card in ('*dload','*dsload'):
            vals=[parse_float_token(p) for p in parts[1:]]
            vals=[v for v in vals if v is not None]
            data['pressure'].append({'target':target,'values':vals,'card':card,'parts':parts})
        elif card in ('*cflux','*dflux','*dsflux'):
            vals=[parse_float_token(p) for p in parts[1:]]
            vals=[v for v in vals if v is not None]
            data['flux'].append({'target':target,'values':vals,'card':card,'parts':parts})
        elif card == '*film':
            vals=[parse_float_token(p) for p in parts[1:]]
            vals=[v for v in vals if v is not None]
            data['film'].append({'target':target,'values':vals,'parts':parts})
    return data


def get_inp_data(model):
    key=SPEC.get('job_name','__default__')
    if key in INP_CACHE: return INP_CACHE[key]
    data={'boundary':[], 'cload':[], 'pressure':[], 'flux':[], 'film':[], 'raw_cards':[]}
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


def inp_entries_for(data, kind, region):
    out=[]
    for entry in data.get(kind,[]):
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


def inp_boundary_has_constraint(model, region):
    data=get_inp_data(model)
    for entry in inp_entries_for(data, 'boundary', region):
        d1=entry.get('dof1'); d2=entry.get('dof2') if entry.get('dof2') is not None else d1
        if d1 is None: continue
        if d2 is None: d2=d1
        if max(int(d1),1) <= min(int(d2),6): return True
    return False


def check_constraint_bc(model, name):
    bc=get_obj(model.boundaryConditions, name)
    if bc is None: return fail('Missing BC '+name)
    vals=numeric_values(bc)
    if vals: return ok('BC '+name+' has constrained/displacement DOFs')
    for attr in ['u1','u2','u3','ur1','ur2','ur3']:
        try:
            if is_set_value(getattr(bc,attr)): return ok('BC '+name+' has constrained DOFs')
        except Exception: pass
    region=object_region_name(bc) or name
    if inp_boundary_has_constraint(model, region): return ok('BC '+name+' has constrained DOFs in INP')
    return fail('BC '+name+' does not constrain any displacement DOF')


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
            if not check_constraint_bc(model,name): return False
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
    if openMdb is None: return fail('Run evaluator with Abaqus cae noGUI')
    path=dp(SPEC['job_name']+'.cae')
    if not nonempty(path,1024): return fail('Missing CAE '+path)
    try: openMdb(pathName=path)
    except Exception as e: return fail('Cannot open CAE: '+str(e))
    mk=find_key(mdb.models,SPEC['model_name'])
    if mk is None: return fail('Missing model '+SPEC['model_name'])
    model=mdb.models[mk]
    if not check_material(model): return False
    if not check_section_assignment(model): return False
    sk=find_key(model.steps,SPEC['step_name'])
    if sk is None: return fail('Missing step '+SPEC['step_name'])
    step_obj=model.steps[sk]
    if not step_kind(step_obj, SPEC['step_kind']): return fail('Step kind mismatch')
    if SPEC.get('step_num_eigen') is not None:
        try: obs=int(getattr(step_obj,'numEigen'))
        except Exception as e: return fail('Step numEigen unreadable: '+str(e))
        if obs != int(SPEC['step_num_eigen']): return fail('Step numEigen mismatch got %s expected %s'%(obs,SPEC['step_num_eigen']))
    set_names=collect_sets(model)
    surf_names=collect_surfaces(model)
    for name in SPEC.get('required_sets',[]):
        if nn(name) not in set_names: return fail('Missing set '+name)
    for name in SPEC.get('required_surfaces',[]):
        if nn(name) not in surf_names: return fail('Missing surface '+name)
    if not check_bc_specs(model): return False
    if not check_load_specs(model): return False
    coords, elems = mesh_info(model)
    if elems < int(SPEC.get('min_elements',1)): return fail('Too few mesh elements')
    if coords:
        spans=[]
        for ax in range(3):
            vals=[float(c[ax]) for c in coords if len(c)>ax]
            if vals: spans.append(max(vals)-min(vals))
        if len(spans) == 3 and not dims_close(spans, SPEC['bbox'], SPEC.get('bbox_tol',8.0)): return fail('CAE mesh bbox mismatch got %s expected %s'%(spans,SPEC['bbox']))
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


def check_odb():
    if openOdb is None: return fail('Run evaluator with Abaqus cae noGUI')
    path=dp(SPEC['job_name']+'.odb')
    if not nonempty(path,1024): return fail('Missing ODB '+path)
    odb=None
    try:
        odb=openOdb(path=path, readOnly=True)
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
        for f in SPEC.get('nonzero_odb_fields',[]):
            key=find_key(last_frame.fieldOutputs, f)
            if key is None: return fail('Required nonzero ODB field missing: '+str(f))
            if not field_nonzero(last_frame.fieldOutputs[key]): return fail('ODB field appears to be zero: '+str(f))
        any_nonzero=SPEC.get('nonzero_odb_any_fields',[])
        if any_nonzero:
            matched=False
            for f in any_nonzero:
                key=find_key(last_frame.fieldOutputs, f)
                if key is not None and field_nonzero(last_frame.fieldOutputs[key]): matched=True
            if not matched: return fail('No required heat-flow ODB field is nonzero: '+str(any_nonzero))
        if SPEC.get('nonzero_odb_fields') or SPEC.get('nonzero_odb_any_fields'):
            return ok('ODB checks passed')
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
