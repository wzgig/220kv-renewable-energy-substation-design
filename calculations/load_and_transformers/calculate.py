from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    """Load the taskbook-derived YAML input."""
    input_path = Path(path)
    with input_path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError("design input must be a YAML mapping")
    return data


def apparent_power_mva(active_power_mw: float, power_factor: float) -> float:
    """Convert three-phase active power to apparent power."""
    if active_power_mw < 0:
        raise ValueError("active power must be non-negative")
    if not 0 < power_factor <= 1:
        raise ValueError("power factor must be within (0, 1]")
    return active_power_mw / power_factor


def three_phase_current_a(apparent_power_mva: float, nominal_voltage_kv: float) -> float:
    """Calculate line current from apparent power and nominal line voltage."""
    if apparent_power_mva < 0:
        raise ValueError("apparent power must be non-negative")
    if nominal_voltage_kv <= 0:
        raise ValueError("nominal voltage must be positive")
    return apparent_power_mva / (math.sqrt(3) * nominal_voltage_kv) * 1000


def _next_standard_capacity(required_kva: float, candidates: list[float]) -> float:
    standards = sorted(float(value) for value in candidates)
    for standard in standards:
        if standard >= required_kva:
            return standard
    raise ValueError(
        f"required station-service capacity {required_kva:.3f} kVA "
        "exceeds the configured standard capacity list"
    )


def _calculate_voltage_level_load(
    *,
    items: list[dict[str, Any]],
    nominal_voltage_kv: float,
    group_factor: float,
    loss_rate: float,
) -> dict[str, Any]:
    if not 0 < group_factor <= 1:
        raise ValueError("group simultaneity/output factor must be within (0, 1]")
    if not 0 <= loss_rate < 1:
        raise ValueError("line loss rate must be within [0, 1)")

    calculated_items: list[dict[str, Any]] = []
    gross_apparent_mva = 0.0

    for item in items:
        active_power_mw = float(item["active_power_mw"])
        power_factor = float(item["power_factor"])
        circuits = int(item["circuits"])
        if circuits <= 0:
            raise ValueError(f"{item['name']} must have at least one circuit")

        base_apparent_mva = apparent_power_mva(active_power_mw, power_factor)
        gross_apparent_mva += base_apparent_mva

        # The taskbook limits the 0.95 factor to main-transformer sizing.
        # Individual circuit current therefore uses the full item maximum,
        # distributed equally over its circuits, with the common 5% loss.
        design_apparent_mva = base_apparent_mva * (1 + loss_rate)
        base_per_circuit_mva = base_apparent_mva / circuits
        per_circuit_mva = design_apparent_mva / circuits
        calculated_items.append(
            {
                "name": item["name"],
                "label_zh": item.get("label_zh", item["name"]),
                "active_power_mw": active_power_mw,
                "power_factor": power_factor,
                "circuits": circuits,
                "base_apparent_mva": base_apparent_mva,
                "base_per_circuit_mva": base_per_circuit_mva,
                "base_per_circuit_current_a": three_phase_current_a(
                    base_per_circuit_mva, nominal_voltage_kv
                ),
                "design_apparent_mva_with_losses": design_apparent_mva,
                "per_circuit_design_mva": per_circuit_mva,
                "per_circuit_current_a": three_phase_current_a(
                    per_circuit_mva, nominal_voltage_kv
                ),
                "simultaneity_applied_to_circuit": False,
            }
        )

    after_group_factor_mva = gross_apparent_mva * group_factor
    with_losses_mva = after_group_factor_mva * (1 + loss_rate)
    exact_loss_interpretation_mva = after_group_factor_mva / (1 - loss_rate)

    return {
        "nominal_voltage_kv": nominal_voltage_kv,
        "group_factor": group_factor,
        "loss_rate": loss_rate,
        "gross_apparent_mva": gross_apparent_mva,
        "after_simultaneity_mva": after_group_factor_mva,
        "with_losses_mva": with_losses_mva,
        "alternative_divide_by_one_minus_loss_mva": exact_loss_interpretation_mva,
        "bus_current_a": three_phase_current_a(with_losses_mva, nominal_voltage_kv),
        "items": calculated_items,
    }


