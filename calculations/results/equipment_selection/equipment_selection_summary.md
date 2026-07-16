# 主要电气设备与课程设计专项校核

本文件由脚本生成。开关设备完成额定值等级预筛；母线、避雷器、CT/PT、ZCT、绝缘子/套管、接地开关及35/10kV接地变压器+中性点电阻设备包完成课程级选择与校核。所有厂家订货型号和施工参数仍保持待定。

- 数值预筛选总状态：`provisional_pass`
- 最终选型总状态：`pending`
- 课程专项预校核状态：`provisional_pass`；最终工程状态：`pending`
- 主回路热稳定统一按C=87、t=1.10s进行课程预校核；接地电阻按限定单相接地电流10s职责计算。精确型号、厂家温升、保护配合、接地与绝缘配合研究仍保持待定，不按零或自动通过处理。

## 回路负荷职责

| 回路组 | 成员 | 最大持续工作电流/A | 来源/状态 |
| --- | --- | ---: | --- |
| 220-line-bays | L1, L2, L3-reserved | 735.559 | outgoing_220kv.single_circuit_contingency_current_a / known |
| 220-transformer-bays | T1-HV, T2-HV | 495.996 | main_transformer.rated_current_with_1_05_margin_a.220kv / known |
| 220-bus-section | 220-BS | 735.559 | conservative_equal_to_outgoing_220kv.single_circuit_contingency_current_a / known_conservative |
| 35-transformer-incomers | T1-LV, T2-LV | 3117.691 | main_transformer.rated_current_with_1_05_margin_a.35kv / known |
| 35-bus-I | 35kV-I | 2230.732 | baseline_feeder_allocation.35kV-I / known |
| 35-bus-II | 35kV-II | 2404.371 | baseline_feeder_allocation.35kV-II / known |
| 35-bus-tie | 35-BT | 3117.691 | main_transformer.rated_current_with_1_05_margin_a.35kv / known |
| 35-aux-transformer-feeders | T10-1-HV, T10-2-HV | 545.596 | auxiliary_transformer.rated_current_with_1_05_margin_a.35kv / known |
| 35-grounding-transformer-feeders | GT35-I, GT35-II | 400.000 | grounding_package_35kv_fault_current_course_feeder_target / known_course_target |
| 35-feeder-wind-A | WA-1, WA-2, WA-3, WA-4 | 364.642 | load_35kv.items.wind_farm_A.per_circuit_current_a / known |
| 35-feeder-wind-B | WB-1, WB-2, WB-3 | 364.642 | load_35kv.items.wind_farm_B.per_circuit_current_a / known |
| 35-feeder-pv-A | PVA-1, PVA-2 | 530.220 | load_35kv.items.pv_plant_A.per_circuit_current_a / known |
| 35-feeder-pv-B | PVB-1, PVB-2 | 353.480 | load_35kv.items.pv_plant_B.per_circuit_current_a / known |
| 35-feeder-storage | ES-1 | 546.963 | load_35kv.items.energy_storage.per_circuit_current_a / known |
| 10-load-station-service-backup | station_service_backup | 57.056 | load_10kv.items.station_service_backup.per_circuit_current_a / known |
| 10-transformer-incomers | T10-1-IN, T10-2-IN | 1909.586 | auxiliary_transformer.rated_current_with_1_05_margin_a.10kv_equipment_basis / known |
| 10-bus-tie | 10-BT | 1909.586 | auxiliary_transformer.rated_current_with_1_05_margin_a.10kv_equipment_basis / known |
| 10-grounding-transformer-feeders | GT10-I, GT10-II | 200.000 | grounding_package_10kv_fault_current_course_feeder_target / known_course_target |
| 10-svg-feeders | SVG-1, SVG-2 | 692.820 | reactive_compensation.svg_rated_current_a.10_5kv_each_with_1_05_margin / known |
| 10-load-reactive-and-cooling | reactive_compensation_and_cooling | 42.792 | load_10kv.items.reactive_compensation_and_cooling.per_circuit_current_a / known |
| 10-load-control-and-monitoring | control_communications_and_monitoring | 26.943 | load_10kv.items.control_communications_and_monitoring.per_circuit_current_a / known |

## 短路职责场景

