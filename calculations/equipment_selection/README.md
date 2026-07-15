# 主要电气设备预筛选模块

该模块把设备选择拆成三个层次：

1. 从现有负荷、持续电流、短路结果和主接线基线生成回路职责；
2. 用 `data/equipment_selection.yaml` 管理场景、回路组和候选分配；
3. 用 `data/equipment_catalog.yaml` 管理候选额定值及证据状态。

运行：

~~~powershell
python -m calculations.load_and_transformers.calculate
python -m calculations.short_circuit.calculate
python -m calculations.equipment_selection.calculate
python -m unittest discover -s tests -v
~~~

当前输出是“额定值等级预筛选”，不是最终型号结论。任何缺失值都会传播为 `pending`，不会被当成零、跳过或自动通过。

当前可以自动完成：

- 220kV线路N-1、主变高低压侧和35kV各类馈线持续电流职责；
- 35kV两段按实际馈线分配的电流复核；
- 220kV、35kV必选、条件性和禁止运行方式的短路场景分级；
- 候选额定电流、开断电流、关合/峰值和短时耐受电流的算术预筛。

当前必须保持待定：

- 最高系统电压、绝缘水平、海拔和污秽修正；
- 保护动作与断路器开断时间、短路等值热效应；
- 220kV新能源短路贡献及新能源峰值模型；
- 10kV无功补偿容量、电源变容量和母线短路电流；
- 厂家精确型号、当前样本、外形尺寸和41℃载流修正；
- 导体、母线、绝缘子、套管、CT/PT和避雷器的专项完整校验。
