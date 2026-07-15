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

    for group_id, group in groups.items():
        voltage_class = group.get("voltage_class")
        if voltage_class not in voltage_classes:
            raise ValueError(
                f"{group_id} references unknown voltage class {voltage_class}"
            )

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

    return {
        "groups": groups,
        "candidates": candidates,
        "selections": selections,
    }
