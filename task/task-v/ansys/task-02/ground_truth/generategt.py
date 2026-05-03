import json
import os
import shutil
from ansys.mapdl.core import launch_mapdl

# ==================== 路径配置 ====================
USER_DESKTOP = r"C:\Users\Administrator\Desktop"
WORK_DIR     = os.path.join(USER_DESKTOP, "ansys_work")  # 子目录，绕开 Desktop 根目录写权限问题

os.makedirs(WORK_DIR, exist_ok=True)

# ==================== 启动 MAPDL ====================
mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\ANSYS Student\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="apdl_plate",
    run_location=WORK_DIR,
    nproc=1,
    port=50140,
    override=True,
)

# ==================== 前处理 ====================
mapdl.prep7()

# 单元类型 PLANE183，KEYOPT(3)=1 启用轴对称
mapdl.et(1, "PLANE183")
mapdl.keyopt(1, 3, 1)

# 材料：线弹性钢（mm-N-MPa 单位制）
mapdl.mp("EX", 1, 210000)
mapdl.mp("PRXY", 1, 0.3)

# 几何：轴对称截面 0 ≤ X ≤ 50 mm, 0 ≤ Y ≤ 1 mm
mapdl.rectng(0, 50, 0, 1)

# 网格：全局单元尺寸 2 mm
mapdl.esize(2)
mapdl.amesh("ALL")

# 保存数据库（生成 apdl_plate.db）
mapdl.save("apdl_plate", "db")

# ==================== 求解 ====================
mapdl.finish()
mapdl.slashsolu()
mapdl.antype("STATIC")

# 对称轴 X=0：约束径向位移 UX = 0
mapdl.nsel("S", "LOC", "X", 0)
mapdl.d("ALL", "UX", 0)
mapdl.nsel("ALL")

# 固支外边缘 X=50：径向和轴向位移均为零（UX=0, UY=0）
mapdl.nsel("S", "LOC", "X", 50)
mapdl.d("ALL", "ALL", 0)
mapdl.nsel("ALL")

# 顶面 Y=1 施加均布压力 0.1 MPa（正值对顶面外法向 +Y 而言指向单元内部，即 -Y 方向）
mapdl.lsel("S", "LOC", "Y", 1)
mapdl.sfl("ALL", "PRES", 0.1)
mapdl.allsel()

# 求解（自动生成 apdl_plate.rst）
mapdl.solve()

# 再次保存数据库
mapdl.finish()
mapdl.save("apdl_plate", "db")

# ==================== 后处理 & 提取 Ground Truth ====================
mapdl.post1()
mapdl.set(1, 1)

# 1. 板中心顶面节点 (X=0, Y=1) 的位移 —— 2D 轴对称只有 UX、UY
mapdl.nsel("S", "LOC", "X", 0)
mapdl.nsel("R", "LOC", "Y", 1)
node_center = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))

ux_center   = float(mapdl.get_value("NODE", node_center, "U", "X"))
uy_center   = float(mapdl.get_value("NODE", node_center, "U", "Y"))
usum_center = float(mapdl.get_value("NODE", node_center, "U", "SUM"))
mapdl.nsel("ALL")

# 2. 最大位移（全模型）
mapdl.run("NSORT, U, Y, 0, 1, ALL")
uy_max = float(mapdl.get_value("SORT", 0, "MAX"))

mapdl.run("NSORT, U, SUM, 0, 1, ALL")
usum_max = float(mapdl.get_value("SORT", 0, "MAX"))

# 3. 最大等效应力（von Mises）
mapdl.run("NSORT, S, EQV, 0, 1, ALL")
seqv_max = float(mapdl.get_value("SORT", 0, "MAX"))

# 4. 固支边 X=50 的反力
mapdl.nsel("S", "LOC", "X", 50)
mapdl.fsum()
fx_react = float(mapdl.get_value("FSUM", 0, "ITEM", "FX"))
fy_react = float(mapdl.get_value("FSUM", 0, "ITEM", "FY"))
mapdl.nsel("ALL")

mapdl.exit()

# ==================== 复制文件到 Desktop 根目录（满足 instruction 保存要求）====================
for ext in [".db", ".rst"]:
    src = os.path.join(WORK_DIR, f"apdl_plate{ext}")
    dst = os.path.join(USER_DESKTOP, f"apdl_plate{ext}")
    if os.path.exists(src):
        shutil.copy2(src, dst)

# ==================== 组装 JSON ====================
ground_truth = {
    "metadata": {
        "description": "ANSYS Axisymmetric Circular Plate - Ground Truth",
        "software": "ANSYS Mechanical APDL Student v261",
        "units": "mm-N-MPa"
    },
    "input_parameters": {
        "geometry": {
            "plate_radius_mm": 50.0,
            "plate_thickness_mm": 1.0,
            "cross_section": "0 <= X <= 50 mm, 0 <= Y <= 1 mm"
        },
        "material": {
            "name": "Steel",
            "youngs_modulus_MPa": 210000.0,
            "poissons_ratio": 0.3
        },
        "mesh": {
            "element_type": "PLANE183",
            "axisymmetric": True,
            "global_element_size_mm": 2.0
        },
        "boundary_conditions": {
            "symmetry_axis": {"location": "X=0", "constraint": "UX=0"},
            "clamped_edge": {"location": "X=50", "constraint": "UX=0, UY=0"}
        },
        "load": {
            "type": "uniform_pressure",
            "surface": "top surface Y=1 mm",
            "magnitude_MPa": 0.1,
            "direction": "-Y"
        }
    },
    "results": {
        "center_top_displacement_mm": {
            "node_number": node_center,
            "UX": ux_center,
            "UY": uy_center,
            "USUM": usum_center
        },
        "maximum_displacement_mm": {
            "UY_MAX": uy_max,
            "USUM_MAX": usum_max
        },
        "maximum_von_mises_stress_MPa": seqv_max,
        "clamped_edge_reaction_force_N": {
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
print(f"  数据库文件: {os.path.join(USER_DESKTOP, 'apdl_plate.db')}")
print(f"  结果文件:   {os.path.join(USER_DESKTOP, 'apdl_plate.rst')}")
print(f"  Ground Truth: {output_path}")
print("=" * 60)
