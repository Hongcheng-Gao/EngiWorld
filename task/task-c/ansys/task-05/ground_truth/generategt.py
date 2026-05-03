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
    jobname="apdl_fixed_beam_modal",
    run_location=WORK_DIR,
    nproc=1,
    port=50200,
    override=True,
)

# ==================== 前处理 ====================
mapdl.prep7()

# 单元类型 BEAM188
mapdl.et(1, "BEAM188")

# 材料属性（N-mm-s 单位制）
mapdl.mp("EX", 1, 210000)      # N/mm²
mapdl.mp("PRXY", 1, 0.3)
mapdl.mp("DENS", 1, 7.85e-9)   # tonne/mm³

# 矩形截面 10 mm × 10 mm
mapdl.sectype(1, "BEAM", "RECT")
mapdl.secdata(10, 10)

# 几何：梁轴线从 (0,0,0) 到 (500,0,0)
mapdl.k(1, 0, 0, 0)
mapdl.k(2, 500, 0, 0)
mapdl.l(1, 2)

# 网格：20 等分
mapdl.lesize("ALL", "", "", 20)
mapdl.lmesh("ALL")

# 保存数据库
mapdl.save("apdl_fixed_beam_modal", "db")

# ==================== 求解：模态分析 ====================
mapdl.finish()
mapdl.slashsolu()
mapdl.antype("MODAL")
mapdl.modopt("LANB", 3)   # Lanczos 法提取前 3 阶
mapdl.mxpand(3)           # 扩展前 3 阶（写入 .rst）

# 边界条件：两端固支（约束全部 6 个自由度）
mapdl.nsel("S", "LOC", "X", 0)
mapdl.d("ALL", "ALL", 0)
mapdl.nsel("ALL")

mapdl.nsel("S", "LOC", "X", 500)
mapdl.d("ALL", "ALL", 0)
mapdl.nsel("ALL")

# 求解
mapdl.solve()

mapdl.finish()
mapdl.save("apdl_fixed_beam_modal", "db")

# ==================== 后处理 & 提取 Ground Truth ====================
mapdl.post1()

# 1. 前 3 阶固有频率 (Hz)
freq1 = float(mapdl.get_value("MODE", 1, "FREQ"))
freq2 = float(mapdl.get_value("MODE", 2, "FREQ"))
freq3 = float(mapdl.get_value("MODE", 3, "FREQ"))

# 周期 = 1 / 频率（ANSYS *GET 不支持 PERIOD，需手动计算）
period1 = 1.0 / freq1 if freq1 != 0 else 0.0
period2 = 1.0 / freq2 if freq2 != 0 else 0.0
period3 = 1.0 / freq3 if freq3 != 0 else 0.0

# 2. 中点 (X=250) 各阶 Y 向振型幅值（归一化位移）
mapdl.set(1, 1)
mapdl.nsel("S", "LOC", "X", 250)
node_mid = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
uy_mode1 = float(mapdl.get_value("NODE", node_mid, "U", "Y"))
mapdl.nsel("ALL")

mapdl.set(1, 2)
mapdl.nsel("S", "LOC", "X", 250)
node_mid = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
uy_mode2 = float(mapdl.get_value("NODE", node_mid, "U", "Y"))
mapdl.nsel("ALL")

mapdl.set(1, 3)
mapdl.nsel("S", "LOC", "X", 250)
node_mid = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
uy_mode3 = float(mapdl.get_value("NODE", node_mid, "U", "Y"))
mapdl.nsel("ALL")

mapdl.exit()

# ==================== 复制文件到 Desktop 根目录 ====================
for ext in [".db", ".rst"]:
    src = os.path.join(WORK_DIR, f"apdl_fixed_beam_modal{ext}")
    dst = os.path.join(USER_DESKTOP, f"apdl_fixed_beam_modal{ext}")
    if os.path.exists(src):
        shutil.copy2(src, dst)

# ==================== 组装 JSON ====================
ground_truth = {
    "metadata": {
        "description": "ANSYS Fixed-Fixed Beam Modal Analysis - Ground Truth",
        "software": "ANSYS Mechanical APDL Student v261",
        "units": "N-mm-s (tonne, mm, s)"
    },
    "input_parameters": {
        "geometry": {
            "beam_length_mm": 500.0,
            "cross_section": {"width_mm": 10.0, "height_mm": 10.0}
        },
        "material": {
            "name": "Steel",
            "youngs_modulus_MPa": 210000.0,
            "poissons_ratio": 0.3,
            "density_tonne_per_mm3": 7.85e-9
        },
        "mesh": {
            "element_type": "BEAM188",
            "divisions": 20
        },
        "boundary_conditions": {
            "left_end": {"location": "X=0", "constraints": ["UX","UY","UZ","ROTX","ROTY","ROTZ"]},
            "right_end": {"location": "X=500", "constraints": ["UX","UY","UZ","ROTX","ROTY","ROTZ"]}
        },
        "analysis_settings": {
            "type": "modal",
            "method": "LANB",
            "modes_extracted": 3
        }
    },
    "results": {
        "natural_frequencies_Hz": {
            "mode_1": freq1,
            "mode_2": freq2,
            "mode_3": freq3
        },
        "periods_s": {
            "mode_1": period1,
            "mode_2": period2,
            "mode_3": period3
        },
        "midpoint_y_displacement_mode_shapes": {
            "mode_1": uy_mode1,
            "mode_2": uy_mode2,
            "mode_3": uy_mode3
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
print(f"  数据库文件: {os.path.join(USER_DESKTOP, 'apdl_fixed_beam_modal.db')}")
print(f"  结果文件:   {os.path.join(USER_DESKTOP, 'apdl_fixed_beam_modal.rst')}")
print(f"  Ground Truth: {output_path}")
print("=" * 60)
