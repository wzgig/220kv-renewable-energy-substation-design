# 计算工作区

本目录用于保存可复核、可重复运行的设计计算，不把最终数值只写在说明书正文里。

当前已建立：

~~~text
load_and_transformers/         负荷、持续电流与主变/T10/所用变初算
short_circuit/                 220/35/10kV标幺网络、变流器课程上界与短路初算
equipment_selection/           回路职责、场景门控、设备额定值和一次设备专项预筛
results/                       JSON、CSV 和 Markdown 统一结果
~~~

设备模块当前已集成：

~~~text
conductor_and_bus_checks        LGJ、220kV管母及35/10kV矩形母线载流/热稳，220kV简化弯曲/电晕
instrument_transformers        三相CT、零序CT、PT/CVT的一次配置与课程职责
insulation_and_arresters        绝缘子/套管、MOA、Um、LIWV及电流/短时/峰值课程检查
grounding_packages              35/10kV接地变+低电阻设备包、馈线柜、CT目标及母联联锁
~~~

仍待工程专题闭合的内容包括：35/10kV母线机械与支撑受力、CT/PT/ZCT完整负担和暂态性能、套管爬距与机械破坏负荷、MOA TOV/能量、接地设备包厂家参数和接地故障/接地网计算。

计算规则：

- 原始参数统一读取 data/design_inputs.yaml；
- 每个结果同时保存输入、公式、单位、中间值和最终设计取值；
- 关键结果采用独立复算或单元测试；
- 报告中的表格和 CAD 标注优先从统一结果文件生成；
- 不使用参考设计书中的旧题数值替代本题输入。