| 电压级 | 必选运行方式RMS/kA | 条件性预校核RMS/kA | 禁止方式仅提示/kA | 峰值预校核/kA | 完整性 |
| --- | ---: | ---: | ---: | ---: | --- |
| 220_bus | 4.033 | 7.385 | 待定 | 18.798 | course_model_complete_exact_converter_model_pending |
| 35_bus | 13.265 | 16.291 | 25.694 | 41.470 | known_with_incomplete_peak_scope |
| 10_bus | 14.492 | 15.638 | 28.472 | 39.808 | course_model_complete_exact_svg_and_motor_model_pending |

## 候选额定值等级

| 选择项 | 回路组 | 候选等级 | 额定电流/A | 开断电流/kA | 峰值耐受/kA | 数值预筛 | 最终状态 |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| SEL-CB-220-LINE | 220-line-bays | TARGET-CB-220 | 3150 | 50.000 | 125.000 | provisional_pass | pending |
| SEL-DS-220-LINE | 220-line-bays | TARGET-DS-220 | 3150 | 待定 | 125.000 | provisional_pass | pending |
| SEL-CB-220-TX | 220-transformer-bays | TARGET-CB-220 | 3150 | 50.000 | 125.000 | provisional_pass | pending |
| SEL-DS-220-TX | 220-transformer-bays | TARGET-DS-220 | 3150 | 待定 | 125.000 | provisional_pass | pending |
| SEL-CB-220-BS | 220-bus-section | TARGET-CB-220 | 3150 | 50.000 | 125.000 | provisional_pass | pending |
| SEL-SWGR-35-IN | 35-transformer-incomers | TARGET-SWGR-35-3150 | 3150 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-35-BT | 35-bus-tie | TARGET-SWGR-35-3150 | 3150 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-35-WA | 35-feeder-wind-A | TARGET-SWGR-35-1250 | 1250 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-35-WB | 35-feeder-wind-B | TARGET-SWGR-35-1250 | 1250 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-35-PVA | 35-feeder-pv-A | TARGET-SWGR-35-1250 | 1250 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-35-PVB | 35-feeder-pv-B | TARGET-SWGR-35-1250 | 1250 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-35-ES | 35-feeder-storage | TARGET-SWGR-35-1250 | 1250 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-35-T10 | 35-aux-transformer-feeders | TARGET-SWGR-35-1250 | 1250 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-35-GT | 35-grounding-transformer-feeders | TARGET-SWGR-35-1250 | 1250 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-10-IN | 10-transformer-incomers | TARGET-SWGR-10-2500 | 2500 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-10-BT | 10-bus-tie | TARGET-SWGR-10-2500 | 2500 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-10-GT | 10-grounding-transformer-feeders | TARGET-SWGR-10-1250 | 1250 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-10-SVG | 10-svg-feeders | TARGET-SWGR-10-1250 | 1250 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-10-SSB | 10-load-station-service-backup | TARGET-SWGR-10-1250 | 1250 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-10-RC | 10-load-reactive-and-cooling | TARGET-SWGR-10-1250 | 1250 | 31.500 | 80.000 | provisional_pass | pending |
| SEL-SWGR-10-CM | 10-load-control-and-monitoring | TARGET-SWGR-10-1250 | 1250 | 31.500 | 80.000 | provisional_pass | pending |

## 课程设计专项闭环

> all supplementary rows are course target classes, not purchase specifications or construction release data

### 方案取舍

| 电压级 | 条件性短路职责/kA | 开关设备开断能力/kA | 限流电抗器结论 |
| --- | ---: | ---: | --- |
| v35 | 16.291 | 31.500 | 不设置（provisional_pass） |
| v10 | 15.638 | 31.500 | 不设置（provisional_pass） |

- 限流电抗器：35/10kV条件性短路水平低于31.5kA开关设备能力，课程方案不设置；reassess if the final grid, converter or parallel-operation study exceeds the selected 31.5kA switchgear rating。
- 高压熔断器：不作为主回路设备选型；only a manufacturer-coordinated primary protection component inside 35kV/10kV VT panels where required。

### 35/10kV接地源运行联锁

| 电压级 | 正常运行 | 母联合闸转供前 | 禁止状态 | 分段恢复 | 课程预校核 |
| --- | --- | --- | --- | --- | --- |
| v35 | 每段一套，共2套投入 | 先断开受电/故障段接地源，仅健康电源侧1套保持投入 | 母联合闸且两套接地源并联 | 母联断开后恢复每段一套，共2套 | provisional_pass |
| v10 | 每段一套，共2套投入 | 先断开受电/故障段接地源，仅健康电源侧1套保持投入 | 母联合闸且两套接地源并联 | 母联断开后恢复每段一套，共2套 | provisional_pass |

