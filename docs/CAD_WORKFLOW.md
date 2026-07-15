# CAD 制图与自动化工作流

## 已确认环境

本机已具备 AutoCAD Electrical 2026、签名有效的 AutoCAD Core Console、GB A0-A4 图框、DWG To PDF 打印配置和黑白打印样式。Core Console 已实测完成 DXF 原生 AUDIT、2018 DWG 保存和 A1 PDF 打印。`acad.exe` 当前 Authenticode 状态为 `HashMismatch`，在安装完整性修复前不启动 GUI 或 GUI COM 自动化；当前用 Core Console 加 PDF 渲染目检完成安全闭环。

现有 17 个参考 DWG 仅作版式和布置理解。其中部分旧图引用本机缺失的第三方 SHX 字体，直接复用可能导致乱码和尺寸漂移，因此新图从统一标准与块库开始构建。

## 目录约定

~~~text
drawings/
├── standards/  图层、文字、标注、线宽、图框与打印标准
├── blocks/     一次设备与电气符号块
├── data/       拓扑、设备、间隔、坐标和净距参数
├── source/     原创 DXF/DWG；DWG 使用 Git LFS
├── scripts/    生成、校核、转换和批量打印脚本
└── exports/    PDF/PNG 预览与兼容版输出
~~~

## 技术路线

1. 用 YAML/CSV 保存主接线拓扑、设备表、间隔顺序、尺寸和安全净距。
2. 使用 Python ezdxf 参数化生成 ASCII DXF，保证源文件可再生。
3. 使用 AutoCAD Core Console 执行 SCR/AutoLISP 校核、转换和批量出图。
4. 使用项目 PowerShell 脚本调用签名有效的 Core Console，执行 AUDIT、保存 2018 DWG 并通过官方 PC3/CTB 打印。
5. 用 Poppler 将 PDF 渲染为 PNG，目检文字、线宽、图框、比例、标注和打印范围；GUI 目检在 `acad.exe` 完整性修复后补做。

Python 依赖统一写入根目录 `requirements.txt` 并安装到项目虚拟环境，不污染系统环境：ezdxf 用于 DXF 生成和语义审计，pypdf 用于规范化 AutoCAD PDF。当前不依赖 pywin32 或 GUI COM。

## 当前主接线产物

~~~text
drawings/data/single_line_layout.yaml
drawings/standards/single_line_standard.yaml
drawings/scripts/sld_symbols.py
drawings/scripts/generate_single_line.py
drawings/scripts/export_single_line.ps1
drawings/scripts/normalize_pdf.py
drawings/source/single_line_a1.dxf
drawings/source/single_line_a1.dwg
drawings/exports/single_line_a1.pdf
drawings/exports/single_line_a1.png
~~~

中文文字采用本机已验证的 `txt.shx + gbcbig.shx` 大字体组合，避免 Core Console 对 TTC 字体替换成问号。DXF 使用 R2018/AC1032、毫米单位、A1 横向 841×594 模型空间纸面坐标；DWG 由 Git LFS 管理。

## 制图顺序

### 1. 电气主接线简图

- 输入：最终主接线方案、主变方案、回路/母线/母联、CT/PT/避雷器配置。
- 重点：220、35、10、0.4kV 电压层次清晰；本期与预留回路区分；设备编号唯一。
- 验收：图中回路数与任务书、回路表、设备表完全一致。

### 2. 配电装置断面图

- 输入：典型间隔设备型号、外形尺寸、安全净距、支架和母线标高。
- 重点：剖切位置、设备中心线、相间/相地净距、基础与检修空间。
- 验收：所有尺寸有来源，不能从参考图按比例猜测。

### 3. 配电装置平面布置图

- 输入：间隔表、出线方向、道路、建筑/构架、设备坐标和断面参数。
- 重点：220kV 向西北出线，35kV 向东/向南，站内与备用电源方向合理；预留间隔清楚。
- 验收：平面与断面使用同一设备、间隔宽度、编号和标高体系。

## 图形标准草案

- 当前中文文字使用 AutoCAD 自带 `txt.shx + gbcbig.shx`，西文与数字使用兼容字体；后续 GUI 完整性恢复后可再比较宋体/仿宋打印效果。
- 不提交版权不明的第三方 SHX；避免外部参照和绝对路径。
- 图层至少区分：母线、一次设备、导线、符号、文字、尺寸、中心线、构筑物、道路、预留和图框。
- 黑白打印依赖线宽表达，不以屏幕颜色代替最终线宽。
- 原生文件保存为 2018 格式，并输出 PDF 与 PNG；2013 兼容版在最终提交前补做。

## CAD 质量检查

- 无缺失字体、代理对象、未绑定外部参照和不可解析路径；
- 图形范围正常，无远离原点的垃圾对象；
- 图层、块名、设备编号和属性命名稳定；
- 图框、比例、单位、线宽和打印区域正确；
- PDF 中无裁切、重叠、黑块、乱码或过细线条；
- DWG 由 Git LFS 管理，DXF/数据/脚本可重建关键图形。
