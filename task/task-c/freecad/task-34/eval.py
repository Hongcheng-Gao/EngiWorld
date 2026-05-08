from __future__ import annotations
import os
from pathlib import Path
import cadquery as cq
DEFAULT_OUTPUT=Path('/home/user/Desktop/freecad_task-34_output.step')
SOLID_COUNT=3
GLOBAL_BBOX=[0.0, 130.0, 0.0, 60.0, 0.0, 22.0]
TOTAL_VOLUME=149117.191952
SOLID_BBOXES=[[0.0, 38.0, 0.0, 60.0, 0.0, 22.0], [44.0, 82.0, 0.0, 60.0, 0.0, 22.0], [90.0, 130.0, 0.0, 60.0, 0.0, 22.0]]
SOLID_VOLUMES=[50160.0, 47671.858618, 51285.333333]
SOLID_PROBES=[[20, 30, 11], [50, 10, 11], [110, 30, 11], [95, 5, 18]]
EMPTY_PROBES=[[41, 30, 11], [86, 30, 11], [63, 30, 11], [91, 1, 21], [129, 59, 21]]
BBOX_TOL=0.15
POINT_TOL=1.0e-4
VOLUME_REL_TOL=0.0125
SOLID_VOLUME_REL_TOL=0.02

def _bbox(s):
    b=s.BoundingBox(); return [b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]
def _all_bbox(solids):
    xs=[];ys=[];zs=[]
    for s in solids:
        b=s.BoundingBox(); xs += [b.xmin,b.xmax]; ys += [b.ymin,b.ymax]; zs += [b.zmin,b.zmax]
    return [min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)]
def _close_list(a,e,t): return all(abs(float(x)-float(y))<=t for x,y in zip(a,e))
def _close_volume(a,e,t): return abs(float(a)-float(e))/max(1.0,abs(float(e)))<=t
def _contains(solids,point): return any(s.isInside(tuple(point),POINT_TOL) for s in solids)
def evaluate()->bool:
    path=Path(os.environ.get('FREECAD_EVAL_OUTPUT',str(DEFAULT_OUTPUT)))
    if not path.exists() or path.stat().st_size<=0: return False
    solids=cq.importers.importStep(str(path)).solids().vals()
    if len(solids)!=SOLID_COUNT or any(not s.isValid() for s in solids): return False
    if not _close_list(_all_bbox(solids),GLOBAL_BBOX,BBOX_TOL): return False
    if not _close_volume(sum(s.Volume() for s in solids),TOTAL_VOLUME,VOLUME_REL_TOL): return False
    actual=sorted([_bbox(s) for s in solids],key=lambda b:(round(b[0],3),round(b[2],3),round(b[4],3)))
    expected=sorted(SOLID_BBOXES,key=lambda b:(round(b[0],3),round(b[2],3),round(b[4],3)))
    for got,want in zip(actual,expected):
        if not _close_list(got,want,BBOX_TOL): return False
    for got,want in zip(sorted([s.Volume() for s in solids]), sorted(SOLID_VOLUMES)):
        if not _close_volume(got,want,SOLID_VOLUME_REL_TOL): return False
    for point in SOLID_PROBES:
        if not _contains(solids,point): return False
    for point in EMPTY_PROBES:
        if _contains(solids,point): return False
    return True
if __name__=='__main__':
    try: ok=evaluate()
    except Exception: ok=False
    print(True if ok else False)
    raise SystemExit(0)
