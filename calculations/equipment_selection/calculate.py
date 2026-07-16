from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

from calculations.equipment_selection.checks import (
    combine_status,
    minimum_check,
    not_applicable_check,
    pending_check,
)
from calculations.equipment_selection.duties import build_duty_registry
from calculations.equipment_selection.models import (
    file_sha256,
    load_json,
    load_yaml,
    validate_configuration,
)
from calculations.equipment_selection.report import write_outputs


def _exact_course_check(
    *, check_id: str, required: Any, available: Any, unit: str | None, note: str
) -> dict[str, Any]:
    passed = available == required
    margin = None
    if isinstance(required, (int, float)) and isinstance(available, (int, float)):
        margin = float(available) - float(required)
    return {
        "id": check_id,
        "status": "provisional_pass" if passed else "fail",
        "required": required,
        "available": available,
        "unit": unit,
        "margin": margin,
        "note": note,
    }


def _resolve_interface_coverage(
    coverage: dict[str, Any], duty_registry: dict[str, Any]
) -> dict[str, Any]:
    groups = duty_registry["circuit_groups"]
    resolved_members: list[str] = []
    for group_id in coverage["covered_circuit_groups"]:
        if group_id not in groups:
            raise ValueError(
                f"{coverage['id']} references unknown circuit group {group_id}"
            )
        resolved_members.extend(groups[group_id]["members"])
    if len(resolved_members) != len(set(resolved_members)):
        raise ValueError(
            f"{coverage['id']} resolves duplicate members across circuit groups"
        )
    configured_members = list(coverage["covered_members"])
    illegal_members = set(configured_members) - set(resolved_members)
    if illegal_members:
        raise ValueError(
            f"{coverage['id']} references members outside its circuit groups: "
            f"{sorted(illegal_members)}"
        )
    if coverage.get("coverage_mode") == "all_group_members" and set(
        configured_members
    ) != set(resolved_members):
        raise ValueError(
            f"{coverage['id']} must cover every resolved circuit-group member"
        )
    return {
        **coverage,
        "resolved_group_members": resolved_members,
        "coverage_check_status": "provisional_pass",
    }


