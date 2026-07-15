# 主要电气设备选择与校验基线

## 1. 当前结论

本阶段完成的是“回路职责 + 额定值等级预筛选”，不是厂家精确型号定型。所有目标等级均由脚本复核；凡缺少系统条件、保护时间、完整短路模型、环境修正或厂家页级证据的项目，状态保持 `pending`。

任务书要求的设备章至少覆盖：高压断路器、隔离开关、母线、绝缘子与穿墙套管、电流互感器、电压互感器、配电装置及主要设备结果总表。依据本地私有《本组任务书.pdf》第2、7、8页。

统一校验链为：

- 额定电压：设备额定电压等级不低于系统要求；
- 持续电流：额定电流或环境修正后允许电流不小于最大持续工作电流；
- 断路器开断：额定短路开断电流不小于触头分离时的短路全电流有效值；
- 关合与动稳定：额定关合电流、峰值耐受电流不小于短路峰值；
- 热稳定：设备允许的短时耐受热量不小于短路等值热效应；
- 环境：复核最高温度、海拔、污秽、安装位置及厂家特殊使用条件。

课程公式及边界核对自本地私有《发电电气部分-第六章-导体和电气设备的选择与原理.pdf》第3-10、80-83、92-94、133-151页。旧指导书中的历史型号、价格和例题数值均不作为本项目输入。

## 2. 已生成的回路职责

| 回路 | 最大持续工作电流 | 采用口径 |
| --- | ---: | --- |
| 220kV线路间隔 | 735.559A | 一回线路退出，另一回承担全部本期汇集负荷 |
| 主变220kV侧 | 495.996A | 180MVA额定电流乘课程1.05系数 |
| 主变35kV侧、35kV母联预筛 | 3117.691A | 180MVA额定电流乘课程1.05系数 |
| 35kV-I段实际馈线分配基础值 | 2230.732A | 按I段6回馈线逐回累加，不使用简单均分 |
| 35kV-II段实际馈线分配基础值 | 2404.371A | 按II段6回馈线逐回累加，不使用简单均分 |
| 35kV单回馈线最大值 | 546.963A | 储能电站单回，含5%线损，不重复叠加同时系数 |
| 35kV至T10-1/T10-2馈线 | pending | 取决于10kV无功补偿Mvar、启动条件和35/10.5kV电源变额定容量 |
| 10kV三类已知负荷馈线 | 57.056/42.792/26.943A | 仅用于负荷馈线电流职责，母线短路与主进线仍待定 |

220kV母线分段设备的持续潮流取决于间隔布置和潮流方向，当前明确标记为 `pending_topology_flow`，不把735.559A机械复制给所有母联设备。

## 3. 短路职责分级

| 场景 | RMS职责 | 峰值职责 | 用途 |
| --- | ---: | ---: | --- |
| 220kV分列必选方式 | 3.607kA，电网贡献 | 分列点电网峰值 | 正常分列方式最低必选职责 |
| 220kV分段闭合条件性方式 | 6.500kA，电网贡献 | 16.546kA，电网贡献 | 等待系统并列许可；作为条件性预校核 |
| 35kV分列必选方式 | 13.265kA，含新能源RMS上界 | 峰值模型未完整 | 正常允许方式 |
| 35kV上游分段闭合条件性方式 | 16.291kA，含新能源RMS上界 | 课程敏感性41.470kA | 当前额定值预筛控制场景 |
| 两台健康主变低压侧并列 | 25.694kA，含新能源RMS上界 | 课程敏感性65.406kA | 基线禁止，仅用于提示联锁与误操作风险 |

35kV课程敏感性峰值按固定k作用于保守RMS上界得到，只用于额定值预筛，不能替代现行标准下的R/X、直流分量和新能源动态模型。220kV故障的新能源贡献尚未建立，因此220kV开断与动稳定仍不是最终值。

## 4. 目标额定值等级

| 设备用途 | 目标等级 | 当前证据状态 | 结论 |
| --- | --- | --- | --- |
| 220kV户外SF6断路器 | 252kV、3150A、50kA开断、125kA关合/峰值、50kA/3s | 仅为目标等级；CHINT LW43-252官方页面证明252kV户外SF6活罐式家族存在，未公开核实所列电流组合 | 数值预筛通过，型号和参数待厂家样本 |
| 220kV隔离开关 | 252kV、3150A、125kA峰值、50kA/3s | 尚无精确厂家候选证据 | 只作目标等级，不得写成已选型号 |
| 35kV主变进线、母联开关柜 | 40.5kV、3150A、31.5kA、80kA峰值 | Siemens NXAirS官方页面证明最高3150A/31.5kA家族可得；峰值和持续时间待精确样本 | 原始电流余量仅32.309A，41℃修正未核实，保持待定 |
| 35kV馈线开关柜 | 40.5kV、1250A、31.5kA、80kA峰值、31.5kA/4s | CHINT KYN61-40.5(Z)官方目录第22页提供家族参数 | 家族级数值预筛通过，精确柜型和订单配置待定 |