def _calculate_station_service(
    config: dict[str, Any],
) -> dict[str, Any]:
    items = config["station_service_loads"]["items"]
    assumptions = config["station_service_loads"][
        "preliminary_selection_assumptions"
    ]

    applicable_items: list[dict[str, Any]] = []
    excluded_items: list[str] = []
    for item in items:
        if not item.get("applicable", True):
            excluded_items.append(str(item["name"]))
            continue

        rated_kw = item.get("calculated_rated_kw", item.get("rated_kw"))
        if rated_kw is None:
            raise ValueError(f"station-service load {item['name']} has no kW value")

        normalized = dict(item)
        normalized["calculated_rated_kw"] = float(rated_kw)
        applicable_items.append(normalized)

    continuous_items = [
        item
        for item in applicable_items
        if str(item["duty"]).startswith("continuous")
    ]
    frequent_short_time_items = [
        item for item in applicable_items if item["duty"] == "short_time_frequent"
    ]
    explicit_frequent_kw = sum(
        item["calculated_rated_kw"]
        for item in applicable_items
        if str(item["duty"]).endswith("_frequent")
    )
    explicit_infrequent_kw = sum(
        item["calculated_rated_kw"]
        for item in applicable_items
        if str(item["duty"]).endswith("_infrequent")
    )
    frequency_unspecified_kw = sum(
        item["calculated_rated_kw"]
        for item in applicable_items
        if item["duty"] in {"continuous", "short_time"}
    )

    continuous_kw = sum(item["calculated_rated_kw"] for item in continuous_items)
    frequent_short_time_kw = sum(
        item["calculated_rated_kw"] for item in frequent_short_time_items
    )
    simultaneous_short_time_kw = sum(
        float(item.get("simultaneous_kw", item["calculated_rated_kw"]))
        for item in frequent_short_time_items
    )
    all_applicable_kw = sum(
        item["calculated_rated_kw"] for item in applicable_items
    )
    short_time_kw = sum(
        item["calculated_rated_kw"]
        for item in applicable_items
        if str(item["duty"]).startswith("short_time")
    )

    power_factor = float(assumptions["power_factor"])
    margin_rate = float(assumptions["margin_rate"])
    if not 0 < power_factor <= 1:
        raise ValueError("station-service power factor must be within (0, 1]")
    if margin_rate < 0:
        raise ValueError("station-service margin must be non-negative")

    base_scenario_kw = continuous_kw + simultaneous_short_time_kw
    worst_frequent_kw = continuous_kw + frequent_short_time_kw
    base_required_kva = base_scenario_kw * (1 + margin_rate) / power_factor
    worst_frequent_required_kva = (
        worst_frequent_kw * (1 + margin_rate) / power_factor
    )
    selection_basis_kva = max(base_required_kva, worst_frequent_required_kva)
    recommended_kva = _next_standard_capacity(
        selection_basis_kva, assumptions["standard_capacity_kva"]
    )

    return {
        "applicable_items": applicable_items,
        "excluded_items": excluded_items,
        "continuous_applicable_kw": continuous_kw,
        "short_time_applicable_kw": short_time_kw,
        "explicit_frequent_kw": explicit_frequent_kw,
        "explicit_infrequent_kw": explicit_infrequent_kw,
        "frequency_unspecified_kw": frequency_unspecified_kw,
        "frequent_short_time_kw": frequent_short_time_kw,
        "simultaneous_short_time_kw": simultaneous_short_time_kw,
        "all_applicable_kw": all_applicable_kw,
        "base_scenario_kw_before_margin": base_scenario_kw,
        "worst_frequent_kw_before_margin": worst_frequent_kw,
        "assumed_power_factor": power_factor,
        "margin_rate": margin_rate,
        "base_required_kva": base_required_kva,
        "worst_frequent_required_kva": worst_frequent_required_kva,
        "selection_basis_kva": selection_basis_kva,
        "recommended_each_transformer_kva": recommended_kva,
        "recommended_transformer_count": int(
            config["station_service_loads"]["transformer_count_preference"]
        ),
        "standby_mode": config["station_service_loads"]["standby_mode"],
    }