def _evaluate_assignment(
    *,
    assignment: dict[str, Any],
    group: dict[str, Any],
    candidate: dict[str, Any],
    voltage_class: dict[str, Any],
    design_inputs: dict[str, Any],
) -> dict[str, Any]:
    ratings = candidate["ratings"]
    fault = group["fault"]
    continuous = group["continuous"]
    service = candidate.get("service_conditions", {})
    device_kind = assignment["device_kind"]

    numeric_checks: list[dict[str, Any]] = []
    final_checks: list[dict[str, Any]] = []

    voltage_check = minimum_check(
        check_id="nominal_voltage_class",
        required=float(voltage_class["nominal_kv"]),
        available=ratings.get("highest_voltage_kv"),
        unit="kV",
        provisional=True,
        note=(
            "Nominal-voltage class precheck."
        ),
    )
    numeric_checks.append(voltage_check)
    final_checks.append(voltage_check)
    if voltage_class.get("highest_system_voltage_kv") is None:
        final_checks.append(
            pending_check(
                "highest_system_voltage",
                "Highest system voltage must be verified from the applicable standard.",
            )
        )
    else:
        final_checks.append(
            minimum_check(
                check_id="highest_system_voltage",
                required=float(voltage_class["highest_system_voltage_kv"]),
                available=ratings.get("highest_voltage_kv"),
                unit="kV",
                provisional=False,
                note="Final voltage-class check.",
            )
        )

    rated_current = ratings.get("continuous_current_a")
    current_correction = service.get("current_correction_factor")
    effective_current = rated_current
    if rated_current is not None and current_correction is not None:
        effective_current = float(rated_current) * float(current_correction)
    current_check = minimum_check(
        check_id="continuous_current",
        required=continuous.get("required_current_a"),
        available=effective_current,
        unit="A",
        provisional=True,
        note=(
            "Candidate current after one configured correction factor; "
            "missing verified correction keeps the final check pending."
        ),
    )
    numeric_checks.append(current_check)
    final_checks.append(current_check)
    if current_correction is None:
        final_checks.append(
            pending_check(
                "current_correction_factor",
                "Verified 41C and installation current correction is not available.",
            )
        )

    provisional_rms = fault.get("provisional_required_rms_ka")
    if device_kind in {"circuit_breaker", "switchgear"}:
        breaking_check = minimum_check(
            check_id="short_circuit_breaking_current",
            required=provisional_rms,
            available=ratings.get("short_circuit_breaking_current_ka_rms"),
            unit="kA rms",
            provisional=True,
            note=(
                "Initial symmetrical current is retained as a conservative course precheck at the 0.09s contact-separation assumption."
            ),
        )
        numeric_checks.append(breaking_check)
        final_checks.append(breaking_check)
        making_required = fault.get("course_total_peak_sensitivity_ka")
        if making_required is None:
            making_required = fault.get("known_grid_peak_ka")
        making_check = minimum_check(
            check_id="short_circuit_making_current",
            required=making_required,
            available=ratings.get("short_circuit_making_current_ka_peak"),
            unit="kA peak",
            provisional=True,
        note="Course-only peak precheck using the fixed-k converter-inclusive RMS upper bound.",
        )
        numeric_checks.append(making_check)
        final_checks.append(making_check)
    else:
        final_checks.append(
            not_applicable_check(
                "short_circuit_breaking_current",
                "Disconnectors do not receive a fault-current breaking check.",
            )
        )

    peak_required = fault.get("course_total_peak_sensitivity_ka")
    if peak_required is None:
        peak_required = fault.get("known_grid_peak_ka")
    peak_check = minimum_check(
        check_id="peak_withstand_current",
        required=peak_required,
        available=ratings.get("peak_withstand_current_ka"),
        unit="kA peak",
        provisional=True,
        note="Dynamic course precheck; exact R/X and converter peak treatment remain for final engineering review.",
    )
    numeric_checks.append(peak_check)
    final_checks.append(peak_check)

    short_time = ratings.get("short_time_withstand", {})
    short_time_check = minimum_check(
        check_id="short_time_withstand_current",
        required=provisional_rms,
        available=short_time.get("current_ka_rms"),
        unit="kA rms",
        provisional=True,
        note="Short-time current-level screen before the explicit I²t comparison.",
    )
    numeric_checks.append(short_time_check)
    final_checks.append(short_time_check)
    thermal_duration = float(
        design_inputs["calculation_rules"]["protection_and_breaker_times"][
            "thermal_equivalent_duration_s"
        ]
    )
    rated_short_time_current = short_time.get("current_ka_rms")
    rated_short_time_duration = short_time.get("duration_s")
    required_i2t = (
        float(provisional_rms) ** 2 * thermal_duration
        if provisional_rms is not None
        else None
    )
    available_i2t = (
        float(rated_short_time_current) ** 2 * float(rated_short_time_duration)
        if rated_short_time_current is not None
        and rated_short_time_duration is not None
        else None
    )
    thermal_check = minimum_check(
        check_id="thermal_energy",
        required=required_i2t,
        available=available_i2t,
        unit="kA^2 s",
        provisional=True,
        note=(
            f"Course I²t screen uses {thermal_duration:.2f}s, based on backup protection plus total breaker clearing time rounded upward."
        ),
    )
    numeric_checks.append(thermal_check)
    final_checks.append(thermal_check)

    natural = design_inputs["natural_conditions"]
    temperature_basis = service.get("temperature_basis", "site_maximum")
    if temperature_basis == "indoor_controlled":
        project_temperature = float(
            natural["indoor_switchgear_max_temperature_c"]
        )
        temperature_note = (
            "Controlled-indoor maximum temperature course basis; exact HVAC and "
            "manufacturer temperature-rise confirmation remain pending."
        )
    else:
        project_temperature = float(natural["maximum_temperature_c"])
        temperature_note = "Maximum site service-temperature check."
    max_ambient = service.get("max_ambient_c")
    if max_ambient is None:
        final_checks.append(
            pending_check(
                "ambient_temperature",
                "Candidate ambient limit and 41C current correction are not verified.",
            )
        )
    else:
        final_checks.append(
            minimum_check(
                check_id="ambient_temperature",
                required=project_temperature,
                available=float(max_ambient),
                unit="degC",
                provisional=False,
                note=temperature_note,
            )
        )

    project_altitude = natural.get("altitude_m")
    candidate_altitude = service.get("max_altitude_m")
    if project_altitude is None:
        final_checks.append(
            pending_check(
                "altitude",
                "Project altitude is not available.",
            )
        )
    elif candidate_altitude is None:
        final_checks.append(
            pending_check(
                "altitude",
                "The course-design altitude is 1000m, but the exact candidate service limit is not verified.",
            )
        )
    else:
        final_checks.append(
            minimum_check(
                check_id="altitude",
                required=float(project_altitude),
                available=float(candidate_altitude),
                unit="m",
                provisional=False,
                note="Maximum installation-altitude check.",
            )
        )

    project_pollution = natural.get("pollution_level")
    candidate_pollution = service.get("pollution_level")
    if project_pollution is None:
        final_checks.append(
            pending_check("pollution_level", "Project pollution level is unavailable.")
        )
    elif candidate_pollution is None:
        final_checks.append(
            pending_check(
                "pollution_level",
                "Project course assumption is pollution class d; exact candidate external-insulation data are not verified.",
            )
        )
    else:
        pollution_rank = {value: index for index, value in enumerate("abcde", start=1)}
        required_rank = pollution_rank.get(str(project_pollution).lower())
        available_rank = pollution_rank.get(str(candidate_pollution).lower())
        final_checks.append(
            minimum_check(
                check_id="pollution_level",
                required=required_rank,
                available=available_rank,
                unit="class a-e",
                provisional=False,
                note="External-insulation pollution-class check.",
            )
        )

    if not fault.get("final_breaking_scope_complete", False):
        final_checks.append(
            pending_check(
                "fault_rms_scope",
                "Renewable contribution or contact-separation current scope is incomplete.",
            )
        )
    if not fault.get("final_peak_scope_complete", False):
        final_checks.append(
            pending_check(
                "fault_peak_scope",
                "Renewable dynamic peak and standard peak-factor treatment are incomplete.",
            )
        )

    evidence_status = candidate["evidence"]["status"]
    if evidence_status != "exact_model_verified":
        final_checks.append(
            pending_check(
                "candidate_evidence",
                f"Candidate evidence status is {evidence_status}; exact model evidence is required.",
            )
        )

    numeric_status = combine_status(
        [check["status"] for check in numeric_checks]
    )
    final_status = combine_status([check["status"] for check in final_checks])
    return {
        "id": assignment["id"],
        "circuit_group": assignment["circuit_group"],
        "device_kind": device_kind,
        "duty": group,
        "candidate": candidate,
        "numeric_checks": numeric_checks,
        "final_checks": final_checks,
        "numeric_precheck_status": numeric_status,
        "final_selection_status": final_status,
    }


def _aggregate_group_requirements(
    *,
    group_ids: list[str],
    duty_registry: dict[str, Any],
    voltage_classes: dict[str, Any],
) -> dict[str, Any]:
    groups = duty_registry["circuit_groups"]
    selected_groups: list[dict[str, Any]] = []
    for group_id in group_ids:
        if group_id not in groups:
            raise ValueError(f"unknown course-completion circuit group: {group_id}")
        selected_groups.append(groups[group_id])

    def maximum(values: list[float | None]) -> float | None:
        known = [float(value) for value in values if value is not None]
        return max(known) if known else None

    peak_values: list[float | None] = []
    for group in selected_groups:
        fault = group["fault"]
        peak = fault.get("course_total_peak_sensitivity_ka")
        if peak is None:
            peak = fault.get("known_grid_peak_ka")
        peak_values.append(peak)

    return {
        "covered_circuit_groups": group_ids,
        "required_continuous_current_a": maximum(
            [group["continuous"].get("required_current_a") for group in selected_groups]
        ),
        "required_short_circuit_rms_ka": maximum(
            [group["fault"].get("provisional_required_rms_ka") for group in selected_groups]
        ),
        "required_peak_current_ka": maximum(peak_values),
        "required_highest_system_voltage_kv": maximum(
            [
                voltage_classes[group["voltage_class"]].get(
                    "highest_system_voltage_kv"
                )
                for group in selected_groups
            ]
        ),
    }


