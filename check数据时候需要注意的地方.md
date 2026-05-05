**评测数据需要逐 task 检查的问题**

请按 task 逐个检查，不要批量套模板。每个 task 本质上独立，必须确认 `instruction`、`init_file`、`ground_truth`、`eval.py` 四者一致。

1. **检查 instruction 和 ground truth 是否一致**

   每个 task 先读 instruction，再打开 ground truth DXF 检查几何是否真的符合 instruction。

   重点看：

   - instruction 要几个孔，GT 是否就是几个孔
   - instruction 要什么形状，GT 是否真的是这个形状
   - instruction 要的尺寸、坐标、半径、直径是否和 GT 一致
   - instruction 没说的东西，GT 里是否偷偷多了要求

   典型错误：

   - instruction 写“开孔”，但 GT 里是 3 个固定孔
   - instruction 写 L-shaped bracket，但 GT 是矩形
   - instruction 写 slot，但 GT 是几个圆孔
   - instruction 没要求文字，但 GT 里有 `TEXT task-XX`

2. **检查 eval.py 是否对着 instruction 写，而不是对着 GT summary 写**

   `eval.py` 不能只是把 GT 的 entity summary 抄进去做 exact match。

   高风险写法：

   - 比较 `summarize_dxf(output) == DXF_SPECS[0]["summary"]`
   - 强制实体数量完全相等
   - 强制 layer 列表完全相等
   - 强制 TEXT 内容完全相等
   - 强制输出 DXF 和 GT 的结构一模一样

   正确做法：

   - eval 只检查 instruction 明确要求的必要条件
   - 例如要求 3 个孔，就检查 3 个孔的位置和直径
   - 要求外轮廓尺寸，就检查外轮廓几何
   - 要求 slot，就检查 slot 的长度、宽度、中心和 arc/line 结构
   - 不要因为模型多画了无害辅助线就直接 0 分，除非 instruction 明确禁止

3. **检查是否存在 hidden requirements**

   eval 里如果检查了 instruction 没写的内容，就必须二选一：

   - 把这个要求补进 instruction
   - 或者从 eval 里删掉这个检查

   常见 hidden requirements：

   - 必须有 `TEXT task-XX`
   - 必须有 `AUX` layer
   - 必须有 `CENTER` layer
   - 必须有固定数量的 `LINE/CIRCLE/LWPOLYLINE`
   - 必须用某种 DXF entity 表达，而不是等价几何表达
   - 必须文件里没有任何额外实体

4. **检查 init_file 是否真的有用**

   每个 `init_file` 应该和 task 有关系，不能是无关模板。

   需要确认：

   - seed 是否是当前 task 的合理起点
   - seed 是否会误导模型
   - instruction 是否说明要如何使用 seed
   - 如果任务是“基于 seed 修改”，seed 应该包含待修改的初始几何
   - 如果任务是“从零绘制”，就不要让 seed 变成干扰项

   典型修复方式：

   - 如果 instruction 说“import seed and modify”，seed 应该是缺少某些目标元素的初始图
   - 如果 seed 无意义，就改 instruction 为从零绘制，或者重做 seed

5. **每个 task 必须做三类自检**

   每个 task 修完后都要跑：

   - **GT 正例测试**：把 ground truth 放到 output 位置，`eval.py` 必须返回 `True`
   - **seed 负例测试**：把 init_file 改名成 final 输出，通常必须返回 `False`
   - **instruction 合规样例测试**：构造一个按 instruction 完成、但不含隐藏 TEXT/layer 的样例，应该返回 `True`

   如果 GT 能过，但 instruction 合规样例过不了，说明 evaluator 仍然对 GT 写死了。

6. **检查 task 之间是否被错误复制模板**

   批量生成任务时很容易出现 20 个 task 共用同一个矩形模板。

   需要检查：

   - 不同 task 的 GT 是否只是宽高/孔数略变
   - 不同 task 的 eval.py 是否只有 `DXF_SPECS` 不同
   - instruction 明明不同，但 GT/eval 结构高度相同
   - 文件里的 `TEXT task-XX` 是否只是模板残留

   如果发现这种情况，要逐 task 重做，不能批量改一个 summary。

7. **检查 instruction 是否足够明确**

   如果 evaluator 要检查具体数字，instruction 必须写清楚。

   需要明确：

   - 孔的数量
   - 孔的直径或半径
   - 孔心坐标
   - 外形尺寸
   - slot 的长度、宽度、中心
   - arc 的半径、圆心、方向
   - 是否要求 layer
   - 是否允许额外辅助线
   - 输出文件名和路径

   模糊句子要改掉，例如：

   - “请开下孔”不够，要写“添加 3 个直径 6 的孔，孔心分别在 ...”
   - “放在边界方向”不够，要写“放在 0°、90°、180° 方向”
   - “画一个支架”不够，要写清外轮廓尺寸和关键坐标

8. **检查 evaluator 的容差和几何等价性**

   CAD 输出可能有小数误差，不能要求完全相等。

   建议：

   - 坐标/尺寸用 tolerance，例如 `0.5` 或 `0.75`
   - 角度用 angle tolerance
   - 圆孔检查圆心和半径
   - 线段检查端点，允许方向反过来
   - arc/slot 检查几何含义，不要只检查实体数量

9. **检查输出文件要求是否一致**

   `instruction`、`task json evaluator`、`eval.py` 必须使用同一个 final 文件名。

   需要确认：

   - instruction 里写的输出文件名
   - `eval.py` 里读取的文件名
   - evaluator command 所在目录
   - postconfig 上传的 eval 文件路径

10. **每个 task 最终要留下简短修复记录**

   建议每个 task 记录：

   - instruction 要求
   - GT 实际包含什么
   - eval.py 检查什么
   - GT 是否能过
   - seed 是否不能误过
   - 是否存在剩余歧义

一句话标准：

> evaluator 应该评估“是否完成 instruction”，而不是评估“是否复刻 ground truth 文件结构”。如果 instruction 没写，eval 就不应该判；如果 eval 必须判，instruction 就必须写清楚。