# 标准与权威资料台账

## 1. 文档目的

本台账用于管理本项目采用的国家标准、电力行业标准、工程建设标准和设备厂家正式样本，为以下工作提供可追溯依据：

- 220kV 新能源汇集变电站电气主接线方案比选；
- 三相短路电流计算；
- 导体和一次设备选择、动稳定及热稳定校验；
- 220kV 户外配电装置与 35kV、10kV 开关设备布置；
- 接地、过电压保护和绝缘配合；
- 电气主接线简图、配电装置断面图和平面布置图的 CAD 制图；
- 技术设计说明书、计算书、设备表和答辩材料的引用核查。

核验日期：2026-07-15。

本台账中的“现行”“废止”和替代关系，按核验日期从国家标准全文公开系统、全国标准信息公共服务平台、国家数字标准馆等官方来源确认。标准在后续设计阶段仍可能修订，正式交付前应再次核验状态。

## 2. 使用规则

### 2.1 证据优先级

1. 国家标准及工程建设国家标准；
2. 国家能源局发布的电力行业标准；
3. 与上级标准不冲突的其他现行行业标准；
4. 最终选定设备厂家的当前正式样本、外形图和技术协议；
5. 教材、设计手册和既有课程设计仅作解释或复核材料，不作为标准状态和强制数值的最终证据。

当不同文件规定不一致时，不直接自行选择较宽松数值，应核对适用范围、标准层级、实施日期、强制性条文及最新替代关系，并在设计决策记录中说明处理结论。

### 2.2 数值条文和表格复核门槛

> 安全净距、通道宽度、设备安装高度、海拔修正值、短路计算系数、允许温度、动热稳定公式、接触电压、跨步电压、接地导体截面以及其他数值性条文，不得仅依据搜索摘要、网络转载、教材转述或本台账直接采用。必须从合法取得的对应版本标准全文中核对，并记录标准编号、年份、条文号或表号、页码、适用条件和复核日期后，方可进入正式计算、设备表或 CAD 图纸。

受版权限制的标准全文和厂家受限资料应保存在非公开资料区，不得上传到公开 Git 仓库。公开仓库可以保存标准题录、官方链接、核对记录和依法形成的设计结果。

### 2.3 状态标识

- 现行：截至 2026-07-15，官方标准平台显示该版本有效。
- 核心：本项目相应设计环节的直接依据，必须获得原文并逐条核对。
- 配套：用于设备或专项设计的补充依据。
- 条件适用：仅在选定对应方案或设备时使用。
- 废止：不得作为本项目主设计依据，只能用于识别旧资料。

## 3. 主接线、总体布置与设计深度

