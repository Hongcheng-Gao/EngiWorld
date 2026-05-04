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
    jobname="apdl_cylinder",
    run_location=WORK_DIR,
    nproc=1,
    port=50210,
    override=True,
)

# ==================== 前处理 ====================
mapdl.prep7()

# PLANE183 + KEYOPT(3)=1 轴对称
mapdl.et(1, "PLANE183")
mapdl.keyopt(1, 3, 1)

# 材料：钢（mm-N-MPa）
mapdl.mp("EX", 1, 210000)
mapdl.mp("PRXY", 1, 0.3)

# 几何：轴对称截面 25≤X≤50 mm, 0≤Y≤10 mm
mapdl.rectng(25, 50, 0, 10)

# 网格：全局 5 mm
mapdl.esize(5)
mapdl.amesh("ALL")

# 保存数据库
mapdl.save("apdl_cylinder", "db")

# ==================== 求解 ====================
mapdl.finish()
mapdl.slashsolu()
mapdl.antype("STATIC")

# 内表面 X=25 施加内压 10 MPa（正值对圆柱内表面外法向 -X 而言，指向 +X 径向向外）
mapdl.lsel("S", "LOC", "X", 25)
mapdl.sfl("ALL", "PRES", 10)
mapdl.lsel("ALL")

# 轴向约束：Y=0 和 Y=10 处 UY=0
mapdl.nsel("S", "LOC", "Y", 0)
mapdl.d("ALL", "UY", 0)
mapdl.nsel("ALL")

mapdl.nsel("S", "LOC", "Y", 10)
mapdl.d("ALL", "UY", 0)
mapdl.nsel("ALL")

# 求解
mapdl.solve()

mapdl.finish()
mapdl.save("apdl_cylinder", "db")

# ==================== 后处理 & 提取 Ground Truth ====================
mapdl.post1()
mapdl.set(1, 1)

# 1. 内壁中点 (X=25, Y=5) 径向位移 + 环向应力
mapdl.nsel("S", "LOC", "X", 25)
mapdl.nsel("R", "LOC", "Y", 5)
node_inner = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
ux_inner = float(mapdl.get_value("NODE", node_inner, "U", "X"))
sz_inner = float(mapdl.get_value("NODE", node_inner, "S", "Z"))
mapdl.nsel("ALL")

# 2. 外壁中点 (X=50, Y=5) 径向位移
mapdl.nsel("S", "LOC", "X", 50)
mapdl.nsel("R", "LOC", "Y", 5)
node_outer = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
ux_outer = float(mapdl.get_value("NODE", node_outer, "U", "X"))
mapdl.nsel("ALL")

# 3. 最大 von Mises 等效应力
mapdl.run("NSORT, S, EQV, 0, 1, ALL")
seqv_max = float(mapdl.get_value("SORT", 0, "MAX"))

# 4. 最大环向应力 SZ（厚壁圆筒理论解关注量）
mapdl.run("NSORT, S, Z, 0, 1, ALL")
sz_max = float(mapdl.get_value("SORT", 0, "MAX"))

mapdl.exit()

# ==================== 复制文件到 Desktop 根目录 ====================
for ext in [".db", ".rst"]:
    src = os.path.join(WORK_DIR, f"apdl_cylinder{ext}")
    dst = os.path.join(USER_DESKTOP, f"apdl_cylinder{ext}")
    if os.path.exists(src):
        shutil.copy2(src, dst)

# ==================== 组装 JSON ====================
ground_truth = {
    "metadata": {
        "description": "ANSYS Axisymmetric Thick-Walled Cylinder - Ground Truth",
        "software": "ANSYS Mechanical APDL Student v261",
        "units": "mm-N-MPa"
    },
    "input_parameters": {
        "geometry": {
            "inner_radius_mm": 25.0,
            "outer_radius_mm": 50.0,
            "axial_thickness_mm": 10.0,
            "cross_section": "25 <= X <= 50 mm, 0 <= Y <= 10 mm"
        },
        "material": {
            "name": "Steel",
            "youngs_modulus_MPa": 210000.0,
            "poissons_ratio": 0.3
        },
        "mesh": {
            "element_type": "PLANE183",
            "axisymmetric": True,
            "global_element_size_mm": 5.0
        },
        "boundary_conditions": {
            "inner_surface": {"location": "X=25", "load": "internal_pressure_10_MPa"},
            "outer_surface": {"location": "X=50", "condition": "free"},
            "axial_faces": {"Y=0": "UY=0", "Y=10": "UY=0"}
        }
    },
    "results": {
        "inner_surface_midpoint": {
            "node_number": node_inner,
            "radial_displacement_UX_mm": ux_inner,
            "hoop_stress_SZ_MPa": sz_inner
        },
        "outer_surface_midpoint": {
            "node_number": node_outer,
            "radial_displacement_UX_mm": ux_outer
        },
        "maximum_von_mises_stress_MPa": seqv_max,
        "maximum_hoop_stress_SZ_MPa": sz_max
    }
}

output_path = os.path.join(USER_DESKTOP, "groundtruth.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(ground_truth, f, indent=2, ensure_ascii=False)

# ==================== 完成 ====================
print("\n" + "=" * 60)
print("  建模、求解、提取完成！")
print("=" * 60)
print(f"  数据库文件: {os.path.join(USER_DESKTOP, 'apdl_cylinder.db')}")
print(f"  结果文件:   {os.path.join(USER_DESKTOP, 'apdl_cylinder.rst')}")
print(f"  Ground Truth: {output_path}")
print("=" * 60)
