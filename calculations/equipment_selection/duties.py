from __future__ import annotations

import math
from typing import Any


def _items_by_name(result: dict[str, Any], voltage_key: str) -> dict[str, dict[str, Any]]:
    return {item["name"]: item for item in result[voltage_key]["items"]}


def _baseline_feeders(baseline: dict[str, Any]) -> list[dict[str, str]]:
    feeders: list[dict[str, str]] = []
    for section in baseline["connection_35kv"]["sections"]:
        for feeder in section["feeder_circuits"]:
            feeders.append(
                {
                    "id": feeder["id"],
                    "source_key": feeder["source_key"],
                    "section_id": section["id"],
                }
            )
    return feeders


def _section_currents(
    load_result: dict[str, Any], baseline: dict[str, Any]
) -> dict[str, dict[str, float]]:
    load_items = _items_by_name(load_result, "load_35kv")
    currents: dict[str, dict[str, float]] = {}
    group_factor = float(load_result["load_35kv"]["group_factor"])
    loss_factor = 1 + float(load_result["load_35kv"]["loss_rate"])

    for section in baseline["connection_35kv"]["sections"]:
        installed_base_current = 0.0
        for feeder in section["feeder_circuits"]:
            source = load_items[feeder["source_key"]]
            installed_base_current += float(
                source["base_per_circuit_current_a"]
            )
        currents[section["id"]] = {
            "installed_base_current_a": installed_base_current,
            "group_and_loss_current_a": (
                installed_base_current * group_factor * loss_factor
            ),
        }
    return currents


