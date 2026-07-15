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
    lines = [
        "# 主要电气设备额定值预筛选",
        "",
        "本文件由脚本生成。当前只完成额定值等级的条件化预筛选，不代表设备型号已经定型。",
        "",
        f"- 数值预筛选总状态：`{result['numeric_precheck_status']}`",
        f"- 最终选型总状态：`{result['final_selection_status']}`",
        "- 热稳定已按1.10s课程等值时间进行I²t预校核；精确型号、41℃修正、外绝缘及标准短路模型仍保持待定，不按零或自动通过处理。",
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
            "## 关键边界",
            "",
            "- 220kV线路一回退出时的持续电流735.559A用于线路间隔预筛；220kV分段回路潮流仍等待明确间隔布置和潮流方向。",
            "- 35kV I、II段按实际馈线分配计算，不把4623.515A全站总电流或2311.758A简单均分值当成物理母线段职责。",
            "- 35kV条件性预校核采用计入新能源RMS上界的16.291kA；两台健康主变低压侧并列25.694kA仅作禁止方式提示。",
            "- 220kV新能源与10kV SVG贡献已按额定电流1.1～1.2倍的课程上界计入；固定k得到的综合峰值仍只作设备等级预筛。",
            "- 热稳定采用后备保护1.00s与全开断0.08s向上取1.10s，通过I²t与候选设备额定短时耐受能力比较。",
            "- 海拔按≤1000m、污秽按d级冻结；41℃电流修正、厂家精确型号、外绝缘爬距和图纸外形尺寸仍需精确资料，因此最终选型保持pending。",
            "- 10kV采用2×±12Mvar SVG和2×31.5MVA T10；单电源条件性综合上限15.638kA，禁止的两台健康T10并列综合上限28.472kA，设备按31.5kA/80kA等级预筛。",
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