def _evaluate_course_busbars(
    *,
    specifications: list[dict[str, Any]],
    common: dict[str, Any],
    duty_registry: dict[str, Any],
    voltage_classes: dict[str, Any],
) -> list[dict[str, Any]]:
    thermal_constant = float(common["thermal_stability_constant_c"])
    thermal_duration = float(common["thermal_equivalent_duration_s"])
    evaluated: list[dict[str, Any]] = []

    for specification in specifications:
        requirements = _aggregate_group_requirements(
            group_ids=list(specification["circuit_groups"]),
            duty_registry=duty_registry,
            voltage_classes=voltage_classes,
        )
        geometry = specification["geometry"]
        geometry_type = geometry["type"]
        section_modulus_mm3: float | None = None
        if geometry_type == "tube":
            outer = float(geometry["outer_diameter_mm"])
            inner = float(geometry["inner_diameter_mm"])
            if inner >= outer:
                raise ValueError(
                    f"{specification['id']} tube inner diameter must be smaller than outer diameter"
                )
            area_mm2 = math.pi * (outer**2 - inner**2) / 4
            section_modulus_mm3 = math.pi * (outer**4 - inner**4) / (
                32 * outer
            )
        elif geometry_type == "rectangular_bundle":
            area_mm2 = (
                float(geometry["count_per_phase"])
                * float(geometry["width_mm"])
                * float(geometry["thickness_mm"])
            )
        else:
            raise ValueError(
                f"{specification['id']} has unsupported busbar geometry {geometry_type}"
            )

        correction = specification["temperature_correction"]
        current_correction_factor = 1.0
        if correction.get("enabled", False):
            ambient = float(correction["project_ambient_c"])
            reference = float(specification["reference_ampacity"]["ambient_c"])
            allowable = float(correction["allowable_conductor_temperature_c"])
            if not reference < allowable or ambient >= allowable:
                raise ValueError(
                    f"{specification['id']} has an invalid temperature-correction basis"
                )
            current_correction_factor = math.sqrt(
                (allowable - ambient) / (allowable - reference)
            )

        reference_ampacity = float(
            specification["reference_ampacity"]["current_a"]
        )
        corrected_ampacity = reference_ampacity * current_correction_factor
        required_rms = requirements["required_short_circuit_rms_ka"]
        thermal_allowable_ka = (
            thermal_constant * area_mm2 / (1000 * math.sqrt(thermal_duration))
        )
        minimum_thermal_area_mm2 = (
            float(required_rms)
            * 1000
            * math.sqrt(thermal_duration)
            / thermal_constant
            if required_rms is not None
            else None
        )

        checks = [
            minimum_check(
                check_id="continuous_ampacity",
                required=requirements["required_continuous_current_a"],
                available=corrected_ampacity,
                unit="A",
                provisional=True,
                note="Course ampacity check using the configured table value and temperature basis.",
            ),
            minimum_check(
                check_id="thermal_stability",
                required=required_rms,
                available=thermal_allowable_ka,
                unit="kA rms at 1.10s",
                provisional=True,
                note="Adiabatic course check using C=87 and t=1.10s.",
            ),
        ]
        calculated: dict[str, Any] = {
            "cross_section_area_mm2": area_mm2,
            "section_modulus_mm3": section_modulus_mm3,
            "current_correction_factor": current_correction_factor,
            "corrected_ampacity_a": corrected_ampacity,
            "thermal_allowable_current_ka": thermal_allowable_ka,
            "minimum_thermal_area_mm2": minimum_thermal_area_mm2,
        }
        engineering_pending_checks: list[dict[str, Any]] = []

        dynamic = specification.get("dynamic_check", {})
        if dynamic.get("enabled", False):
            if section_modulus_mm3 is None:
                raise ValueError(
                    f"{specification['id']} dynamic check requires a section modulus"
                )
            peak_current_ka = requirements["required_peak_current_ka"]
            phase_spacing_m = float(dynamic["phase_spacing_m"])
            frozen_layout_spacing_m = float(
                dynamic.get("frozen_layout_phase_spacing_m", phase_spacing_m)
            )
            if phase_spacing_m > frozen_layout_spacing_m:
                raise ValueError(
                    f"{specification['id']} calculation spacing must not exceed the frozen layout spacing"
                )
            support_span_m = float(dynamic["support_span_m"])
            amplification = float(dynamic["dynamic_amplification_factor"])
            force_n_per_m = (
                2e-7 * (float(peak_current_ka) * 1000) ** 2 / phase_spacing_m
                if peak_current_ka is not None
                else None
            )
            design_force_n_per_m = (
                force_n_per_m * amplification if force_n_per_m is not None else None
            )
            bending_moment_nm = (
                design_force_n_per_m * support_span_m**2 / 8
                if design_force_n_per_m is not None
                else None
            )
            bending_stress_mpa = (
                bending_moment_nm * 1000 / section_modulus_mm3
                if bending_moment_nm is not None
                else None
            )
            calculated["dynamic"] = {
                "calculation_phase_spacing_m": phase_spacing_m,
                "frozen_layout_phase_spacing_m": frozen_layout_spacing_m,
                "base_electromagnetic_force_n_per_m": force_n_per_m,
                "design_force_n_per_m": design_force_n_per_m,
                "maximum_bending_moment_nm": bending_moment_nm,
                "calculated_bending_stress_mpa": bending_stress_mpa,
            }
            checks.append(
                minimum_check(
                    check_id="simplified_dynamic_bending_stress",
                    required=bending_stress_mpa,
                    available=float(dynamic["allowable_bending_stress_mpa"]),
                    unit="MPa",
                    provisional=True,
                    note=(
                        "Simplified simply-supported uniform-load course check; "
                        "support resonance and connection forces remain pending."
                    ),
                )
            )
        elif dynamic.get("status") == "pending":
            engineering_pending_checks.append(
                pending_check(
                    "busbar_mechanical_dynamic_stability",
                    dynamic.get(
                        "reason",
                        "Busbar support geometry and mechanical dynamic stability remain pending.",
                    ),
                )
            )

        corona = specification.get("corona_check", {})
        if corona.get("enabled", False):
            if geometry_type != "tube":
                raise ValueError(
                    f"{specification['id']} Peek corona check currently requires tube geometry"
                )
            radius_cm = float(geometry["outer_diameter_mm"]) / 20
            spacing_cm = float(dynamic["phase_spacing_m"]) * 100
            critical_phase_voltage_kv = (
                float(corona["peek_constant_kv_per_cm"])
                * float(corona["surface_factor"])
                * float(corona["atmospheric_density_factor"])
                * radius_cm
                * math.log(spacing_cm / radius_cm)
            )
            highest_phase_voltage_kv = (
                float(
                    voltage_classes[specification["voltage_class"]][
                        "highest_system_voltage_kv"
                    ]
                )
                / math.sqrt(3)
            )
            calculated["corona"] = {
                "conductor_radius_cm": radius_cm,
                "phase_spacing_cm": spacing_cm,
                "critical_disruptive_phase_voltage_kv": critical_phase_voltage_kv,
                "highest_operating_phase_voltage_kv": highest_phase_voltage_kv,
            }
            checks.append(
                minimum_check(
                    check_id="simplified_corona_inception",
                    required=highest_phase_voltage_kv,
                    available=critical_phase_voltage_kv,
                    unit="kV phase-to-earth rms",
                    provisional=True,
                    note=(
                        "Peek-formula course screen; surface condition, weather, radio "
                        "interference and audible-noise design remain pending."
                    ),
                )
            )

        evaluated.append(
            {
                **specification,
                "requirements": requirements,
                "calculated": calculated,
                "checks": checks,
                "engineering_pending_checks": engineering_pending_checks,
                "course_precheck_status": combine_status(
                    [check["status"] for check in checks]
                ),
            }
        )
    return evaluated


