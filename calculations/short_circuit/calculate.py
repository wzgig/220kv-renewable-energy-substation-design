from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def parallel_equivalent(*reactances: float) -> float:
    if not reactances or any(value <= 0 for value in reactances):
        raise ValueError("parallel reactances must be positive")
    return 1 / sum(1 / value for value in reactances)


def base_current_ka(base_capacity_mva: float, base_voltage_kv: float) -> float:
    if base_capacity_mva <= 0 or base_voltage_kv <= 0:
        raise ValueError("base capacity and voltage must be positive")
    return base_capacity_mva / (math.sqrt(3) * base_voltage_kv)


def _fault_point(
    *,
    point_id: str,
    voltage_level: str,
    base_capacity_mva: float,
    base_voltage_kv: float,
    equivalent_reactance_pu: float,
    peak_factor_k: float,
    operating_status: str,
    normal_operation_status: str,
) -> dict[str, Any]:
    grid_symmetrical_current_ka = (
        base_current_ka(base_capacity_mva, base_voltage_kv)
        / equivalent_reactance_pu
    )
    return {
        "point_id": point_id,
        "voltage_level": voltage_level,
        "base_voltage_kv": base_voltage_kv,
        "equivalent_reactance_pu": equivalent_reactance_pu,
        "grid_symmetrical_current_ka": grid_symmetrical_current_ka,
        "peak_factor_k": peak_factor_k,
        "grid_peak_current_ka": math.sqrt(2)
        * peak_factor_k
        * grid_symmetrical_current_ka,
        "grid_short_circuit_capacity_mva": math.sqrt(3)
        * base_voltage_kv
        * grid_symmetrical_current_ka,
        "operating_status": operating_status,
        "normal_operation_status": normal_operation_status,
        "current_scope": "grid_contribution_only",
    }


def _validated_multiplier_range(values: Any) -> tuple[float, float]:
    if not isinstance(values, (list, tuple)) or len(values) != 2:
        raise ValueError("renewable multiplier range must contain two values")
    minimum, maximum = map(float, values)
    if minimum <= 0 or maximum <= 0 or minimum > maximum:
        raise ValueError(
            "renewable multiplier range must satisfy 0 < minimum <= maximum"
        )
    return minimum, maximum


def _attach_renewable_sensitivity(
    point: dict[str, Any], contribution: dict[str, float]
) -> None:
    point["renewable_contribution_sensitivity_ka"] = contribution
    point["conservative_total_symmetrical_current_range_ka"] = {
        "minimum": point["grid_symmetrical_current_ka"]
        + contribution["minimum"],
        "maximum": point["grid_symmetrical_current_ka"]
        + contribution["maximum"],
        "combination_method": (
            "arithmetic_upper_bound_for_course_sensitivity"
        ),
    }


def _section_renewable_contribution(
    *,
    section: dict[str, Any],
    load_items: list[dict[str, Any]],
    nominal_voltage_kv: float,
    multiplier_range: list[float],
) -> dict[str, float]:
    source_map = {item["name"]: item for item in load_items}
    apparent_power_mva = 0.0
    for feeder in section["feeder_circuits"]:
        source = source_map[feeder["source_key"]]
        apparent_power_mva += (
            float(source["active_power_mw"])
            / float(source["power_factor"])
            / int(source["circuits"])
        )

    rated_current_ka = apparent_power_mva / (
        math.sqrt(3) * nominal_voltage_kv
    )
    minimum_multiplier, maximum_multiplier = _validated_multiplier_range(
        multiplier_range
    )
    return {
        "section_apparent_power_mva": apparent_power_mva,
        "section_rated_current_ka": rated_current_ka,
        "minimum_multiplier": minimum_multiplier,
        "maximum_multiplier": maximum_multiplier,
        "minimum": rated_current_ka * minimum_multiplier,
        "maximum": rated_current_ka * maximum_multiplier,
    }


