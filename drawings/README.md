# 图纸工作区

本目录保存本项目原创的 CAD 标准、块库、结构化绘图数据、源图和导出图。第三方参考 DWG 位于本地私有材料区，不进入仓库。

本项目按“三张必交图 + 一张增强详图”组织四张 CAD 图纸。

三张必交图纸：

1. 电气主接线简图；
2. 配电装置断面图；
3. 配电装置平面布置图。

一张增强详图：

4. 220kV I 段 L1 线路间隔断面详图，用于补足设备链、接地开关、基础和净距表达。

所有图纸共用一份设备表、间隔表和尺寸/净距数据。公开仓库以可再生 DXF 为编辑源，PDF/PNG 预览放在 exports/；AutoCAD 生成的 DWG 保留在本地并由 `.gitignore` 排除，避免公开机器写入的 LastAuthor 元数据。详细流程见 [CAD 工作流](../docs/CAD_WORKFLOW.md)。

## 四张工程底图范围

| 图号 | 图纸 | 图幅/比例 | 可再生源 | AutoCAD与预览 |
| --- | --- | --- | --- | --- |
| SLD-01 | 电气主接线简图 | A1/NTS | `data/single_line_layout.yaml`、`scripts/generate_single_line.py` | 公开 `source/single_line_a1.dxf`、`exports/single_line_a1.pdf/.png`；DWG 本地生成 |
| LAY-220-01 | 220kV户外AIS平面布置图 | A1/1:200 | `data/switchyard_layout.yaml`、`scripts/generate_switchyard_drawings.py` | 公开 `source/switchyard_plan_a1.dxf`、`exports/switchyard_plan_a1.pdf/.png`；DWG 本地生成 |
| SEC-220-01 | 220kV户外AIS典型间隔断面图 | A1/1:100 | 同上 | 公开 `source/switchyard_section_a1.dxf`、`exports/switchyard_section_a1.pdf/.png`；DWG 本地生成 |
| SEC-220-L1-01 | 220kV I段L1线路间隔断面详图 | A1/1:50 | `data/switchyard_layout.yaml`、线路间隔详图生成逻辑 | 公开 `source/switchyard_line_bay_detail_a1.dxf`、`exports/switchyard_line_bay_detail_a1.pdf/.png`；DWG 本地生成 |

平面图表达两段三相母线、正常断开的分段间隔、L1/L2、远期L3、T1/T2、母线PT/CVT、道路、主控楼和35/10kV配电楼。SEC-220-01 同页表达线路间隔A-A与主变间隔B-B，标注母线/构架标高、相间距、设备序列和课程净距表。SEC-220-L1-01 将线路设备链放大到 1:50，表达母线侧QS、QF、TA、线路侧QS+常开ES、CVT、MOA、出线构架、基础及接地连接；地下接地网只作接口示意，不虚构接地电阻、接触电压或跨步电压计算。

~~~powershell
.venv\Scripts\python.exe drawings\scripts\generate_single_line.py
.venv\Scripts\python.exe drawings\scripts\generate_switchyard_drawings.py
powershell -NoProfile -ExecutionPolicy Bypass -File drawings\scripts\export_all_drawings.ps1
pdftoppm -png -r 150 -singlefile drawings\exports\single_line_a1.pdf drawings\exports\single_line_a1
pdftoppm -png -r 150 -singlefile drawings\exports\switchyard_plan_a1.pdf drawings\exports\switchyard_plan_a1
pdftoppm -png -r 150 -singlefile drawings\exports\switchyard_section_a1.pdf drawings\exports\switchyard_section_a1
pdftoppm -png -r 150 -singlefile drawings\exports\switchyard_line_bay_detail_a1.pdf drawings\exports\switchyard_line_bay_detail_a1
~~~

`normalize_pdf.py` 会在规范化元数据时清除 AutoCAD 为 SHX 文字自动写入的 PDF 批注层；公开版四图必须保持单页横向 A1、`/Annots` 为 0，且规范化前后 PNG 像素哈希一致。

主接线图统一采用：主变2×180MVA、220/35kV、YNd11、uk=14%；T10 2×31.5MVA、35/10.5kV、YNd11、uk=8%；所用变2×200kVA、SCB14、Dyn11、uk=4%；SVG 2×±12Mvar。35kV每段采用1000kVA ZN接地变+低电阻，400A/10s、R≈50.5Ω；10kV每段采用200kVA，200A/10s、R≈28.9Ω。正常每段1套，母联合闸前退出受电/故障段接地源，只保留健康侧1套，禁止母联合闸且两套并联。7回35kV架空入口标MOA，5回35kV电缆及10kV电缆/SVG回路标ZCT。`R`表示预留；CT/PT完整二次负荷、ZCT窗口/负担、41℃厂家适配、MOA能量/TOV和真实场址资料仍由后续专题覆盖。

平断面图中的A1/A2/B1/B2/C/D来自课程第七章表7-2；14m典型间隔、4m相间距、9m母线标高、道路、建筑和设备外形均明确标为课程设计几何假设，不得当作施工放样尺寸。