def _evaluate_course_arresters(
    *,
    specifications: list[dict[str, Any]],
    candidates: dict[str, dict[str, Any]],
    voltage_classes: dict[str, Any],
    duty_registry: dict[str, Any],
) -> list[dict[str, Any]]:
    evaluated: list[dict[str, Any]] = []
    for specification in specifications:
        candidate = candidates[specification["candidate_id"]]
        arrester = candidate["ratings"]["arrester"]
        highest_system_voltage = float(
            voltage_classes[specification["voltage_class"]][
                "highest_system_voltage_kv"
            ]
        )
        required_continuous_voltage = highest_system_voltage * float(
            specification["required_continuous_voltage_factor_to_um"]
        )
        continuous_voltage = float(arrester["continuous_operating_voltage_kv"])
        residual_voltage = float(arrester["lightning_residual_voltage_kv"])
        protected_liwv = float(specification["protected_equipment_liwv_kv"])
        protection_ratio = protected_liwv / residual_voltage
        checks = [
            minimum_check(
                check_id="continuous_operating_voltage",
                required=required_continuous_voltage,
                available=continuous_voltage,
                unit="kV rms",
                provisional=True,
                note=specification["continuous_voltage_basis"],
            ),
            minimum_check(
                check_id="lightning_protection_ratio",
                required=float(specification["minimum_protection_ratio"]),
                available=protection_ratio,
                unit="p.u. LIWV/residual voltage",
                provisional=True,
                note="Course insulation-coordination margin screen.",
            ),
        ]
        interface_coverage = [
            _resolve_interface_coverage(item, duty_registry)
            for item in specification.get("interface_coverage", [])
        ]
        evaluated.append(
            {
                **specification,
                "interface_coverage": interface_coverage,
                "model": candidate["model"],
                "evidence_status": candidate["evidence"]["status"],
                "ratings": arrester,
                "calculated": {
                    "required_continuous_voltage_kv": required_continuous_voltage,
                    "continuous_voltage_margin_kv": (
                        continuous_voltage - required_continuous_voltage
                    ),
                    "protection_ratio": protection_ratio,
                    "protection_margin_percent": (protection_ratio - 1) * 100,
                },
                "checks": checks,
                "course_precheck_status": combine_status(
                    [check["status"] for check in checks]
                ),
            }
        )
    return evaluated


def _evaluate_grounding_source_interlock(
    specification: dict[str, Any], duty_registry: dict[str, Any]
) -> dict[str, Any]:
    evaluated_levels: list[dict[str, Any]] = []
    statuses: list[str] = []
    for item in specification["voltage_levels"]:
        section_count = len(item["section_ids"])
        source_count = len(item["source_ids"])
        bus_tie_group = duty_registry["circuit_groups"][
            item["bus_tie_circuit_group"]
        ]
        checks = [
            _exact_course_check(
                check_id="grounding_normal_one_source_per_section",
                required=section_count,
                available=int(item["normal_sources_in_service"]),
                unit="sources",
                note="Normal sectionalized operation keeps one grounding source on each energized section.",
            ),
            _exact_course_check(
                check_id="grounding_source_count_matches_sections",
                required=section_count,
                available=source_count,
                unit="sources",
                note="Each bus section has one dedicated grounding-transformer and resistor set.",
            ),
            _exact_course_check(
                check_id="grounding_transfer_single_healthy_source",
                required=1,
                available=int(item["transfer_sources_in_service"]),
                unit="sources",
                note="Before bus-tie closure, the receiving or faulted section source is opened and only the healthy-side source remains.",
            ),
            _exact_course_check(
                check_id="grounding_restoration_one_source_per_section",
                required=section_count,
                available=int(item["restored_sources_in_service"]),
                unit="sources",
                note="After sectionalized operation is restored, each energized section regains one grounding source.",
            ),
            _exact_course_check(
                check_id="grounding_parallel_interlock_defined",
                required=True,
                available=(
                    "two_grounding_sources"
                    in str(item.get("prohibited_state", ""))
                    and "only_the_healthy_source_side"
                    in str(item.get("close_permissive", ""))
                ),
                unit=None,
                note="The bus tie cannot close with both section grounding sources connected in parallel.",
            ),
        ]
        status = combine_status([check["status"] for check in checks])
        statuses.append(status)
        evaluated_levels.append(
            {
                **item,
                "bus_tie_role": bus_tie_group["role"],
                "checks": checks,
                "course_precheck_status": status,
            }
        )
    return {
        **specification,
        "voltage_levels": evaluated_levels,
        "course_precheck_status": combine_status(statuses),
    }