def build_fault_profiles(short_circuit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    points = short_circuit["points"]
    peak_factor = float(short_circuit["basis"]["peak_factor_k"])

    separated_220 = [
        points["SC-220-I-SEPARATE"],
        points["SC-220-II-SEPARATE"],
    ]
    closed_220 = points["SC-220-BUS-CLOSED"]
    profile_220 = {
        "status": "known_with_incomplete_scope",
        "mandatory_rms_ka": max(
            point["grid_symmetrical_current_ka"] for point in separated_220
        ),
        "conditional_rms_ka": closed_220["grid_symmetrical_current_ka"],
        "provisional_required_rms_ka": closed_220[
            "grid_symmetrical_current_ka"
        ],
        "advisory_rms_ka": None,
        "known_grid_peak_ka": closed_220["grid_peak_current_ka"],
        "course_total_peak_sensitivity_ka": None,
        "rms_scope": "grid_only_missing_220kv_renewable_contribution",
        "peak_scope": "grid_only_fixed_course_peak_factor",
        "final_breaking_scope_complete": False,
        "final_peak_scope_complete": False,
        "conditional_reason": "system_1_and_system_2_parallel_permission",
    }

    separated_35 = [
        points["SC-35-I-220-SEPARATE"],
        points["SC-35-II-220-SEPARATE"],
    ]
    closed_35 = [
        points["SC-35-I-220-CLOSED"],
        points["SC-35-II-220-CLOSED"],
    ]
    advisory_35 = points["SC-35-BOTH-TRANSFORMERS-SENSITIVITY"]

    def conservative_max(point: dict[str, Any]) -> float:
        return float(
            point["conservative_total_symmetrical_current_range_ka"][
                "maximum"
            ]
        )

    conditional_35_rms = max(conservative_max(point) for point in closed_35)
    profile_35 = {
        "status": "known_with_incomplete_peak_scope",
        "mandatory_rms_ka": max(
            conservative_max(point) for point in separated_35
        ),
        "conditional_rms_ka": conditional_35_rms,
        "provisional_required_rms_ka": conditional_35_rms,
        "advisory_rms_ka": conservative_max(advisory_35),
        "known_grid_peak_ka": max(
            float(point["grid_peak_current_ka"]) for point in closed_35
        ),
        "course_total_peak_sensitivity_ka": (
            math.sqrt(2) * peak_factor * conditional_35_rms
        ),
        "advisory_course_peak_sensitivity_ka": (
            math.sqrt(2) * peak_factor * conservative_max(advisory_35)
        ),
        "rms_scope": "grid_plus_renewable_arithmetic_upper_bound",
        "peak_scope": (
            "course_only_fixed_k_applied_to_conservative_rms_not_final"
        ),
        "final_breaking_scope_complete": False,
        "final_peak_scope_complete": False,
        "conditional_reason": "system_1_and_system_2_parallel_permission",
        "advisory_reason": "healthy_main_transformer_low_sides_parallel_prohibited",
    }

    return {
        "220_bus": profile_220,
        "35_bus": profile_35,
        "10_bus": {
            "status": "pending_input",
            "mandatory_rms_ka": None,
            "conditional_rms_ka": None,
            "provisional_required_rms_ka": None,
            "advisory_rms_ka": None,
            "known_grid_peak_ka": None,
            "course_total_peak_sensitivity_ka": None,
            "rms_scope": "pending_35_10_5kv_transformer_rating_and_mvar",
            "peak_scope": "pending",
            "final_breaking_scope_complete": False,
            "final_peak_scope_complete": False,
        },
    }


def _continuous_duty(
    duty: dict[str, Any],
    load_result: dict[str, Any],
    section_currents: dict[str, dict[str, float]],
) -> dict[str, Any]:
    duty_type = duty["type"]
    main_transformer = load_result["main_transformer"]
    if duty_type == "220_line_n_minus_one":
        return {
            "status": "known",
            "required_current_a": load_result["outgoing_220kv"][
                "single_circuit_contingency_current_a"
            ],
            "source": "outgoing_220kv.single_circuit_contingency_current_a",
        }
    if duty_type == "main_transformer_220kv":
        return {
            "status": "known",
            "required_current_a": main_transformer[
                "rated_current_with_1_05_margin_a"
            ]["220kv"],
            "source": "main_transformer.rated_current_with_1_05_margin_a.220kv",
        }
    if duty_type == "main_transformer_35kv":
        return {
            "status": "known",
            "required_current_a": main_transformer[
                "rated_current_with_1_05_margin_a"
            ]["35kv"],
            "source": "main_transformer.rated_current_with_1_05_margin_a.35kv",
        }
    if duty_type == "pending_topology_flow":
        return {
            "status": "pending_topology_flow",
            "required_current_a": None,
            "source": "explicit_power_flow_and_bay_placement_required",
        }
    if duty_type == "pending_10kv_source_transformer_rating":
        return {
            "status": "pending_input",
            "required_current_a": None,
            "source": "10kv_reactive_compensation_and_35_10_5kv_transformer_rating_required",
        }
    if duty_type == "section_allocated_base":
        section_id = duty["section_id"]
        section = section_currents[section_id]
        return {
            "status": "known",
            "required_current_a": section["installed_base_current_a"],
            "source": f"baseline_feeder_allocation.{section_id}",
            "group_and_loss_current_a": section["group_and_loss_current_a"],
        }
    if duty_type in {"35kv_feeder_source", "10kv_feeder_source"}:
        voltage_key = "load_35kv" if duty_type.startswith("35kv") else "load_10kv"
        source_key = duty["source_key"]
        item = _items_by_name(load_result, voltage_key)[source_key]
        return {
            "status": "known",
            "required_current_a": item["per_circuit_current_a"],
            "source": f"{voltage_key}.items.{source_key}.per_circuit_current_a",
        }
    raise ValueError(f"unsupported continuous duty type: {duty_type}")


def build_duty_registry(
    *,
    selection: dict[str, Any],
    load_result: dict[str, Any],
    short_circuit: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    profiles = build_fault_profiles(short_circuit)
    section_currents = _section_currents(load_result, baseline)
    feeders = _baseline_feeders(baseline)
    feeder_ids = {feeder["id"] for feeder in feeders}
    if len(feeders) != 12 or len(feeder_ids) != 12:
        raise ValueError("expected 12 unique in-service 35kV feeders")

    groups: dict[str, dict[str, Any]] = {}
    for group in selection["circuit_groups"]:
        members = list(group.get("members", []))
        member_source = group.get("member_source")
        if member_source:
            source_key = member_source["baseline_feeders_where_source_key"]
            members = [
                feeder["id"]
                for feeder in feeders
                if feeder["source_key"] == source_key
            ]
            if not members:
                raise ValueError(
                    f"circuit group {group['id']} resolved to no feeder members"
                )

        fault_profile_id = group["fault_profile"]
        groups[group["id"]] = {
            "id": group["id"],
            "role": group["role"],
            "voltage_class": group["voltage_class"],
            "members": members,
            "continuous": _continuous_duty(
                group["continuous_duty"], load_result, section_currents
            ),
            "fault_profile_id": fault_profile_id,
            "fault": profiles[fault_profile_id],
        }

    return {
        "fault_profiles": profiles,
        "section_allocated_currents": section_currents,
        "circuit_groups": groups,
    }
