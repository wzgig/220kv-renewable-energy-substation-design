from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: yaml.SafeLoader, node: yaml.nodes.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load_yaml(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    with source.open("r", encoding="utf-8") as stream:
        data = yaml.load(stream, Loader=_UniqueKeyLoader)
    if not isinstance(data, dict):
        raise ValueError(f"{source} must contain a YAML mapping")
    return data


def load_json(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{source} must contain a JSON object")
    return data


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def index_unique(items: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for item in items:
        identifier = str(item.get("id", ""))
        if not identifier:
            raise ValueError(f"{label} item is missing an id")
        if identifier in index:
            raise ValueError(f"duplicate {label} id: {identifier}")
        index[identifier] = item
    return index


def _validate_positive_or_null(value: Any, label: str) -> None:
    if value is not None and float(value) <= 0:
        raise ValueError(f"{label} must be positive when provided")


def validate_configuration(
    selection: dict[str, Any], catalog: dict[str, Any]
) -> dict[str, dict[str, dict[str, Any]]]:
    if int(selection.get("schema_version", 0)) != 1:
        raise ValueError("unsupported equipment-selection schema version")
    if int(catalog.get("schema_version", 0)) != 1:
        raise ValueError("unsupported equipment-catalog schema version")

    voltage_classes = selection.get("voltage_classes")
    if not isinstance(voltage_classes, dict) or not voltage_classes:
        raise ValueError("voltage_classes must be a non-empty mapping")
    for class_id, voltage_class in voltage_classes.items():
        nominal = float(voltage_class["nominal_kv"])
        if nominal <= 0:
            raise ValueError(f"{class_id} nominal voltage must be positive")
        _validate_positive_or_null(
            voltage_class.get("highest_system_voltage_kv"),
            f"{class_id} highest system voltage",
        )
        _validate_positive_or_null(
            voltage_class.get("required_liwv_kv"),
            f"{class_id} required LIWV",
        )

    groups = index_unique(selection.get("circuit_groups", []), "circuit group")
    candidates = index_unique(catalog.get("candidates", []), "candidate")
    selections = index_unique(selection.get("selections", []), "selection")

    allowed_evidence = {"target_only", "family_verified", "exact_model_verified"}
    for candidate_id, candidate in candidates.items():
        evidence_status = candidate.get("evidence", {}).get("status")
        if evidence_status not in allowed_evidence:
            raise ValueError(
                f"{candidate_id} has unsupported evidence status {evidence_status}"
            )
        ratings = candidate.get("ratings")
        if not isinstance(ratings, dict):
            raise ValueError(f"{candidate_id} ratings must be a mapping")
        for key in (
            "highest_voltage_kv",
            "continuous_current_a",
            "short_circuit_breaking_current_ka_rms",
            "short_circuit_making_current_ka_peak",
            "peak_withstand_current_ka",
        ):
            _validate_positive_or_null(ratings.get(key), f"{candidate_id}.{key}")
        short_time = ratings.get("short_time_withstand", {})
        if not isinstance(short_time, dict):
            raise ValueError(
                f"{candidate_id}.short_time_withstand must be a mapping"
            )
        _validate_positive_or_null(
            short_time.get("current_ka_rms"),
            f"{candidate_id}.short_time_withstand.current",
        )
        _validate_positive_or_null(
            short_time.get("duration_s"),
            f"{candidate_id}.short_time_withstand.duration",
        )
        service = candidate.get("service_conditions", {})
        _validate_positive_or_null(
            service.get("current_correction_factor"),
            f"{candidate_id}.current_correction_factor",
        )
        arrester = ratings.get("arrester")
        if arrester is not None:
            if not isinstance(arrester, dict):
                raise ValueError(f"{candidate_id}.arrester ratings must be a mapping")
            for key in (
                "rated_voltage_kv",
                "continuous_operating_voltage_kv",
                "nominal_discharge_current_ka",
                "lightning_residual_voltage_kv",
            ):
                _validate_positive_or_null(
                    arrester.get(key), f"{candidate_id}.arrester.{key}"
                )
        grounding_package = ratings.get("grounding_package")
        if grounding_package is not None:
            if not isinstance(grounding_package, dict):
                raise ValueError(
                    f"{candidate_id}.grounding_package ratings must be a mapping"
                )
            for key in (
                "ground_fault_current_a",
                "duration_s",
                "resistor_ohm_approx",
                "transformer_capacity_kva",
            ):
                _validate_positive_or_null(
                    grounding_package.get(key),
                    f"{candidate_id}.grounding_package.{key}",
                )

    for group_id, group in groups.items():
        voltage_class = group.get("voltage_class")
        if voltage_class not in voltage_classes:
            raise ValueError(
                f"{group_id} references unknown voltage class {voltage_class}"
            )
        members = list(group.get("members", []))
        if len(members) != len(set(members)):
            raise ValueError(f"{group_id} contains duplicate circuit members")
        continuous_duty = group.get("continuous_duty", {})
        if continuous_duty.get("type") == "fixed_course_current":
            _validate_positive_or_null(
                continuous_duty.get("current_a"),
                f"{group_id}.continuous_duty.current_a",
            )

    assignment_pairs: set[tuple[str, str]] = set()
    for selection_id, assignment in selections.items():
        group_id = assignment.get("circuit_group")
        candidate_id = assignment.get("candidate_id")
        if group_id not in groups:
            raise ValueError(
                f"{selection_id} references unknown circuit group {group_id}"
            )
        if candidate_id not in candidates:
            raise ValueError(
                f"{selection_id} references unknown candidate {candidate_id}"
            )
        if assignment.get("device_kind") != candidates[candidate_id].get("kind"):
            raise ValueError(
                f"{selection_id} device kind does not match {candidate_id}"
            )
        assignment_pair = (str(group_id), str(assignment.get("device_kind")))
        if assignment_pair in assignment_pairs:
            raise ValueError(
                f"duplicate selection assignment for {group_id} {assignment.get('device_kind')}"
            )
        assignment_pairs.add(assignment_pair)

    completion = selection.get("course_completion")
    if not isinstance(completion, dict):
        raise ValueError("course_completion must be a mapping")
    common = completion.get("common_assumptions", {})
    for key in ("thermal_stability_constant_c", "thermal_equivalent_duration_s"):
        _validate_positive_or_null(common.get(key), f"course_completion.{key}")

    decisions = completion.get("design_decisions")
    if not isinstance(decisions, dict):
        raise ValueError("course_completion.design_decisions must be a mapping")
    reactor = decisions.get("current_limiting_reactor", {})
    for item in reactor.get("checks", []):
        candidate_id = item.get("candidate_id")
        if item.get("voltage_class") not in voltage_classes:
            raise ValueError("current-limiting-reactor check references unknown voltage class")
        if item.get("fault_profile") not in {"220_bus", "35_bus", "10_bus"}:
            raise ValueError("current-limiting-reactor check references unknown fault profile")
        if candidate_id not in candidates:
            raise ValueError(
                f"current-limiting-reactor check references unknown candidate {candidate_id}"
            )
        if candidates[candidate_id].get("kind") != "switchgear":
            raise ValueError(
                "current-limiting-reactor check candidate must be switchgear"
            )

    grounding_interlock = completion.get("grounding_source_interlock")
    if not isinstance(grounding_interlock, dict):
        raise ValueError("course_completion.grounding_source_interlock must be a mapping")
    interlock_levels = index_unique(
        [
            {"id": item.get("voltage_class"), **item}
            for item in grounding_interlock.get("voltage_levels", [])
        ],
        "grounding-source interlock voltage level",
    )
    for voltage_class, item in interlock_levels.items():
        if voltage_class not in voltage_classes:
            raise ValueError(
                f"grounding-source interlock references unknown voltage class {voltage_class}"
            )
        bus_tie_group = item.get("bus_tie_circuit_group")
        if bus_tie_group not in groups:
            raise ValueError(
                f"grounding-source interlock references unknown circuit group {bus_tie_group}"
            )
        section_ids = list(item.get("section_ids", []))
        source_ids = list(item.get("source_ids", []))
        if not section_ids or len(section_ids) != len(set(section_ids)):
            raise ValueError(
                f"grounding-source interlock {voltage_class} section ids must be unique"
            )
        if len(source_ids) != len(section_ids) or len(source_ids) != len(set(source_ids)):
            raise ValueError(
                f"grounding-source interlock {voltage_class} requires one unique source per section"
            )
        if int(item.get("normal_sources_in_service", 0)) != len(section_ids):
            raise ValueError(
                f"grounding-source interlock {voltage_class} normal state must energize one source per section"
            )
        if int(item.get("transfer_sources_in_service", 0)) != 1:
            raise ValueError(
                f"grounding-source interlock {voltage_class} transfer state must retain exactly one grounding source"
            )
        if int(item.get("restored_sources_in_service", 0)) != len(section_ids):
            raise ValueError(
                f"grounding-source interlock {voltage_class} restored state must return one source per section"
            )
        if "two_grounding_sources" not in str(item.get("prohibited_state", "")):
            raise ValueError(
                f"grounding-source interlock {voltage_class} must explicitly prohibit two grounding sources in parallel"
            )

    grounding_packages = index_unique(
        completion.get("grounding_transformer_resistor_packages", []),
        "grounding transformer and resistor package",
    )
    package_voltage_classes: set[str] = set()
    for package_id, package in grounding_packages.items():
        voltage_class = package.get("voltage_class")
        candidate_id = package.get("candidate_id")
        group_id = package.get("circuit_group")
        selection_id = package.get("feeder_switchgear_selection_id")
        if voltage_class not in voltage_classes:
            raise ValueError(f"{package_id} references unknown voltage class")
        if voltage_class in package_voltage_classes:
            raise ValueError(
                f"duplicate grounding package voltage class: {voltage_class}"
            )
        package_voltage_classes.add(str(voltage_class))
        if candidate_id not in candidates:
            raise ValueError(f"{package_id} references unknown candidate {candidate_id}")
        if candidates[candidate_id].get("kind") != "grounding_transformer_resistor_package":
            raise ValueError(f"{package_id} candidate is not a grounding package")
        if group_id not in groups:
            raise ValueError(f"{package_id} references unknown circuit group {group_id}")
        if groups[group_id].get("voltage_class") != voltage_class:
            raise ValueError(
                f"{package_id} circuit group voltage class does not match"
            )
        if selection_id not in selections:
            raise ValueError(f"{package_id} references unknown selection {selection_id}")
        if selections[selection_id].get("circuit_group") != group_id:
            raise ValueError(
                f"{package_id} feeder switchgear selection does not cover {group_id}"
            )
        if selections[selection_id].get("device_kind") != "switchgear":
            raise ValueError(f"{package_id} feeder device must be switchgear")
        section_ids = list(package.get("section_ids", []))
        source_ids = list(package.get("source_ids", []))
        if int(package.get("quantity", 0)) != len(section_ids):
            raise ValueError(f"{package_id} quantity must match section count")
        if len(source_ids) != len(section_ids) or len(source_ids) != len(set(source_ids)):
            raise ValueError(f"{package_id} source ids must be unique and match sections")
        for key in (
            "nominal_line_voltage_kv",
            "target_ground_fault_current_a",
            "short_time_s",
            "target_resistance_ohm",
            "maximum_resistance_deviation_percent",
            "short_time_overload_factor",
            "selected_transformer_capacity_kva_each",
        ):
            _validate_positive_or_null(package.get(key), f"{package_id}.{key}")
        for ct_label in ("phase_ct_target", "neutral_ct_target"):
            ct_target = package.get(ct_label, {})
            _validate_positive_or_null(
                ct_target.get("primary_rated_current_a"),
                f"{package_id}.{ct_label}.primary_rated_current_a",
            )

    busbars = index_unique(completion.get("busbars", []), "course busbar")
    for busbar_id, busbar in busbars.items():
        if busbar.get("voltage_class") not in voltage_classes:
            raise ValueError(f"{busbar_id} references unknown voltage class")
        busbar_groups = list(busbar.get("circuit_groups", []))
        if len(busbar_groups) != len(set(busbar_groups)):
            raise ValueError(f"{busbar_id} contains duplicate circuit-group references")
        for group_id in busbar_groups:
            if group_id not in groups:
                raise ValueError(f"{busbar_id} references unknown circuit group {group_id}")
        _validate_positive_or_null(
            busbar.get("reference_ampacity", {}).get("current_a"),
            f"{busbar_id}.reference_ampacity.current_a",
        )
        geometry = busbar.get("geometry", {})
        if geometry.get("type") == "tube":
            for key in ("outer_diameter_mm", "inner_diameter_mm"):
                _validate_positive_or_null(geometry.get(key), f"{busbar_id}.{key}")
        elif geometry.get("type") == "rectangular_bundle":
            for key in ("count_per_phase", "width_mm", "thickness_mm"):
                _validate_positive_or_null(geometry.get(key), f"{busbar_id}.{key}")
        else:
            raise ValueError(f"{busbar_id} has unsupported geometry type")
        dynamic = busbar.get("dynamic_check", {})
        if dynamic and not dynamic.get("enabled", False):
            if dynamic.get("status") != "pending":
                raise ValueError(
                    f"{busbar_id} disabled dynamic check must remain explicitly pending"
                )

    arresters = index_unique(
        completion.get("surge_arresters", []), "course surge arrester"
    )
    for arrester_id, arrester in arresters.items():
        voltage_class = arrester.get("voltage_class")
        candidate_id = arrester.get("candidate_id")
        if voltage_class not in voltage_classes:
            raise ValueError(f"{arrester_id} references unknown voltage class")
        if candidate_id not in candidates:
            raise ValueError(f"{arrester_id} references unknown candidate {candidate_id}")
        if candidates[candidate_id].get("kind") != "surge_arrester":
            raise ValueError(f"{arrester_id} candidate is not a surge arrester")
        if not isinstance(candidates[candidate_id]["ratings"].get("arrester"), dict):
            raise ValueError(f"{arrester_id} candidate lacks exact course target ratings")
        for key in (
            "required_continuous_voltage_factor_to_um",
            "protected_equipment_liwv_kv",
            "minimum_protection_ratio",
        ):
            _validate_positive_or_null(arrester.get(key), f"{arrester_id}.{key}")
        coverages = index_unique(
            arrester.get("interface_coverage", []),
            f"{arrester_id} interface coverage",
        )
        for coverage_id, coverage in coverages.items():
            covered_groups = list(coverage.get("covered_circuit_groups", []))
            if not covered_groups:
                raise ValueError(f"{coverage_id} must cover at least one circuit group")
            if len(covered_groups) != len(set(covered_groups)):
                raise ValueError(
                    f"{coverage_id} contains duplicate circuit-group references"
                )
            for group_id in covered_groups:
                if group_id not in groups:
                    raise ValueError(
                        f"{coverage_id} references unknown circuit group {group_id}"
                    )
                if groups[group_id].get("voltage_class") != voltage_class:
                    raise ValueError(
                        f"{coverage_id} circuit group voltage class does not match {arrester_id}"
                    )
            covered_members = list(coverage.get("covered_members", []))
            if not covered_members or len(covered_members) != len(set(covered_members)):
                raise ValueError(
                    f"{coverage_id} covered members must be non-empty and unique"
                )

    supplementary = completion.get("supplementary")
    if not isinstance(supplementary, dict):
        raise ValueError("course_completion.supplementary must be a mapping")

    current_transformers = index_unique(
        supplementary.get("current_transformers", []),
        "supplementary current transformer",
    )
    for ct_id, current_transformer in current_transformers.items():
        covered_groups = list(current_transformer.get("covered_circuit_groups", []))
        if len(covered_groups) != len(set(covered_groups)):
            raise ValueError(f"{ct_id} contains duplicate circuit-group references")
        for group_id in covered_groups:
            if group_id not in groups:
                raise ValueError(f"{ct_id} references unknown circuit group {group_id}")
        _validate_positive_or_null(
            current_transformer.get("primary_rated_current_a"),
            f"{ct_id}.primary_rated_current_a",
        )
        short_time = current_transformer.get("rated_short_time", {})
        _validate_positive_or_null(
            short_time.get("current_ka_rms"), f"{ct_id}.short_time_current"
        )
        _validate_positive_or_null(
            short_time.get("duration_s"), f"{ct_id}.short_time_duration"
        )
        _validate_positive_or_null(
            current_transformer.get("rated_dynamic_current_ka_peak"),
            f"{ct_id}.dynamic_current",
        )

    zcts = index_unique(
        supplementary.get("zero_sequence_current_transformers", []),
        "supplementary zero-sequence current transformer",
    )
    all_zct_members: set[str] = set()
    for zct_id, zct in zcts.items():
        covered_groups = list(zct.get("covered_circuit_groups", []))
        if len(covered_groups) != len(set(covered_groups)):
            raise ValueError(f"{zct_id} contains duplicate circuit-group references")
        for group_id in covered_groups:
            if group_id not in groups:
                raise ValueError(f"{zct_id} references unknown circuit group {group_id}")
        covered_members = list(zct.get("covered_members", []))
        if not covered_members or len(covered_members) != len(set(covered_members)):
            raise ValueError(f"{zct_id} covered members must be non-empty and unique")
        overlap = all_zct_members.intersection(covered_members)
        if overlap:
            raise ValueError(
                f"zero-sequence CT member is duplicated across interfaces: {sorted(overlap)}"
            )
        all_zct_members.update(covered_members)
        for key in (
            "target_primary_residual_current_a",
            "minimum_linear_primary_residual_current_a",
        ):
            _validate_positive_or_null(zct.get(key), f"{zct_id}.{key}")

    voltage_transformers = index_unique(
        supplementary.get("voltage_transformers", []),
        "supplementary voltage transformer",
    )
    for item_id, item in voltage_transformers.items():
        if item.get("voltage_class") not in voltage_classes:
            raise ValueError(f"{item_id} references unknown voltage class")

    insulators_and_bushings = index_unique(
        supplementary.get("insulators_and_bushings", []),
        "supplementary insulator and bushing",
    )
    for item_id, item in insulators_and_bushings.items():
        voltage_class = item.get("voltage_class")
        if voltage_class not in voltage_classes:
            raise ValueError(f"{item_id} references unknown voltage class")
        covered_groups = list(item.get("covered_circuit_groups", []))
        if len(covered_groups) != len(set(covered_groups)):
            raise ValueError(f"{item_id} contains duplicate circuit-group references")
        for group_id in covered_groups:
            if group_id not in groups:
                raise ValueError(f"{item_id} references unknown circuit group {group_id}")
        for key in (
            "target_highest_voltage_kv",
            "target_liwv_kv",
            "bushing_rated_continuous_current_a",
            "bushing_rated_dynamic_current_ka_peak",
        ):
            _validate_positive_or_null(item.get(key), f"{item_id}.{key}")
        short_time = item.get("bushing_rated_short_time", {})
        _validate_positive_or_null(
            short_time.get("current_ka_rms"), f"{item_id}.short_time_current"
        )
        _validate_positive_or_null(
            short_time.get("duration_s"), f"{item_id}.short_time_duration"
        )
        if not item.get("pending_engineering_checks"):
            raise ValueError(
                f"{item_id} must retain pending creepage and mechanical checks"
            )

    earthing_switches = index_unique(
        supplementary.get("earthing_switches", []),
        "supplementary earthing switch",
    )
    for switch_id, earthing_switch in earthing_switches.items():
        covered_groups = list(earthing_switch.get("covered_circuit_groups", []))
        if len(covered_groups) != len(set(covered_groups)):
            raise ValueError(f"{switch_id} contains duplicate circuit-group references")
        for group_id in covered_groups:
            if group_id not in groups:
                raise ValueError(f"{switch_id} references unknown circuit group {group_id}")
        _validate_positive_or_null(
            earthing_switch.get("target_highest_voltage_kv"),
            f"{switch_id}.target_highest_voltage_kv",
        )
        short_time = earthing_switch.get("rated_short_time", {})
        _validate_positive_or_null(
            short_time.get("current_ka_rms"), f"{switch_id}.short_time_current"
        )
        _validate_positive_or_null(
            short_time.get("duration_s"), f"{switch_id}.short_time_duration"
        )
        _validate_positive_or_null(
            earthing_switch.get("rated_dynamic_current_ka_peak"),
            f"{switch_id}.dynamic_current",
        )

    return {
        "groups": groups,
        "candidates": candidates,
        "selections": selections,
    }