> 联锁原则：母联闭合许可必须同时确认受电/故障段接地源已断开，禁止两套低电阻接地源经母联并联。硬接点、软件逻辑、控制电源失效模式及保护跳闸矩阵仍由最终厂家设计。

### 接地变压器+中性点电阻课程设备包

| 设备包 | 每段配置 | Ig/A×s | R计算/选取Ω | 10s等效功率/MVA | 10倍短时过载最小容量/kVA | 选用/kVA | 馈线柜 | 相/中性CT目标 | 课程预校核 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| GRD-PKG-35 | 2套ZN中性点形成、每段一套 | 400×10 | 50.518/50.5 | 8.083 | 808.290 | 1000 | SEL-SWGR-35-GT | 600/1A / 400/1A | provisional_pass |
| GRD-PKG-10 | 2套ZN中性点形成、每段一套 | 200×10 | 28.868/28.9 | 1.155 | 115.470 | 200 | SEL-SWGR-10-GT | 300/1A / 200/1A | provisional_pass |

设备包包含接地变馈线开关柜、相CT与中性点CT课程目标、相/零序过流、母线零序过压、接地变与电阻温度/连续性监视及断路器失灵接口；零序阻抗、损耗温升、NGR结构、CT饱和和完整保护定值由同一最终厂家协调。

### 导体与母线

| 项目 | 方案 | 持续职责/A | 修正后载流量/A | K | 1.10s热稳定允许/kA | 课程预校核 | 最终工程状态 |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| BUS-220-TUBE-100-90 | 220kV aluminum-alloy tubular busbar, phi100/90mm | 735.559 | 1605.546 | 0.8028 | 123.785 | provisional_pass | pending_exact_conductor_and_support_manufacturer_data |
| BUS-35-3X125X10 | 35kV rectangular aluminum busbar, 3x125x10mm per phase | 3117.691 | 4194.000 | 1.0000 | 311.067 | provisional_pass | pending_exact_busbar_arrangement_and_manufacturer_temperature_rise_data |
| BUS-10-2X125X10 | 10kV rectangular aluminum busbar, 2x125x10mm per phase | 1909.586 | 3282.000 | 1.0000 | 207.378 | provisional_pass | pending_exact_busbar_arrangement_and_manufacturer_temperature_rise_data |

> BUS-35-3X125X10, BUS-10-2X125X10仅完成载流与热稳定课程预校核；支撑间距、共振、连接受力和机械动稳定明确保持pending，不作自动通过。

220kV管形母线附加课程校核：

| 项目 | 计算值 | 允许/要求值 | 结论 |
| --- | ---: | ---: | --- |
| 简化动稳定弯曲应力/MPa（校核相距3.0m≤布置4.0m） | 10.048 | 70.000 | provisional_pass |
| 简化电晕起始相电压/kV | 330.444 | 运行相电压 145.492 | provisional_pass |

### 金属氧化物避雷器

| 电压级 | 课程目标型号 | Uc/kV | 持续电压要求/kV | 持续裕度/kV | In/kA | 残压/kV | 设备LIWV/kV | LIWV/残压 | 课程预校核 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| v220 | YH10W-204/532 | 159.000 | 145.492 | 13.508 | 10.000 | 532.000 | 950.000 | 1.786 | provisional_pass |
| v35 | YH5WZ-51/134 | 40.800 | 40.500 | 0.300 | 5.000 | 134.000 | 185.000 | 1.381 | provisional_pass |
| v10 | YH5WZ-17/45 | 13.600 | 12.000 | 1.600 | 5.000 | 45.000 | 75.000 | 1.667 | provisional_pass |

> MOA-35-OHL-ENTRY：overhead_line_entry覆盖35-feeder-wind-A, 35-feeder-wind-B，回路WA-1, WA-2, WA-3, WA-4, WB-1, WB-2, WB-3；映射校核provisional_pass。

### CT课程选择与动热稳定预校核