| 标准 | 状态 | 项目应用 | 官方来源 |
| --- | --- | --- | --- |
| DL/T 5218-2012《220kV～750kV变电站设计技术规程》 | 现行；核心；替代 DL/T 5218-2005 | 220kV 主接线、主变压器配置、站用电、无功补偿及变电站电气总体设计 | [全国标准信息公共服务平台](https://std.samr.gov.cn/hb/search/stdHBDetailed?id=8B1827F23CB5BB19E05397BE0A0AB44A) |
| DL/T 5452-2025《变电工程初步设计内容深度规定》 | 现行；核心；2026-03-28 实施；替代 DL/T 5452-2012 | 约束说明书、计算书、设备表、主接线图、平面图和断面图应达到的初步设计深度 | [全国标准信息公共服务平台](https://std.samr.gov.cn/hb/search/stdHBDetailed?id=424790975E72BCA9E06397BE0A0A3788) |
| DL/T 5056-2024《变电工程总布置设计规程》 | 现行；核心；替代 DL/T 5056-2007 | 站区功能分区、主变及配电装置相对位置、道路、运输和检修通道 | [全国标准信息公共服务平台](https://std.samr.gov.cn/hb/search/stdHBDetailed?id=1B4DE7F0E05DB814E06397BE0A0A5DEE) |
| DL/T 5458-2012《变电工程施工图设计内容深度规定》 | 现行；配套 | 辅助检查 CAD 平面图、断面图和设备标注的信息完整性，不替代课程任务书对初步设计的要求 | [全国标准信息公共服务平台](https://std.samr.gov.cn/hb/search/stdHBDetailed?id=8B1827F23CCEBB19E05397BE0A0AB44A) |

适用边界：本项目最高电压等级为 220kV。GB 50059-2011《35kV～110kV变电站设计规范》不能替代 DL/T 5218-2012 作为全站总体设计依据。

## 4. 短路电流、导体与电器选择

| 标准 | 状态 | 项目应用 | 官方来源 |
| --- | --- | --- | --- |
| GB/T 15544.1-2023《三相交流系统短路电流计算 第1部分：电流计算》 | 现行；核心；替代 GB/T 15544.1-2013 | 最大和最小短路电流、初始对称短路电流、峰值电流及开断相关电流计算 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=D86399BB0989F89A79B6CACBB666DA09) |
| GB/T 15544.2-2017《三相交流系统短路电流计算 第2部分：短路电流计算应用的系数》 | 现行；配套 | 核对短路计算所用系数及适用条件 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=5D0E7DDDB4F76AB1891D0B35977E958D) |
| GB/T 15544.3-2017《三相交流系统短路电流计算 第3部分：电气设备数据》 | 现行；配套 | 规范系统、线路、变压器等元件数据的选取 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=691C753840801F6FD5E17A86BBA9E50D) |
| GB/T 15544.5-2017《三相交流系统短路电流计算 第5部分：算例》 | 现行；配套 | 用标准算例复核短路计算程序和手算链路 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=B46A703A3A607C50E04F95E5C7831596) |
| DL/T 5222-2021《导体和电器选择设计规程》 | 现行；核心；替代 DL/T 5222-2005 | 3kV～1000kV 导体和电器的额定电压、持续电流、开断、动稳定、热稳定和环境修正 | [全国标准信息公共服务平台](https://std.samr.gov.cn/hb/search/stdHBDetailed?id=D961281962894C9BE05397BE0A0A7A39) |
| GB/T 1179-2017《圆线同心绞架空导线》 | 现行；配套 | 核查任务书给定 LGJ-400/50 出线导线的产品参数和材料要求 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F936B58052E9B750D1FEF196B660A084) |
| GB/T 5585.1-2018《电工用铜、铝及其合金母线 第1部分：铜和铜合金母线》 | 现行；条件适用 | 采用铜母线时核对材料和截面产品要求 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=942B6BCC24D80C0796F31F217A4A4370) |
| GB/T 5585.2-2018《电工用铜、铝及其合金母线 第2部分：铝和铝合金母线》 | 现行；条件适用 | 采用铝或铝合金硬母线时核对材料和截面产品要求 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=D70AA7B5DFC0D0845CD88820A94B5D24) |

LGJ-400/50当前592A基准来自标注GB1179-83的旧版二手课程参数表，仅用于41℃保守课程校核；GB/T 1179-2017是产品结构标准，不能替代在明确风速、日照、环境温度和最高导体温度下的现行厂家热额定值。

短路计算原文复核重点包括：电压系数、变压器修正系数、峰值系数、最大和最小运行方式、故障前条件、开断时刻、短路持续时间，以及风电、光伏和储能变流器短路贡献的建模边界。

## 5. 配电装置、开关设备与一次设备

### 5.1 户外配电装置和绝缘配合

