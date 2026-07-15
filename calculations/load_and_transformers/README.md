# 负荷与变压器计算模块

该模块直接读取 data/design_inputs.yaml，生成：

- 35kV、10kV 综合视在功率；
- 各类单回线路基础最大持续工作电流；
- 2×180MVA 主变正常负载率与 N-1 限发量；
- 220kV 出线均分电流基础值；
- 0.4kV 所用电连续/短时负荷统计和所用变初选；
- JSON、CSV 和 Markdown 结果文件。

运行：

~~~powershell
python -m calculations.load_and_transformers.calculate
python -m unittest discover -s tests -v
~~~

当前计算口径：

- 0.95 新能源同时出力系数只用于主变综合容量，不用于单回线路最大电流；
- 单回线路按该类最大负荷在回路间平均分配，并计 5% 线损；
- 主结果按乘 1.05 处理线损，同时保留除以 0.95 的敏感性值；
- 10kV 综合负荷暂计入主变总需求；
- 所用变初选的功率因数 0.80 为显式假设，最终设备选型前必须复核。
