<div align="center">

# 220kV 新能源汇集变电所电气一次部分初步设计

[![Project health](https://github.com/wzgig/220kv-renewable-energy-substation-design/actions/workflows/project-health.yml/badge.svg)](https://github.com/wzgig/220kv-renewable-energy-substation-design/actions/workflows/project-health.yml)

课程设计工程仓库：主接线方案、负荷与短路计算、设备选型、配电装置设计、CAD 图纸、说明书与答辩材料。

[正式报告](report/README.md) · [交付说明](deliverables/README.md) · [执行提示词](docs/EXECUTION_PROMPT.md) · [假设台账](docs/DESIGN_ASSUMPTIONS_REGISTER.md) · [手绘指南](docs/HAND_DRAWING_GUIDE.md) · [总体规划](docs/MASTER_PLAN.md) · [接线基线](docs/MAIN_SCHEME_BASELINE.md) · [设备预筛](docs/EQUIPMENT_SELECTION_BASELINE.md) · [设计输入](data/design_inputs.yaml) · [标准台账](docs/STANDARDS_REGISTER.md) · [需求追踪](docs/REQUIREMENTS_TRACEABILITY.md) · [CAD 工作流](docs/CAD_WORKFLOW.md) · [项目日志](PROJECT_LOG.md)

</div>

> [!IMPORTANT]
> 当前候选树只保留原创且已脱敏的成果。任务书原件、课程讲义、教材手册、他人设计书、参考 DWG、手稿照片和带个人元数据的文件均保留在本地私有材料区；既有公开历史中的旧 DWG 与身份记录需经用户确认后统一清理。

## 项目目标

完成一座 220/35/10kV 新能源汇集变电所的电气一次部分初步设计，形成可复核、可编辑、可打印和可答辩的完整交付物。当前任务书对应第 5 组，主变初始方案为 2×180MVA。

| 设计项 | 已确认输入 |
| --- | --- |
| 电压等级 | 220/35/10kV，另设 0.4kV 所用电系统 |
| 主变压器 | 2×180MVA、220/35kV双绕组 |
| 220kV 出线 | 2 回，预留 1 回；LGJ-400/50 |
| 35kV 集电线路 | 12 回，预留 2 回；架空线与电缆混合 |
| 10kV 系统 | 2×31.5MVA T10；2×±12Mvar SVG；站用及辅助负荷 |
| 短路计算基准 | 100MVA；平均额定电压 230/37/10.5kV |
| 必交图纸 | 电气主接线简图、配电装置断面图、配电装置平面布置图 |

## 当前设计基线

| 项目 | 已冻结结论 |
| --- | --- |
| 主变容量 | 2×180MVA；正常负载率 77.857%；主变 N-1 需限发 35.780% |
| 10kV 电源与无功 | 2×31.5MVA T10；2×±12Mvar SVG |
| 220kV 送出回路 | 正常每回 367.780A；单回全送出职责 735.559A；41℃课程保守允许载流量 475.242A |
| 10kV 短路等级 | 单台 T10 条件性最大综合上限 15.638kA；两台健康 T10 并列属禁止方式，敏感性为 28.472kA |
| 正常运行方式 | 220/35/10kV 母联正常断开；0.4kV 母联正常闭合，一台所用变运行、另一台暗备用 |

这些数值是任务书缺项条件下的课程设计基线；教师明确口径、现行标准原文或厂家项目资料可以覆盖相应假设。

## 已形成的核心交付物

- 技术设计说明书：DOCX/PDF，20 页 A4。
- 技术设计计算书：DOCX/PDF，17 页 A4。
- 课程设计总结：DOCX/PDF，4 页 A4。
- 答辩汇报：PPTX/PDF，11 页 16:9。
- 答辩问题清单：DOCX/PDF，7 页 A4。
- 三张 A1 CAD 图：电气主接线简图、配电装置平面布置图、配电装置断面图，公开 DXF/PDF/PNG，并在本地生成可编辑 DWG。
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
- [x] 生成三张 A1 CAD 工程底图；公开 DXF/PDF/PNG，本地 DWG 通过 AutoCAD 原生 AUDIT，且通过 PDF/PNG 目检和 47 项阶段单元测试
- [x] 完成四份正式报告 DOCX/PDF，并通过隐私、可访问性、审阅残留和逐页视觉终审
- [x] 完成11页答辩 PPTX/PDF，通过逐页渲染、画布溢出和元数据复核
- [ ] 完成精确设备型号、完整动热稳定、CT/PT、导体母线和环境校验
- [x] 完成本轮当前树隐私扫描、51 项测试、64 项健康检查及 GitHub Actions 等价再生成核验
- [ ] 经确认后改写含旧身份/DWG 的公开历史，再提交、推送并核验 GitHub Actions 与远端一致性

## 本地验证状态

| 验证对象 | 已完成 | 尚待完成 |
| --- | --- | --- |
| 四份正式报告 | 20/17/4/7 页 A4 逐页终审 PASS；DOCX 隐私、可访问性和审阅残留检查 PASS | 若后续重新生成，需重做目录、PDF 和隐私闭环 |
| 11 页答辩汇报 | PPTX/PDF 逐页渲染、画布溢出、页数和元数据检查 PASS | 当前树发布检查已通过 |
| 三张 A1 CAD 图 | AutoCAD Core Console AUDIT、A1 PDF/PNG 目检与 CAD 生成阶段 47 项单元测试通过 | 以已核验的 PDF/PNG 为提交与手绘临摹底图 |
| 仓库发布 | 当前树隐私扫描、51 项测试、64 项健康检查及 CI 等价再生成均通过 | 公开历史改写授权、提交推送、GitHub Actions 和远端一致性确认 |

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
