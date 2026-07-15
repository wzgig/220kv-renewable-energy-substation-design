# 主要电气设备额定值预筛选

本文件由脚本生成。当前只完成额定值等级的条件化预筛选，不代表设备型号已经定型。

- 数值预筛选总状态：`pending`
- 最终选型总状态：`pending`
- 任务书要求的热稳定、动稳定、开断和环境校验中，缺失数据均保持待定，不按零或自动通过处理。

## 回路负荷职责

| 回路组 | 成员 | 最大持续工作电流/A | 来源/状态 |
| --- | --- | ---: | --- |
| 220-line-bays | L1, L2, L3-reserved | 735.559 | outgoing_220kv.single_circuit_contingency_current_a / known |
| 220-transformer-bays | T1-HV, T2-HV | 495.996 | main_transformer.rated_current_with_1_05_margin_a.220kv / known |
| 220-bus-section | 220-BS | 待定 | explicit_power_flow_and_bay_placement_required / pending_topology_flow |
| 35-transformer-incomers | T1-LV, T2-LV | 3117.691 | main_transformer.rated_current_with_1_05_margin_a.35kv / known |
| 35-bus-I | 35kV-I | 2230.732 | baseline_feeder_allocation.35kV-I / known |
| 35-bus-II | 35kV-II | 2404.371 | baseline_feeder_allocation.35kV-II / known |
| 35-bus-tie | 35-BT | 3117.691 | main_transformer.rated_current_with_1_05_margin_a.35kv / known |
| 35-feeder-wind-A | WA-1, WA-2, WA-3, WA-4 | 364.642 | load_35kv.items.wind_farm_A.per_circuit_current_a / known |
| 35-feeder-wind-B | WB-1, WB-2, WB-3 | 364.642 | load_35kv.items.wind_farm_B.per_circuit_current_a / known |
| 35-feeder-pv-A | PVA-1, PVA-2 | 530.220 | load_35kv.items.pv_plant_A.per_circuit_current_a / known |
| 35-feeder-pv-B | PVB-1, PVB-2 | 353.480 | load_35kv.items.pv_plant_B.per_circuit_current_a / known |
| 35-feeder-storage | ES-1 | 546.963 | load_35kv.items.energy_storage.per_circuit_current_a / known |
| 10-load-station-service-backup | station_service_backup | 57.056 | load_10kv.items.station_service_backup.per_circuit_current_a / known |
| 10-load-reactive-and-cooling | reactive_compensation_and_cooling | 42.792 | load_10kv.items.reactive_compensation_and_cooling.per_circuit_current_a / known |
| 10-load-control-and-monitoring | control_communications_and_monitoring | 26.943 | load_10kv.items.control_communications_and_monitoring.per_circuit_current_a / known |

## 短路职责场景

| 电压级 | 必选运行方式RMS/kA | 条件性预校核RMS/kA | 禁止方式仅提示/kA | 峰值预校核/kA | 完整性 |
| --- | ---: | ---: | ---: | ---: | --- |
| 220_bus | 3.607 | 6.500 | 待定 | 16.546 | known_with_incomplete_scope |
| 35_bus | 13.265 | 16.291 | 25.694 | 41.470 | known_with_incomplete_peak_scope |
| 10_bus | 待定 | 待定 | 待定 | 待定 | pending_input |

## 候选额定值等级

| 选择项 | 回路组 | 候选等级 | 额定电流/A | 开断电流/kA | 峰值耐受/kA | 数值预筛 | 最终状态 |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| SEL-CB-220-LINE | 220-line-bays | TARGET-CB-220 | 3150 | 50.000 | 125.000 | provisional_pass | pending |
| SEL-DS-220-LINE | 220-line-bays | TARGET-DS-220 | 3150 | 待定 | 125.000 | provisional_pass | pending |
| SEL-CB-220-TX | 220-transformer-bays | TARGET-CB-220 | 3150 | 50.000 | 125.000 | provisional_pass | pending |
| SEL-DS-220-TX | 220-transformer-bays | TARGET-DS-220 | 3150 | 待定 | 125.000 | provisional_pass | pending |
| SEL-CB-220-BS | 220-bus-section | TARGET-CB-220 | 3150 | 50.000 | 125.000 | pending | pending |
| SEL-SWGR-35-IN | 35-transformer-incomers | TARGET-SWGR-35-3150 | 3150 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-35-BT | 35-bus-tie | TARGET-SWGR-35-3150 | 3150 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-35-WA | 35-feeder-wind-A | TARGET-SWGR-35-1250 | 1250 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-35-WB | 35-feeder-wind-B | TARGET-SWGR-35-1250 | 1250 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-35-PVA | 35-feeder-pv-A | TARGET-SWGR-35-1250 | 1250 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-35-PVB | 35-feeder-pv-B | TARGET-SWGR-35-1250 | 1250 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-35-ES | 35-feeder-storage | TARGET-SWGR-35-1250 | 1250 | 31.500 | 80.000 | provisional_pass | pending |

## 关键边界

- 220kV线路一回退出时的持续电流735.559A用于线路间隔预筛；220kV分段回路潮流仍等待明确间隔布置和潮流方向。
- 35kV I、II段按实际馈线分配计算，不把4623.515A全站总电流或2311.758A简单均分值当成物理母线段职责。
- 35kV条件性预校核采用计入新能源RMS上界的16.291kA；两台健康主变低压侧并列25.694kA仅作禁止方式提示。
- 220kV故障缺新能源贡献；35kV峰值缺新能源动态模型；固定k得到的峰值只作课程敏感性预筛。
- 热稳定最终校验等待保护动作时间、断路器全开断时间、等值热效应和候选设备短时耐受持续时间。
- 海拔、污秽等级、41℃电流修正、厂家精确型号和图纸外形尺寸未确认，因此所有候选项保持pending。
- 10kV母线和主进线设备等待无功补偿Mvar及35/10.5kV电源变容量；当前仅保留三类已知负荷馈线电流。
