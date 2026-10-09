"""Debug what's in the saved answer.blend."""
import bpy, os
HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
bpy.ops.wm.open_mainfile(filepath=os.path.join(TASK, "ground_truth", "answer.blend"))
sc = bpy.context.scene
print("frame_end:", sc.frame_end)
print("Objects:")
for o in bpy.data.objects:
    print("  ", o.name, o.type, "hide_render=", o.hide_render,
          "hide_viewport=", o.hide_viewport,
          "visible_get=", o.visible_get(),
          "loc=", tuple(round(v, 2) for v in o.location),
          "parent=", (o.parent.name if o.parent else None))
    if o.type == "MESH":
        print("     verts=", len(o.data.vertices),
              " mats=", [m.name if m else None for m in o.data.materials],
              " modifiers=", [(m.name, m.type) for m in o.modifiers])
        attrs = [(a.name, a.data_type, a.domain) for a in o.data.attributes]
        print("     attrs=", attrs)

# Force evaluation and see how many realized instances are emitted.
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
dg.update()

bp = bpy.data.objects.get("BrickPoints")
if bp is None:
    print("No BrickPoints")
else:
    ev = bp.evaluated_get(dg)
    me = ev.data if ev.type == "MESH" else None
    if me is not None:
        print("BrickPoints evaluated verts:", len(me.vertices), "polys:", len(me.polygons))
        attr_names = [a.name for a in me.attributes]
        print("  evaluated mesh attrs:", attr_names)

# Also check instance enumeration.
n_inst = 0
for oi in dg.object_instances:
    if oi.is_instance and oi.parent is not None and oi.parent.original == bp:
        n_inst += 1
print("Instances with parent BrickPoints:", n_inst)

# Render preview frame 15 and look at mean alpha.
sc.frame_set(15)
bpy.context.view_layer.update()
out = "/tmp/kh02_debug_f15.png"
sc.render.filepath = out
sc.render.engine = "CYCLES"
sc.cycles.samples = 4
sc.render.resolution_x = 128
sc.render.resolution_y = 128
bpy.ops.render.render(write_still=True)
print("Rendered debug frame to", out)

img = bpy.data.images.load(out, check_existing=False)
px = list(img.pixels)
w, h = img.size
n_alpha = sum(1 for i in range(3, len(px), 4) if px[i] > 0.5)
print("debug frame w,h =", w, h, "alpha>0.5 count =", n_alpha, "/", w*h)
rgb_samples = [(px[i], px[i+1], px[i+2], px[i+3]) for i in range(0, min(len(px), 4*50), 4)]
print("first 5 rgba samples:", rgb_samples[:5])
bpy.data.images.remove(img, do_unlink=True)
