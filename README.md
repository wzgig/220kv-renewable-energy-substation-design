<div align="center">

# 220kV 新能源汇集变电所电气一次部分初步设计

[![Project health](https://github.com/wzgig/220kv-renewable-energy-substation-design/actions/workflows/project-health.yml/badge.svg)](https://github.com/wzgig/220kv-renewable-energy-substation-design/actions/workflows/project-health.yml)

课程设计工程仓库：主接线方案、负荷与短路计算、设备选型、配电装置设计、CAD 图纸、说明书与答辩材料。

[正式报告](report/README.md) · [交付说明](deliverables/README.md) · [完整性复盘](docs/DESIGN_COMPLETENESS_AUDIT.md) · [执行提示词](docs/EXECUTION_PROMPT.md) · [假设台账](docs/DESIGN_ASSUMPTIONS_REGISTER.md) · [手绘指南](docs/HAND_DRAWING_GUIDE.md) · [总体规划](docs/MASTER_PLAN.md) · [接线基线](docs/MAIN_SCHEME_BASELINE.md) · [设备预筛](docs/EQUIPMENT_SELECTION_BASELINE.md) · [设计输入](data/design_inputs.yaml) · [标准台账](docs/STANDARDS_REGISTER.md) · [需求追踪](docs/REQUIREMENTS_TRACEABILITY.md) · [CAD 工作流](docs/CAD_WORKFLOW.md) · [项目日志](PROJECT_LOG.md)

</div>

> [!IMPORTANT]
> 当前公开树及 `main` 可达历史只保留原创且已脱敏的成果。任务书原件、课程讲义、教材手册、他人设计书、参考 DWG、手稿照片和带个人元数据的文件均保留在本地私有材料区；旧 DWG 与身份记录已通过历史重写从 `main` 可达历史移除，可编辑 DWG 仅在本地保留。

本仓库固定对应第5组。第7组“220kV城市负荷中心变电所”已建立[独立公开仓库](https://github.com/wzgig/220kv-city-load-center-substation-design)，两组只共享通用工作流程，不共享设计数据和成果文件。

## 项目目标

完成一座 220/35/10kV 新能源汇集变电所的电气一次部分初步设计，形成可复核、可编辑、可打印和可答辩的完整交付物。当前任务书对应第 5 组，主变初始方案为 2×180MVA。

| 设计项 | 已确认输入 |
| --- | --- |
| 电压等级 | 220/35/10kV，另设 0.4kV 所用电系统 |
| 主变压器 | 2×180MVA、220/35kV、YNd11、uk=14% |
| 220kV 出线 | 2 回，预留 1 回；LGJ-400/50 |
| 35kV 集电线路 | 12 回，预留 2 回；WA-1～4、WB-1～3 为架空线并配置入口MOA，PVA-1～2、PVB-1～2、ES-1 为电缆并配置零序CT |
| 10kV 系统 | 2×31.5MVA、35/10.5kV、YNd11、uk=8% 的 T10；2×±12Mvar SVG；站用及辅助负荷 |
| 所用电系统 | 2×200kVA、10/0.4kV、SCB14 干式、Dyn11、uk=4%；轮换暗备用 |
| 短路计算基准 | 100MVA；平均额定电压 230/37/10.5kV |
| CAD 图纸范围 | 三张必交图：主接线、配电装置断面、平面布置；一张增强详图：SEC-220-L1-01 L1 线路间隔断面详图 |

## 当前设计基线

| 项目 | 已冻结结论 |
| --- | --- |
| 主变容量 | 2×180MVA、220/35kV、YNd11、uk=14%；正常负载率 77.857%；主变 N-1 需限发 35.780% |
| 10kV 电源与无功 | 2×31.5MVA、35/10.5kV、YNd11、uk=8% 的 T10；2×±12Mvar SVG |
| 所用变 | 2×200kVA、SCB14、Dyn11、uk=4%；正常一台运行，另一台暗备用 |
| 220kV 送出与分段职责 | 正常每回 367.780A；单回全送出及分段事故转供课程持续职责均取 735.559A；41℃课程保守允许载流量 475.242A |
| 220kV 短路职责 | 分列4.033kA/10.266kA，分段条件闭合7.385kA/18.798kA（RMS/峰值，含新能源课程上界）；电网单独3.607/6.500kA不是最终控制职责 |
| 10kV 短路等级 | 单台 T10 条件性最大综合上限 15.638kA；两台健康 T10 并列属禁止方式，敏感性为 28.472kA |
| 正常运行方式 | 220kV分段断路器、35/10kV母联正常断开；0.4kV母联正常闭合，一台所用变运行、另一台暗备用 |
| 中性点接地 | 220kV 中性点经中性点 CT 直接接地；35kV为2×1000kVA ZN接地变+低电阻、400A/10s、R≈50.5Ω；10kV为2×200kVA、200A/10s、R≈28.9Ω |
| 接地源联锁 | 正常分列时每段1套；母联合闸前退出受电/故障段接地源，仅保留健康侧1套；禁止母联闭合且两套接地源并联；重新分列后恢复每段1套 |
| MOA/零序CT | 220/35/10kV分别采用YH10W-204/532、YH5WZ-51/134、YH5WZ-17/45；7回35kV架空入口设MOA，5回35kV电缆及10kV电缆/SVG回路设零序CT；TOV/能量和精确型号待专题 |

这些数值是任务书缺项条件下的课程设计基线；教师明确口径、现行标准原文或厂家项目资料可以覆盖相应假设。

## 已形成的核心交付物

- 技术设计说明书：DOCX/PDF，正式 PDF 25 页 A4。
- 技术设计计算书：DOCX/PDF，18 页 A4。
- 课程设计总结：DOCX/PDF，4 页 A4。
- 答辩汇报：PPTX/PDF，11 页 16:9。
- 答辩问题清单：DOCX/PDF，7 页 A4。
- CAD 图纸按“三张必交图 + 一张增强详图”组织，共四张 A1 图：SLD-01、LAY-220-01、SEC-220-01 和 SEC-220-L1-01；公开 DXF/PDF/PNG，并在本地生成可编辑 DWG。四图已完成统一语义校验、AutoCAD AUDIT、A1 PDF/PNG 导出和逐图目检。
- 可再生的计算数据、脚本和 CAD 数据源。

## 仓库结构

~~~text
calculations/   可复核的负荷、电流、短路和设备校验计算
data/           任务书参数与后续设备数据
deliverables/   最终交付说明；压缩包本身不进入 Git 历史
docs/           项目范围、总体计划、决策、追踪矩阵与发布边界
drawings/       CAD 标准、块库、源图、导出图和绘图脚本
report/         说明书、计算书、总结和答辩材料
scripts/        项目健康检查及后续自动化工具
materials-private/  本地私有资料，仅 README 进入公开仓库
~~~

## 当前进度

- [x] 完成 128 个文件、约 283MiB 资料的结构与公开风险审计
- [x] 提取并冻结本组任务书的核心参数与交付要求
- [x] 确认 AutoCAD Core Console、A1 打印和 PDF/PNG 复核环境可用
- [x] 建立公开/私有边界、仓库结构和持续同步规则
- [x] 建立负荷/变压器、无功、LGJ温度修正、短路和设备预筛的可重复计算
- [x] 完成主接线技术经济比较并冻结可推进基线
- [x] 建立现行标准、废止版本和原文复核门槛台账
- [x] 完成220/35/10kV三相短路、变流器课程上界和1.10s I²t预校核
- [x] 建立220/35/10kV设备职责注册表和额定值等级预筛
- [x] 完成制图前拓扑复核：补入两回35kV电源变间隔并修正0.4kV暗备用正常状态
- [x] 冻结2×±12Mvar SVG、2×31.5MVA T10、海拔/污秽/保护时间等课程假设
- [x] 生成三张必交 A1 CAD 工程底图；公开 DXF/PDF/PNG，本地 DWG 通过 AutoCAD 原生 AUDIT，且通过 PDF/PNG 目检和 47 项阶段单元测试
- [x] 生成第四张 SEC-220-L1-01 A1/1:50 线路间隔增强详图的 DXF/PDF/PNG
- [x] 对本轮四图集成结果统一重跑 AutoCAD AUDIT、PDF/PNG 目检与语义检查；四图均为0错误并通过语义一致性校验
- [x] 完成四份正式报告 DOCX/PDF，并通过隐私、可访问性、审阅残留和逐页视觉终审
- [x] 完成11页答辩 PPTX/PDF，通过逐页渲染、画布溢出和元数据复核
- [x] 补齐课程级CT/PT与零序CT、MOA、接地变/NGR和接地开关；220kV管母完成载流/热稳/简化弯曲/电晕，35/10kV母线完成载流/热稳，绝缘子/套管完成电压、LIWV和持续/短时/峰值检查
- [ ] 完成精确设备型号、完整二次负荷、厂家动热稳定/温升、TOV/能量、外绝缘和真实场址校验
- [x] 完成本轮当前树隐私扫描、62 项测试、68 项健康检查及 GitHub Actions 等价再生成核验
- [x] 经授权完成含旧身份/DWG 的公开历史改写和精确租约强推；可达历史、GitHub Actions、远端提交与本地工作树均已核验

## 本地验证状态

| 验证对象 | 已完成 | 尚待完成 |
| --- | --- | --- |
| 四份正式报告 | 正式 PDF 为 25/18/4/7 页 A4，DOCX 与 PDF 已逐页终审 PASS；隐私、可访问性和审阅残留检查 PASS | 若后续重新生成，需重做目录、PDF 和隐私闭环 |
| 11 页答辩汇报 | PPTX/PDF 逐页渲染、画布溢出、页数和元数据检查 PASS | 当前树发布检查已通过 |
| 四张 A1 CAD 图（3+1） | 四图均完成DXF语义一致性校验、AutoCAD原生AUDIT（0错误）、单页A1 PDF/PNG导出和逐图目检 | 厂家外形、真实场址和施工级净距仍由后续工程资料覆盖 |
| 仓库发布 | 当前树隐私扫描、62 项测试、68 项健康检查、四图再生成校验和公开历史治理均已通过 | 后续有效修改继续执行提交、推送、Actions 和远端一致性闭环 |

## 工作方式

每个有效修改批次都执行以下闭环：

1. 更新计算、文档或图纸源文件。
2. 更新 PROJECT_LOG.md 和相关决策/追踪状态。
3. 运行项目检查：

   ~~~powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/project_health_check.ps1
   ~~~

4. 使用 Conventional Commit 提交并推送到 main。
5. 核对 GitHub Actions、远端提交和工作区状态。

> [!NOTE]
> 任务书写明文档一般手写、图纸手绘。用户已确认CAD图作为完整工程底稿，最终按图手绘临摹；课程假设均可由教师或真实工程资料覆盖。

## 权利与资料边界

仓库目前不附开放源代码或内容许可证。第三方资料不在仓库中；后续若拆分原创脚本与原创图纸的授权，将分别处理，不能将第三方材料的权利扩展到本项目。
