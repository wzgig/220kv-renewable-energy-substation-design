# 计算工作区

本目录用于保存可复核、可重复运行的设计计算，不把最终数值只写在说明书正文里。

当前已建立：

~~~text
load_and_transformers/         负荷、持续电流与主变/所用变初算
short_circuit/                 220kV、35kV 标幺网络与短路电流初算
results/                       JSON、CSV 和 Markdown 统一结果
~~~

后续将增加：

~~~text
equipment_selection/           断路器、隔离开关、母线、CT/PT 等
~~~

计算规则：

- 原始参数统一读取 data/design_inputs.yaml；
- 每个结果同时保存输入、公式、单位、中间值和最终设计取值；
- 关键结果采用独立复算或单元测试；
- 报告中的表格和 CAD 标注优先从统一结果文件生成；
- 不使用参考设计书中的旧题数值替代本题输入。