| CT目标 | 覆盖回路 | 变比 | 持续职责/额定A | 短路职责/额定kA | 峰值职责/额定kA | 课程预校核 | 最终工程状态 |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| CT-220-LINE | 220-line-bays | 1000/1A | 735.559/1000 | 7.385/50.000×3s | 18.798/125.000 | provisional_pass | pending_burden_knee_point_and_exact_model |
| CT-220-TRANSFORMER | 220-transformer-bays | 600/1A | 495.996/600 | 7.385/50.000×3s | 18.798/125.000 | provisional_pass | pending_burden_knee_point_and_exact_model |
| CT-220-TRANSFORMER-NEUTRAL | 220-transformer-bays | 600/1A | 待定/600 | 待定/50.000×3s | 待定/125.000 | pending | pending_grounding_fault_study_burden_knee_point_and_exact_model |
| CT-220-BUS-SECTION | 220-bus-section | 1000/1A | 735.559/1000 | 7.385/50.000×3s | 18.798/125.000 | provisional_pass | pending_burden_knee_point_and_exact_model |
| CT-35-INCOMER-TIE | 35-transformer-incomers, 35-bus-tie | 4000/1A | 3117.691/4000 | 16.291/31.500×4s | 41.470/80.000 | provisional_pass | pending_burden_knee_point_and_exact_model |
| CT-35-FEEDER | 35-aux-transformer-feeders, 35-feeder-wind-A, 35-feeder-wind-B, 35-feeder-pv-A, 35-feeder-pv-B, 35-feeder-storage | 800/1A | 546.963/800 | 16.291/31.500×4s | 41.470/80.000 | provisional_pass | pending_burden_knee_point_and_exact_model |
| CT-10-INCOMER-TIE | 10-transformer-incomers, 10-bus-tie | 2500/1A | 1909.586/2500 | 15.638/31.500×4s | 39.808/80.000 | provisional_pass | pending_burden_knee_point_and_exact_model |
| CT-10-FEEDER-SVG | 10-svg-feeders, 10-load-station-service-backup, 10-load-reactive-and-cooling, 10-load-control-and-monitoring | 1000/1A | 692.820/1000 | 15.638/31.500×4s | 39.808/80.000 | provisional_pass | pending_burden_knee_point_and_exact_model |

> 主变220kV中性点CT的600/1A、PX+5P30仅为课程配置目标。其持续、短时和峰值职责必须按单相接地及零序电流专题确定，不能沿用主变相回路的三相短路电流，因此本表保持待定。

### 电缆馈线ZCT课程目标与接口校核

| ZCT目标 | 电压级 | 覆盖回路组 | 覆盖电缆回路 | 变比 | 接地电流目标/最小线性范围A | 课程预校核 | 最终工程状态 |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| ZCT-35-CABLE-FEEDERS | v35 | 35-feeder-pv-A, 35-feeder-pv-B, 35-feeder-storage | PVA-1, PVA-2, PVB-1, PVB-2, ES-1 | 100/1A | 400/400 | provisional_pass | pending_window_size_cable_shield_routing_burden_knee_point_and_exact_model |
| ZCT-10-CABLE-FEEDERS | v10 | 10-svg-feeders, 10-load-station-service-backup, 10-load-reactive-and-cooling, 10-load-control-and-monitoring | SVG-1, SVG-2, station_service_backup, reactive_compensation_and_cooling, control_communications_and_monitoring | 50/1A | 200/200 | provisional_pass | pending_window_size_cable_shield_routing_burden_knee_point_and_exact_model |

> 35kV电缆回路PVA-1/2、PVB-1/2、ES-1和10kV电缆馈线均已映射至ZCT；窗口尺寸、电缆屏蔽层接地回流路径、负担、拐点和厂家准确级保持pending。

### PT课程选择表

| PT目标 | 电压级 | 型式 | 一次额定 | 二次绕组 | 准确级目标 | 最终工程状态 |
| --- | --- | --- | --- | --- | --- | --- |
| PT-220-BUS | v220 | single-phase CVT set | 220/sqrt(3)kV | 100/sqrt(3)V measurement; 100/sqrt(3)V protection; 100/3V open-delta | 0.2, 3P | pending_burden_resonance_and_exact_model |
| PT-35-BUS | v35 | three single-phase inductive VT set | 35/sqrt(3)kV | 100/sqrt(3)V measurement; 100/sqrt(3)V protection; 100/3V open-delta | 0.5, 3P | pending_burden_ferroresonance_and_exact_model |
| PT-10-BUS | v10 | three single-phase inductive VT set | 10/sqrt(3)kV | 100/sqrt(3)V measurement; 100/sqrt(3)V protection; 100/3V open-delta | 0.5, 3P | pending_burden_ferroresonance_and_exact_model |

### 绝缘子与套管课程选择表

