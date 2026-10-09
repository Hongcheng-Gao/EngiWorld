"""Build ground_truth/answer.blend for task AH02 - Simulation Zone Confetti.

Architecture (all built on the Emitter object via a Geometry Nodes modifier):

    Group Input (Emitter geometry)
        |
        v
    +-- Simulation Zone ------------------------------------------------+
    |   [prev state geometry comes in from sim_in; dt = sim_in.DT ]    |
    |                                                                  |
    |   A. PHYSICS UPDATE on existing points                           |
    |      - Named Attribute "velocity" (FLOAT_VECTOR, POINT)          |
    |      - new_vel_pre = old_vel + (0,0,-9.81)*dt                    |
    |      - new_pos_pre = Position + new_vel_pre * dt                 |
    |      - if new_pos_pre.z < 0:  pos.z = 0, vel.z = 0               |
    |      - Set Position to clamped_pos                               |
    |      - Store Named Attribute velocity = clamped_vel              |
    |                                                                  |
    |   B. EMIT 10 NEW POINTS                                          |
    |      - Points node (Count=10)                                    |
    |      - Position = (random in [-2,2], random in [-2,2], 5)        |
    |      - Store velocity = (rand[-3,3], rand[-3,3], 3)              |
    |                                                                  |
    |   C. JOIN(updated_existing, new_emission) -> sim_out             |
    +------------------------------------------------------------------+
        |
        v
    Group Output

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os

import bpy

HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INPUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
OUT_PATH   = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

# Physics / emission constants.
GRAVITY_Z      = -9.81
INITIAL_VZ     =  3.0
HORIZ_SPEED    =  3.0      # initial velocity x,y in [-3, +3]
EMIT_PER_FRAME = 10
EMIT_Z         =  5.0
EMIT_HALF      =  2.0      # emitter plane half-extent (scale=2 on size=2 plane)
SEED_EMIT_XY   =  17       # random seed for horizontal initial velocity
SEED_EMIT_POS  =  23       # random seed for emission position on plane
SEED_EMIT_VY   =  41       # second seed for velocity.y vs velocity.x


def main():
    bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

    emitter = bpy.data.objects["Emitter"]

    # --- Add GN modifier --------------------------------------------------
    mod = emitter.modifiers.new(name="ConfettiGN", type="NODES")

    tree = bpy.data.node_groups.new(name="ConfettiSimGN",
                                    type="GeometryNodeTree")
    mod.node_group = tree

    tree.interface.new_socket(name="Geometry",
                              in_out="INPUT",
                              socket_type="NodeSocketGeometry")
    tree.interface.new_socket(name="Geometry",
                              in_out="OUTPUT",
                              socket_type="NodeSocketGeometry")

    # --- Group I/O boundary ----------------------------------------------
    n_in  = tree.nodes.new("NodeGroupInput")
    n_out = tree.nodes.new("NodeGroupOutput")
    n_in.location  = (-1800.0, 0.0)
    n_out.location = ( 2600.0, 0.0)

    # --- Simulation Zone --------------------------------------------------
    # Default state_items already contains one GEOMETRY item named "Geometry".
    sim_in  = tree.nodes.new("GeometryNodeSimulationInput")
    sim_out = tree.nodes.new("GeometryNodeSimulationOutput")
    sim_in.pair_with_output(sim_out)
    sim_in.location  = (-1500.0, 0.0)
    sim_out.location = ( 2200.0, 0.0)

    # ---- INSIDE THE SIMULATION ZONE -------------------------------------
    # (A) Physics update on existing persistent points.

    # Read the per-point stored velocity attribute.
    n_vel_attr = tree.nodes.new("GeometryNodeInputNamedAttribute")
    n_vel_attr.data_type = "FLOAT_VECTOR"
    n_vel_attr.inputs["Name"].default_value = "velocity"
    n_vel_attr.location = (-1200.0, -300.0)

    # dt = sim_in "Delta Time" output (seconds between frames).
    # gravity vector (0, 0, -9.81) as a constant.
    n_grav = tree.nodes.new("FunctionNodeInputVector")
    n_grav.vector = (0.0, 0.0, GRAVITY_Z)
    n_grav.location = (-1200.0, -500.0)

    # g * dt  (VectorMath SCALE: vector * scalar).
    n_grav_dt = tree.nodes.new("ShaderNodeVectorMath")
    n_grav_dt.operation = "SCALE"
    n_grav_dt.location = (-1000.0, -500.0)

    # new_vel = old_vel + g*dt   (VectorMath ADD).
    n_new_vel = tree.nodes.new("ShaderNodeVectorMath")
    n_new_vel.operation = "ADD"
    n_new_vel.location = (-800.0, -400.0)

    # Current position input.
    n_cur_pos = tree.nodes.new("GeometryNodeInputPosition")
    n_cur_pos.location = (-1200.0, 200.0)

    # new_vel * dt  (VectorMath SCALE).
    n_vdt = tree.nodes.new("ShaderNodeVectorMath")
    n_vdt.operation = "SCALE"
    n_vdt.location = (-600.0, -400.0)

    # new_pos_pre = Position + new_vel * dt   (VectorMath ADD).
    n_new_pos = tree.nodes.new("ShaderNodeVectorMath")
    n_new_pos.operation = "ADD"
    n_new_pos.location = (-400.0, 0.0)

    # Clamp Z: if new_pos_pre.z < 0 -> pos.z = 0, vel.z = 0.
    # Separate new_pos_pre so we can get its Z.
    n_sep_pos = tree.nodes.new("ShaderNodeSeparateXYZ")
    n_sep_pos.location = (-200.0, 100.0)

    # Compare: pos_z < 0.
    n_cmp = tree.nodes.new("FunctionNodeCompare")
    n_cmp.data_type = "FLOAT"
    n_cmp.operation = "LESS_THAN"
    n_cmp.location = (0.0, 100.0)
    n_cmp.inputs[1].default_value = 0.0

    # Clamp pos.z: new_z = max(new_pos_pre.z, 0)  (Math MAXIMUM).
    n_max_z = tree.nodes.new("ShaderNodeMath")
    n_max_z.operation = "MAXIMUM"
    n_max_z.location = (0.0, -100.0)
    n_max_z.inputs[1].default_value = 0.0

    # Build clamped pos = (x, y, max(z, 0)).
    n_sep_pos2 = tree.nodes.new("ShaderNodeSeparateXYZ")
    n_sep_pos2.location = (-200.0, -300.0)
    n_comb_pos = tree.nodes.new("ShaderNodeCombineXYZ")
    n_comb_pos.location = (200.0, -100.0)

    # Wait: we need original X,Y from new_pos_pre, and max(z, 0) for Z.
    # We already have n_sep_pos giving X,Y,Z of new_pos_pre — reuse it.
    # (The n_sep_pos2 above is unused; delete it.)
    tree.nodes.remove(n_sep_pos2)

    # Clamped velocity: if below_zero, vel.z = 0; else vel.z = new_vel.z.
    # Simpler approach: vel_z_clamped = vel.z * (below_zero ? 0 : 1)
    #                                = vel.z * (1 - below_zero_as_float)
    # or use Switch FLOAT.
    n_sep_vel = tree.nodes.new("ShaderNodeSeparateXYZ")
    n_sep_vel.location = (-600.0, -700.0)

    n_sw_vz = tree.nodes.new("GeometryNodeSwitch")
    n_sw_vz.input_type = "FLOAT"
    n_sw_vz.location = (0.0, -500.0)
    # inputs: Switch (bool), False (float), True (float).
    # If pos_z < 0 (below_zero True) -> vel_z = 0 (True branch).
    n_sw_vz.inputs["True"].default_value = 0.0

    n_comb_vel = tree.nodes.new("ShaderNodeCombineXYZ")
    n_comb_vel.location = (200.0, -500.0)

    # Set Position on previous-state geometry to clamped pos.
    n_setpos = tree.nodes.new("GeometryNodeSetPosition")
    n_setpos.location = (450.0, 0.0)

    # Store Named Attribute "velocity" = clamped_vel (FLOAT_VECTOR, POINT).
    n_store_vel = tree.nodes.new("GeometryNodeStoreNamedAttribute")
    n_store_vel.data_type = "FLOAT_VECTOR"
    n_store_vel.domain = "POINT"
    n_store_vel.inputs["Name"].default_value = "velocity"
    n_store_vel.location = (700.0, 0.0)

    # -------- (B) Emit 10 NEW points this frame -------------------------
    n_points = tree.nodes.new("GeometryNodePoints")
    n_points.location = (-400.0, 900.0)
    n_points.inputs["Count"].default_value = EMIT_PER_FRAME
    n_points.inputs["Radius"].default_value = 0.05

    # Random emission position (x in [-2,2], y in [-2,2], z=5).
    n_rnd_xy = tree.nodes.new("FunctionNodeRandomValue")
    n_rnd_xy.data_type = "FLOAT_VECTOR"
    n_rnd_xy.location = (-800.0, 800.0)
    # Use the first (VECTOR) Min/Max inputs (enabled when data_type=FLOAT_VECTOR).
    # The Min input has identifier "Min" for the VECTOR variant.
    n_rnd_xy.inputs["Min"].default_value = (-EMIT_HALF, -EMIT_HALF, EMIT_Z)
    n_rnd_xy.inputs["Max"].default_value = ( EMIT_HALF,  EMIT_HALF, EMIT_Z)
    n_rnd_xy.inputs["Seed"].default_value = SEED_EMIT_POS
    # ID via Index so each of the 10 points gets a distinct random value.
    n_idx_p = tree.nodes.new("GeometryNodeInputIndex")
    n_idx_p.location = (-1000.0, 700.0)

    # Random initial velocity: x in [-3,3], y in [-3,3], z=3.
    n_rnd_vel = tree.nodes.new("FunctionNodeRandomValue")
    n_rnd_vel.data_type = "FLOAT_VECTOR"
    n_rnd_vel.location = (-800.0, 500.0)
    n_rnd_vel.inputs["Min"].default_value = (-HORIZ_SPEED, -HORIZ_SPEED, INITIAL_VZ)
    n_rnd_vel.inputs["Max"].default_value = ( HORIZ_SPEED,  HORIZ_SPEED, INITIAL_VZ)
    n_rnd_vel.inputs["Seed"].default_value = SEED_EMIT_XY

    # To make each frame emit DIFFERENT random points, we need the ID
    # (or Seed) to vary per frame. Use Scene Time (Frame) combined with
    # point index. Random Value's ID input changes the hash: we want
    # ID = index + frame * large_stride so points on different frames
    # generate distinct random values.
    n_time = tree.nodes.new("GeometryNodeInputSceneTime")
    n_time.location = (-1400.0, 500.0)

    # frame * 1000 (sub)
    n_frame_stride = tree.nodes.new("ShaderNodeMath")
    n_frame_stride.operation = "MULTIPLY"
    n_frame_stride.inputs[1].default_value = 1000.0
    n_frame_stride.location = (-1200.0, 500.0)

    # id = index + frame*1000 (add)
    n_id_sum = tree.nodes.new("ShaderNodeMath")
    n_id_sum.operation = "ADD"
    n_id_sum.location = (-1000.0, 500.0)

    # The Random Value node's ID input expects INT.
    # ShaderNodeMath outputs float but auto-converts to int via the socket.

    # Set Position on the new points (use Position input, not Offset).
    n_setpos_new = tree.nodes.new("GeometryNodeSetPosition")
    n_setpos_new.location = (-150.0, 900.0)

    # Store velocity attribute on the new points (POINT domain).
    n_store_vel_new = tree.nodes.new("GeometryNodeStoreNamedAttribute")
    n_store_vel_new.data_type = "FLOAT_VECTOR"
    n_store_vel_new.domain = "POINT"
    n_store_vel_new.inputs["Name"].default_value = "velocity"
    n_store_vel_new.location = (150.0, 900.0)

    # ---- (C) Join updated existing + new emission -----------------------
    n_join = tree.nodes.new("GeometryNodeJoinGeometry")
    n_join.location = (1100.0, 300.0)

    # ---- Links ----------------------------------------------------------
    L = tree.links.new

    # A. Physics chain on prev-state geometry.
    dt_out = sim_in.outputs["Delta Time"]
    prev_state_geo = sim_in.outputs["Geometry"]  # Item_0

    # g * dt.
    L(n_grav.outputs["Vector"], n_grav_dt.inputs[0])
    L(dt_out, n_grav_dt.inputs["Scale"])

    # Named velocity attribute vector output is "Attribute".
    vel_attr_out = n_vel_attr.outputs["Attribute"]

    # new_vel = old_vel + g*dt.
    L(vel_attr_out, n_new_vel.inputs[0])
    L(n_grav_dt.outputs["Vector"], n_new_vel.inputs[1])

    # new_vel * dt.
    L(n_new_vel.outputs["Vector"], n_vdt.inputs[0])
    L(dt_out, n_vdt.inputs["Scale"])

    # new_pos = pos + new_vel*dt.
    L(n_cur_pos.outputs["Position"], n_new_pos.inputs[0])
    L(n_vdt.outputs["Vector"], n_new_pos.inputs[1])

    # Separate new_pos to get (x, y, z).
    L(n_new_pos.outputs["Vector"], n_sep_pos.inputs["Vector"])

    # below_zero = (new_pos.z < 0).
    L(n_sep_pos.outputs["Z"], n_cmp.inputs[0])

    # clamped_z = max(new_pos.z, 0).
    L(n_sep_pos.outputs["Z"], n_max_z.inputs[0])

    # clamped pos = (new_pos.x, new_pos.y, clamped_z).
    L(n_sep_pos.outputs["X"], n_comb_pos.inputs["X"])
    L(n_sep_pos.outputs["Y"], n_comb_pos.inputs["Y"])
    L(n_max_z.outputs["Value"], n_comb_pos.inputs["Z"])

    # Separate new_vel to build clamped vel.
    L(n_new_vel.outputs["Vector"], n_sep_vel.inputs["Vector"])

    # vel_z_clamped = (below_zero) ? 0 : new_vel.z.
    L(n_cmp.outputs["Result"], n_sw_vz.inputs["Switch"])
    L(n_sep_vel.outputs["Z"], n_sw_vz.inputs["False"])
    # True-branch default_value = 0.0 already set.

    # clamped_vel = (new_vel.x, new_vel.y, vel_z_clamped).
    L(n_sep_vel.outputs["X"], n_comb_vel.inputs["X"])
    L(n_sep_vel.outputs["Y"], n_comb_vel.inputs["Y"])
    L(n_sw_vz.outputs["Output"], n_comb_vel.inputs["Z"])

    # Apply clamped pos to existing geometry.
    L(prev_state_geo, n_setpos.inputs["Geometry"])
    L(n_comb_pos.outputs["Vector"], n_setpos.inputs["Position"])

    # Store clamped vel on existing geometry.
    L(n_setpos.outputs["Geometry"], n_store_vel.inputs["Geometry"])
    L(n_comb_vel.outputs["Vector"], n_store_vel.inputs["Value"])

    # --- B. New point emission --------------------------------------------
    # id = index + frame*1000.
    L(n_time.outputs["Frame"], n_frame_stride.inputs[0])
    L(n_frame_stride.outputs["Value"], n_id_sum.inputs[0])
    L(n_idx_p.outputs["Index"], n_id_sum.inputs[1])

    # Feed random value nodes their ID.
    L(n_id_sum.outputs["Value"], n_rnd_xy.inputs["ID"])
    L(n_id_sum.outputs["Value"], n_rnd_vel.inputs["ID"])

    # Create 10 points at origin (default).
    # Set their position from n_rnd_xy.
    # The Points node's default position is (0,0,0). Use SetPosition.
    L(n_points.outputs["Geometry"], n_setpos_new.inputs["Geometry"])
    # n_rnd_xy Value output is the VECTOR output.
    rnd_xy_out = n_rnd_xy.outputs["Value"]  # first (VECTOR) output
    L(rnd_xy_out, n_setpos_new.inputs["Position"])

    # Store velocity on new points.
    L(n_setpos_new.outputs["Geometry"], n_store_vel_new.inputs["Geometry"])
    rnd_vel_out = n_rnd_vel.outputs["Value"]
    L(rnd_vel_out, n_store_vel_new.inputs["Value"])

    # --- C. Join existing + new emission into sim_out --------------------
    # Order: updated existing first, new emission second (doesn't matter
    # for counts; both feed Join).
    L(n_store_vel.outputs["Geometry"], n_join.inputs["Geometry"])
    L(n_store_vel_new.outputs["Geometry"], n_join.inputs["Geometry"])

    # Sim zone output.
    L(n_join.outputs["Geometry"], sim_out.inputs["Geometry"])

    # --- Outside the sim zone: sim_in initial geometry ------------------
    # For frame 1 the zone uses sim_in.input as the initial state.
    # We want it to be empty geometry (no points). The Group Input
    # Emitter-geometry is not empty (it's the plane mesh), but the
    # evaluator only reads the final output. A clean empty point cloud
    # as initial state ensures no stray plane vertices get integrated.
    n_empty = tree.nodes.new("GeometryNodePoints")
    n_empty.location = (-1800.0, 300.0)
    n_empty.inputs["Count"].default_value = 0
    # But Count=0 might not produce valid geometry on every version; we
    # can also simply wire Group Input (non-empty) — but that will treat
    # the emitter's 4 vertices as part of the simulation state with no
    # `velocity` attribute -> falls back to (0,0,0) velocity -> they stay
    # put at z=5 forever and won't fall. They'd ALSO add 4 to every
    # frame's count. Better to start with an EMPTY Points node.
    # Blender's GeometryNodePoints with Count=0 produces an empty point
    # cloud which is valid.
    L(n_empty.outputs["Geometry"], sim_in.inputs["Geometry"])

    # --- Outside: convert point cloud -> mesh so evaluator sees verts ----
    # GeometryNodePointsToVertices keeps each point as a vertex and
    # preserves POINT-domain attributes (including `velocity`).
    n_p2v = tree.nodes.new("GeometryNodePointsToVertices")
    n_p2v.location = (2400.0, 0.0)
    L(sim_out.outputs["Geometry"], n_p2v.inputs["Points"])

    # --- Outside: Points-to-Vertices mesh -> Group Output ---------------
    L(n_p2v.outputs["Mesh"], n_out.inputs["Geometry"])

    # --- Sanity check: step through frames 1..30 so sim cache builds ----
    for f in range(1, 31):
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()

    dg = bpy.context.evaluated_depsgraph_get()
    ev_obj = emitter.evaluated_get(dg)
    ev_mesh = ev_obj.to_mesh()
    n_pts = len(ev_mesh.vertices)
    print(f"  evaluated vert count at frame 30: {n_pts} (expect ~300)")
    if n_pts:
        zs = [v.co.z for v in ev_mesh.vertices]
        print(f"  Z range: [{min(zs):.4f}, {max(zs):.4f}]")
        print(f"  # points with z in [3,5]: "
              f"{sum(1 for z in zs if 3.0 <= z <= 5.0)}")
        print(f"  # points with z in [0, 2]: "
              f"{sum(1 for z in zs if 0.0 <= z <= 2.0)}")
        print(f"  # points with z <= 0.01: "
              f"{sum(1 for z in zs if z <= 0.01)}")
    attrs = {a.name: (a.domain, a.data_type) for a in ev_mesh.attributes}
    print(f"  attributes: {attrs}")
    ev_obj.to_mesh_clear()

    # Reset frame to 1 for clean file state.
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

    bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
    print(f"  saved -> {OUT_PATH}")


if __name__ == "__main__":
    main()
