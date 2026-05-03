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
    jobname="apdl_solid_beam",
    run_location=WORK_DIR,
    nproc=1,
    port=50220,
    override=True,
)

# ==================== 前处理 ====================
mapdl.prep7()

# 单元类型 SOLID185
mapdl.et(1, "SOLID185")

# 材料：线弹性钢（mm-N-MPa）
mapdl.mp("EX", 1, 210000)
mapdl.mp("PRXY", 1, 0.3)

# 几何：100 mm(X) × 10 mm(Y) × 10 mm(Z)
mapdl.block(0, 100, 0, 10, 0, 10)

# 网格：全局 5 mm
mapdl.esize(5)
mapdl.vmesh("ALL")

# 保存数据库
mapdl.save("apdl_solid_beam", "db")

# ==================== 求解 ====================
mapdl.finish()
mapdl.slashsolu()
mapdl.antype("STATIC")

# 固定端 X=0：全约束
mapdl.nsel("S", "LOC", "X", 0)
mapdl.d("ALL", "ALL", 0)
mapdl.nsel("ALL")

# 载荷：自由端顶面中点 (100, 10, 5)，FY = -100 N
mapdl.nsel("S", "LOC", "X", 100)
mapdl.nsel("R", "LOC", "Y", 10)
mapdl.nsel("R", "LOC", "Z", 5)
mapdl.f("ALL", "FY", -100)
mapdl.nsel("ALL")

# 求解
mapdl.solve()

mapdl.finish()
mapdl.save("apdl_solid_beam", "db")

# ==================== 后处理 & 提取 Ground Truth ====================
mapdl.post1()
mapdl.set(1, 1)

# 1. 加载点 (100, 10, 5) 位移
mapdl.nsel("S", "LOC", "X", 100)
mapdl.nsel("R", "LOC", "Y", 10)
mapdl.nsel("R", "LOC", "Z", 5)
node_load = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))

ux_load = float(mapdl.get_value("NODE", node_load, "U", "X"))
uy_load = float(mapdl.get_value("NODE", node_load, "U", "Y"))
uz_load = float(mapdl.get_value("NODE", node_load, "U", "Z"))
usum_load = float(mapdl.get_value("NODE", node_load, "U", "SUM"))
mapdl.nsel("ALL")

# 2. 最大位移（全模型）
mapdl.run("NSORT, U, X, 0, 1, ALL")
ux_max = float(mapdl.get_value("SORT", 0, "MAX"))

mapdl.run("NSORT, U, Y, 0, 1, ALL")
uy_max = float(mapdl.get_value("SORT", 0, "MAX"))

mapdl.run("NSORT, U, Z, 0, 1, ALL")
uz_max = float(mapdl.get_value("SORT", 0, "MAX"))

mapdl.run("NSORT, U, SUM, 0, 1, ALL")
usum_max = float(mapdl.get_value("SORT", 0, "MAX"))

# 3. 最大等效应力
mapdl.run("NSORT, S, EQV, 0, 1, ALL")
seqv_max = float(mapdl.get_value("SORT", 0, "MAX"))

# 4. 固定端 X=0 反力
mapdl.nsel("S", "LOC", "X", 0)
mapdl.fsum()
fx_react = float(mapdl.get_value("FSUM", 0, "ITEM", "FX"))
fy_react = float(mapdl.get_value("FSUM", 0, "ITEM", "FY"))
fz_react = float(mapdl.get_value("FSUM", 0, "ITEM", "FZ"))
mapdl.nsel("ALL")

mapdl.exit()

# ==================== 复制文件到 Desktop 根目录 ====================
for ext in [".db", ".rst"]:
    src = os.path.join(WORK_DIR, f"apdl_solid_beam{ext}")
    dst = os.path.join(USER_DESKTOP, f"apdl_solid_beam{ext}")
    if os.path.exists(src):
        shutil.copy2(src, dst)

# ==================== 组装 JSON ====================
ground_truth = {
    "metadata": {
        "description": "ANSYS 3D Solid Cantilever Beam - Ground Truth",
        "software": "ANSYS Mechanical APDL Student v261",
        "units": "mm-N-MPa"
    },
    "input_parameters": {
        "geometry": {
            "length_x_mm": 100.0,
            "height_y_mm": 10.0,
            "width_z_mm": 10.0
        },
        "material": {
            "name": "Steel",
            "youngs_modulus_MPa": 210000.0,
            "poissons_ratio": 0.3
        },
        "mesh": {
            "element_type": "SOLID185",
            "global_element_size_mm": 5.0
        },
        "boundary_conditions": {
            "fixed_end": {"location": "X=0", "constraint": "All DOF = 0"}
        },
        "load": {
            "type": "concentrated_force",
            "location": {"X_mm": 100.0, "Y_mm": 10.0, "Z_mm": 5.0},
            "direction": "-Y",
            "magnitude_N": 100.0
        }
    },
    "results": {
        "load_point_displacement_mm": {
            "node_number": node_load,
            "UX": ux_load,
            "UY": uy_load,
            "UZ": uz_load,
            "USUM": usum_load
        },
        "maximum_displacement_mm": {
            "UX_MAX": ux_max,
            "UY_MAX": uy_max,
            "UZ_MAX": uz_max,
            "USUM_MAX": usum_max
        },
        "maximum_von_mises_stress_MPa": seqv_max,
        "fixed_end_reaction_force_N": {
            "FX": fx_react,
            "FY": fy_react,
            "FZ": fz_react
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
print(f"  数据库文件: {os.path.join(USER_DESKTOP, 'apdl_solid_beam.db')}")
print(f"  结果文件:   {os.path.join(USER_DESKTOP, 'apdl_solid_beam.rst')}")
print(f"  Ground Truth: {output_path}")
print("=" * 60)