def _evaluate_grounding_packages(
    *,
    specifications: list[dict[str, Any]],
    candidates: dict[str, dict[str, Any]],
    duty_registry: dict[str, Any],
    voltage_classes: dict[str, Any],
) -> list[dict[str, Any]]:
    evaluated: list[dict[str, Any]] = []
    for specification in specifications:
        voltage_class = voltage_classes[specification["voltage_class"]]
        candidate = candidates[specification["candidate_id"]]
        candidate_package = candidate["ratings"]["grounding_package"]
        group = duty_registry["circuit_groups"][specification["circuit_group"]]

        line_voltage_kv = float(specification["nominal_line_voltage_kv"])
        fault_current_a = float(specification["target_ground_fault_current_a"])
        duration_s = float(specification["short_time_s"])
        phase_voltage_kv = line_voltage_kv / math.sqrt(3)
        calculated_resistance_ohm = phase_voltage_kv * 1000 / fault_current_a
        short_time_equivalent_power_kva = phase_voltage_kv * fault_current_a
        short_time_energy_mj = short_time_equivalent_power_kva * duration_s / 1000
        overload_factor = float(specification["short_time_overload_factor"])
        minimum_transformer_capacity_kva = (
            short_time_equivalent_power_kva / overload_factor
        )
        configured_resistance_ohm = float(specification["target_resistance_ohm"])
        resistance_deviation_percent = (
            abs(configured_resistance_ohm - calculated_resistance_ohm)
            / calculated_resistance_ohm
            * 100
        )
        candidate_resistance_ohm = float(candidate_package["resistor_ohm_approx"])
        candidate_resistance_deviation_percent = (
            abs(candidate_resistance_ohm - calculated_resistance_ohm)
            / calculated_resistance_ohm
            * 100
        )
        phase_ct = specification["phase_ct_target"]
        neutral_ct = specification["neutral_ct_target"]
        checks = [
            _exact_course_check(
                check_id="grounding_package_nominal_voltage",
                required=float(voltage_class["nominal_kv"]),
                available=line_voltage_kv,
                unit="kV",
                note="Grounding-resistor arithmetic uses nominal line voltage and phase-to-earth voltage U/sqrt(3).",
            ),
            minimum_check(
                check_id="grounding_resistance_deviation",
                required=resistance_deviation_percent,
                available=float(
                    specification["maximum_resistance_deviation_percent"]
                ),
                unit="percent",
                provisional=True,
                note="Configured course resistance is checked against Uphase/Ig.",
            ),
            minimum_check(
                check_id="grounding_transformer_short_time_capacity",
                required=minimum_transformer_capacity_kva,
                available=float(
                    specification["selected_transformer_capacity_kva_each"]
                ),
                unit="kVA",
                provisional=True,
                note="Minimum transformer capacity equals the 10s equivalent power divided by the configured short-time overload factor.",
            ),
            _exact_course_check(
                check_id="grounding_feeder_fixed_course_current",
                required=fault_current_a,
                available=float(group["continuous"]["required_current_a"]),
                unit="A",
                note="Grounding-transformer feeder switchgear uses the frozen course current target.",
            ),
            _exact_course_check(
                check_id="grounding_package_quantity_per_section",
                required=len(specification["section_ids"]),
                available=int(specification["quantity"]),
                unit="sets",
                note="One package is provided for each bus section.",
            ),
            minimum_check(
                check_id="grounding_phase_ct_primary_target",
                required=fault_current_a,
                available=float(phase_ct["primary_rated_current_a"]),
                unit="A primary",
                provisional=True,
                note="Phase CT course target covers the feeder current target; exact burden and saturation remain pending.",
            ),
            minimum_check(
                check_id="grounding_neutral_ct_primary_target",
                required=fault_current_a,
                available=float(neutral_ct["primary_rated_current_a"]),
                unit="A primary",
                provisional=True,
                note="Neutral CT course target covers the limited ground-fault current; exact burden and saturation remain pending.",
            ),
            minimum_check(
                check_id="grounding_catalog_current_target",
                required=fault_current_a,
                available=float(candidate_package["ground_fault_current_a"]),
                unit="A",
                provisional=True,
                note="Catalog row is a course target package, not an exact manufacturer model.",
            ),
            _exact_course_check(
                check_id="grounding_catalog_connection_target",
                required=specification["grounding_transformer_connection"],
                available=candidate_package["connection"],
                unit=None,
                note="Catalog course target uses the same ZN neutral-forming connection.",
            ),
            minimum_check(
                check_id="grounding_catalog_duration_target",
                required=duration_s,
                available=float(candidate_package["duration_s"]),
                unit="s",
                provisional=True,
                note="Course target package retains the required resistor duration.",
            ),
            minimum_check(
                check_id="grounding_catalog_capacity_target",
                required=float(
                    specification["selected_transformer_capacity_kva_each"]
                ),
                available=float(candidate_package["transformer_capacity_kva"]),
                unit="kVA",
                provisional=True,
                note="Catalog target and selected course transformer capacity are aligned.",
            ),
            minimum_check(
                check_id="grounding_catalog_resistance_deviation",
                required=candidate_resistance_deviation_percent,
                available=float(
                    specification["maximum_resistance_deviation_percent"]
                ),
                unit="percent",
                provisional=True,
                note="Catalog target resistance is consistent with Uphase/Ig within the course tolerance.",
            ),
        ]
        evaluated.append(
            {
                **specification,
                "candidate": {
                    "id": candidate["id"],
                    "kind": candidate["kind"],
                    "evidence_status": candidate["evidence"]["status"],
                    "final_vendor_boundary": candidate["final_vendor_boundary"],
                },
                "calculated": {
                    "phase_to_earth_voltage_kv": phase_voltage_kv,
                    "resistance_ohm": calculated_resistance_ohm,
                    "configured_resistance_deviation_percent": resistance_deviation_percent,
                    "short_time_equivalent_power_kva": short_time_equivalent_power_kva,
                    "short_time_equivalent_power_mva": short_time_equivalent_power_kva
                    / 1000,
                    "short_time_energy_mj": short_time_energy_mj,
                    "minimum_transformer_capacity_kva_at_overload_factor": minimum_transformer_capacity_kva,
                },
                "checks": checks,
                "course_precheck_status": combine_status(
                    [check["status"] for check in checks]
                ),
            }
        )
    return evaluated


