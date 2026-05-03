import json
import os
import shutil
from ansys.mapdl.core import launch_mapdl

# ==================== 路径配置 ====================
USER_DESKTOP = r"C:\Users\Administrator\Desktop"
WORK_DIR = os.path.join(USER_DESKTOP, "ansys_work")
os.makedirs(WORK_DIR, exist_ok=True)

# ==================== 启动 MAPDL ====================
mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\ANSYS Student\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="apdl_hole_plate",
    run_location=WORK_DIR,
    nproc=1,
    port=50150,
    override=True,
)

# ==================== 前处理 ====================
mapdl.prep7()

# PLANE183，KEYOPT(3)=3 启用 plane stress with thickness
mapdl.et(1, "PLANE183")
mapdl.keyopt(1, 3, 3)

# 厚度 1 mm
mapdl.r(1, 1.0)

# 材料：线弹性钢（mm-N-MPa）
mapdl.mp("EX", 1, 210000)
mapdl.mp("PRXY", 1, 0.3)

# 几何：矩形 0≤X≤100, 0≤Y≤200，减去中心圆孔 (50,100) 半径5
mapdl.blc4(0, 0, 100, 200)   # 矩形面
mapdl.cyl4(50, 100, 5)       # 圆面（孔）
mapdl.asba(1, 2)             # 布尔减：矩形减圆

# 网格控制
# 孔周围局部加密 1 mm（选中圆心附近 45≤X≤55, 95≤Y≤105 的边界线）
mapdl.lsel("S", "LOC", "X", 45, 55)
mapdl.lsel("R", "LOC", "Y", 95, 105)
mapdl.lesize("ALL", 1)
mapdl.lsel("ALL")

# 全局尺寸 5 mm
mapdl.esize(5)
mapdl.amesh("ALL")

# 保存数据库
mapdl.save("apdl_hole_plate", "db")

# ==================== 求解 ====================
mapdl.finish()
mapdl.slashsolu()
mapdl.antype("STATIC")

# 载荷：左右垂直边施加均布拉应力 10 MPa
# 左边界 X=0，traction in -X（拉力，负值压力）
mapdl.lsel("S", "LOC", "X", 0)
mapdl.sfl("ALL", "PRES", -10)
mapdl.lsel("ALL")

# 右边界 X=100，traction in +X（拉力，负值压力）
mapdl.lsel("S", "LOC", "X", 100)
mapdl.sfl("ALL", "PRES", -10)
mapdl.lsel("ALL")

# 最小约束消除刚体位移
# 参考节点1：(0, 0)，UX=0, UY=0
mapdl.nsel("S", "LOC", "X", 0)
mapdl.nsel("R", "LOC", "Y", 0)
mapdl.d("ALL", "UX", 0)
mapdl.d("ALL", "UY", 0)
mapdl.nsel("ALL")

# 参考节点2：(100, 0)，UY=0（与节点1在 X 方向分离）
mapdl.nsel("S", "LOC", "X", 100)
mapdl.nsel("R", "LOC", "Y", 0)
mapdl.d("ALL", "UY", 0)
mapdl.nsel("ALL")

# 求解
mapdl.solve()

mapdl.finish()
mapdl.save("apdl_hole_plate", "db")

# ==================== 后处理 & 提取 Ground Truth ====================
mapdl.post1()
mapdl.set(1, 1)

# 1. 孔边最大 X 方向正应力（应力集中）
mapdl.nsel("S", "LOC", "X", 45, 55)
mapdl.nsel("R", "LOC", "Y", 95, 105)
mapdl.run("NSORT, S, X, 0, 1, ALL")
sx_max = float(mapdl.get_value("SORT", 0, "MAX"))
mapdl.nsel("ALL")

# 2. 最大等效应力（von Mises）
mapdl.run("NSORT, S, EQV, 0, 1, ALL")
seqv_max = float(mapdl.get_value("SORT", 0, "MAX"))

# 3. 最大位移
mapdl.run("NSORT, U, SUM, 0, 1, ALL")
usum_max = float(mapdl.get_value("SORT", 0, "MAX"))

# 4. 参考节点1 (0,0) 的反力
mapdl.nsel("S", "LOC", "X", 0)
mapdl.nsel("R", "LOC", "Y", 0)
mapdl.fsum()
fx_react = float(mapdl.get_value("FSUM", 0, "ITEM", "FX"))
fy_react = float(mapdl.get_value("FSUM", 0, "ITEM", "FY"))
mapdl.nsel("ALL")

mapdl.exit()

# ==================== 复制文件到 Desktop 根目录 ====================
for ext in [".db", ".rst"]:
    src = os.path.join(WORK_DIR, f"apdl_hole_plate{ext}")
    dst = os.path.join(USER_DESKTOP, f"apdl_hole_plate{ext}")
    if os.path.exists(src):
        shutil.copy2(src, dst)

# ==================== 组装 JSON ====================
ground_truth = {
    "metadata": {
        "description": "ANSYS 2D Plane-Stress Plate with Hole - Ground Truth",
        "software": "ANSYS Mechanical APDL Student v261",
        "units": "mm-N-MPa"
    },
    "input_parameters": {
        "geometry": {
            "plate_width_mm": 100.0,
            "plate_length_mm": 200.0,
            "thickness_mm": 1.0,
            "hole_center": {"X_mm": 50.0, "Y_mm": 100.0},
            "hole_diameter_mm": 10.0,
            "hole_radius_mm": 5.0
        },
        "material": {
            "name": "Steel",
            "youngs_modulus_MPa": 210000.0,
            "poissons_ratio": 0.3
        },
        "mesh": {
            "element_type": "PLANE183",
            "element_behavior": "plane stress with thickness",
            "thickness_mm": 1.0,
            "global_element_size_mm": 5.0,
            "local_element_size_hole_mm": 1.0
        },
        "boundary_conditions": {
            "load": {
                "type": "uniaxial tension",
                "nominal_stress_MPa": 10.0,
                "left_edge_X0": "traction in -X",
                "right_edge_X100": "traction in +X"
            },
            "rigid_body_constraints": {
                "reference_node_1": {"location": "(0,0)", "UX": 0, "UY": 0},
                "reference_node_2": {"location": "(100,0)", "UY": 0}
            }
        }
    },
    "results": {
        "hole_edge_max_sx_MPa": sx_max,
        "maximum_von_mises_stress_MPa": seqv_max,
        "maximum_displacement_mm": {
            "USUM_MAX": usum_max
        },
        "reference_node_reaction_force_N": {
            "FX": fx_react,
            "FY": fy_react
        }
    }
}

output_path = os.path.join(USER_DESKTOP, "groundtruth.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(ground_truth, f, indent=2, ensure_ascii=False)

# ==================== 完成 ====================
print("\n" + "=" * 60)
print("  建模、求解、提取完成！")
print("=" * 60)
print(f"  数据库文件: {os.path.join(USER_DESKTOP, 'apdl_hole_plate.db')}")
print(f"  结果文件:   {os.path.join(USER_DESKTOP, 'apdl_hole_plate.rst')}")
print(f"  Ground Truth: {output_path}")
print("=" * 60)