| 标准 | 状态 | 项目应用 | 官方来源 |
| --- | --- | --- | --- |
| DL/T 5352-2018《高压配电装置设计规范》 | 现行；核心；替代 DL/T 5352-2006 | 220kV 户外 AIS 型式、带电体安全净距、构架、母线、围栏、道路及检修空间 | [全国标准信息公共服务平台](https://std.samr.gov.cn/hb/search/stdHBDetailed?id=8B1827F25307BB19E05397BE0A0AB44A) |
| GB 50060-2008《3～110kV高压配电装置设计规范》 | 现行；核心；适用 35kV 和 10kV，不适用 220kV 净距 | 35kV、10kV 配电装置及开关柜室的安全和布置要求 | [国家数字标准馆](https://www.ndls.org.cn/standard/detail/089c7f70db68305bddb5572bcfe46f3c) |
| GB/T 50064-2014《交流电气装置的过电压保护和绝缘配合设计规范》 | 现行；核心 | 避雷器配置、雷电和操作过电压保护、设备绝缘水平配合 | [国家数字标准馆](https://www.ndls.org.cn/standard/detail/bb1e1526e905c478b1e95bac24d96379) |
| GB/T 311.1-2012《绝缘配合 第1部分：定义、原则和规则》 | 现行；配套 | 设备耐受电压、绝缘水平和绝缘配合的基础规则 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=B101E5946B69F7ADA8ADA3D09622A37D) |
| GB/T 11032-2020《交流无间隙金属氧化物避雷器》 | 现行；核心 | 220kV、35kV和10kV无间隙金属氧化物避雷器的额定值、试验和保护性能 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=861E4F271389864CF8B0FFA403A87E00) |
| Q/GDW 13039.2-2018《220kV交流无间隙金属氧化物避雷器采购标准 第2部分：Y(H)10W-204/532专用技术规范》 | 国家电网企业标准；设备参数核验依据 | 核对220kV MOA 的204kV额定电压、159kV持续运行电压、10kA标称放电电流和不大于532kV雷电残压 | 国家电网有限公司正式PDF；核验副本仅保留本地私有材料区 |

DL/T 5352-2018 中的安全净距类别、相间和相地距离、带电体对围栏及道路距离、设备和母线安装高度、跨越高度以及海拔修正值，必须依据标准全文逐条核对后才能冻结断面图和平面图。

### 5.2 35kV、10kV 开关设备

| 标准 | 状态 | 项目应用 | 官方来源 |
| --- | --- | --- | --- |
| GB/T 3906-2020《3.6kV～40.5kV交流金属封闭开关设备和控制设备》 | 现行；核心 | 10kV、35kV 开关柜分类、隔室、联锁、内部电弧及型式试验要求 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=074ACACFFF9618BF5F3E922120A87E5B) |
| DL/T 404-2018《3.6kV～40.5kV交流金属封闭开关设备和控制设备》 | 现行；配套；替代 DL/T 404-2007 | 补充电力行业对 35kV、10kV 开关设备的技术要求 | [全国标准信息公共服务平台](https://std.samr.gov.cn/hb/search/stdHBDetailed?id=8B1827F15147BB19E05397BE0A0AB44A) |
| GB/T 11022-2020《高压交流开关设备和控制设备标准的共用技术要求》 | 现行；核心 | 高压开关设备的环境、额定值、试验和通用技术条件 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=196F732DBD167D2F302AF52BA6FAFAA1) |
| DL/T 593-2016《高压开关设备和控制设备标准的共用技术要求》 | 现行；配套；替代 DL/T 593-2006 | 补充电力行业通用技术要求 | [全国标准信息公共服务平台](https://std.samr.gov.cn/hb/search/stdHBDetailed?id=8B1827F2299ABB19E05397BE0A0AB44A) |
| GB/T 1984-2024《高压交流断路器》 | 现行；核心；替代 GB/T 1984-2014 | 断路器开断、关合、操作顺序、耐受和机械性能校验 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=05878AD1D8427B64705075DB83FD468C) |
| GB/T 1985-2023《高压交流隔离开关和接地开关》 | 现行；核心；替代 GB/T 1985-2014 | 隔离开关和接地开关额定值、耐受及关合能力 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=66EC8A1CCDF11D2CA3826648ECF3BB4F) |
| GB/T 7674-2020《额定电压72.5kV及以上气体绝缘金属封闭开关设备》 | 现行；条件适用 | 仅在 220kV GIS 方案进入正式比选或被选用时采用 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=614C6271842A7CE4B08512846AF2BD9D) |