def calculate_design(config: dict[str, Any]) -> dict[str, Any]:
    """Calculate the load, circuit-current, and transformer-sizing baseline."""
    loss_rate = float(config["calculation_rules"]["line_loss_rate"])

    load_35kv = _calculate_voltage_level_load(
        items=config["loads_35kv"]["items"],
        nominal_voltage_kv=35.0,
        group_factor=float(config["loads_35kv"]["simultaneous_output_factor"]),
        loss_rate=loss_rate,
    )
    load_35kv["equal_bus_section_current_a"] = load_35kv["bus_current_a"] / 2

    load_10kv = _calculate_voltage_level_load(
        items=config["loads_10kv"]["items"],
        nominal_voltage_kv=10.0,
        group_factor=float(config["loads_10kv"]["simultaneity_factor"]),
        loss_rate=loss_rate,
    )

    transformer_config = config["system"]["main_transformer_proposal"]
    transformer_count = int(transformer_config["count"])
    rated_mva_each = float(transformer_config["rated_capacity_mva_each"])
    if transformer_count <= 0 or rated_mva_each <= 0:
        raise ValueError("main-transformer count and rating must be positive")

    renewable_required_mva = load_35kv["with_losses_mva"]
    including_10kv_mva = renewable_required_mva + load_10kv["with_losses_mva"]
    installed_capacity_mva = transformer_count * rated_mva_each
    per_transformer_mva = renewable_required_mva / transformer_count
    main_transformer = {
        "primary_case_basis": "35kV renewable aggregate",
        "includes_10kv_load_in_primary_case": False,
        "transformer_count": transformer_count,
        "rated_mva_each": rated_mva_each,
        "installed_capacity_mva": installed_capacity_mva,
        "total_required_mva": renewable_required_mva,
        "per_transformer_mva": per_transformer_mva,
        "normal_loading_percent": renewable_required_mva
        / installed_capacity_mva
        * 100,
        "n_minus_one_supply_percent": rated_mva_each
        / renewable_required_mva
        * 100,
        "n_minus_one_shortfall_mva": max(
            renewable_required_mva - rated_mva_each, 0
        ),
        "sensitivity_including_10kv": {
            "total_required_mva": including_10kv_mva,
            "per_transformer_mva": including_10kv_mva / transformer_count,
            "normal_loading_percent": including_10kv_mva
            / installed_capacity_mva
            * 100,
            "n_minus_one_supply_percent": rated_mva_each
            / including_10kv_mva
            * 100,
            "n_minus_one_shortfall_mva": max(
                including_10kv_mva - rated_mva_each, 0
            ),
        },
        "rated_current_a": {
            "220kv": three_phase_current_a(rated_mva_each, 220.0),
            "35kv": three_phase_current_a(rated_mva_each, 35.0),
        },
        "rated_current_with_1_05_margin_a": {
            "220kv": three_phase_current_a(rated_mva_each, 220.0) * 1.05,
            "35kv": three_phase_current_a(rated_mva_each, 35.0) * 1.05,
        },
    }

    outgoing_circuits = int(config["system"]["outgoing_220kv"]["in_service_circuits"])
    if outgoing_circuits <= 0:
        raise ValueError("at least one 220kV outgoing circuit is required")
    outgoing_equal_share_mva = load_35kv["with_losses_mva"] / outgoing_circuits

    return {
        "project": {
            "title": config["project"]["title"],
            "taskbook_group": config["project"]["taskbook_group"],
        },
        "load_35kv": load_35kv,
        "load_10kv": load_10kv,
        "main_transformer": main_transformer,
        "outgoing_220kv": {
            "in_service_circuits": outgoing_circuits,
            "equal_share_mva": outgoing_equal_share_mva,
            "equal_share_current_a": three_phase_current_a(
                outgoing_equal_share_mva, 220.0
            ),
            "single_circuit_contingency_mva": load_35kv["with_losses_mva"],
            "single_circuit_contingency_current_a": three_phase_current_a(
                load_35kv["with_losses_mva"], 220.0
            ),
            "basis": "35kV renewable aggregate before subtracting local auxiliary use",
        },
        "station_service": _calculate_station_service(config),
        "calculation_notes": [
            "0.95 新能源同时出力系数仅用于主变综合容量计算。",
            "单回馈线电流采用该类最大负荷除以回路数，不叠加系统同时系数。",
            "主结果按乘 1.05 处理 5% 线损。",
            "同时保留除以 (1-线损率) 的敏感性数值。",
            "主变主校核按35kV汇集负荷；另保留叠加10kV负荷的保守敏感性场景。",
            "所用变 kVA 建议为初选值，因其功率因数属于显式假设。",
        ],
    }


