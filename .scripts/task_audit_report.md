# Engiworld Task 配置 QA 审计报告

扫描根目录: `D:\research\project-engiworld\Engiworld\task` | task JSON 数: **986** | 格式异常: **0**

## 1. 总览统计

| 指标 | 数量 |
|---|---:|
| 总 task 数 | 986 |
| 路径对齐 ✅ | 341 |
| 路径不对齐 ❌ | 6 |
| 路径未声明 ⚠️ | 639 |
| 软件能完成 ✅ | 958 |
| 软件不能完成 ❌ | 0 |
| 能完成歧义 ⚠️ | 28 |
| 禁码 + eval 一致 ✅ | 76 |
| 禁码但 eval 缺失 ❌ | 200 |
| instruction 未禁码 ⚪ | 710 |
| 格式异常 JSON | 0 |

## 2. 逐 task 明细（精简：仅路径❌/可行性❌/禁码❌/⚠️路径）

| task id | 软件 | 路径 | 能否完成 | 禁码 | eval查禁码 | 备注 |
|---|---|---|---|---|---|---|
| c-blender-task-01-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: GN Cable Sag. `/home/user/Desktop/scen |
| c-blender-task-02-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Simulation Zone Confetti. `/home/user/ |
| c-blender-task-03-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Menger Sponge via Geometry Nodes (Repe |
| c-blender-task-04-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Procedural Tree with LOD. `/home/user/ |
| c-blender-task-05-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Proximity Vertex Group. `/home/user/De |
| c-blender-task-06-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Field-Driven Instance Rotation. `/home |
| c-blender-task-07-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Heightmap to Terrain Mesh `/home/user/ |
| c-blender-task-08-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: CSV-Driven Brick Wall `/home/user/Desk |
| c-blender-task-09-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: bmesh Boolean Welder `/home/user/Deskt |
| c-blender-task-10-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Geometry Nodes Tree Built From Python  |
| c-blender-task-11-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: IK Chain + Driver Rigger `/home/user/D |
| c-blender-task-12-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Three-Point Studio Lighting `/home/use |
| c-blender-task-13-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Compositor multi-output: beauty + dept |
| c-blender-task-14-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: AOV output -> MultiLayer EXR. `/home/u |
| c-blender-task-15-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Compositor Glare (Fog Glow) vs raw. `/ |
| c-blender-task-16-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Normal Bake High → Low `/home/user/Des |
| c-blender-task-17-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: PBR Texture Set -> Shader Graph Wiring |
| c-blender-task-18-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: UV Pack + Bake Ambient Occlusion `/hom |
| c-blender-task-19-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Spine IK Bend `/home/user/Desktop/scen |
| c-blender-task-20-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: FK/IK Switch via Driver `/home/user/De |
| c-blender-task-21-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: BVH Retarget + Bake to Action `/home/u |
| c-blender-task-22-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Shape-key Smile Morph + Bone Driver `/ |
| c-blender-task-23-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Cloth Drape Alembic `/home/user/Deskto |
| c-blender-task-24-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Rigid Body Bake to Keyframes `/home/us |
| c-blender-task-25-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Procedural Wood Material `/home/user/D |
| c-blender-task-26-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Car Paint Shader (two-lobe BSDF) `/hom |
| c-blender-task-27-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Triplanar Projection `/home/user/Deskt |
| c-blender-task-28-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Rotate Middle Arm, Preserve End-Effect |
| c-blender-task-29-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Weight-Selective Bevel `/home/user/Des |
| c-blender-task-30-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Parametric Row of Through-Holes `/home |
| c-blender-task-31-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Retopology Target-Count Decimation `/h |
| c-blender-task-32-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Boolean Multi-Hole Plate `/home/user/D |
| c-blender-task-33-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: OBJ scale-and-axis cleanup `/home/user |
| c-blender-task-34-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: glTF 2.0 roundtrip with PBR materials  |
| c-blender-task-35-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: USD preview surface export `/home/user |
| c-blender-task-36-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Texture-Link Repair `/home/user/Deskto |
| c-blender-task-37-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Library Link + Override `/home/user/De |
| c-blender-task-38-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Append asset-library material `/home/u |
| c-blender-task-39-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Scan → Retopo → Unwrap → Bake → Render |
| c-blender-task-40-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: CSV -> Geometry Nodes -> Shader -> Ani |
| c-blender-task-41-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: BVH retarget -> FK/IK switch -> bake - |
| c-blender-task-42-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Broken Scene Repair `/home/user/Deskto |
| c-blender-task-43-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Camera Silhouette Optimization. `/home |
| c-blender-task-44-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Procedural city USD export. `/home/use |
| c-blender-task-45-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Non-Manifold Repair `/home/user/Deskto |
| c-blender-task-46-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Modifier-Order Bug `/home/user/Desktop |
| c-blender-task-47-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Broken Driver Expression `/home/user/D |
| c-blender-task-48-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Purge Orphan Datablocks `/home/user/De |
| c-blender-task-49-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Rename Armature Bones to Restore Skinn |
| c-blender-task-50-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Shader Colorspace Corruption `/home/us |
| c-bonsai-task-01-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-bonsai-task-02-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-bonsai-task-03-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-bonsai-task-04-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-bonsai-task-05-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-bonsai-task-06-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-bonsai-task-07-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-bonsai-task-08-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-bonsai-task-09-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-bonsai-task-10-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-bonsai-task-11-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-bonsai-task-12-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-bonsai-task-13-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-bonsai-task-14-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-bonsai-task-15-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-bonsai-task-16-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-bonsai-task-17-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-bonsai-task-18-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-bonsai-task-19-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-bonsai-task-20-ubuntu | bonsai | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-01-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-02-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-03-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-04-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-05-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-06-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-07-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-08-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-09-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-10-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-11-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-12-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-13-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-14-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-15-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-16-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-17-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-18-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-19-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-fenics-task-20-ubuntu | fenics | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-01-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-02-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-03-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-04-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-05-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-06-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-07-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-08-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-09-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-10-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-11-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-12-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-13-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-14-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-15-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-16-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-17-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-18-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-19-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-floris-task-20-ubuntu | floris | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-01-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-02-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-03-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-04-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-05-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-06-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-07-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-08-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-09-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-10-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-11-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-12-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-13-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-14-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-15-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-16-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-17-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-18-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-19-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-openfoam-task-20-ubuntu | openfoam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-01-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-02-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-03-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-04-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-05-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-06-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-07-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-08-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-09-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-10-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-11-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-12-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-13-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-14-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-15-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-16-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-17-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-18-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-19-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidcam-task-20-windows | solidcam | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| c-solidworks-task-01-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_021_thr |
| c-solidworks-task-02-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_022_hol |
| c-solidworks-task-03-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_023_cut |
| c-solidworks-task-04-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_024_bat |
| c-solidworks-task-05-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_025_imp |
| c-solidworks-task-06-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_026_int |
| c-solidworks-task-07-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_027_mas |
| c-solidworks-task-08-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_028_sma |
| c-solidworks-task-09-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_029_var |
| c-solidworks-task-10-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_030_spl |
| c-solidworks-task-11-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_031_rib |
| c-solidworks-task-12-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_032_dra |
| c-solidworks-task-13-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_033_mir |
| c-solidworks-task-14-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_034_pin |
| c-solidworks-task-15-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_035_fla |
| c-solidworks-task-16-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_036_mol |
| c-solidworks-task-17-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_037_rep |
| c-solidworks-task-18-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_038_bou |
| c-solidworks-task-19-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_039_thr |
| c-solidworks-task-20-windows | solidworks | ⚠️ | ✅ | 未禁止 | — | 有 Launch 表述但未给出可比对路径: Open C:\Users\User\Desktop\cli_040_ste |
| c-abaqus-windows | abaqus | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| v-altium-designer-windows | altium-designer | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| v-ansys-windows | ansys | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| v-archicad-windows | archicad | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| v-autocad-windows | autocad | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| c-blender-ubuntu | blender | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| c-bonsai-ubuntu | bonsai | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| c-brl-cad-ubuntu | brl-cad | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| v-cadence-orcad-windows | cadence-orcad | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| c-calculix-ubuntu | calculix | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| c-eagle-ubuntu | eagle | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| c-fenics-ubuntu | fenics | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| c-floris-ubuntu | floris | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| c-freecad-ubuntu | freecad | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| c-freecad-path-ubuntu | freecad-path | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| c-kicad-ubuntu | kicad | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| v-librecad-ubuntu | librecad | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| c-nx-cam-windows | nx-cam | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| c-openfast-ubuntu | openfast | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| c-openfoam-ubuntu | openfoam | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| c-openscad-ubuntu | openscad | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| c-openstudio-ubuntu | openstudio | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| v-revit-windows | revit | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| v-sketchup-windows | sketchup | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| v-solidcam-windows | solidcam | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| v-solidworks-windows | solidworks | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| v-solvespace-ubuntu | solvespace | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| v-zbrush-windows | zbrush | ⚠️ | ⚠️ | 未禁止 | — | instruction 中未声明启动路径; 缺少 eval.py |
| v-abaqus-task-01-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-abaqus-task-02-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-abaqus-task-03-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-abaqus-task-04-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-abaqus-task-05-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-abaqus-task-06-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-abaqus-task-07-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-abaqus-task-08-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-abaqus-task-09-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-abaqus-task-10-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-abaqus-task-11-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-abaqus-task-12-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-abaqus-task-13-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-abaqus-task-14-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-abaqus-task-15-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-abaqus-task-16-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-abaqus-task-17-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-abaqus-task-18-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-abaqus-task-19-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-abaqus-task-20-windows | abaqus | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-altium-designer-task-01-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-02-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-03-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-04-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-05-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-06-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-07-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-08-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-09-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-10-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-11-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-12-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-13-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-14-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-15-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-16-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-17-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-18-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-19-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-20-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-21-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-22-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-23-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-altium-designer-task-24-windows | altium-designer | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-ansys-task-01-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-ansys-task-02-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-ansys-task-03-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-ansys-task-04-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-ansys-task-05-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-ansys-task-06-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-ansys-task-07-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-ansys-task-08-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-ansys-task-09-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-ansys-task-10-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-ansys-task-11-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-ansys-task-12-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-ansys-task-13-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-ansys-task-14-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-ansys-task-15-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-ansys-task-16-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-ansys-task-17-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-ansys-task-18-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-ansys-task-19-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-ansys-task-20-windows | ansys | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-archicad-task-01-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-archicad-task-02-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-archicad-task-03-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-archicad-task-04-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-archicad-task-05-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-archicad-task-06-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-archicad-task-07-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-archicad-task-08-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-archicad-task-09-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-archicad-task-10-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-archicad-task-11-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-archicad-task-12-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-archicad-task-13-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-archicad-task-14-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-archicad-task-15-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-archicad-task-16-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-archicad-task-17-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-archicad-task-18-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-archicad-task-19-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-archicad-task-20-windows | archicad | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-autocad-task-01-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-autocad-task-02-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-autocad-task-03-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-autocad-task-04-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-autocad-task-05-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-autocad-task-06-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-autocad-task-07-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-autocad-task-08-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-autocad-task-09-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-autocad-task-10-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-autocad-task-11-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-autocad-task-12-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-autocad-task-13-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-autocad-task-14-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-autocad-task-15-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-autocad-task-16-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-autocad-task-17-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-autocad-task-18-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-autocad-task-19-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-autocad-task-20-windows | autocad | ⚠️ | ✅ | 已禁止 | 无 | instruction 中未声明启动路径 |
| v-blender-task-01-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-02-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-03-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-04-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-05-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-06-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-07-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-08-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-09-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-10-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-11-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-12-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-13-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-14-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-15-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-16-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-17-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-18-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-19-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-20-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-21-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-22-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-23-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-24-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-25-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-26-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-27-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-28-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-29-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-30-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-31-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-32-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-33-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-34-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-35-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-36-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-37-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-38-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-39-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-blender-task-40-ubuntu | blender | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-bonsai-task-01-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-bonsai-task-02-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-bonsai-task-03-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-bonsai-task-04-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-bonsai-task-05-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-bonsai-task-06-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-bonsai-task-07-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-bonsai-task-08-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-bonsai-task-09-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-bonsai-task-10-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-bonsai-task-11-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-bonsai-task-12-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-bonsai-task-13-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-bonsai-task-14-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-bonsai-task-15-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-bonsai-task-16-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-bonsai-task-17-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-bonsai-task-18-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-bonsai-task-19-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-bonsai-task-20-ubuntu | bonsai | ⚠️ | ✅ | 已禁止 | 有 | instruction 中未声明启动路径 |
| v-cadence-orcad-task-01-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-02-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-03-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-04-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-05-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-06-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-07-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-08-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-09-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-10-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-11-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-12-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-13-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-14-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-15-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-16-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-17-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-18-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-19-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-20-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-21-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-22-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-23-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-24-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-25-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-26-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-27-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-28-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-29-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-cadence-orcad-task-30-windows | cadence-orcad | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-eagle-task-01-ubuntu | eagle | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-eagle-task-02-ubuntu | eagle | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-eagle-task-03-ubuntu | eagle | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-eagle-task-04-ubuntu | eagle | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-eagle-task-05-ubuntu | eagle | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-eagle-task-06-ubuntu | eagle | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-eagle-task-07-ubuntu | eagle | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| v-eagle-task-08-ubuntu | eagle | ⚠️ | ✅ | 未禁止 | — | instruction 中未声明启动路径 |
| … | … | … | … | … | … | （另有 245 条，见完整 CSV） |

## 3. 问题清单

### 路径不对齐 (6)

- **v-revit-task-11-windows** (`task-v/revit/task-11/task-11.json`): Desktop 快捷方式 vs 标准 `C:\Program Files\Autodesk\Revit 2025\Revit.exe`
- **v-revit-task-12-windows** (`task-v/revit/task-12/task-12.json`): Desktop 快捷方式 vs 标准 `C:\Program Files\Autodesk\Revit 2025\Revit.exe`
- **v-revit-task-13-windows** (`task-v/revit/task-13/task-13.json`): Desktop 快捷方式 vs 标准 `C:\Program Files\Autodesk\Revit 2025\Revit.exe`
- **v-revit-task-14-windows** (`task-v/revit/task-14/task-14.json`): Desktop 快捷方式 vs 标准 `C:\Program Files\Autodesk\Revit 2025\Revit.exe`
- **v-revit-task-15-windows** (`task-v/revit/task-15/task-15.json`): Desktop 快捷方式 vs 标准 `C:\Program Files\Autodesk\Revit 2025\Revit.exe`
- **v-revit-task-16-windows** (`task-v/revit/task-16/task-16.json`): Desktop 快捷方式 vs 标准 `C:\Program Files\Autodesk\Revit 2025\Revit.exe`

### 禁码eval缺失 (200)

- **v-abaqus-task-01-windows** (`task-v/abaqus/task-01/task-01.json`): instruction 中未声明启动路径
- **v-abaqus-task-02-windows** (`task-v/abaqus/task-02/task-02.json`): instruction 中未声明启动路径
- **v-abaqus-task-03-windows** (`task-v/abaqus/task-03/task-03.json`): instruction 中未声明启动路径
- **v-abaqus-task-04-windows** (`task-v/abaqus/task-04/task-04.json`): instruction 中未声明启动路径
- **v-abaqus-task-05-windows** (`task-v/abaqus/task-05/task-05.json`): instruction 中未声明启动路径
- **v-abaqus-task-06-windows** (`task-v/abaqus/task-06/task-06.json`): instruction 中未声明启动路径
- **v-abaqus-task-07-windows** (`task-v/abaqus/task-07/task-07.json`): instruction 中未声明启动路径
- **v-abaqus-task-08-windows** (`task-v/abaqus/task-08/task-08.json`): instruction 中未声明启动路径
- **v-abaqus-task-09-windows** (`task-v/abaqus/task-09/task-09.json`): instruction 中未声明启动路径
- **v-abaqus-task-10-windows** (`task-v/abaqus/task-10/task-10.json`): instruction 中未声明启动路径
- **v-abaqus-task-11-windows** (`task-v/abaqus/task-11/task-11.json`): instruction 中未声明启动路径
- **v-abaqus-task-12-windows** (`task-v/abaqus/task-12/task-12.json`): instruction 中未声明启动路径
- **v-abaqus-task-13-windows** (`task-v/abaqus/task-13/task-13.json`): instruction 中未声明启动路径
- **v-abaqus-task-14-windows** (`task-v/abaqus/task-14/task-14.json`): instruction 中未声明启动路径
- **v-abaqus-task-15-windows** (`task-v/abaqus/task-15/task-15.json`): instruction 中未声明启动路径
- **v-abaqus-task-16-windows** (`task-v/abaqus/task-16/task-16.json`): instruction 中未声明启动路径
- **v-abaqus-task-17-windows** (`task-v/abaqus/task-17/task-17.json`): instruction 中未声明启动路径
- **v-abaqus-task-18-windows** (`task-v/abaqus/task-18/task-18.json`): instruction 中未声明启动路径
- **v-abaqus-task-19-windows** (`task-v/abaqus/task-19/task-19.json`): instruction 中未声明启动路径
- **v-abaqus-task-20-windows** (`task-v/abaqus/task-20/task-20.json`): instruction 中未声明启动路径
- **v-ansys-task-01-windows** (`task-v/ansys/task-01/task-01.json`): instruction 中未声明启动路径
- **v-ansys-task-02-windows** (`task-v/ansys/task-02/task-02.json`): instruction 中未声明启动路径
- **v-ansys-task-03-windows** (`task-v/ansys/task-03/task-03.json`): instruction 中未声明启动路径
- **v-ansys-task-04-windows** (`task-v/ansys/task-04/task-04.json`): instruction 中未声明启动路径
- **v-ansys-task-05-windows** (`task-v/ansys/task-05/task-05.json`): instruction 中未声明启动路径
- … 另有 175 项

## 4. 共性问题与全局建议

1. **Revit task-v (11–16) 等**：instruction 要求 Desktop 快捷方式启动，与标准 `Revit.exe` 路径不一致；建议在 instruction 末尾统一 `[Software] Launch ... Revit.exe` 或 eval 不依赖绝对路径。
2. **大量 task 无 `[Software]` 启动路径**（路径 ⚠️）：Linux/CLI 类（blender、freecad、fenics）instruction 未写 Launch；若 VM 靠 snapshot 预装，可接受；否则补 `[Software]` 块。
3. **GUI-only + eval**：Revit/Archicad/OpenStudio 等 task-v 已用 `GUI_BYPASS_*` 检测脚本绕过；禁码与 eval 一致。
4. **task-c AutoCAD 等**：instruction 已对齐 `acad.exe`；eval 用 ezdxf 验几何（非验 AutoCAD 签名）— 未禁止写码的 task 不属此项缺陷。
5. **占位 eval**：若 instruction 写 Recreate 复杂 DXF 而 eval 仅 1 polyline+1 text，应替换为真实几何校验或放宽 instruction。

### 修复模板

**instruction 补标准路径：**
```
[Software] Launch <App> with `C:\\...\\app.exe`.
```

**eval 补禁码检查（instruction 已 GUI-only 时）：**
```python
def _check_no_script_bypass(desktop: Path) -> bool:
    # 检测 desktop 上除 eval.py 外的 .py/.ps1 及 shell history 中的 deliverable 生成命令
    ...
```