def _evaluate_course_zcts(
    *,
    specifications: list[dict[str, Any]],
    duty_registry: dict[str, Any],
    grounding_packages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grounding_current_by_voltage = {
        item["voltage_class"]: float(item["target_ground_fault_current_a"])
        for item in grounding_packages
    }
    evaluated: list[dict[str, Any]] = []
    for specification in specifications:
        coverage = _resolve_interface_coverage(specification, duty_registry)
        group_voltage_classes = {
            duty_registry["circuit_groups"][group_id]["voltage_class"]
            for group_id in specification["covered_circuit_groups"]
        }
        if len(group_voltage_classes) != 1:
            raise ValueError(
                f"{specification['id']} must cover groups from exactly one voltage class"
            )
        voltage_class = next(iter(group_voltage_classes))
        package_current = grounding_current_by_voltage[voltage_class]
        checks = [
            _exact_course_check(
                check_id="zct_ground_fault_target_alignment",
                required=package_current,
                available=float(
                    specification["target_primary_residual_current_a"]
                ),
                unit="A residual primary",
                note="ZCT course target follows the limited ground-fault current of its voltage level.",
            ),
            minimum_check(
                check_id="zct_primary_residual_current_target",
                required=float(
                    specification["target_primary_residual_current_a"]
                ),
                available=float(
                    specification["minimum_linear_primary_residual_current_a"]
                ),
                unit="A residual primary",
                provisional=True,
                note="Minimum linear residual-current target check only; burden, knee point, cable-window size and shield routing remain pending.",
            ),
        ]
        evaluated.append(
            {
                **coverage,
                "voltage_class": voltage_class,
                "checks": checks,
                "course_precheck_status": combine_status(
                    [check["status"] for check in checks]
                ),
            }
        )
    return evaluated


def _evaluate_insulators_and_bushings(
    *,
    specifications: list[dict[str, Any]],
    common: dict[str, Any],
    duty_registry: dict[str, Any],
    voltage_classes: dict[str, Any],
) -> list[dict[str, Any]]:
    thermal_duration = float(common["thermal_equivalent_duration_s"])
    evaluated: list[dict[str, Any]] = []
    for specification in specifications:
        voltage_class = voltage_classes[specification["voltage_class"]]
        requirements = _aggregate_group_requirements(
            group_ids=list(specification["covered_circuit_groups"]),
            duty_registry=duty_registry,
            voltage_classes=voltage_classes,
        )
        short_time = specification["bushing_rated_short_time"]
        required_rms = requirements["required_short_circuit_rms_ka"]
        required_i2t = (
            float(required_rms) ** 2 * thermal_duration
            if required_rms is not None
            else None
        )
        available_i2t = float(short_time["current_ka_rms"]) ** 2 * float(
            short_time["duration_s"]
        )
        checks = [
            minimum_check(
                check_id="insulator_bushing_highest_voltage",
                required=float(voltage_class["highest_system_voltage_kv"]),
                available=float(specification["target_highest_voltage_kv"]),
                unit="kV",
                provisional=True,
                note="Course highest-system-voltage target.",
            ),
            minimum_check(
                check_id="insulator_bushing_liwv",
                required=float(voltage_class["required_liwv_kv"]),
                available=float(specification["target_liwv_kv"]),
                unit="kV peak",
                provisional=True,
                note="Course lightning-impulse withstand target.",
            ),
            minimum_check(
                check_id="bushing_continuous_current",
                required=requirements["required_continuous_current_a"],
                available=float(
                    specification["bushing_rated_continuous_current_a"]
                ),
                unit="A",
                provisional=True,
                note="Bushing continuous-current target for the covered circuit groups.",
            ),
            minimum_check(
                check_id="bushing_short_time_current_level",
                required=required_rms,
                available=float(short_time["current_ka_rms"]),
                unit="kA rms",
                provisional=True,
                note="Bushing short-time current-level target.",
            ),
            minimum_check(
                check_id="bushing_thermal_energy",
                required=required_i2t,
                available=available_i2t,
                unit="kA^2 s",
                provisional=True,
                note="Bushing I2t course precheck at the 1.10s equivalent duration.",
            ),
            minimum_check(
                check_id="bushing_dynamic_current",
                required=requirements["required_peak_current_ka"],
                available=float(
                    specification["bushing_rated_dynamic_current_ka_peak"]
                ),
                unit="kA peak",
                provisional=True,
                note="Bushing dynamic-current course precheck.",
            ),
        ]
        pending_checks = [
            pending_check(
                f"insulator_bushing_{name}",
                f"Final {name.replace('_', ' ')} remains pending exact geometry, installation loads and manufacturer data.",
            )
            for name in specification["pending_engineering_checks"]
        ]
        evaluated.append(
            {
                **specification,
                "requirements": requirements,
                "calculated": {
                    "required_thermal_energy_ka2s": required_i2t,
                    "available_thermal_energy_ka2s": available_i2t,
                },
                "checks": checks,
                "engineering_pending_checks": pending_checks,
                "course_precheck_status": combine_status(
                    [check["status"] for check in checks]
                ),
            }
        )
    return evaluated


def _evaluate_course_cts(
    *,
    specifications: list[dict[str, Any]],
    common: dict[str, Any],
    duty_registry: dict[str, Any],
    voltage_classes: dict[str, Any],
) -> list[dict[str, Any]]:
    thermal_duration = float(common["thermal_equivalent_duration_s"])
    evaluated: list[dict[str, Any]] = []
    for specification in specifications:
        requirements = _aggregate_group_requirements(
            group_ids=list(specification["covered_circuit_groups"]),
            duty_registry=duty_registry,
            voltage_classes=voltage_classes,
        )
        short_time = specification["rated_short_time"]
        if (
            specification.get("evaluation_basis")
            == "single_phase_ground_and_zero_sequence_study_pending"
        ):
            requirements = {
                **requirements,
                "required_continuous_current_a": None,
                "required_short_circuit_rms_ka": None,
                "required_peak_current_ka": None,
            }
            checks = [
                pending_check(
                    "ct_neutral_continuous_current",
                    "Neutral CT continuous duty requires the transformer neutral and zero-sequence protection study; phase-load current is not applicable.",
                ),
                pending_check(
                    "ct_neutral_short_time_current_level",
                    "Neutral CT short-time duty requires the maximum single-phase-to-ground and zero-sequence current study.",
                ),
                pending_check(
                    "ct_neutral_thermal_energy",
                    "Neutral CT I2t remains pending the ground-fault clearing time and zero-sequence duty.",
                ),
                pending_check(
                    "ct_neutral_dynamic_current",
                    "Neutral CT peak duty remains pending the single-phase ground-fault study.",
                ),
            ]
            evaluated.append(
                {
                    **specification,
                    "requirements": requirements,
                    "calculated": {
                        "required_thermal_energy_ka2s": None,
                        "available_thermal_energy_ka2s": None,
                    },
                    "checks": checks,
                    "course_precheck_status": "pending",
                }
            )
            continue
        required_rms = requirements["required_short_circuit_rms_ka"]
        required_i2t = (
            float(required_rms) ** 2 * thermal_duration
            if required_rms is not None
            else None
        )
        available_i2t = (
            float(short_time["current_ka_rms"]) ** 2
            * float(short_time["duration_s"])
        )
        checks = [
            minimum_check(
                check_id="ct_primary_continuous_current",
                required=requirements["required_continuous_current_a"],
                available=float(specification["primary_rated_current_a"]),
                unit="A primary",
                provisional=True,
                note="Course CT ratio and continuous-current target screen.",
            ),
            minimum_check(
                check_id="ct_short_time_current_level",
                required=required_rms,
                available=float(short_time["current_ka_rms"]),
                unit="kA rms",
                provisional=True,
                note="CT short-time current-level course screen.",
            ),
            minimum_check(
                check_id="ct_thermal_energy",
                required=required_i2t,
                available=available_i2t,
                unit="kA^2 s",
                provisional=True,
                note="CT I2t course precheck at the 1.10s project equivalent duration.",
            ),
            minimum_check(
                check_id="ct_dynamic_current",
                required=requirements["required_peak_current_ka"],
                available=float(specification["rated_dynamic_current_ka_peak"]),
                unit="kA peak",
                provisional=True,
                note="CT dynamic-current course precheck.",
            ),
        ]
        evaluated.append(
            {
                **specification,
                "requirements": requirements,
                "calculated": {
                    "required_thermal_energy_ka2s": required_i2t,
                    "available_thermal_energy_ka2s": available_i2t,
                },
                "checks": checks,
                "course_precheck_status": combine_status(
                    [check["status"] for check in checks]
                ),
            }
        )
    return evaluated


def _evaluate_course_earthing_switches(
    *,
    specifications: list[dict[str, Any]],
    common: dict[str, Any],
    duty_registry: dict[str, Any],
    voltage_classes: dict[str, Any],
) -> list[dict[str, Any]]:
    thermal_duration = float(common["thermal_equivalent_duration_s"])
    evaluated: list[dict[str, Any]] = []
    for specification in specifications:
        requirements = _aggregate_group_requirements(
            group_ids=list(specification["covered_circuit_groups"]),
            duty_registry=duty_registry,
            voltage_classes=voltage_classes,
        )
        short_time = specification["rated_short_time"]
        required_rms = requirements["required_short_circuit_rms_ka"]
        required_i2t = (
            float(required_rms) ** 2 * thermal_duration
            if required_rms is not None
            else None
        )
        available_i2t = (
            float(short_time["current_ka_rms"]) ** 2
            * float(short_time["duration_s"])
        )
        checks = [
            minimum_check(
                check_id="earthing_switch_voltage",
                required=requirements["required_highest_system_voltage_kv"],
                available=float(specification["target_highest_voltage_kv"]),
                unit="kV",
                provisional=True,
                note="Course highest-voltage target check.",
            ),
            minimum_check(
                check_id="earthing_switch_short_time_current_level",
                required=required_rms,
                available=float(short_time["current_ka_rms"]),
                unit="kA rms",
                provisional=True,
                note="Course short-time current-level target check.",
            ),
            minimum_check(
                check_id="earthing_switch_thermal_energy",
                required=required_i2t,
                available=available_i2t,
                unit="kA^2 s",
                provisional=True,
                note="Course I2t target check.",
            ),
            minimum_check(
                check_id="earthing_switch_dynamic_current",
                required=requirements["required_peak_current_ka"],
                available=float(specification["rated_dynamic_current_ka_peak"]),
                unit="kA peak",
                provisional=True,
                note="Course dynamic-current target check.",
            ),
        ]
        evaluated.append(
            {
                **specification,
                "requirements": requirements,
                "calculated": {
                    "required_thermal_energy_ka2s": required_i2t,
                    "available_thermal_energy_ka2s": available_i2t,
                },
                "checks": checks,
                "course_precheck_status": combine_status(
                    [check["status"] for check in checks]
                ),
            }
        )
    return evaluated


def _build_course_completion(
    *,
    completion: dict[str, Any],
    candidates: dict[str, dict[str, Any]],
    duty_registry: dict[str, Any],
    voltage_classes: dict[str, Any],
) -> dict[str, Any]:
    common = completion["common_assumptions"]
    decision_inputs = completion["design_decisions"]
    reactor_input = decision_inputs["current_limiting_reactor"]
    reactor_rows: list[dict[str, Any]] = []
    reactor_checks: list[dict[str, Any]] = []
    for item in reactor_input["checks"]:
        candidate = candidates[item["candidate_id"]]
        required_rms = duty_registry["fault_profiles"][item["fault_profile"]][
            "provisional_required_rms_ka"
        ]
        available_rms = candidate["ratings"][
            "short_circuit_breaking_current_ka_rms"
        ]
        check = minimum_check(
            check_id=f"current_limiting_reactor_{item['voltage_class']}",
            required=required_rms,
            available=available_rms,
            unit="kA rms",
            provisional=True,
            note=(
                "A limiting reactor is not required on the course fault level when "
                "the selected switchgear breaking class exceeds the conditional duty."
            ),
        )
        reactor_checks.append(check)
        reactor_rows.append(
            {
                **item,
                "required_fault_current_ka": required_rms,
                "selected_switchgear_breaking_current_ka": available_rms,
                "check": check,
            }
        )
    reactor_status = combine_status(
        [check["status"] for check in reactor_checks]
    )
    design_decisions = {
        "current_limiting_reactor": {
            **reactor_input,
            "checks": reactor_rows,
            "course_precheck_status": reactor_status,
        },
        "high_voltage_fuse": {
            **decision_inputs["high_voltage_fuse"],
            "course_boundary_status": "defined",
        },
    }
    grounding_source_interlock = _evaluate_grounding_source_interlock(
        completion["grounding_source_interlock"], duty_registry
    )
    grounding_packages = _evaluate_grounding_packages(
        specifications=completion["grounding_transformer_resistor_packages"],
        candidates=candidates,
        duty_registry=duty_registry,
        voltage_classes=voltage_classes,
    )
    busbars = _evaluate_course_busbars(
        specifications=completion["busbars"],
        common=common,
        duty_registry=duty_registry,
        voltage_classes=voltage_classes,
    )
    arresters = _evaluate_course_arresters(
        specifications=completion["surge_arresters"],
        candidates=candidates,
        voltage_classes=voltage_classes,
        duty_registry=duty_registry,
    )
    supplementary = completion["supplementary"]
    current_transformers = _evaluate_course_cts(
        specifications=supplementary["current_transformers"],
        common=common,
        duty_registry=duty_registry,
        voltage_classes=voltage_classes,
    )
    zero_sequence_current_transformers = _evaluate_course_zcts(
        specifications=supplementary["zero_sequence_current_transformers"],
        duty_registry=duty_registry,
        grounding_packages=grounding_packages,
    )
    earthing_switches = _evaluate_course_earthing_switches(
        specifications=supplementary["earthing_switches"],
        common=common,
        duty_registry=duty_registry,
        voltage_classes=voltage_classes,
    )

    voltage_transformers = []
    for item in supplementary["voltage_transformers"]:
        voltage_transformers.append(
            {
                **item,
                "required_highest_system_voltage_kv": voltage_classes[
                    item["voltage_class"]
                ]["highest_system_voltage_kv"],
                "course_target_status": "defined",
            }
        )

    insulators_and_bushings = _evaluate_insulators_and_bushings(
        specifications=supplementary["insulators_and_bushings"],
        common=common,
        duty_registry=duty_registry,
        voltage_classes=voltage_classes,
    )

    course_statuses = [
        reactor_status,
        grounding_source_interlock["course_precheck_status"],
        *[item["course_precheck_status"] for item in grounding_packages],
        *[item["course_precheck_status"] for item in busbars],
        *[item["course_precheck_status"] for item in arresters],
        *[
            item["course_precheck_status"]
            for item in current_transformers
            if not item.get("exclude_from_course_precheck", False)
        ],
        *[
            item["course_precheck_status"]
            for item in insulators_and_bushings
        ],
        *[
            item["course_precheck_status"]
            for item in zero_sequence_current_transformers
        ],
        *[item["course_precheck_status"] for item in earthing_switches],
    ]
    return {
        "scope": completion["scope"],
        "common_assumptions": common,
        "design_decisions": design_decisions,
        "grounding_source_interlock": grounding_source_interlock,
        "grounding_transformer_resistor_packages": grounding_packages,
        "course_precheck_status": combine_status(course_statuses),
        "final_engineering_status": "pending",
        "busbars": busbars,
        "surge_arresters": arresters,
        "supplementary": {
            "status": supplementary["status"],
            "ordering_boundary": supplementary["ordering_boundary"],
            "current_transformers": current_transformers,
            "zero_sequence_current_transformers": zero_sequence_current_transformers,
            "voltage_transformers": voltage_transformers,
            "insulators_and_bushings": insulators_and_bushings,
            "earthing_switches": earthing_switches,
        },
    }


def calculate_equipment_screening(
    *,
    selection: dict[str, Any],
    catalog: dict[str, Any],
    load_result: dict[str, Any],
    short_circuit: dict[str, Any],
    baseline: dict[str, Any],
    design_inputs: dict[str, Any],
) -> dict[str, Any]:
    indexes = validate_configuration(selection, catalog)
    duty_registry = build_duty_registry(
        selection=selection,
        load_result=load_result,
        short_circuit=short_circuit,
        baseline=baseline,
    )

    evaluated: list[dict[str, Any]] = []
    for assignment in selection["selections"]:
        group = duty_registry["circuit_groups"][assignment["circuit_group"]]
        candidate = indexes["candidates"][assignment["candidate_id"]]
        voltage_class = selection["voltage_classes"][group["voltage_class"]]
        evaluated.append(
            _evaluate_assignment(
                assignment=assignment,
                group=group,
                candidate=candidate,
                voltage_class=voltage_class,
                design_inputs=design_inputs,
            )
        )

    course_completion = _build_course_completion(
        completion=selection["course_completion"],
        candidates=indexes["candidates"],
        duty_registry=duty_registry,
        voltage_classes=selection["voltage_classes"],
    )

    return {
        "metadata": selection["metadata"],
        "policy": selection["policy"],
        "duty_registry": duty_registry,
        "selections": evaluated,
        "course_completion": course_completion,
        "numeric_precheck_status": combine_status(
            [item["numeric_precheck_status"] for item in evaluated]
        ),
        "final_selection_status": combine_status(
            [item["final_selection_status"] for item in evaluated]
        ),
        "pending_final_inputs": [
            "highest system voltage classes and insulation levels",
            "system 1/system 2 parallel-operation permission",
            "final reactive-power/voltage/harmonic study and 41C outdoor T10/SVG vendor confirmation",
            "final protection coordination and manufacturer breaker clearing data",
            "renewable peak-current and 220kV fault-contribution model",
            "site-confirmed altitude/pollution, 41C outdoor ratings, and controlled-indoor 40C switchgear ratings",
            "exact manufacturer models, verified datasheets, and dimensions",
            "LGJ-400/50 manufacturer thermal rating under defined weather plus mechanical and corona checks",
            "final CT/PT burden, saturation, transient class, resonance, and protection-core coordination",
            "busbar support resonance/end-force study and exact conductor temperature-rise data",
            "surge-arrester grounding, energy-duty and exact insulation-coordination study",
            "grounding-transformer zero-sequence impedance, neutral-resistor thermal design, CT saturation, protection and interlock vendor coordination",
            "ZCT window size, cable-shield return routing, burden, knee point and exact model",
            "insulator creepage/mechanical loads, 35/10kV busbar mechanical dynamic stability and earthing-switch induced-current duty",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build equipment duties and screen provisional rating classes."
    )
    parser.add_argument(
        "--selection",
        type=Path,
        default=Path("data/equipment_selection.yaml"),
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("data/equipment_catalog.yaml"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("calculations/results/equipment_selection"),
    )
    args = parser.parse_args()

    selection = load_yaml(args.selection)
    catalog = load_yaml(args.catalog)
    upstream = selection["upstream"]
    upstream_paths = {
        key: Path(value) for key, value in upstream.items()
    }
    result = calculate_equipment_screening(
        selection=selection,
        catalog=catalog,
        load_result=load_json(upstream_paths["load_results"]),
        short_circuit=load_json(upstream_paths["short_circuit_results"]),
        baseline=load_yaml(upstream_paths["baseline"]),
        design_inputs=load_yaml(upstream_paths["design_inputs"]),
    )
    result["upstream_provenance"] = {
        key: {"path": str(path).replace("\\", "/"), "sha256": file_sha256(path)}
        for key, path in upstream_paths.items()
    }
    for output in write_outputs(result, args.output_dir):
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
