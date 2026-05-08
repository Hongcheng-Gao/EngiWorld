from __future__ import annotations
import os
from pathlib import Path
import cadquery as cq
DEFAULT_OUTPUT=Path('/home/user/Desktop/freecad_task-25_output.step')
SOLID_COUNT=1
GLOBAL_BBOX=[-74.0, 74.0, -74.0, 74.0, 0.0, 18.0]
TOTAL_VOLUME=266482.455248
SOLID_PROBES=[[70, 0, 9], [0, 70, 9], [64, 0, 2], [49.18376618407356, 38.18376618407356, 16], [-64, 0, 2]]
EMPTY_PROBES=[[0, 0, 9], [54, 0, 9], [0, 54, 9], [-54, 0, 9], [38.18376618407356, 38.18376618407356, 9], [60, 0, 2], [45.18376618407356, 38.18376618407356, 16], [-45.18376618407356, 38.18376618407356, 16]]
BBOX_TOL=0.2
POINT_TOL=1.0e-4
VOLUME_REL_TOL=0.015

def _bbox(solids):
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
    if not _close_list(_bbox(solids),GLOBAL_BBOX,BBOX_TOL): return False
    if not _close_volume(sum(s.Volume() for s in solids),TOTAL_VOLUME,VOLUME_REL_TOL): return False
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