官方可访问证据：

- [CHINT LW43-252官方产品页](https://www.chintglobal.com/global/en/products/power-transmission-and-distribution/transmission/lw43-252.html)
- [Hitachi Energy LTB E官方产品页](https://www.hitachienergy.com/products-and-solutions/high-voltage-switchgear-and-breakers/air-insulated-switchgear/live-tank-circuit-breaker-ltb-e-72-5-800-kv)
- [CHINT KYN61-40.5(Z)官方目录](https://www.chintglobal.com/content/dam/chint/global/product-center/power-transmission-and-distribution/distribution/mv-switchgear/mv-air-insulated-switchgear/kyn61-40-5(z)(630~3150)/catalog/KYN61-40.5(Z)-MV%20Air%20Insulated%20Switchgear-Catalog.pdf)
- [Siemens NXAirS官方页面](https://www.siemens.com/zh-cn/products/energy-systems/nxairs/)

目标等级与厂家家族证据分开管理。一个家族“最高可到某额定值”不能证明本项目所需组合已经形成精确订单型号。

## 5. CT/PT配置基线

- 220kV、35kV、10kV每段主母线配置电压互感器；220kV优先研究CVT，35kV采用单相电磁式VT组，10kV采用适合绝缘监视的电磁式VT方案。
- 凡装有断路器的回路原则上配置CT：220kV线路、主变和分段回路；35kV主变进线、母联、12回本期馈线、两回T10电源变馈线及必要预留；10kV主进线、母联和负荷/补偿回路。
- CT变比初步量级可由当前持续电流提出，但准确级、保护级、准确限值系数/暂态性能、二次额定电流、容量和电缆负荷必须等待保护与计量清册。
- PT/CVT变比、二次绕组、准确级、容量、剩余电压绕组和同期电压引出必须等待测量、保护、同期及自动装置需求表。

因此本阶段只冻结配置原则，不冻结CT/PT精确型号和二次参数。

已核验但尚未定型的220kV家族参考包括：[CHINT LB-35~275 CT](https://www.chintglobal.com/global/en/products/power-transmission-and-distribution/transmission/lb-35~275.html)、[CHINT LVB-35~275 CT](https://www.chintglobal.com/global/en/products/power-transmission-and-distribution/transmission/lvb-35~275.html)、[CHINT TYD-35~220 CVT](https://www.chintglobal.com/global/en/products/power-transmission-and-distribution/transmission/tyd-35~220.html)和[CHINT JDCF-66~220 VT](https://www.chintglobal.com/global/en/products/power-transmission-and-distribution/transmission/jdcf-66~220.html)。这些公开页面未提供本项目所需的完整变比、芯数、准确级、额定负荷和暂态保护参数，只能证明产品家族范围。

避雷器可得性参考为[CHINT YH10W家族](https://www.chintglobal.com/global/en/products/power-transmission-and-distribution/transmission/yh10w.html)和[Hitachi Energy PEXLIM](https://www.hitachienergy.com/products-and-solutions/surge-arresters/high-voltage-surge-arresters/silicone-housed-surge-arrester-pexlim)。额定电压Ur、持续运行电压Uc、暂时过电压和残压必须在接地与绝缘配合计算完成后确定。

## 6. 必须补齐后才能转为最终选型

1. 最高系统电压、设备绝缘水平、海拔和污秽等级；
2. 41℃条件下开关柜、母线和LGJ-400/50的修正载流量；
3. 系统1、系统2并列许可及220kV母联潮流；
4. 主保护、后备保护、固有分闸和燃弧时间，用于触头分离电流和短路热效应；
5. 220kV新能源短路贡献、35kV新能源峰值和必要的衰减模型；
6. 10kV无功补偿Mvar、分组方式及35/10.5kV电源变容量；
7. 厂家精确型号、正式样本版本、页码、服务条件和外形安装图；
8. CT/PT二次负荷、保护与计量准确级、同期和自动装置清册；
9. 母线、导体、绝缘子、穿墙套管及避雷器的专项参数和校验。