def calculate_short_circuit(
    inputs: dict[str, Any], baseline: dict[str, Any]
) -> dict[str, Any]:
    rules = inputs["calculation_rules"]
    source_data = inputs["system_sources"]
    base_capacity_mva = float(rules["short_circuit_base_mva"])
    peak_factor_k = float(rules["short_circuit_peak_factor_k"])
    average_voltages = rules["average_rated_voltage_kv"]
    voltage_220kv = float(average_voltages["220kv"])
    voltage_35kv = float(average_voltages["35kv"])
    voltage_10kv = float(average_voltages["10kv"])
    if base_capacity_mva <= 0:
        raise ValueError("short-circuit base capacity must be positive")
    if peak_factor_k <= 0:
        raise ValueError("short-circuit peak factor must be positive")
    if min(voltage_220kv, voltage_35kv, voltage_10kv) <= 0:
        raise ValueError("average rated voltages must be positive")

    source_1 = source_data["source_1"]
    source_2 = source_data["source_2"]
    line_reactance_220 = float(
        rules["line_reactance_ohm_per_km"]["220kv_overhead"]
    )
    if line_reactance_220 <= 0:
        raise ValueError("220kV line reactance must be positive")
    impedance_base_220_ohm = voltage_220kv**2 / base_capacity_mva

    source_1_system_pu = (
        float(source_1["reactance_pu_on_own_base"])
        * base_capacity_mva
        / float(source_1["equivalent_capacity_mva"])
    )
    source_2_system_pu = (
        float(source_2["reactance_pu_on_own_base"])
        * base_capacity_mva
        / float(source_2["equivalent_capacity_mva"])
    )
    source_1_line_pu = (
        line_reactance_220
        * float(source_1["line_length_km"])
        / impedance_base_220_ohm
    )
    source_2_line_pu = (
        line_reactance_220
        * float(source_2["line_length_km"])
        / impedance_base_220_ohm
    )
    source_1_path_pu = source_1_system_pu + source_1_line_pu
    source_2_path_pu = source_2_system_pu + source_2_line_pu
    source_parallel_pu = parallel_equivalent(
        source_1_path_pu, source_2_path_pu
    )

    transformer = baseline["main_transformers"]
    transformer_x_pu = (
        float(transformer["short_circuit_voltage_percent"])
        / 100
        * base_capacity_mva
        / float(transformer["rated_capacity_mva_each"])
    )
    if transformer_x_pu <= 0:
        raise ValueError("main-transformer reactance must be positive")

    points: dict[str, dict[str, Any]] = {}
    points["SC-220-BUS-CLOSED"] = _fault_point(
        point_id="SC-220-BUS-CLOSED",
        voltage_level="220kV",
        base_capacity_mva=base_capacity_mva,
        base_voltage_kv=voltage_220kv,
        equivalent_reactance_pu=source_parallel_pu,
        peak_factor_k=peak_factor_k,
        operating_status="maximum_base_case",
        normal_operation_status=(
            "conditional_pending_system_parallel_permission"
        ),
    )
    points["SC-220-BUS-CLOSED"]["renewable_contribution_status"] = (
        "not_modelled_pending_converter_transformer_line_model"
    )
    points["SC-220-I-SEPARATE"] = _fault_point(
        point_id="SC-220-I-SEPARATE",
        voltage_level="220kV",
        base_capacity_mva=base_capacity_mva,
        base_voltage_kv=voltage_220kv,
        equivalent_reactance_pu=source_1_path_pu,
        peak_factor_k=peak_factor_k,
        operating_status="separate_bus_sensitivity",
        normal_operation_status="permitted_separate_operation",
    )
    points["SC-220-I-SEPARATE"]["renewable_contribution_status"] = (
        "not_modelled_pending_converter_transformer_line_model"
    )
    points["SC-220-II-SEPARATE"] = _fault_point(
        point_id="SC-220-II-SEPARATE",
        voltage_level="220kV",
        base_capacity_mva=base_capacity_mva,
        base_voltage_kv=voltage_220kv,
        equivalent_reactance_pu=source_2_path_pu,
        peak_factor_k=peak_factor_k,
        operating_status="separate_bus_sensitivity",
        normal_operation_status="permitted_separate_operation",
    )
    points["SC-220-II-SEPARATE"]["renewable_contribution_status"] = (
        "not_modelled_pending_converter_transformer_line_model"
    )

    normal_35kv_reactance_pu = source_parallel_pu + transformer_x_pu
    sections = baseline["connection_35kv"]["sections"]
    multiplier_range = rules["renewable_short_circuit_contribution"][
        "sensitivity_multiplier_range"
    ]
    section_contributions: dict[str, dict[str, float]] = {}
    for index, section in enumerate(sections, start=1):
        section_key = f"SC-35-{'I' if index == 1 else 'II'}-220-CLOSED"
        contribution = _section_renewable_contribution(
            section=section,
            load_items=inputs["loads_35kv"]["items"],
            nominal_voltage_kv=35.0,
            multiplier_range=multiplier_range,
        )
        section_contributions[section["id"]] = contribution
        point = _fault_point(
            point_id=section_key,
            voltage_level="35kV",
            base_capacity_mva=base_capacity_mva,
            base_voltage_kv=voltage_35kv,
            equivalent_reactance_pu=normal_35kv_reactance_pu,
            peak_factor_k=peak_factor_k,
            operating_status="35kv_sectioned_with_220kv_bus_tie_closed",
            normal_operation_status=(
                "conditional_pending_system_parallel_permission"
            ),
        )
        _attach_renewable_sensitivity(point, contribution)
        points[section_key] = point

    separate_section_1 = _fault_point(
        point_id="SC-35-I-220-SEPARATE",
        voltage_level="35kV",
        base_capacity_mva=base_capacity_mva,
        base_voltage_kv=voltage_35kv,
        equivalent_reactance_pu=source_1_path_pu + transformer_x_pu,
        peak_factor_k=peak_factor_k,
        operating_status="220kv_bus_sections_separate",
        normal_operation_status="permitted_separate_operation",
    )
    _attach_renewable_sensitivity(
        separate_section_1, section_contributions[sections[0]["id"]]
    )
    points[separate_section_1["point_id"]] = separate_section_1

    separate_section_2 = _fault_point(
        point_id="SC-35-II-220-SEPARATE",
        voltage_level="35kV",
        base_capacity_mva=base_capacity_mva,
        base_voltage_kv=voltage_35kv,
        equivalent_reactance_pu=source_2_path_pu + transformer_x_pu,
        peak_factor_k=peak_factor_k,
        operating_status="220kv_bus_sections_separate",
        normal_operation_status="permitted_separate_operation",
    )
    _attach_renewable_sensitivity(
        separate_section_2, section_contributions[sections[1]["id"]]
    )
    points[separate_section_2["point_id"]] = separate_section_2

    both_transformers_pu = source_parallel_pu + parallel_equivalent(
        transformer_x_pu, transformer_x_pu
    )
    parallel_point = _fault_point(
        point_id="SC-35-BOTH-TRANSFORMERS-SENSITIVITY",
        voltage_level="35kV",
        base_capacity_mva=base_capacity_mva,
        base_voltage_kv=voltage_35kv,
        equivalent_reactance_pu=both_transformers_pu,
        peak_factor_k=peak_factor_k,
        operating_status="non_normal_parallel_sensitivity",
        normal_operation_status="not_permitted_non_normal_sensitivity",
    )
    total_renewable_min = sum(
        contribution["minimum"]
        for contribution in section_contributions.values()
    )
    total_renewable_max = sum(
        contribution["maximum"]
        for contribution in section_contributions.values()
    )
    total_renewable_contribution = {
        "minimum": total_renewable_min,
        "maximum": total_renewable_max,
    }
    _attach_renewable_sensitivity(
        parallel_point, total_renewable_contribution
    )
    points[parallel_point["point_id"]] = parallel_point

    aux_transformer_rating = baseline["connection_10kv"]["source_transformers"][
        "rated_capacity_mva_each"
    ]
    pending_points: dict[str, dict[str, str]] = {}
    if aux_transformer_rating is None:
        pending_points["10kv_bus"] = {
            "status": "pending_input",
            "reason": (
                "35/10.5kV source-transformer rated capacity is unknown; "
                "reactive-compensation Mvar must be confirmed before the "
                "10kV short-circuit current can be finalized."
            ),
        }
    else:
        pending_points["10kv_bus"] = {
            "status": "not_implemented",
            "reason": (
                "A 35/10.5kV source-transformer rating is present, but the "
                "10kV fault model must still be implemented and verified "
                "before a result is published."
            ),
        }

    return {
        "basis": {
            "calculation_method": "taskbook_per_unit_x_only_preliminary",
            "standard_reference_for_final_review": "GB/T 15544.1-2023",
            "standard_alignment_status": "not_a_full_standard_implementation",
            "base_capacity_mva": base_capacity_mva,
            "average_rated_voltage_kv": {
                "220kv": voltage_220kv,
                "35kv": voltage_35kv,
                "10kv": voltage_10kv,
            },
            "resistance_treatment": rules[
                "preliminary_short_circuit_resistance"
            ],
            "peak_factor_k": peak_factor_k,
            "peak_factor_source": (
                "course_assumption_pending_r_over_x_review"
            ),
            "voltage_factor_treatment": (
                "not_applied_under_taskbook_preliminary_method"
            ),
            "renewable_base_case": rules[
                "renewable_short_circuit_contribution"
            ]["base_case"],
            "future_220kv_line_treatment": source_data[
                "future_or_tie_line"
            ]["status"],
            "future_220kv_line_in_service_for_base_case": source_data[
                "future_or_tie_line"
            ]["in_service_for_base_case"],
        },
        "network": {
            "impedance_base_220kv_ohm": impedance_base_220_ohm,
            "source_system_reactance_pu": {
                "source_1": source_1_system_pu,
                "source_2": source_2_system_pu,
            },
            "source_line_reactance_pu": {
                "source_1": source_1_line_pu,
                "source_2": source_2_line_pu,
            },
            "source_paths_220kv_pu": {
                "source_1": source_1_path_pu,
                "source_2": source_2_path_pu,
            },
            "parallel_source_equivalent_220kv_pu": source_parallel_pu,
            "main_transformer_reactance_pu_each": transformer_x_pu,
        },
        "points": points,
        "pending_points": pending_points,
        "notes": [
            "220kV分段断路器闭合场景须以系统1、系统2允许并列为前提，目前仅作最大基准敏感性。",
            "35kV正常保持分段运行，不允许两台健康主变低压侧长期并列。",
            "两台主变低压侧并列值仅保留为非正常敏感性场景。",
            "新能源贡献采用算术相加的课程设计保守上界，不等同于变流器电磁暂态模型。",
            "峰值仅表示电网贡献；固定k值是待按R/X复核的课程假设，并非由忽略电阻自动推导。",
            "220kV故障点的新能源贡献及35kV新能源峰值贡献尚未建模，设备最终校验前必须补充。",
            "第三回220kV线路L3不参加本期基准计算，远期投入场景另行计算。",
        ],
    }