GB/T 3906 和 DL/T 404 不提供可直接用于本项目 CAD 的统一柜体外形尺寸。柜宽、柜深、柜高、泄压通道、后维护空间和电缆弯曲空间必须取自最终型号的当前厂家正式样本和外形图。

### 5.3 互感器和变压器

| 标准 | 状态 | 项目应用 | 官方来源 |
| --- | --- | --- | --- |
| GB/T 20840.1-2010《互感器 第1部分：通用技术要求》 | 现行；核心 | CT、VT 和 CVT 的通用环境、额定值和试验要求 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=A40AEB77EBAB85616E49BD48E25C0C44) |
| GB/T 20840.2-2014《互感器 第2部分：电流互感器的补充技术要求》 | 现行；核心 | CT 变比、准确级、热稳定和动稳定等选型依据 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=9D2A5ECCC914E53080EBF5E3DFC7233E) |
| GB/T 20840.3-2013《互感器 第3部分：电磁式电压互感器的补充技术要求》 | 现行；核心 | 电磁式 VT 的额定参数和准确级 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=0C1DC45D6A311BCF9BD3C9E8AA9B0F16) |
| GB/T 20840.5-2013《互感器 第5部分：电容式电压互感器的补充技术要求》 | 现行；条件适用 | 220kV 侧采用 CVT 时的选型依据 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1B0D4AF1336CA344200B2CD79B631848) |
| GB/T 1094.1-2013《电力变压器 第1部分：总则》 | 现行；核心 | 主变压器及辅助变压器的通用技术条件 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=C3539A02733314553221D30BB7A2A0DF) |
| GB/T 6451-2023《油浸式电力变压器技术参数和要求》 | 现行；核心；替代 GB/T 6451-2015 | 两台 180MVA 户外油浸式主变的参数和产品要求 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=A75E4FE74ED07563EAD11D6379E0E3A5) |

### 5.4 无功补偿、运行与保护假设

| 标准 | 状态 | 项目应用 | 官方来源 |
| --- | --- | --- | --- |
| GB/T 29321-2012《光伏发电站无功补偿技术规范》 | 现行；配套 | 支撑集中无功补偿可设置在升压变低压侧、容量需结合接入条件确定的原则；不把0.98或24Mvar写成强制值 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=E6451F89B113960B614337BEDD30194A) |
| GB/T 19963.1-2021《风电场接入电力系统技术规定 第1部分：陆上风电》 | 现行；配套 | 风电场无功、电压与并网运行能力复核 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=F0127C2B431AC283CD6ED17CE67F8E46) |
| GB/T 19964-2024《光伏发电站接入电力系统技术规定》 | 现行；配套 | 光伏场站无功、电压与并网运行能力复核 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=40D8691DFD7EC3CBA423CCBA65D262F3) |
| GB/T 14285-2023《继电保护和安全自动装置技术规程》 | 现行；核心；替代2006版 | 保护配置与配合原则；本项目0.05s/1.00s仍是显式课程假设，不冒充标准固定整定值 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=0F1C15A59731267D3A756D6AFBB32841) |
| GB/T 31464-2022《电网运行准则》 | 现行；配套；替代2015版 | 系统并列、调度许可和运行边界的原则性依据 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=2E138E6A6D540124290DBBA47FFA1E14) |
| GB/T 26218.1-2010、GB/T 26218.2-2010 | 现行；配套 | d级污秽课程假设下的外绝缘选择与最终爬电距离复核 | [第1部分](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=5BC1117698E6281FAABB3CECFD85AF0C)；[第2部分](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=84465B7D3FDCD8B1F9498C236C5D550B) |

## 6. 接地

