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
    jobname="apdl_transient_thermal",
    run_location=WORK_DIR,
    nproc=1,
    port=50180,
    override=True,
)

# ==================== 前处理 ====================
mapdl.prep7()

# 单元类型 SOLID70
mapdl.et(1, "SOLID70")

# 材料属性（mm-s-J-kg-°C）
mapdl.mp("KXX", 1, 0.05)
mapdl.mp("DENS", 1, 7.85e-6)
mapdl.mp("C", 1, 460)

# 几何：50 mm(X) × 20 mm(Y) × 20 mm(Z)
mapdl.block(0, 50, 0, 20, 0, 20)

# 网格：全局 2 mm
mapdl.esize(2)
mapdl.vmesh("ALL")

# 保存数据库
mapdl.save("apdl_transient_thermal", "db")

# ==================== 求解 ====================
mapdl.finish()
mapdl.slashsolu()

# 瞬态热分析
mapdl.antype("TRANS")
mapdl.timint("ON")

# 时间控制：总时间 10 s，固定步长 0.1 s
mapdl.time(10)
mapdl.autots("OFF")
mapdl.deltim(0.1)

# 初始温度 20 °C
mapdl.tunif(20)

# 边界条件：X=0 面温度 100 °C
mapdl.nsel("S", "LOC", "X", 0)
mapdl.d("ALL", "TEMP", 100)
mapdl.nsel("ALL")

# 求解（生成 .rth）
mapdl.solve()

mapdl.finish()
mapdl.save("apdl_transient_thermal", "db")

# ==================== 后处理 & 提取 Ground Truth (t = 10 s) ====================
mapdl.post1()
mapdl.set(1, "LAST")

# 1. X = 4 mm 处温度（中心线 Y=10, Z=10）
mapdl.nsel("S", "LOC", "X", 4)
mapdl.nsel("R", "LOC", "Y", 10)
mapdl.nsel("R", "LOC", "Z", 10)
node_4mm = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
t_4mm = float(mapdl.get_value("NODE", node_4mm, "TEMP"))
mapdl.nsel("ALL")

# 2. X = 6 mm 处温度
mapdl.nsel("S", "LOC", "X", 6)
mapdl.nsel("R", "LOC", "Y", 10)
mapdl.nsel("R", "LOC", "Z", 10)
node_6mm = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
t_6mm = float(mapdl.get_value("NODE", node_6mm, "TEMP"))
mapdl.nsel("ALL")

# 3. 最大 / 最小温度（NSORT 排序法）
mapdl.run("NSORT, TEMP, , 0, 1, ALL")
tmax = float(mapdl.get_value("SORT", 0, "MAX"))

mapdl.run("NSORT, TEMP, , 0, 1, ALL")
tmin = float(mapdl.get_value("SORT", 0, "MIN"))

# 4. X=0 面总热流
mapdl.nsel("S", "LOC", "X", 0)
mapdl.fsum()
heat_flow_x0 = float(mapdl.get_value("FSUM", 0, "ITEM", "HEAT"))
mapdl.nsel("ALL")

mapdl.exit()

# ==================== 复制文件到 Desktop 根目录 ====================
for ext in [".db", ".rth"]:
    src = os.path.join(WORK_DIR, f"apdl_transient_thermal{ext}")
    dst = os.path.join(USER_DESKTOP, f"apdl_transient_thermal{ext}")
    if os.path.exists(src):
        shutil.copy2(src, dst)

# ==================== 组装 JSON ====================
ground_truth = {
    "metadata": {
        "description": "ANSYS 3D Transient Thermal Conduction - Ground Truth",
        "software": "ANSYS Mechanical APDL Student v261",
        "units": "mm-s-J-kg-degC"
    },
    "input_parameters": {
        "geometry": {"length_x_mm": 50.0, "width_y_mm": 20.0, "height_z_mm": 20.0},
        "material": {
            "name": "Steel",
            "thermal_conductivity_W_per_mm_degC": 0.05,
            "specific_heat_J_per_kg_degC": 460.0,
            "density_kg_per_mm3": 7.85e-6
        },
        "mesh": {"element_type": "SOLID70", "global_element_size_mm": 2.0},
        "initial_condition": {"uniform_temperature_degC": 20.0},
        "boundary_conditions": {
            "x0_face": {"location": "X=0", "type": "prescribed_temperature", "value_degC": 100.0},
            "other_surfaces": {"type": "adiabatic"}
        },
        "analysis_settings": {"type": "transient_thermal", "total_time_s": 10.0, "time_step_s": 0.1}
    },
    "results": {
        "time_s": 10.0,
        "temperature_at_x4mm_degC": t_4mm,
        "temperature_at_x6mm_degC": t_6mm,
        "max_temperature_degC": tmax,
        "min_temperature_degC": tmin,
        "x0_boundary_total_heat_flow_W": heat_flow_x0
    }
}

output_path = os.path.join(USER_DESKTOP, "groundtruth.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(ground_truth, f, indent=2, ensure_ascii=False)

# ==================== 完成 ====================
print("\n" + "=" * 60)
print("  建模、求解、提取完成！")
print("=" * 60)
print(f"  数据库文件: {os.path.join(USER_DESKTOP, 'apdl_transient_thermal.db')}")
print(f"  结果文件:   {os.path.join(USER_DESKTOP, 'apdl_transient_thermal.rth')}")
print(f"  Ground Truth: {output_path}")
print("=" * 60)