def write_outputs(result: dict[str, Any], output_dir: str | Path) -> list[Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "short_circuit_results.json"
    csv_path = destination / "short_circuit_points.csv"
    markdown_path = destination / "short_circuit_summary.md"

    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    fieldnames = [
        "point_id",
        "voltage_level",
        "operating_status",
        "normal_operation_status",
        "equivalent_reactance_pu",
        "grid_symmetrical_current_ka",
        "grid_peak_current_ka",
        "grid_short_circuit_capacity_mva",
        "renewable_contribution_status",
        "renewable_minimum_ka",
        "renewable_maximum_ka",
        "conservative_total_maximum_ka",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fieldnames, lineterminator="\n"
        )
        writer.writeheader()
        for point in result["points"].values():
            renewable = point.get("renewable_contribution_sensitivity_ka", {})
            total_range = point.get(
                "conservative_total_symmetrical_current_range_ka", {}
            )
            writer.writerow(
                {
                    "point_id": point["point_id"],
                    "voltage_level": point["voltage_level"],
                    "operating_status": point["operating_status"],
                    "normal_operation_status": point[
                        "normal_operation_status"
                    ],
                    "equivalent_reactance_pu": point[
                        "equivalent_reactance_pu"
                    ],
                    "grid_symmetrical_current_ka": point[
                        "grid_symmetrical_current_ka"
                    ],
                    "grid_peak_current_ka": point[
                        "grid_peak_current_ka"
                    ],
                    "grid_short_circuit_capacity_mva": point[
                        "grid_short_circuit_capacity_mva"
                    ],
                    "renewable_contribution_status": point.get(
                        "renewable_contribution_status", "modelled_rms_only"
                    ),
                    "renewable_minimum_ka": renewable.get("minimum", ""),
                    "renewable_maximum_ka": renewable.get("maximum", ""),
                    "conservative_total_maximum_ka": total_range.get(
                        "maximum", ""
                    ),
                }
            )

    basis = result["basis"]
    average_voltages = basis["average_rated_voltage_kv"]
    base_capacity = basis["base_capacity_mva"]
    peak_factor = basis["peak_factor_k"]
    resistance_labels = {"ignored": "忽略"}
    operating_labels = {
        "maximum_base_case": "分段闭合最大基准",
        "separate_bus_sensitivity": "220kV分列",
        "35kv_sectioned_with_220kv_bus_tie_closed": (
            "35kV分段、220kV分段闭合"
        ),
        "220kv_bus_sections_separate": "220kV分列",
        "non_normal_parallel_sensitivity": "主变低压侧非正常并列",
    }
    permission_labels = {
        "conditional_pending_system_parallel_permission": (
            "待系统并列许可"
        ),
        "permitted_separate_operation": "允许分列运行",
        "not_permitted_non_normal_sensitivity": "不允许，仅敏感性",
    }
    lines = [
        "# 220kV与35kV三相短路电流初算",
        "",
        (
            f"基准：{base_capacity:g}MVA；平均额定电压"
            f"{average_voltages['220kv']:g}/"
            f"{average_voltages['35kv']:g}/"
            f"{average_voltages['10kv']:g}kV；"
            "初算电阻处理："
            f"{resistance_labels.get(basis['resistance_treatment'], basis['resistance_treatment'])}；"
            f"课程假设峰值系数k={peak_factor:g}。"
        ),
        "",
        (
            "本结果采用任务书标幺制X-only初算方法，并非GB/T 15544.1-2023"
            "的完整实现；最终设备校验须按标准原文复核电压系数、变压器修正系数和κ。"
        ),
        "",
        (
            "| 计算点 | 运行方式 | 正常运行许可 | XΣ/pu | "
            "电网对称电流/kA | 新能源RMS范围/kA | "
            "保守综合上限/kA | 电网峰值/kA |"
        ),
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for point in result["points"].values():
        renewable = point.get("renewable_contribution_sensitivity_ka", {})
        total_range = point.get(
            "conservative_total_symmetrical_current_range_ka", {}
        )
        if "minimum" in renewable and "maximum" in renewable:
            renewable_text = (
                f"{renewable['minimum']:.3f}～{renewable['maximum']:.3f}"
            )
        else:
            renewable_text = "未建模"
        total_text = (
            f"{total_range['maximum']:.3f}"
            if "maximum" in total_range
            else "—"
        )
        lines.append(
            f"| {point['point_id']} | "
            f"{operating_labels.get(point['operating_status'], point['operating_status'])} | "
            f"{permission_labels.get(point['normal_operation_status'], point['normal_operation_status'])} | "
            f"{point['equivalent_reactance_pu']:.6f} | "
            f"{point['grid_symmetrical_current_ka']:.3f} | "
            f"{renewable_text} | {total_text} | "
            f"{point['grid_peak_current_ka']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## 关键结论",
            "",
            (
                "- 220kV分段闭合的条件性最大基准电网贡献："
                f"{result['points']['SC-220-BUS-CLOSED']['grid_symmetrical_current_ka']:.3f}kA；"
                "该方式等待系统并列许可确认。"
            ),
            (
                "- 35kV-I段在220kV分段闭合时的电网贡献："
                f"{result['points']['SC-35-I-220-CLOSED']['grid_symmetrical_current_ka']:.3f}kA；"
                "计入新能源RMS保守上界后为"
                f"{result['points']['SC-35-I-220-CLOSED']['conservative_total_symmetrical_current_range_ka']['maximum']:.3f}kA。"
            ),
            (
                "- 35kV-II段在220kV分段闭合时计入新能源RMS保守上界后为"
                f"{result['points']['SC-35-II-220-CLOSED']['conservative_total_symmetrical_current_range_ka']['maximum']:.3f}kA。"
            ),
            (
                "- 两台健康主变低压侧并列的非正常电网敏感性值："
                f"{result['points']['SC-35-BOTH-TRANSFORMERS-SENSITIVITY']['grid_symmetrical_current_ka']:.3f}kA；"
                "计入新能源RMS保守上界后为"
                f"{result['points']['SC-35-BOTH-TRANSFORMERS-SENSITIVITY']['conservative_total_symmetrical_current_range_ka']['maximum']:.3f}kA。"
            ),
            "- 峰值列仅含电网贡献，不能直接作为已计及新能源的动稳定最终值。",
            "- 10kV短路电流等待35/10.5kV电源变容量及10kV无功补偿Mvar确认。",
            "",
            "## 注意",
            "",
        ]
    )
    lines.extend(f"- {note}" for note in result["notes"])
    markdown_path.write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )
    return [json_path, csv_path, markdown_path]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calculate preliminary 220kV and 35kV short-circuit currents."
    )
    parser.add_argument(
        "--inputs",
        type=Path,
        default=Path("data/design_inputs.yaml"),
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("data/design_baseline.yaml"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("calculations/results/short_circuit"),
    )
    args = parser.parse_args()

    result = calculate_short_circuit(
        load_yaml(args.inputs), load_yaml(args.baseline)
    )
    for output in write_outputs(result, args.output_dir):
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
