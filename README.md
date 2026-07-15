<div align="center">

# 220kV 新能源汇集变电所电气一次部分初步设计

[![Project health](https://github.com/wzgig/220kv-renewable-energy-substation-design/actions/workflows/project-health.yml/badge.svg)](https://github.com/wzgig/220kv-renewable-energy-substation-design/actions/workflows/project-health.yml)

课程设计工程仓库：主接线方案、负荷与短路计算、设备选型、配电装置设计、CAD 图纸、说明书与答辩材料。

[总体规划](docs/MASTER_PLAN.md) · [接线基线](docs/MAIN_SCHEME_BASELINE.md) · [设计输入](data/design_inputs.yaml) · [标准台账](docs/STANDARDS_REGISTER.md) · [需求追踪](docs/REQUIREMENTS_TRACEABILITY.md) · [CAD 工作流](docs/CAD_WORKFLOW.md) · [项目日志](PROJECT_LOG.md)

</div>

> [!IMPORTANT]
> 本仓库只公开原创且已脱敏的成果。任务书原件、课程讲义、教材手册、他人设计书、参考 DWG、手稿照片和带个人元数据的文件均保留在本地私有材料区，不进入 Git 历史。

## 项目目标

完成一座 220/35/10kV 新能源汇集变电所的电气一次部分初步设计，形成可复核、可编辑、可打印和可答辩的完整交付物。当前任务书对应第 5 组，主变初始方案为 2×180MVA。

| 设计项 | 已确认输入 |
| --- | --- |
| 电压等级 | 220/35/10kV，另设 0.4kV 所用电系统 |
| 主变压器 | 拟采用 2×180MVA |
| 220kV 出线 | 2 回，预留 1 回；LGJ-400/50 |
| 35kV 集电线路 | 12 回，预留 2 回；架空线与电缆混合 |
| 10kV 系统 | 站用电、无功补偿及辅助系统电源 |
| 短路计算基准 | 100MVA；平均额定电压 230/37/10.5kV |
| 必交图纸 | 电气主接线简图、配电装置断面图、配电装置平面布置图 |

## 预期交付物

- 技术设计说明书
- 技术设计计算书
- 电气主接线简图
- 配电装置断面图
- 配电装置平面布置图
- 课程设计总结与答辩材料
- 可再生的计算数据、脚本和 CAD 源文件

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
- [x] 确认 AutoCAD Electrical 2026、核心控制台、COM 和打印环境可用
- [x] 建立公开/私有边界、仓库结构和持续同步规则
- [x] 建立负荷/变压器可重复计算、结果表和 9 项单元测试
- [x] 完成主接线技术经济比较并冻结可推进基线
- [x] 建立现行标准、废止版本和原文复核门槛台账
- [x] 完成负荷、主回路持续电流基础值以及 220/35kV 三相短路初算（全项目 17 项单元测试）
- [ ] 确认 10kV 无功补偿容量并完成 10kV 短路电流计算
- [ ] 完成设备选择、校验和配电装置型式确定
- [ ] 完成三类 CAD 图纸、说明书、计算书和答辩材料

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
> 任务书写明文档一般手写、图纸手绘。CAD 图将作为工程底稿、打印稿和手绘复核依据；是否可直接提交 CAD 输出，需尽早向指导教师确认。

## 权利与资料边界

仓库目前不附开放源代码或内容许可证。第三方资料不在仓库中；后续若拆分原创脚本与原创图纸的授权，将分别处理，不能将第三方材料的权利扩展到本项目。
