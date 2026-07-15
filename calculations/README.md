# 计算工作区

本目录用于保存可复核、可重复运行的设计计算，不把最终数值只写在说明书正文里。

计划文件：

~~~text
01_load_and_transformers/      负荷、主变与所用变选择
02_max_continuous_current/     各回路最大持续工作电流
03_short_circuit/              标幺网络与短路电流
04_equipment_selection/        断路器、隔离开关、母线、CT/PT 等
05_results/                    统一结果表，供报告和 CAD 引用
~~~

计算规则：

- 原始参数统一读取 data/design_inputs.yaml；
- 每个结果同时保存输入、公式、单位、中间值和最终设计取值；
- 关键结果采用独立复算或单元测试；
- 报告中的表格和 CAD 标注优先从统一结果文件生成；
- 不使用参考设计书中的旧题数值替代本题输入。