def _write_circuit_csv(result: dict[str, Any], path: Path) -> None:
    fieldnames = [
        "voltage_level",
        "name",
        "label_zh",
        "active_power_mw",
        "power_factor",
        "circuits",
        "base_apparent_mva",
        "base_per_circuit_mva",
        "base_per_circuit_current_a",
        "per_circuit_design_mva",
        "per_circuit_current_a",
        "simultaneity_applied_to_circuit",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for voltage_key, label in (("load_35kv", "35kV"), ("load_10kv", "10kV")):
            for item in result[voltage_key]["items"]:
                writer.writerow(
                    {
                        "voltage_level": label,
                        "name": item["name"],
                        "label_zh": item["label_zh"],
                        "active_power_mw": item["active_power_mw"],
                        "power_factor": item["power_factor"],
                        "circuits": item["circuits"],
                        "base_apparent_mva": item["base_apparent_mva"],
                        "base_per_circuit_mva": item["base_per_circuit_mva"],
                        "base_per_circuit_current_a": item[
                            "base_per_circuit_current_a"
                        ],
                        "per_circuit_design_mva": item["per_circuit_design_mva"],
                        "per_circuit_current_a": item["per_circuit_current_a"],
                        "simultaneity_applied_to_circuit": item[
                            "simultaneity_applied_to_circuit"
                        ],
                    }
                )


def _write_station_service_csv(result: dict[str, Any], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "name",
                "calculated_rated_kw",
                "duty",
                "simultaneous_kw",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for item in result["station_service"]["applicable_items"]:
            writer.writerow(
                {
                    "name": item["name"],
                    "calculated_rated_kw": item["calculated_rated_kw"],
                    "duty": item["duty"],
                    "simultaneous_kw": item.get("simultaneous_kw", ""),
                }
            )


def _write_markdown_summary(result: dict[str, Any], path: Path) -> None:
    load_35 = result["load_35kv"]
    load_10 = result["load_10kv"]
    transformer = result["main_transformer"]
    station = result["station_service"]

    lines = [
        "# 负荷、持续电流与变压器容量初算",
        "",
        "本文件由计算脚本生成。所有数值应在主接线与供电路径冻结后再转为最终设计值。",
        "",
        "## 综合负荷",
        "",
        "| 项目 | 结果 |",
        "| --- | ---: |",
        f"| 35kV 负荷视在功率原始合计 | {load_35['gross_apparent_mva']:.6f} MVA |",
        f"| 35kV 计 0.95 同时出力后 | {load_35['after_simultaneity_mva']:.6f} MVA |",
        f"| 35kV 再计 5% 线损 | {load_35['with_losses_mva']:.6f} MVA |",
        f"| 10kV 计 0.80 同时系数和 5% 线损 | {load_10['with_losses_mva']:.6f} MVA |",
        f"| 主变本期校核容量（35kV汇集负荷） | {transformer['total_required_mva']:.6f} MVA |",
        f"| 保守叠加10kV负荷的敏感性容量 | {transformer['sensitivity_including_10kv']['total_required_mva']:.6f} MVA |",
        "",
        "## 主变压器校验",
        "",
        "| 项目 | 结果 |",
        "| --- | ---: |",
        f"| 装机容量 | {transformer['installed_capacity_mva']:.3f} MVA |",
        f"| 正常每台承担 | {transformer['per_transformer_mva']:.6f} MVA |",
        f"| 正常负载率 | {transformer['normal_loading_percent']:.3f}% |",
        f"| N-1 单台可覆盖比例 | {transformer['n_minus_one_supply_percent']:.3f}% |",
        f"| N-1 需限发/缺口 | {transformer['n_minus_one_shortfall_mva']:.6f} MVA |",
        f"| 叠加10kV敏感性场景正常负载率 | {transformer['sensitivity_including_10kv']['normal_loading_percent']:.3f}% |",
        "",
        "## 35kV 单回线路基础电流",
        "",
        "| 回路类别 | 回路数 | 自身最大电流/A | 计5%线损设计电流/A |",
        "| --- | ---: | ---: | ---: |",
    ]
    for item in load_35["items"]:
        lines.append(
            f"| {item['label_zh']} | {item['circuits']} | "
            f"{item['base_per_circuit_current_a']:.3f} | "
            f"{item['per_circuit_current_a']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## 10kV 单回线路基础电流",
            "",
            "| 回路类别 | 自身最大电流/A | 计5%线损设计电流/A |",
            "| --- | ---: | ---: |",
        ]
    )
    for item in load_10["items"]:
        lines.append(
            f"| {item['label_zh']} | "
            f"{item['base_per_circuit_current_a']:.3f} | "
            f"{item['per_circuit_current_a']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## 所用电变压器初选",
            "",
            "| 项目 | 结果 |",
            "| --- | ---: |",
            f"| 连续适用负荷 | {station['continuous_applicable_kw']:.3f} kW |",
            f"| 短时适用负荷 | {station['short_time_applicable_kw']:.3f} kW |",
            f"| 明确标为经常的负荷 | {station['explicit_frequent_kw']:.3f} kW |",
            f"| 明确标为不经常的负荷 | {station['explicit_infrequent_kw']:.3f} kW |",
            f"| 未标频度的连续负荷 | {station['frequency_unspecified_kw']:.3f} kW |",
            f"| 基准场景所需容量 | {station['base_required_kva']:.3f} kVA |",
            f"| 经常短时负荷全投入场景 | {station['worst_frequent_required_kva']:.3f} kVA |",
            f"| 每台建议标准容量 | {station['recommended_each_transformer_kva']:.0f} kVA |",
            "",
            "初选建议为两台所用变、单母线分段、暗备用。0.80 功率因数属于显式假设，最终型号需结合实际设备功率因数、启动条件和教师口径复核。",
            "",
            "## 计算口径",
            "",
        ]
    )
    lines.extend(f"- {note}" for note in result["calculation_notes"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_outputs(result: dict[str, Any], output_dir: str | Path) -> list[Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    json_path = destination / "load_and_transformer_results.json"
    circuit_csv_path = destination / "circuit_currents.csv"
    station_csv_path = destination / "station_service_loads.csv"
    summary_path = destination / "load_and_transformer_summary.md"

    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_circuit_csv(result, circuit_csv_path)
    _write_station_service_csv(result, station_csv_path)
    _write_markdown_summary(result, summary_path)
    return [json_path, circuit_csv_path, station_csv_path, summary_path]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calculate load, circuit current, and transformer sizing."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/design_inputs.yaml"),
        help="Taskbook-derived YAML input.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("calculations/results"),
        help="Directory for generated JSON, CSV, and Markdown results.",
    )
    args = parser.parse_args()

    result = calculate_design(load_config(args.input))
    outputs = write_outputs(result, args.output_dir)
    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
