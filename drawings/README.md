# 图纸工作区

本目录保存本项目原创的 CAD 标准、块库、结构化绘图数据、源图和导出图。第三方参考 DWG 位于本地私有材料区，不进入仓库。

三张必交图纸：

1. 电气主接线简图；
2. 配电装置断面图；
3. 配电装置平面布置图。

所有图纸共用一份设备表、间隔表和尺寸/净距数据。原创 DWG 放在 source/ 并使用 Git LFS；PDF/PNG 预览放在 exports/。详细流程见 [CAD 工作流](../docs/CAD_WORKFLOW.md)。

## 已生成的三张工程底图

| 图号 | 图纸 | 图幅/比例 | 可再生源 | AutoCAD与预览 |
| --- | --- | --- | --- | --- |
| SLD-01 | 电气主接线简图 | A1/NTS | `data/single_line_layout.yaml`、`scripts/generate_single_line.py` | `source/single_line_a1.dxf/.dwg`、`exports/single_line_a1.pdf/.png` |
| LAY-220-01 | 220kV户外AIS平面布置图 | A1/1:200 | `data/switchyard_layout.yaml`、`scripts/generate_switchyard_drawings.py` | `source/switchyard_plan_a1.dxf/.dwg`、`exports/switchyard_plan_a1.pdf/.png` |
| SEC-220-01 | 220kV户外AIS典型间隔断面图 | A1/1:100 | 同上 | `source/switchyard_section_a1.dxf/.dwg`、`exports/switchyard_section_a1.pdf/.png` |

平面图表达两段三相母线、正常断开的分段间隔、L1/L2、远期L3、T1/T2、母线PT/CVT、道路、主控楼和35/10kV配电楼。断面图同页表达线路间隔A-A与主变间隔B-B，标注母线/构架标高、相间距、设备序列和课程净距表。

~~~powershell
.venv\Scripts\python.exe drawings\scripts\generate_single_line.py
.venv\Scripts\python.exe drawings\scripts\generate_switchyard_drawings.py
powershell -NoProfile -ExecutionPolicy Bypass -File drawings\scripts\export_all_drawings.ps1
pdftoppm -png -r 150 -singlefile drawings\exports\switchyard_plan_a1.pdf drawings\exports\switchyard_plan_a1
pdftoppm -png -r 150 -singlefile drawings\exports\switchyard_section_a1.pdf drawings\exports\switchyard_section_a1
~~~

主接线图已将T10冻结为2×31.5MVA、SVG冻结为2×±12Mvar，220/35/10kV母联均按正常断开表达。`R`表示预留；设备精确型号、CT/PT二次参数、41℃厂家适配、谐波和真实场址资料仍由后续专题覆盖。

平断面图中的A1/A2/B1/B2/C/D来自课程第七章表7-2；14m典型间隔、4m相间距、9m母线标高、道路、建筑和设备外形均明确标为课程设计几何假设，不得当作施工放样尺寸。