| 标准 | 状态 | 项目应用 | 官方来源 |
| --- | --- | --- | --- |
| GB/T 50065-2011《交流电气装置的接地设计规范》 | 现行；核心 | 接地网设计、接触电压、跨步电压、接地导体热稳定及故障电流分流 | [国家数字标准馆](https://www.ndls.org.cn/standard/detail/4a5f1191d275a706ce9a4e274db80130) |
| GB 50169-2016《电气装置安装工程 接地装置施工及验收规范》 | 现行；配套；替代 GB 50169-2006 | 接地装置焊接、连接、施工和验收；不替代接地设计计算 | [国家数字标准馆](https://www.ndls.org.cn/standard/detail/503cb582b61febf4ef65e73de7ff64e5) |

接地计算原文复核重点包括：故障持续时间、故障电流分流系数、地表层修正、接触和跨步电压限值、接地导体最小截面及腐蚀裕量。

## 7. 电气与 CAD 制图

| 标准 | 状态 | 项目应用 | 官方来源 |
| --- | --- | --- | --- |
| DL/T 5028.1-2015《电力工程制图标准 第1部分：一般规则》 | 现行；核心 | 图幅、比例、线型、线宽、文字、标注和图签 | [全国标准信息公共服务平台](https://std.samr.gov.cn/hb/search/stdHBDetailed?id=8B1827F20FAABB19E05397BE0A0AB44A) |
| DL/T 5028.3-2015《电力工程制图标准 第3部分：电气、仪表与控制部分》 | 现行；核心 | 主接线、电气设备编号以及电气平面和断面的表达 | [全国标准信息公共服务平台](https://std.samr.gov.cn/hb/search/stdHBDetailed?id=8B1827F20CF0BB19E05397BE0A0AB44A) |
| GB/T 4728.1-2018《电气简图用图形符号 第1部分：一般要求》 | 现行；核心 | 电气图形符号的一般规则 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=AFB34DDA789F637546166983140B34C5) |
| GB/T 4728.2-2018《电气简图用图形符号 第2部分：符号要素、限定符号和其他常用符号》 | 现行；配套 | 组合符号、限定符号和常用符号 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=30174DF769B49D331AB0682057955D9C) |
| GB/T 4728.3-2018《电气简图用图形符号 第3部分：导体和连接件》 | 现行；核心 | 母线、导体、连接点和端子表达 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=6F06A509CE0C66B30F0A21D1B6CEE3E0) |
| GB/T 4728.6-2022《电气简图用图形符号 第6部分：电能的发生与转换》 | 现行；核心 | 发电、变压器及电能转换设备符号 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=01195C7C62A31C6D9F84B2A6B106EA71) |
| GB/T 4728.7-2022《电气简图用图形符号 第7部分：开关、控制和保护器件》 | 现行；核心 | 断路器、隔离开关、接地开关和保护器件符号 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=D0D8E532BD220616FADD0B9D3A4E1346) |
| GB/T 4728.11-2022《电气简图用图形符号 第11部分：建筑安装平面布置图》 | 现行；配套 | 平面布置图中的安装和设备符号 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=CF672DA6DE990B8A0808524E9B9A4C24) |
| GB/T 6988.1-2024《电气技术用文件的编制 第1部分：规则》 | 现行；核心；替代 GB/T 6988.1-2008 | 电气技术文件的结构、简图编制和引用规则 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=3FE198A10F973D18CF8CA9893E1E7C9E) |
| GB/T 14689-2008《技术制图 图纸幅面和格式》 | 现行；配套 | 通用图幅和格式 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=6C3BD0FCD8FFFE7CEC6404FB0180EA96) |
| GB/T 14690-1993《技术制图 比例》 | 现行；配套 | 图纸比例 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=C111329A862219BCCCAAF32E14FF4CD0) |
| GB/T 14691-1993《技术制图 字体》 | 现行；配套 | 制图字体 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=44F8A8E5B9D37004AB8445B42992B1BC) |
| GB/T 17450-1998《技术制图 图线》 | 现行；配套 | 图线类型和表达 | [国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=ED5D794A6EFCD039618233C957C058DB) |

