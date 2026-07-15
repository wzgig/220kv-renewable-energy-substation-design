# 图纸工作区

本目录保存本项目原创的 CAD 标准、块库、结构化绘图数据、源图和导出图。第三方参考 DWG 位于本地私有材料区，不进入仓库。

三张必交图纸：

1. 电气主接线简图；
2. 配电装置断面图；
3. 配电装置平面布置图。

所有图纸共用一份设备表、间隔表和尺寸/净距数据。原创 DWG 放在 source/ 并使用 Git LFS；PDF/PNG 预览放在 exports/。详细流程见 [CAD 工作流](../docs/CAD_WORKFLOW.md)。

## 已生成的主接线工程底图

- `data/single_line_layout.yaml`：A1图幅、母线、间隔、坐标和运行状态；
- `standards/single_line_standard.yaml`：图层、线宽、线型、字体和字高；
- `source/single_line_a1.dxf`：可由脚本再生的R2018文本源图；
- `source/single_line_a1.dwg`：经签名有效的AutoCAD Core Console执行AUDIT后保存的2018原生DWG；
- `exports/single_line_a1.pdf`、`exports/single_line_a1.png`：A1横向打印稿和预览图。

~~~powershell
.venv\Scripts\python.exe drawings\scripts\generate_single_line.py
powershell -NoProfile -ExecutionPolicy Bypass -File drawings\scripts\export_single_line.ps1
.venv\Scripts\python.exe drawings\scripts\normalize_pdf.py
pdftoppm -png -r 150 -singlefile drawings\exports\single_line_a1.pdf drawings\exports\single_line_a1
~~~

图中`P`为暂定、`R`为预留、`NO`为正常断开。10kV无功容量、T10容量、系统并列许可、CT/PT精确参数和设备最终型号未确认前，图纸保持工程底图状态，不作为最终定型图。
