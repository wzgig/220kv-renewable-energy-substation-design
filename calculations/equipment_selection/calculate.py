from __future__ import annotations

import argparse
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
    project_temperature = float(natural["maximum_temperature_c"])
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
                note="Maximum service-temperature check.",
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

    return {
        "metadata": selection["metadata"],
        "policy": selection["policy"],
        "duty_registry": duty_registry,
        "selections": evaluated,
        "numeric_precheck_status": combine_status(
            [item["numeric_precheck_status"] for item in evaluated]
        ),
        "final_selection_status": combine_status(
            [item["final_selection_status"] for item in evaluated]
        ),
        "pending_final_inputs": [
            "highest system voltage classes and insulation levels",
            "system 1/system 2 parallel-operation permission",
            "10kV reactive-compensation Mvar and 35/10.5kV transformer rating",
            "protection and breaker clearing times for thermal duty",
            "renewable peak-current and 220kV fault-contribution model",
            "altitude, pollution level, and 41C current correction",
            "exact manufacturer models, verified datasheets, and dimensions",
            "LGJ-400/50 corrected ampacity, thermal, mechanical, and corona data",
            "CT/PT secondary allocation, accuracy, burden, and protection data",
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