## 8. 厂家正式样本

设备标准规定额定值、结构和试验要求，但通常不提供可直接用于 CAD 的项目外形尺寸。最终图纸必须采用所选厂家的当前正式样本、外形图和安装资料。

已核验可公开访问的厂家样本示例：

- ABB《UniGear Product Guide》（Rev. 4；非本项目选型依据，仅作厂家资料格式示例）：[ABB Library PDF](https://library.e.abb.com/public/40813c97d07812bdc1257b13005735d2/Guide_UNIGEAR(en)_1VLM000005%20Rev4.pdf)。
- CHINT《KYN61-40.5(Z) MV Air Insulated Switchgear Catalog》：[官方目录](https://www.chintglobal.com/content/dam/chint/global/product-center/power-transmission-and-distribution/distribution/mv-switchgear/mv-air-insulated-switchgear/kyn61-40-5(z)(630~3150)/catalog/KYN61-40.5(Z)-MV%20Air%20Insulated%20Switchgear-Catalog.pdf)。
- Siemens NXAirS 40.5kV开关柜：[官方产品页](https://www.siemens.com/zh-cn/products/energy-systems/nxairs/)。
- CHINT LW43-252户外SF6断路器：[官方产品页](https://www.chintglobal.com/global/en/products/power-transmission-and-distribution/transmission/lw43-252.html)。

上述资料仅说明厂家家族可得性和正式样本的资料形式，不代表本项目已经选定对应厂家。CHINT KYN61当前网页声称电流范围可到3150A，但链接目录第22页列出的母线/断路器电流最高为2500A，两者存在版本或配置差异；3150A配置必须取得更新样本或型式试验证明后再采用。设备定型时至少应记录厂家、产品系列、额定电压、额定电流、短路等级、柜型或设备型号、样本版本、发布日期、下载链接及外形图页码。

本轮另核对 Siemens 官方《NXAirS 40.5 kV Air-Insulated Medium-Voltage Switchgear》样本，其40.5kV主母线额定电流上限为3150A。因此当前35kV 3150A方案不能简单上调到4000A；课程设计通过把开关柜室控制在不高于40℃满足常规使用条件形成紧裕度方案，最终仍须取得明确支持3150A、项目环境和温升条件的厂家配置及型式试验资料。

## 9. 重点废止或被替代版本（非完整清单）

| 旧标准 | 官方状态或替代关系 | 本项目处理 | 官方来源 |
| --- | --- | --- | --- |
| DL/T 5218-2005 | 被 DL/T 5218-2012 替代 | 全站总体设计采用 2012 版 | [现行版本元数据](https://std.samr.gov.cn/hb/search/stdHBDetailed?id=8B1827F23CB5BB19E05397BE0A0AB44A) |
| DL/T 5452-2012 | 废止，被 DL/T 5452-2025 替代 | 不再作为初步设计内容深度依据 | [旧版元数据](https://std.samr.gov.cn/hb/search/stdHBDetailed?id=8B1827F23D0ABB19E05397BE0A0AB44A) |
| DL/T 5056-2007 | 被 DL/T 5056-2024 替代 | 总布置采用 2024 版 | [现行版本元数据](https://std.samr.gov.cn/hb/search/stdHBDetailed?id=1B4DE7F0E05DB814E06397BE0A0A5DEE) |
| GB/T 15544.1-2013 | 废止，被 GB/T 15544.1-2023 替代 | 不再用于短路计算 | [旧版官方页面](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=2EF5BD24DFB40A481218BEFE9FD94ABD) |
| DL/T 5222-2005 | 被 DL/T 5222-2021 替代 | 导体和电器选择采用 2021 版 | [现行版本元数据](https://std.samr.gov.cn/hb/search/stdHBDetailed?id=D961281962894C9BE05397BE0A0A7A39) |
| DL/T 5352-2006 | 被 DL/T 5352-2018 替代 | 220kV 户外配电装置采用 2018 版 | [现行版本元数据](https://std.samr.gov.cn/hb/search/stdHBDetailed?id=8B1827F25307BB19E05397BE0A0AB44A) |
| DL/T 404-2007 | 被 DL/T 404-2018 替代 | 35kV、10kV 开关设备采用 2018 版 | [现行版本元数据](https://std.samr.gov.cn/hb/search/stdHBDetailed?id=8B1827F15147BB19E05397BE0A0AB44A) |
| DL/T 593-2006 | 被 DL/T 593-2016 替代 | 开关设备行业共用要求采用 2016 版 | [现行版本元数据](https://std.samr.gov.cn/hb/search/stdHBDetailed?id=8B1827F2299ABB19E05397BE0A0AB44A) |
| GB/T 1984-2014 | 废止，被 GB/T 1984-2024 替代 | 旧断路器选型表必须按新版本复核 | [旧版官方页面](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=B4E75F2578A2D58E1D96B14F0FE015CA) |
| GB/T 1985-2014 | 废止，被 GB/T 1985-2023 替代 | 旧隔离开关、接地开关选型表必须按新版本复核 | [旧版官方页面](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=036A5E8A55CF987FBE2950AFDB50071D) |
| GB/T 6451-2015 | 废止，被 GB/T 6451-2023 替代 | 主变产品参数采用 2023 版 | [旧版官方页面](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=2A7013702A4DE775A78EC1944199FBD4) |
| GB 50169-2006 | 被 GB 50169-2016 替代 | 接地施工与验收采用 2016 版 | [现行版本元数据](https://www.ndls.org.cn/standard/detail/503cb582b61febf4ef65e73de7ff64e5) |
| GB/T 6988.1-2008 | 废止，被 GB/T 6988.1-2024 替代 | CAD 和技术文件编制采用 2024 版 | [旧版官方页面](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=40EDE34EABD26A911B9D993DCDD28873) |
| DL/T 621-1997《交流电气装置的接地》 | 废止 | 接地设计以 GB/T 50065-2011 为主，不引用该旧版作为现行依据 | [旧版元数据](https://std.samr.gov.cn/hb/search/stdHBDetailed?id=8B1827F18828BB19E05397BE0A0AB44A) |

旧教材、既有课程设计或设备资料如引用上述版本，必须标记为“历史资料”，不得把其中数值直接带入当前计算和图纸。

## 10. 本项目待确认条件

以下条件会直接影响标准条文选择或数值结果，未确认前不得冻结相应设备参数和 CAD 尺寸：

| 条件 | 影响 |
| --- | --- |
| 海拔 | 绝缘水平、外绝缘和安全净距修正 |
| 污秽等级 | 爬电距离、绝缘子和设备外绝缘选型 |
| 220kV 配电装置最终采用 AIS 或 GIS | 适用设备标准、站区占地和平断面结构 |
| 主变采用三绕组方案或 220/35kV 双绕组加 35/10.5kV 辅助变方案 | 主接线、短路网络、设备数量和布置 |
| 35kV、10kV 开关柜最终厂家和型号 | 柜体尺寸、维护通道、泄压方式和电缆空间 |
| 新能源短路电流贡献模型 | 最大短路电流、开断能力和设备裕度 |
| 任务书对 CAD 直接提交或作为手绘底稿的最终口径 | 图幅、出图比例和交付格式 |

## 11. 标准采用记录要求

每次从标准中采用数值、公式或强制性要求时，应在计算书、设计说明或独立核对记录中留下以下信息：

1. 标准编号、名称和年份；
2. 标准状态核验日期；
3. 条文号、表号、图号或附录号；
4. 原文页码和适用条件；
5. 本项目采用值及必要的修正过程；
6. 核对人和复核日期；
7. 若使用厂家数据，补充厂家、型号、样本版本和外形图页码。

标准状态或厂家样本发生变化时，应先更新本台账，再修改计算、设备表和图纸，避免说明书、计算书和 CAD 使用不同版本的依据。
