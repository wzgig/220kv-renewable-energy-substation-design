from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _write_csv(result: dict[str, Any], path: Path) -> None:
    fieldnames = [
        "selection_id",
        "circuit_group",
        "device_kind",
        "candidate_id",
        "required_current_a",
        "rated_current_a",
        "provisional_required_rms_ka",
        "rated_breaking_current_ka",
        "course_peak_precheck_ka",
        "rated_peak_withstand_ka",
        "numeric_precheck_status",
        "final_selection_status",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for item in result["selections"]:
            ratings = item["candidate"]["ratings"]
            duty = item["duty"]
            writer.writerow(
                {
                    "selection_id": item["id"],
                    "circuit_group": item["circuit_group"],
                    "device_kind": item["device_kind"],
                    "candidate_id": item["candidate"]["id"],
                    "required_current_a": duty["continuous"].get(
                        "required_current_a", ""
                    ),
                    "rated_current_a": ratings.get("continuous_current_a", ""),
                    "provisional_required_rms_ka": duty["fault"].get(
                        "provisional_required_rms_ka", ""
                    ),
                    "rated_breaking_current_ka": ratings.get(
                        "short_circuit_breaking_current_ka_rms", ""
                    ),
                    "course_peak_precheck_ka": duty["fault"].get(
                        "course_total_peak_sensitivity_ka"
                    )
                    or duty["fault"].get("known_grid_peak_ka", ""),
                    "rated_peak_withstand_ka": ratings.get(
                        "peak_withstand_current_ka", ""
                    ),
                    "numeric_precheck_status": item[
                        "numeric_precheck_status"
                    ],
                    "final_selection_status": item[
                        "final_selection_status"
                    ],
                }
            )


def _format_value(value: Any, digits: int = 3) -> str:
    if value is None:
        return "待定"
    return f"{float(value):.{digits}f}"


def _write_markdown(result: dict[str, Any], path: Path) -> None:
    duties = result["duty_registry"]
    completion = result["course_completion"]
    lines = [
        "# 主要电气设备与课程设计专项校核",
        "",
        "本文件由脚本生成。开关设备完成额定值等级预筛；母线、避雷器、CT/PT、ZCT、绝缘子/套管、接地开关及35/10kV接地变压器+中性点电阻设备包完成课程级选择与校核。所有厂家订货型号和施工参数仍保持待定。",
        "",
        f"- 数值预筛选总状态：`{result['numeric_precheck_status']}`",
        f"- 最终选型总状态：`{result['final_selection_status']}`",
        f"- 课程专项预校核状态：`{completion['course_precheck_status']}`；最终工程状态：`{completion['final_engineering_status']}`",
        "- 主回路热稳定统一按C=87、t=1.10s进行课程预校核；接地电阻按限定单相接地电流10s职责计算。精确型号、厂家温升、保护配合、接地与绝缘配合研究仍保持待定，不按零或自动通过处理。",
        "",
        "## 回路负荷职责",
        "",
        "| 回路组 | 成员 | 最大持续工作电流/A | 来源/状态 |",
        "| --- | --- | ---: | --- |",
    ]
    for group in duties["circuit_groups"].values():
        continuous = group["continuous"]
        lines.append(
            f"| {group['id']} | {', '.join(group['members'])} | "
            f"{_format_value(continuous.get('required_current_a'))} | "
            f"{continuous['source']} / {continuous['status']} |"
        )

    profiles = duties["fault_profiles"]
    lines.extend(
        [
            "",
            "## 短路职责场景",
            "",
            "| 电压级 | 必选运行方式RMS/kA | 条件性预校核RMS/kA | 禁止方式仅提示/kA | 峰值预校核/kA | 完整性 |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for profile_id in ("220_bus", "35_bus", "10_bus"):
        profile = profiles[profile_id]
        peak = profile.get("course_total_peak_sensitivity_ka")
        if peak is None:
            peak = profile.get("known_grid_peak_ka")
        lines.append(
            f"| {profile_id} | {_format_value(profile.get('mandatory_rms_ka'))} | "
            f"{_format_value(profile.get('conditional_rms_ka'))} | "
            f"{_format_value(profile.get('advisory_rms_ka'))} | "
            f"{_format_value(peak)} | {profile['status']} |"
        )

    lines.extend(
        [
            "",
            "## 候选额定值等级",
            "",
            "| 选择项 | 回路组 | 候选等级 | 额定电流/A | 开断电流/kA | 峰值耐受/kA | 数值预筛 | 最终状态 |",
            "| --- | --- | --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for item in result["selections"]:
        ratings = item["candidate"]["ratings"]
        lines.append(
            f"| {item['id']} | {item['circuit_group']} | "
            f"{item['candidate']['id']} | "
            f"{_format_value(ratings.get('continuous_current_a'), 0)} | "
            f"{_format_value(ratings.get('short_circuit_breaking_current_ka_rms'))} | "
            f"{_format_value(ratings.get('peak_withstand_current_ka'))} | "
            f"{item['numeric_precheck_status']} | "
            f"{item['final_selection_status']} |"
        )

    lines.extend(
        [
            "",
            "## 课程设计专项闭环",
            "",
            f"> {completion['scope']['ordering_boundary']}",
            "",
            "### 方案取舍",
            "",
            "| 电压级 | 条件性短路职责/kA | 开关设备开断能力/kA | 限流电抗器结论 |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    reactor = completion["design_decisions"]["current_limiting_reactor"]
    for item in reactor["checks"]:
        lines.append(
            f"| {item['voltage_class']} | "
            f"{_format_value(item['required_fault_current_ka'])} | "
            f"{_format_value(item['selected_switchgear_breaking_current_ka'])} | "
            f"不设置（{item['check']['status']}） |"
        )
    high_voltage_fuse = completion["design_decisions"]["high_voltage_fuse"]
    lines.extend(
        [
            "",
            f"- 限流电抗器：35/10kV条件性短路水平低于31.5kA开关设备能力，课程方案不设置；{reactor['boundary']}。",
            f"- 高压熔断器：不作为主回路设备选型；{high_voltage_fuse['scope']}。",
        ]
    )
    grounding_interlock = completion["grounding_source_interlock"]
    lines.extend(
        [
            "",
            "### 35/10kV接地源运行联锁",
            "",
            "| 电压级 | 正常运行 | 母联合闸转供前 | 禁止状态 | 分段恢复 | 课程预校核 |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in grounding_interlock["voltage_levels"]:
        lines.append(
            f"| {item['voltage_class']} | 每段一套，共{item['normal_sources_in_service']}套投入 | "
            f"先断开受电/故障段接地源，仅健康电源侧{item['transfer_sources_in_service']}套保持投入 | "
            f"母联合闸且两套接地源并联 | "
            f"母联断开后恢复每段一套，共{item['restored_sources_in_service']}套 | "
            f"{item['course_precheck_status']} |"
        )
    lines.extend(
        [
            "",
            "> 联锁原则：母联闭合许可必须同时确认受电/故障段接地源已断开，禁止两套低电阻接地源经母联并联。硬接点、软件逻辑、控制电源失效模式及保护跳闸矩阵仍由最终厂家设计。",
            "",
            "### 接地变压器+中性点电阻课程设备包",
            "",
            "| 设备包 | 每段配置 | Ig/A×s | R计算/选取Ω | 10s等效功率/MVA | 10倍短时过载最小容量/kVA | 选用/kVA | 馈线柜 | 相/中性CT目标 | 课程预校核 |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
        ]
    )
    for package in completion["grounding_transformer_resistor_packages"]:
        calculated = package["calculated"]
        lines.append(
            f"| {package['id']} | {package['quantity']}套ZN中性点形成、每段一套 | "
            f"{_format_value(package['target_ground_fault_current_a'], 0)}×{_format_value(package['short_time_s'], 0)} | "
            f"{_format_value(calculated['resistance_ohm'])}/{_format_value(package['target_resistance_ohm'], 1)} | "
            f"{_format_value(calculated['short_time_equivalent_power_mva'])} | "
            f"{_format_value(calculated['minimum_transformer_capacity_kva_at_overload_factor'])} | "
            f"{_format_value(package['selected_transformer_capacity_kva_each'], 0)} | "
            f"{package['feeder_switchgear_selection_id']} | "
            f"{package['phase_ct_target']['ratio']} / {package['neutral_ct_target']['ratio']} | "
            f"{package['course_precheck_status']} |"
        )
    lines.extend(
        [
            "",
            "设备包包含接地变馈线开关柜、相CT与中性点CT课程目标、相/零序过流、母线零序过压、接地变与电阻温度/连续性监视及断路器失灵接口；零序阻抗、损耗温升、NGR结构、CT饱和和完整保护定值由同一最终厂家协调。",
            "",
            "### 导体与母线",
            "",
            "| 项目 | 方案 | 持续职责/A | 修正后载流量/A | K | 1.10s热稳定允许/kA | 课程预校核 | 最终工程状态 |",
            "| --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for busbar in completion["busbars"]:
        calculated = busbar["calculated"]
        requirements = busbar["requirements"]
        lines.append(
            f"| {busbar['id']} | {busbar['description']} | "
            f"{_format_value(requirements['required_continuous_current_a'])} | "
            f"{_format_value(calculated['corrected_ampacity_a'])} | "
            f"{_format_value(calculated['current_correction_factor'], 4)} | "
            f"{_format_value(calculated['thermal_allowable_current_ka'])} | "
            f"{busbar['course_precheck_status']} | "
            f"{busbar['final_engineering_status']} |"
        )
    pending_busbar_mechanical = [
        item["id"]
        for item in completion["busbars"]
        if item.get("dynamic_check", {}).get("status") == "pending"
    ]
    if pending_busbar_mechanical:
        lines.extend(
            [
                "",
                f"> {', '.join(pending_busbar_mechanical)}仅完成载流与热稳定课程预校核；支撑间距、共振、连接受力和机械动稳定明确保持pending，不作自动通过。",
            ]
        )

    busbar_220 = next(
        item for item in completion["busbars"] if item["voltage_class"] == "v220"
    )
    dynamic = busbar_220["calculated"]["dynamic"]
    corona = busbar_220["calculated"]["corona"]
    lines.extend(
        [
            "",
            "220kV管形母线附加课程校核：",
            "",
            "| 项目 | 计算值 | 允许/要求值 | 结论 |",
            "| --- | ---: | ---: | --- |",
            f"| 简化动稳定弯曲应力/MPa（校核相距{_format_value(dynamic['calculation_phase_spacing_m'], 1)}m≤布置{_format_value(dynamic['frozen_layout_phase_spacing_m'], 1)}m） | {_format_value(dynamic['calculated_bending_stress_mpa'])} | {_format_value(busbar_220['dynamic_check']['allowable_bending_stress_mpa'])} | provisional_pass |",
            f"| 简化电晕起始相电压/kV | {_format_value(corona['critical_disruptive_phase_voltage_kv'])} | 运行相电压 {_format_value(corona['highest_operating_phase_voltage_kv'])} | provisional_pass |",
            "",
            "### 金属氧化物避雷器",
            "",
            "| 电压级 | 课程目标型号 | Uc/kV | 持续电压要求/kV | 持续裕度/kV | In/kA | 残压/kV | 设备LIWV/kV | LIWV/残压 | 课程预校核 |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for arrester in completion["surge_arresters"]:
        ratings = arrester["ratings"]
        calculated = arrester["calculated"]
        lines.append(
            f"| {arrester['voltage_class']} | {arrester['model']} | "
            f"{_format_value(ratings['continuous_operating_voltage_kv'])} | "
            f"{_format_value(calculated['required_continuous_voltage_kv'])} | "
            f"{_format_value(calculated['continuous_voltage_margin_kv'])} | "
            f"{_format_value(ratings['nominal_discharge_current_ka'])} | "
            f"{_format_value(ratings['lightning_residual_voltage_kv'])} | "
            f"{_format_value(arrester['protected_equipment_liwv_kv'])} | "
            f"{_format_value(calculated['protection_ratio'])} | "
            f"{arrester['course_precheck_status']} |"
        )
    for arrester in completion["surge_arresters"]:
        for coverage in arrester.get("interface_coverage", []):
            lines.extend(
                [
                    "",
                    f"> {coverage['id']}：{coverage['interface_type']}覆盖"
                    f"{', '.join(coverage['covered_circuit_groups'])}，回路"
                    f"{', '.join(coverage['covered_members'])}；映射校核"
                    f"{coverage['coverage_check_status']}。",
                ]
            )

    supplementary = completion["supplementary"]
    lines.extend(
        [
            "",
            "### CT课程选择与动热稳定预校核",
            "",
            "| CT目标 | 覆盖回路 | 变比 | 持续职责/额定A | 短路职责/额定kA | 峰值职责/额定kA | 课程预校核 | 最终工程状态 |",
            "| --- | --- | --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for current_transformer in supplementary["current_transformers"]:
        requirements = current_transformer["requirements"]
        short_time = current_transformer["rated_short_time"]
        lines.append(
            f"| {current_transformer['id']} | "
            f"{', '.join(current_transformer['covered_circuit_groups'])} | "
            f"{current_transformer['ratio']} | "
            f"{_format_value(requirements['required_continuous_current_a'])}/{_format_value(current_transformer['primary_rated_current_a'], 0)} | "
            f"{_format_value(requirements['required_short_circuit_rms_ka'])}/{_format_value(short_time['current_ka_rms'])}×{_format_value(short_time['duration_s'], 0)}s | "
            f"{_format_value(requirements['required_peak_current_ka'])}/{_format_value(current_transformer['rated_dynamic_current_ka_peak'])} | "
            f"{current_transformer['course_precheck_status']} | "
            f"{current_transformer['final_engineering_status']} |"
        )
    lines.extend(
        [
            "",
            "> 主变220kV中性点CT的600/1A、PX+5P30仅为课程配置目标。其持续、短时和峰值职责必须按单相接地及零序电流专题确定，不能沿用主变相回路的三相短路电流，因此本表保持待定。",
            "",
            "### 电缆馈线ZCT课程目标与接口校核",
            "",
            "| ZCT目标 | 电压级 | 覆盖回路组 | 覆盖电缆回路 | 变比 | 接地电流目标/最小线性范围A | 课程预校核 | 最终工程状态 |",
            "| --- | --- | --- | --- | --- | ---: | --- | --- |",
        ]
    )
    for zct in supplementary["zero_sequence_current_transformers"]:
        lines.append(
            f"| {zct['id']} | {zct['voltage_class']} | "
            f"{', '.join(zct['covered_circuit_groups'])} | "
            f"{', '.join(zct['covered_members'])} | {zct['ratio']} | "
            f"{_format_value(zct['target_primary_residual_current_a'], 0)}/"
            f"{_format_value(zct['minimum_linear_primary_residual_current_a'], 0)} | "
            f"{zct['course_precheck_status']} | {zct['final_engineering_status']} |"
        )
    lines.extend(
        [
            "",
            "> 35kV电缆回路PVA-1/2、PVB-1/2、ES-1和10kV电缆馈线均已映射至ZCT；窗口尺寸、电缆屏蔽层接地回流路径、负担、拐点和厂家准确级保持pending。",
        ]
    )

    lines.extend(
        [
            "",
            "### PT课程选择表",
            "",
            "| PT目标 | 电压级 | 型式 | 一次额定 | 二次绕组 | 准确级目标 | 最终工程状态 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for voltage_transformer in supplementary["voltage_transformers"]:
        lines.append(
            f"| {voltage_transformer['id']} | {voltage_transformer['voltage_class']} | "
            f"{voltage_transformer['type']} | {voltage_transformer['primary_ratio']} | "
            f"{'; '.join(voltage_transformer['secondary_windings'])} | "
            f"{', '.join(voltage_transformer['accuracy_targets'])} | "
            f"{voltage_transformer['final_engineering_status']} |"
        )

    lines.extend(
        [
            "",
            "### 绝缘子与套管课程选择表",
            "",
            "| 目标 | 应用 | Um/kV | LIWV/kV | 套管持续职责/额定A | 短时职责/额定kA×s | 峰值职责/额定kA | 课程预校核 | 最终工程状态 |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for insulator in supplementary["insulators_and_bushings"]:
        requirements = insulator["requirements"]
        short_time = insulator["bushing_rated_short_time"]
        lines.append(
            f"| {insulator['id']} | {insulator['application']} | "
            f"{_format_value(insulator['target_highest_voltage_kv'])} | "
            f"{_format_value(insulator['target_liwv_kv'])} | "
            f"{_format_value(requirements['required_continuous_current_a'])}/"
            f"{_format_value(insulator['bushing_rated_continuous_current_a'], 0)} | "
            f"{_format_value(requirements['required_short_circuit_rms_ka'])}/"
            f"{_format_value(short_time['current_ka_rms'])}×{_format_value(short_time['duration_s'], 0)} | "
            f"{_format_value(requirements['required_peak_current_ka'])}/"
            f"{_format_value(insulator['bushing_rated_dynamic_current_ka_peak'])} | "
            f"{insulator['course_precheck_status']} | "
            f"{insulator['final_engineering_status']} |"
        )
    lines.extend(
        [
            "",
            "> 套管已完成Um、LIWV、持续电流及动热稳定课程预校核；绝缘子/套管爬电距离、端子与悬臂机械负荷、抗震和精确型号仍明确保持pending。",
        ]
    )

    lines.extend(
        [
            "",
            "### 接地开关课程选择与动热稳定预校核",
            "",
            "| 目标 | 覆盖回路 | Um/kV | 短时耐受 | 峰值耐受/kA | 课程预校核 | 特殊边界 |",
            "| --- | --- | ---: | --- | ---: | --- | --- |",
        ]
    )
    for earthing_switch in supplementary["earthing_switches"]:
        short_time = earthing_switch["rated_short_time"]
        lines.append(
            f"| {earthing_switch['id']} | "
            f"{', '.join(earthing_switch['covered_circuit_groups'])} | "
            f"{_format_value(earthing_switch['target_highest_voltage_kv'])} | "
            f"{_format_value(short_time['current_ka_rms'])}kA×{_format_value(short_time['duration_s'], 0)}s | "
            f"{_format_value(earthing_switch['rated_dynamic_current_ka_peak'])} | "
            f"{earthing_switch['course_precheck_status']} | "
            f"{earthing_switch['special_duty']} |"
        )

    lines.extend(
        [
            "",
            "## 关键边界",
            "",
            "- 220kV线路一回退出及分段回路均按735.559A保守持续职责闭环；最终潮流研究只能提高精度，不能将该课程预筛值重新置空。",
            "- 35kV I、II段按实际馈线分配计算，不把4623.515A全站总电流或2311.758A简单均分值当成物理母线段职责。",
            "- 35kV条件性预校核采用计入新能源RMS上界的16.291kA；两台健康主变低压侧并列25.694kA仅作禁止方式提示。",
            "- 220kV新能源与10kV SVG贡献已按额定电流1.1～1.2倍的课程上界计入；固定k得到的综合峰值仍只作设备等级预筛。",
            "- 热稳定采用后备保护1.00s与全开断0.08s向上取1.10s，通过I²t与候选设备额定短时耐受能力比较。",
            "- 35kV 3150A进线/母联按室内最高40℃受控环境、K=1.0进行课程预校核；空调可靠性和厂家温升资料未冻结，因此最终型号仍为pending。",
            "- 10kV进线及母联升级为2500A目标；采用2×±12Mvar SVG和2×31.5MVA T10，单电源条件性综合上限15.638kA，禁止的两台健康T10并列综合上限28.472kA。",
            "- Φ100/90管形母线的温度修正、热稳定、简化动稳定和电晕校核，以及35/10kV矩形母线热稳定均为可再生课程计算；35/10kV母线机械动稳定、支撑共振、端部效应和厂家温升明确保持pending。",
            "- 35kV每段采用ZN接地变+约50.5Ω电阻，400A/10s、等效功率约8.083MVA，按10倍短时过载最小约808kVA并选1000kVA；10kV相应为约28.9Ω、200A/10s、约1.155MVA、最小约115.5kVA并选200kVA。",
            "- 正常运行35/10kV每段各一套接地源；母联转供前先断开受电/故障段接地源，仅健康电源侧一套投入，联锁禁止母联闭合且两套并联；分段恢复后各段一套。",
            "- 35kV架空入口MOA及35/10kV电缆馈线ZCT已建立回路映射；避雷器能量、ZCT窗口/屏蔽层回流、CT负担饱和和精确型号仍待厂家复核。",
            "- 避雷器型号、CT/PT/ZCT变比与准确级、绝缘子/套管绝缘水平和接地开关耐受等级是课程目标表，不是订货规范；接地、能量、负担、饱和、爬距、机械负荷和感应电流开合研究仍待完成。",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_outputs(result: dict[str, Any], output_dir: str | Path) -> list[Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "equipment_selection_results.json"
    csv_path = destination / "equipment_selection_screening.csv"
    markdown_path = destination / "equipment_selection_summary.md"

    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_csv(result, csv_path)
    _write_markdown(result, markdown_path)
    return [json_path, csv_path, markdown_path]
