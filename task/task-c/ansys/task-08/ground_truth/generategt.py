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
    jobname="apdl_thermal_stress",
    run_location=WORK_DIR,
    nproc=1,
    port=50240,
    override=True,
)

# ==================== 前处理 ====================
mapdl.prep7()

# 单元类型 SOLID185
mapdl.et(1, "SOLID185")

# 材料：钢（mm-N-MPa），含热膨胀系数
mapdl.mp("EX", 1, 210000)
mapdl.mp("PRXY", 1, 0.3)
mapdl.mp("ALPX", 1, 1.5e-5)

# 几何：100 mm(X) × 10 mm(Y) × 10 mm(Z)
mapdl.block(0, 100, 0, 10, 0, 10)

# 网格：全局 5 mm
mapdl.esize(5)
mapdl.vmesh("ALL")

# 保存数据库
mapdl.save("apdl_thermal_stress", "db")

# ==================== 求解 ====================
mapdl.finish()
mapdl.slashsolu()
mapdl.antype("STATIC")

# 热条件：参考温度 20 °C，均匀体温度 100 °C
mapdl.tref(20)
mapdl.bfe("ALL", "TEMP", "", 100)

# 结构约束：两端 X=0 和 X=100 约束 UX=0（限制轴向膨胀）
mapdl.nsel("S", "LOC", "X", 0)
mapdl.d("ALL", "UX", 0)
mapdl.nsel("ALL")

mapdl.nsel("S", "LOC", "X", 100)
mapdl.d("ALL", "UX", 0)
mapdl.nsel("ALL")

# 最小横向约束（消除刚体运动，不限制横向自由变形）：
# 点1 (0,0,0)：UY=0, UZ=0
mapdl.nsel("S", "LOC", "X", 0)
mapdl.nsel("R", "LOC", "Y", 0)
mapdl.nsel("R", "LOC", "Z", 0)
mapdl.d("ALL", "UY", 0)
mapdl.d("ALL", "UZ", 0)
mapdl.nsel("ALL")

# 点2 (0,10,0)：UZ=0（与点1形成 X=0 面上两点 UZ=0，消除绕 X/Y 转动）
mapdl.nsel("S", "LOC", "X", 0)
mapdl.nsel("R", "LOC", "Y", 10)
mapdl.nsel("R", "LOC", "Z", 0)
mapdl.d("ALL", "UZ", 0)
mapdl.nsel("ALL")

# 求解
mapdl.solve()

mapdl.finish()
mapdl.save("apdl_thermal_stress", "db")

# ==================== 后处理 & 提取 Ground Truth ====================
mapdl.post1()
mapdl.set(1, 1)

# 1. 中点 (50, 5, 5) 位移
mapdl.nsel("S", "LOC", "X", 50)
mapdl.nsel("R", "LOC", "Y", 5)
mapdl.nsel("R", "LOC", "Z", 5)
node_mid = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))

ux_mid = float(mapdl.get_value("NODE", node_mid, "U", "X"))
uy_mid = float(mapdl.get_value("NODE", node_mid, "U", "Y"))
uz_mid = float(mapdl.get_value("NODE", node_mid, "U", "Z"))
usum_mid = float(mapdl.get_value("NODE", node_mid, "U", "SUM"))
mapdl.nsel("ALL")

# 2. 轴向应力 SX 最大/最小值
mapdl.run("NSORT, S, X, 0, 1, ALL")
sx_max = float(mapdl.get_value("SORT", 0, "MAX"))
sx_min = float(mapdl.get_value("SORT", 0, "MIN"))

# 3. 最大等效应力
mapdl.run("NSORT, S, EQV, 0, 1, ALL")
seqv_max = float(mapdl.get_value("SORT", 0, "MAX"))

# 4. 固定端 X=0 反力
mapdl.nsel("S", "LOC", "X", 0)
mapdl.fsum()
fx_react = float(mapdl.get_value("FSUM", 0, "ITEM", "FX"))
mapdl.nsel("ALL")

mapdl.exit()

# ==================== 复制文件到 Desktop 根目录 ====================
for ext in [".db", ".rst"]:
    src = os.path.join(WORK_DIR, f"apdl_thermal_stress{ext}")
    dst = os.path.join(USER_DESKTOP, f"apdl_thermal_stress{ext}")
    if os.path.exists(src):
        shutil.copy2(src, dst)

# ==================== 组装 JSON ====================
ground_truth = {
    "metadata": {
        "description": "ANSYS Thermal-Stress Bar - Ground Truth",
        "software": "ANSYS Mechanical APDL Student v261",
        "units": "mm-N-MPa-degC"
    },
    "input_parameters": {
        "geometry": {
            "length_x_mm": 100.0,
            "width_y_mm": 10.0,
            "height_z_mm": 10.0
        },
        "material": {
            "name": "Steel",
            "youngs_modulus_MPa": 210000.0,
            "poissons_ratio": 0.3,
            "thermal_expansion_coefficient_per_degC": 1.5e-5
        },
        "mesh": {
            "element_type": "SOLID185",
            "global_element_size_mm": 5.0
        },
        "thermal_condition": {
            "reference_temperature_degC": 20.0,
            "uniform_body_temperature_degC": 100.0
        },
        "boundary_conditions": {
            "axial_restraint": {"locations": ["X=0", "X=100"], "UX": 0},
            "rigid_body_constraints": [
                {"location": "(0,0,0)", "UY": 0, "UZ": 0},
                {"location": "(0,10,0)", "UZ": 0}
            ]
        }
    },
    "results": {
        "midpoint_displacement_mm": {
            "node_number": node_mid,
            "UX": ux_mid,
            "UY": uy_mid,
            "UZ": uz_mid,
            "USUM": usum_mid
        },
        "axial_stress_SX_MPa": {
            "SX_MAX": sx_max,
            "SX_MIN": sx_min
        },
        "maximum_von_mises_stress_MPa": seqv_max,
        "fixed_end_reaction_force_N": {
            "FX": fx_react
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
print(f"  数据库文件: {os.path.join(USER_DESKTOP, 'apdl_thermal_stress.db')}")
print(f"  结果文件:   {os.path.join(USER_DESKTOP, 'apdl_thermal_stress.rst')}")
print(f"  Ground Truth: {output_path}")
print("=" * 60)