| 目标 | 应用 | Um/kV | LIWV/kV | 套管持续职责/额定A | 短时职责/额定kA×s | 峰值职责/额定kA | 课程预校核 | 最终工程状态 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| INS-BUSH-220 | outdoor post insulators and main-transformer 220kV bushings | 252.000 | 950.000 | 495.996/630 | 7.385/50.000×3 | 18.798/125.000 | provisional_pass | pending_creepage_mechanical_load_and_exact_model |
| INS-BUSH-35 | indoor supports and main-transformer or switchgear 35kV bushings | 40.500 | 185.000 | 3117.691/4000 | 16.291/31.500×4 | 41.470/80.000 | provisional_pass | pending_creepage_mechanical_load_and_exact_model |
| INS-BUSH-10 | indoor supports and T10 or switchgear 10kV bushings | 12.000 | 75.000 | 1909.586/2500 | 15.638/31.500×4 | 39.808/80.000 | provisional_pass | pending_creepage_mechanical_load_and_exact_model |

> 套管已完成Um、LIWV、持续电流及动热稳定课程预校核；绝缘子/套管爬电距离、端子与悬臂机械负荷、抗震和精确型号仍明确保持pending。

### 接地开关课程选择与动热稳定预校核

| 目标 | 覆盖回路 | Um/kV | 短时耐受 | 峰值耐受/kA | 课程预校核 | 特殊边界 |
| --- | --- | ---: | --- | ---: | --- | --- |
| ES-220-LINE | 220-line-bays | 252.000 | 50.000kA×3s | 125.000 | provisional_pass | line-side induced-current switching duty pending study |
| ES-35-SWITCHGEAR | 35-transformer-incomers, 35-bus-tie, 35-aux-transformer-feeders, 35-grounding-transformer-feeders, 35-feeder-wind-A, 35-feeder-wind-B, 35-feeder-pv-A, 35-feeder-pv-B, 35-feeder-storage | 40.500 | 31.500kA×4s | 80.000 | provisional_pass | integrated switchgear earthing switch course target |
| ES-10-SWITCHGEAR | 10-transformer-incomers, 10-bus-tie, 10-grounding-transformer-feeders, 10-svg-feeders, 10-load-station-service-backup, 10-load-reactive-and-cooling, 10-load-control-and-monitoring | 12.000 | 31.500kA×4s | 80.000 | provisional_pass | integrated switchgear earthing switch course target |

## 关键边界

- 220kV线路一回退出及分段回路均按735.559A保守持续职责闭环；最终潮流研究只能提高精度，不能将该课程预筛值重新置空。
- 35kV I、II段按实际馈线分配计算，不把4623.515A全站总电流或2311.758A简单均分值当成物理母线段职责。
- 35kV条件性预校核采用计入新能源RMS上界的16.291kA；两台健康主变低压侧并列25.694kA仅作禁止方式提示。
- 220kV新能源与10kV SVG贡献已按额定电流1.1～1.2倍的课程上界计入；固定k得到的综合峰值仍只作设备等级预筛。
- 热稳定采用后备保护1.00s与全开断0.08s向上取1.10s，通过I²t与候选设备额定短时耐受能力比较。
- 35kV 3150A进线/母联按室内最高40℃受控环境、K=1.0进行课程预校核；空调可靠性和厂家温升资料未冻结，因此最终型号仍为pending。
- 10kV进线及母联升级为2500A目标；采用2×±12Mvar SVG和2×31.5MVA T10，单电源条件性综合上限15.638kA，禁止的两台健康T10并列综合上限28.472kA。
- Φ100/90管形母线的温度修正、热稳定、简化动稳定和电晕校核，以及35/10kV矩形母线热稳定均为可再生课程计算；35/10kV母线机械动稳定、支撑共振、端部效应和厂家温升明确保持pending。
- 35kV每段采用ZN接地变+约50.5Ω电阻，400A/10s、等效功率约8.083MVA，按10倍短时过载最小约808kVA并选1000kVA；10kV相应为约28.9Ω、200A/10s、约1.155MVA、最小约115.5kVA并选200kVA。
- 正常运行35/10kV每段各一套接地源；母联转供前先断开受电/故障段接地源，仅健康电源侧一套投入，联锁禁止母联闭合且两套并联；分段恢复后各段一套。
- 35kV架空入口MOA及35/10kV电缆馈线ZCT已建立回路映射；避雷器能量、ZCT窗口/屏蔽层回流、CT负担饱和和精确型号仍待厂家复核。
- 避雷器型号、CT/PT/ZCT变比与准确级、绝缘子/套管绝缘水平和接地开关耐受等级是课程目标表，不是订货规范；接地、能量、负担、饱和、爬距、机械负荷和感应电流开合研究仍待完成。
