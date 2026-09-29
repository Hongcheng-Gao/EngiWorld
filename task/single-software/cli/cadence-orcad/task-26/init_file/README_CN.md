[English](README.md) | [简体中文](README_CN.md)

导出 `HSD_FPGA_final.brd` 的真实 Allegro 过孔报告。

所需文件：

- `vialist_net.txt`
- `vialist_netlayer.txt`

典型流程：

1. 将 `HSD_FPGA_final.brd` 复制到可写工作目录。
2. 执行 `report -v vialist_net HSD_FPGA_final.brd vialist_net.txt`。
3. 执行 `report -v vialist_netlayer HSD_FPGA_final.brd vialist_netlayer.txt`。
4. 提交两个文件。
