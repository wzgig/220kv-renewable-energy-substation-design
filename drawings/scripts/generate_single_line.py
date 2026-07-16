"""Generate the A1 electrical single-line diagram from project data.

The DXF is the reproducible drawing source.  AutoCAD Core Console is used in a
separate step for native AUDIT, DWG conversion and plotting.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import ezdxf
import yaml
from ezdxf import bbox, units

try:  # Supports both module imports and direct script execution.
    from .sld_symbols import ensure_symbol_blocks, insert_symbol
except ImportError:  # pragma: no cover - exercised by direct CLI execution
    from sld_symbols import ensure_symbol_blocks, insert_symbol


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LAYOUT = PROJECT_ROOT / "drawings" / "data" / "single_line_layout.yaml"
DEFAULT_STANDARD = (
    PROJECT_ROOT / "drawings" / "standards" / "single_line_standard.yaml"
)
DEFAULT_BASELINE = PROJECT_ROOT / "data" / "design_baseline.yaml"
DEFAULT_DESIGN_INPUTS = PROJECT_ROOT / "data" / "design_inputs.yaml"
DEFAULT_LOAD_RESULTS = (
    PROJECT_ROOT / "calculations" / "results" / "load_and_transformer_results.json"
)
DEFAULT_EQUIPMENT_RESULTS = (
    PROJECT_ROOT
    / "calculations"
    / "results"
    / "equipment_selection"
    / "equipment_selection_results.json"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "drawings" / "source" / "single_line_a1.dxf"


BUS_LAYER_BY_LEVEL = {
    "220kv": "E-BUS-220",
    "35kv": "E-BUS-35",
    "10kv": "E-BUS-10",
    "0_4kv": "E-BUS-0P4",
}

LEVEL_PREFIX = {
    "220kv": "BUS-220-",
    "35kv": "BUS-35-",
    "10kv": "BUS-10-",
    "0_4kv": "BUS-0P4-",
}

DEVICE_HALF_LENGTH = {
    "SLD_CB_CLOSED": 4.0,
    "SLD_CB_OPEN": 4.0,
    "SLD_DS_CLOSED": 5.0,
    "SLD_DS_OPEN": 5.0,
    "SLD_CT": 5.0,
    "SLD_TX_2W": 13.0,
}


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as source:
        data = yaml.safe_load(source)
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping in {path}")
    return data


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as source:
        data = json.load(source)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON mapping in {path}")
    return data


def load_project_data(
    *,
    layout_path: Path = DEFAULT_LAYOUT,
    standard_path: Path = DEFAULT_STANDARD,
    baseline_path: Path = DEFAULT_BASELINE,
    design_inputs_path: Path = DEFAULT_DESIGN_INPUTS,
    load_results_path: Path = DEFAULT_LOAD_RESULTS,
    equipment_results_path: Path = DEFAULT_EQUIPMENT_RESULTS,
) -> dict[str, dict[str, Any]]:
    return {
        "layout": _read_yaml(layout_path),
        "standard": _read_yaml(standard_path),
        "baseline": _read_yaml(baseline_path),
        "design_inputs": _read_yaml(design_inputs_path),
        "load_results": _read_json(load_results_path),
        "equipment_results": _read_json(equipment_results_path),
    }


def _ids(items: list[dict[str, Any]]) -> list[str]:
    return [str(item["id"]) for item in items]


def validate_project_data(data: dict[str, dict[str, Any]]) -> None:
    layout = data["layout"]
    standard = data["standard"]
    baseline = data["baseline"]
    design_inputs = data["design_inputs"]

    if layout.get("schema_version") != 1 or standard.get("schema_version") != 1:
        raise ValueError("Unsupported single-line schema version")

    sheet = layout["sheet"]
    defaults = standard["sheet_defaults"]
    for key in ("format", "orientation", "width", "height"):
        if sheet[key] != defaults[key]:
            raise ValueError(f"Layout and standard disagree on sheet {key}")

    sections = layout["bus_sections"]
    if len(sections) != 8:
        raise ValueError("The drawing must contain exactly two bus sections at four levels")
    for level, prefix in LEVEL_PREFIX.items():
        matches = [item for item in sections if str(item["id"]).startswith(prefix)]
        if len(matches) != 2:
            raise ValueError(f"Expected two {level} bus sections, found {len(matches)}")

    line_layout = layout["circuits"]["220kv"]["lines"]
    expected_lines = set(baseline["connection_220kv"]["line_circuits_in_service"])
    expected_lines.update(baseline["connection_220kv"]["reserved_line_circuits"])
    if set(_ids(line_layout)) != expected_lines:
        raise ValueError("220kV line circuits do not match the design baseline")

    transformer_bays = layout["circuits"]["220kv"]["transformer_bays"]
    if set(_ids(transformer_bays)) != set(baseline["main_transformers"]["identifiers"]):
        raise ValueError("220kV transformer bays do not match the design baseline")

    baseline_feeders: set[str] = set()
    baseline_by_section: dict[str, set[str]] = {}
    for section in baseline["connection_35kv"]["sections"]:
        ids = {str(item["id"]) for item in section["feeder_circuits"]}
        baseline_feeders.update(ids)
        baseline_by_section[str(section["id"])] = ids
    layout_feeders = layout["circuits"]["35kv"]["collector_feeders"]
    if set(_ids(layout_feeders)) != baseline_feeders:
        raise ValueError("35kV collector feeders do not match the design baseline")
    for section_id, expected in baseline_by_section.items():
        actual = {
            str(item["id"])
            for item in layout_feeders
            if item["section"] == section_id
        }
        if actual != expected:
            raise ValueError(f"35kV feeder allocation mismatch for {section_id}")

    reserved_expected = sum(
        int(section["reserved_bays"])
        for section in baseline["connection_35kv"]["sections"]
    )
    if len(layout["circuits"]["35kv"]["reserved_bays"]) != reserved_expected:
        raise ValueError("35kV reserved-bay count does not match the baseline")

    aux_expected = {
        str(item["id"])
        for item in baseline["connection_35kv"]["auxiliary_transformer_bays"]
    }
    aux_actual = set(_ids(layout["circuits"]["35kv"]["source_transformer_bays"]))
    if aux_actual != aux_expected:
        raise ValueError("35kV T10 source-transformer bays are incomplete")

    source_transformers = set(
        baseline["connection_10kv"]["source_transformers"]["identifiers"]
    )
    if set(_ids(layout["transformers"]["source_35_10"])) != source_transformers:
        raise ValueError("35/10.5kV source transformers do not match the baseline")
    source_rating = float(
        baseline["connection_10kv"]["source_transformers"][
            "rated_capacity_mva_each"
        ]
    )
    for transformer in layout["transformers"]["source_35_10"]:
        if float(transformer["rated_capacity_mva"]) != source_rating:
            raise ValueError("T10 drawing rating does not match the frozen baseline")

    baseline_svg = {
        str(item["id"]): float(item["rated_mvar"])
        for item in baseline["connection_10kv"]["reactive_compensation"]["units"]
    }
    layout_svg = {
        str(item["id"]): float(item["rated_mvar"])
        for item in layout["circuits"]["10kv"]["reactive_compensation_feeders"]
    }
    if layout_svg != baseline_svg:
        raise ValueError("10kV SVG drawing data do not match the frozen baseline")

    result_auxiliary_loads = {
        str(item["name"]): item for item in data["load_results"]["load_10kv"]["items"]
    }
    layout_auxiliary_loads = layout["circuits"]["10kv"]["auxiliary_load_groups"]
    layout_load_refs = [str(item["load_ref"]) for item in layout_auxiliary_loads]
    if len(layout_load_refs) != len(set(layout_load_refs)):
        raise ValueError("10kV auxiliary drawing contains duplicate load references")
    if set(layout_load_refs) != set(result_auxiliary_loads):
        raise ValueError("10kV auxiliary drawing does not match calculated load circuits")
    if any(int(item["circuits"]) != 1 for item in result_auxiliary_loads.values()):
        raise ValueError("Single-line auxiliary feeder layout expects one circuit per load item")

    station_transformers = set(
        baseline["connection_0_4kv"]["station_service_transformers"]["identifiers"]
    )
    if set(_ids(layout["transformers"]["station_service"])) != station_transformers:
        raise ValueError("Station-service transformers do not match the baseline")

    tie_states = {str(item["id"]): str(item["state"]) for item in layout["ties"]}
    expected_ties = {
        "TIE-220": baseline["connection_220kv"]["normal_bus_tie_state"],
        "TIE-35": baseline["connection_35kv"]["bus_tie_normal_state"],
        "TIE-10": baseline["connection_10kv"]["bus_tie_normal_state"],
        "TIE-0P4": baseline["connection_0_4kv"]["bus_tie_normal_state"],
    }
    if tie_states != expected_ties:
        raise ValueError(f"Bus-tie states mismatch: {tie_states!r}")

    grounding = design_inputs["calculation_rules"]["grounding"]
    expected_method = "grounding_transformer_plus_low_resistance"
    expected_baseline = f"{expected_method}_course_assumption"
    for level in ("35kv", "10kv"):
        specification = grounding[level]
        if not isinstance(specification, dict):
            raise ValueError(f"Expected structured {level} grounding data")
        if specification.get("method") != expected_method:
            raise ValueError(f"Unexpected {level} grounding basis: {specification!r}")
        if baseline["neutral_grounding"][level] != expected_baseline:
            raise ValueError(f"Baseline and design inputs disagree on {level} grounding")
        prefix = level.replace("kv", "kv_")
        comparisons = {
            "target_ground_fault_current_a": f"{prefix}ground_fault_current_a",
            "resistor_ohm_approx": f"{prefix}resistor_ohm_approx",
            "short_time_s": f"{prefix}short_time_s",
        }
        for input_key, baseline_key in comparisons.items():
            if not abs(
                float(specification[input_key])
                - float(baseline["neutral_grounding"][baseline_key])
            ) < 1e-9:
                raise ValueError(
                    f"Baseline and design inputs disagree on {level} {input_key}"
                )
        package = baseline["neutral_grounding"]["equipment_packages"][level]
        if int(specification["source_count"]) != int(package["quantity"]):
            raise ValueError(f"Baseline and design inputs disagree on {level} source count")
        if specification["grounding_transformer_connection"] != package["connection"]:
            raise ValueError(f"Baseline and design inputs disagree on {level} connection")
        if int(specification["selected_grounding_transformer_capacity_kva_each"]) != int(
            package["selected_capacity_kva_each"]
        ):
            raise ValueError(f"Baseline and design inputs disagree on {level} capacity")

    grounding_scheme = baseline["neutral_grounding"]["sectionalized_source_scheme"]
    if grounding_scheme["bus_tie_transfer"]["prohibited"] != (
        "bus_tie_closed_with_two_section_grounding_sources_connected_in_parallel"
    ):
        raise ValueError("Grounding-source bus-tie interlock baseline is incomplete")

    station_incomers = layout["circuits"]["0_4kv"]["station_service_incomers"]
    closed_incomers = [item for item in station_incomers if item["state"] == "closed"]
    if len(closed_incomers) != baseline["connection_0_4kv"][
        "normal_transformers_in_service"
    ]:
        raise ValueError("Normal 0.4kV state must have exactly one closed incomer")
    if tie_states["TIE-0P4"] != "closed":
        raise ValueError("Dark-standby normal mode requires the 0.4kV bus tie closed")

    circuit_ids: list[str] = []
    for level_groups in layout["circuits"].values():
        for items in level_groups.values():
            circuit_ids.extend(_ids(items))
    duplicates = [item for item, count in Counter(circuit_ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"Duplicate circuit IDs in layout: {duplicates}")


def _lineweight_hundredths(value_mm: float) -> int:
    supported = [5, 9, 13, 15, 18, 20, 25, 30, 35, 40, 50, 53, 60, 70, 80, 90, 100]
    desired = round(float(value_mm) * 100)
    return min(supported, key=lambda item: abs(item - desired))


def _configure_document(doc: ezdxf.document.Drawing, standard: dict[str, Any]) -> None:
    doc.units = units.MM
    doc.header["$INSUNITS"] = units.MM
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LTSCALE"] = float(standard["global_linetype_scale"])
    doc.header["$LWDISPLAY"] = 1

    for name, spec in standard["linetypes"].items():
        if name == "CONTINUOUS" or name in doc.linetypes:
            continue
        pattern = [float(value) for value in spec["pattern_mm"]]
        total_length = sum(abs(value) for value in pattern)
        doc.linetypes.add(
            name,
            description=str(spec["description"]),
            pattern=[total_length, *pattern],
        )

    for name, spec in standard["layers"].items():
        if name in doc.layers:
            layer = doc.layers.get(name)
        else:
            layer = doc.layers.add(name)
        layer.dxf.color = int(spec["aci_color"])
        layer.dxf.linetype = str(spec["linetype"])
        layer.dxf.lineweight = _lineweight_hundredths(spec["lineweight_mm"])
        layer.dxf.plot = int(bool(spec["plot"]))

    for name, spec in standard["text_styles"].items():
        if name in doc.styles:
            style = doc.styles.get(name)
            style.dxf.font = str(spec["font_file"])
        else:
            style = doc.styles.add(name, font=str(spec["font_file"]))
        if spec.get("bigfont_file"):
            style.dxf.bigfont = str(spec["bigfont_file"])
        style.dxf.width = float(spec["width_factor"])
        style.dxf.oblique = float(spec["oblique_angle_deg"])

    ensure_symbol_blocks(doc)


def _add_mtext(
    msp: Any,
    text: str,
    insert: tuple[float, float],
    *,
    height: float,
    width: float = 0.0,
    layer: str = "E-TEXT",
    style: str = "HZTXT",
    attachment: int = 5,
    rotation: float = 0.0,
) -> Any:
    entity = msp.add_mtext(
        text.replace("\n", "\\P"),
        dxfattribs={
            "layer": layer,
            "style": style,
            "char_height": height,
            "attachment_point": attachment,
            "rotation": rotation,
        },
    )
    if width > 0:
        entity.dxf.width = width
    entity.set_location(insert, attachment_point=attachment)
    return entity


def _add_rect(msp: Any, bounds: list[float], *, layer: str) -> None:
    x1, y1, x2, y2 = [float(value) for value in bounds]
    msp.add_lwpolyline(
        [(x1, y1), (x2, y1), (x2, y2), (x1, y2)],
        close=True,
        dxfattribs={"layer": layer},
    )


def _add_line(
    msp: Any,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    layer: str = "E-CONDUCTOR",
) -> None:
    if start == end:
        return
    msp.add_line(start, end, dxfattribs={"layer": layer})


def _add_polyline(msp: Any, points: list[tuple[float, float]], *, layer: str) -> None:
    msp.add_lwpolyline(points, dxfattribs={"layer": layer})


def _status_layer(status: str, default: str = "E-CONDUCTOR") -> str:
    if status in {"reserved", "provisional"}:
        return "E-RESERVED"
    if status in {"pending", "conditional"}:
        return "E-CONDITIONAL"
    return default


def _draw_vertical_series(
    msp: Any,
    *,
    x: float,
    y1: float,
    y2: float,
    devices: list[dict[str, Any]],
    layer: str,
    bay_id: str,
    status: str,
    section: str,
) -> None:
    low, high = sorted((float(y1), float(y2)))
    previous = low
    for item in sorted(devices, key=lambda value: float(value["center"])):
        center = float(item["center"])
        block = str(item["block"])
        half = DEVICE_HALF_LENGTH[block]
        _add_line(msp, (x, previous), (x, center - half), layer=layer)
        insert_symbol(
            msp,
            block,
            (x, center),
            layer=layer,
            bay_id=bay_id,
            device_type=str(item["type"]),
            state=str(item.get("state", "closed")),
            status=status,
            section=section,
        )
        previous = center + half
    _add_line(msp, (x, previous), (x, high), layer=layer)


def _draw_horizontal_series(
    msp: Any,
    *,
    x1: float,
    x2: float,
    y: float,
    devices: list[dict[str, Any]],
    layer: str,
    bay_id: str,
    status: str,
    section: str,
) -> None:
    low, high = sorted((float(x1), float(x2)))
    previous = low
    for item in sorted(devices, key=lambda value: float(value["center"])):
        center = float(item["center"])
        block = str(item["block"])
        half = DEVICE_HALF_LENGTH[block]
        _add_line(msp, (previous, y), (center - half, y), layer=layer)
        insert_symbol(
            msp,
            block,
            (center, y),
            layer=layer,
            bay_id=bay_id,
            device_type=str(item["type"]),
            state=str(item.get("state", "closed")),
            status=status,
            section=section,
            rotation=90.0,
        )
        previous = center + half
    _add_line(msp, (previous, y), (high, y), layer=layer)


def _draw_frame_and_title(
    msp: Any,
    layout: dict[str, Any],
    standard: dict[str, Any],
) -> None:
    sheet = layout["sheet"]
    width, height = float(sheet["width"]), float(sheet["height"])
    _add_rect(msp, [10, 10, width - 10, height - 10], layer="E-FRAME")
    _add_rect(msp, sheet["frame_bounds"], layer="E-FRAME")

    heights = standard["text_heights_mm"]
    _add_mtext(
        msp,
        "220kV新能源汇集变电所电气主接线简图",
        (width / 2.0, height - 20.0),
        height=float(heights["drawing_title"]),
        width=500.0,
        layer="E-TITLE",
        attachment=5,
    )
    _add_mtext(
        msp,
        "220/35/10kV一次系统  -  结构化数据驱动工程底图",
        (width / 2.0, height - 30.0),
        height=float(heights["body"]),
        width=400.0,
        layer="E-NOTE",
        attachment=5,
    )

    _add_rect(msp, layout["title_block"]["bounds"], layer="E-TITLE")
    for cell in layout["title_block"]["cells"]:
        bounds = [float(value) for value in cell["bounds"]]
        _add_rect(msp, bounds, layer="E-TITLE")
        x1, y1, x2, y2 = bounds
        cell_height = 4.0 if cell["id"] == "drawing_title" else 3.0
        _add_mtext(
            msp,
            str(cell["label"]),
            ((x1 + x2) / 2.0, (y1 + y2) / 2.0),
            height=cell_height,
            width=max(5.0, x2 - x1 - 4.0),
            layer="E-TITLE",
            attachment=5,
        )

    note_bounds = [35.0, 10.0, 641.0, 66.0]
    _add_rect(msp, note_bounds, layer="E-TITLE")
    _add_mtext(
        msp,
        "图例：QF-断路器  QS-隔离开关  ES-接地开关  TA-电流互感器  TV/CVT-电压互感器  MOA-避雷器  ZN+R-接地变及低电阻  R-预留  NO-正常断开",
        (40.0, 59.0),
        height=2.7,
        width=590.0,
        layer="E-NOTE",
        attachment=1,
    )
    footer_notes = (
        "配置说明：35/10kV各段设PT+MOA柜；7回35kV架空入口设MOA；5回35kV电缆及10kV电缆/SVG回路设ZCT。"
        "现有短路水平低于31.5kA设备能力，本方案不设限流电抗器。\n"
        "接地源联锁：35/10kV母联合闸前退出受电/故障段接地源，仅保留健康侧1套；禁止母联合闸且两套并联。\n"
        "制图边界：T10=2×31.5MVA、SVG=2×±12Mvar、海拔≤1000m、污秽d级均按课程设计基线表达；"
        "精确型号、CT/PT二次参数、谐波、室外设备41℃及室内开关柜≤40℃厂家适配待最终复核。"
        "220kV分段断路器、35/10kV母联正常断开。"
    )
    _add_mtext(
        msp,
        footer_notes,
        (40.0, 48.0),
        height=2.15,
        width=590.0,
        layer="E-NOTE",
        attachment=1,
    )
    _add_mtext(
        msp,
        "公开仓库工程底图；课程提交是否允许直接使用CAD输出须由指导教师确认。",
        (40.0, 22.0),
        height=2.6,
        width=590.0,
        layer="E-NOTE",
        attachment=1,
    )


def _draw_buses_and_ties(
    msp: Any,
    layout: dict[str, Any],
    standard: dict[str, Any],
) -> None:
    section_lookup = {str(item["id"]): item for item in layout["bus_sections"]}
    heights = standard["text_heights_mm"]
    for level, prefix in LEVEL_PREFIX.items():
        layer = BUS_LAYER_BY_LEVEL[level]
        for section in [item for item in layout["bus_sections"] if item["id"].startswith(prefix)]:
            x1, x2 = [float(value) for value in section["x"]]
            y = float(section["y"])
            _add_line(msp, (x1, y), (x2, y), layer=layer)
            _add_mtext(
                msp,
                str(section["label"]),
                ((x1 + x2) / 2.0, y + 8.0),
                height=float(heights["section_title"]),
                width=x2 - x1,
                layer="E-TEXT",
                attachment=5,
            )

    tie_definitions = {
        "TIE-220": (section_lookup["BUS-220-I"], section_lookup["BUS-220-II"]),
        "TIE-35": (section_lookup["BUS-35-I"], section_lookup["BUS-35-II"]),
        "TIE-10": (section_lookup["BUS-10-I"], section_lookup["BUS-10-II"]),
        "TIE-0P4": (section_lookup["BUS-0P4-I"], section_lookup["BUS-0P4-II"]),
    }
    for tie in layout["ties"]:
        left, right = tie_definitions[str(tie["id"])]
        x1 = float(left["x"][1])
        x2 = float(right["x"][0])
        y = float(left["y"])
        state = str(tie["state"])
        conditional = state == "conditional"
        layer = "E-CONDITIONAL" if conditional else "E-SYMBOL"
        breaker = "SLD_CB_CLOSED" if state == "closed" else "SLD_CB_OPEN"
        center = float(tie["x"])
        if tie["id"] == "TIE-220":
            devices = [
                {"center": center - 25.0, "block": "SLD_DS_CLOSED", "type": "disconnector"},
                {"center": center - 12.0, "block": "SLD_CT", "type": "current_transformer"},
                {"center": center, "block": breaker, "type": "circuit_breaker", "state": state},
                {"center": center + 12.0, "block": "SLD_CT", "type": "current_transformer"},
                {"center": center + 25.0, "block": "SLD_DS_CLOSED", "type": "disconnector"},
            ]
        else:
            devices = [
                {"center": center - 14.0, "block": "SLD_CT", "type": "current_transformer"},
                {"center": center, "block": breaker, "type": "circuit_breaker", "state": state},
                {"center": center + 14.0, "block": "SLD_CT", "type": "current_transformer"},
            ]
        _draw_horizontal_series(
            msp,
            x1=x1,
            x2=x2,
            y=y,
            devices=devices,
            layer=layer,
            bay_id=str(tie["id"]),
            status="conditional" if conditional else "in_service",
            section=str(tie["section"]),
        )
        label_y = y - 9.0 if tie["id"] != "TIE-0P4" else y + 10.0
        _add_mtext(
            msp,
            str(tie["label"]),
            (center, label_y),
            height=2.5,
            width=90.0,
            layer="E-NOTE" if not conditional else "E-CONDITIONAL",
            attachment=5,
        )


def _duty_current_map(equipment_results: dict[str, Any]) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    groups = equipment_results["duty_registry"]["circuit_groups"]
    for group in groups.values():
        current = group["continuous"].get("required_current_a")
        for member in group["members"]:
            result[str(member)] = float(current) if current is not None else None
    return result


def _current_text(value: float | None) -> str:
    return "Imax=P" if value is None else f"Imax={value:.3f}A"


def _draw_shunt_symbol(
    msp: Any,
    *,
    main_x: float,
    main_y: float,
    symbol_x: float,
    symbol_y: float,
    block: str,
    layer: str,
    bay_id: str,
    device_type: str,
    status: str,
    section: str,
    state: str = "closed",
) -> None:
    _add_polyline(
        msp,
        [(main_x, main_y), (symbol_x, main_y), (symbol_x, symbol_y + 6.0)],
        layer=layer,
    )
    insert_symbol(
        msp,
        block,
        (symbol_x, symbol_y),
        layer=layer,
        bay_id=bay_id,
        device_type=device_type,
        state=state,
        status=status,
        section=section,
    )


def _draw_220kv(
    msp: Any,
    layout: dict[str, Any],
    standard: dict[str, Any],
    load_results: dict[str, Any],
) -> None:
    bus_y = float(layout["level_geometry"]["bus_y"]["220kv"])
    device_height = float(standard["text_heights_mm"]["device_id"])
    normal_line_current = float(
        load_results["outgoing_220kv"]["equal_share_current_a"]
    )
    contingency_required_current = float(
        load_results["outgoing_220kv"]["single_circuit_contingency_current_a"]
    )
    for circuit in layout["circuits"]["220kv"]["lines"]:
        x = float(circuit["x"])
        status = str(circuit["status"])
        layer = _status_layer(status)
        breaker = "SLD_CB_OPEN" if status == "reserved" else "SLD_CB_CLOSED"
        disconnector = "SLD_DS_OPEN" if status == "reserved" else "SLD_DS_CLOSED"
        disconnector_state = "open" if status == "reserved" else "closed"
        _draw_vertical_series(
            msp,
            x=x,
            y1=bus_y,
            y2=557.0,
            devices=[
                {
                    "center": 511.0,
                    "block": disconnector,
                    "type": "bus_disconnector",
                    "state": disconnector_state,
                },
                {"center": 523.0, "block": breaker, "type": "circuit_breaker", "state": "open" if status == "reserved" else "closed"},
                {"center": 535.0, "block": "SLD_CT", "type": "current_transformer"},
                {
                    "center": 547.0,
                    "block": disconnector,
                    "type": "line_disconnector",
                    "state": disconnector_state,
                },
            ],
            layer=layer,
            bay_id=str(circuit["id"]),
            status=status,
            section=str(circuit["section"]),
        )
        insert_symbol(
            msp,
            "SLD_ARROW_UP",
            (x, 562.0),
            layer=layer,
            bay_id=str(circuit["id"]),
            device_type="line_terminal",
            state="open" if status == "reserved" else "closed",
            status=status,
            section=str(circuit["section"]),
        )
        _draw_shunt_symbol(
            msp,
            main_x=x,
            main_y=551.0,
            symbol_x=x - 12.0,
            symbol_y=542.0,
            block="SLD_LA",
            layer=layer,
            bay_id=str(circuit["id"]),
            device_type="surge_arrester",
            status=status,
            section=str(circuit["section"]),
        )
        _draw_shunt_symbol(
            msp,
            main_x=x,
            main_y=554.0,
            symbol_x=x + 28.0,
            symbol_y=543.0,
            block="SLD_ES_OPEN",
            layer=layer,
            bay_id=str(circuit["id"]),
            device_type="line_earthing_switch",
            status=status,
            section=str(circuit["section"]),
            state="open",
        )
        _draw_shunt_symbol(
            msp,
            main_x=x,
            main_y=552.0,
            symbol_x=x + 13.0,
            symbol_y=541.0,
            block="SLD_CVT",
            layer=layer,
            bay_id=str(circuit["id"]),
            device_type="line_cvt",
            status=status,
            section=str(circuit["section"]),
        )
        current = (
            "R / 不计入本期"
            if status == "reserved"
            else (
                f"正常{normal_line_current:.3f}A\n"
                f"N-1需{contingency_required_current:.3f}A（须限发）"
            )
        )
        _add_mtext(
            msp,
            f"{circuit['label']}\n{current}",
            (x, 571.0),
            height=device_height,
            width=64.0,
            layer="E-RESERVED" if status == "reserved" else "E-TEXT",
            attachment=8,
        )

    for item in layout["circuits"]["220kv"]["voltage_transformers"]:
        x = float(item["x"])
        _add_line(msp, (x, bus_y), (x, 525.0), layer="E-CONDUCTOR")
        insert_symbol(
            msp,
            "SLD_CVT",
            (x, 519.0),
            layer="E-DEVICE",
            bay_id=str(item["id"]),
            device_type="bus_cvt",
            status=str(item["status"]),
            section=str(item["section"]),
        )
        _add_mtext(
            msp,
            str(item["label"]),
            (x, 535.0),
            height=2.4,
            width=48.0,
            attachment=8,
        )


def _draw_main_transformers(
    msp: Any,
    layout: dict[str, Any],
    load_results: dict[str, Any],
    baseline: dict[str, Any],
) -> None:
    bus_35 = float(layout["level_geometry"]["bus_y"]["35kv"])
    bus_220 = float(layout["level_geometry"]["bus_y"]["220kv"])
    center_y = float(layout["level_geometry"]["transformer_center_y"]["main"])
    duty_hv = float(
        load_results["main_transformer"]["rated_current_with_1_05_margin_a"]["220kv"]
    )
    duty_lv = float(
        load_results["main_transformer"]["rated_current_with_1_05_margin_a"]["35kv"]
    )
    for transformer in layout["transformers"]["main"]:
        x = float(transformer["x"])
        transformer_id = str(transformer["id"])
        section = str(transformer["section"])
        _draw_vertical_series(
            msp,
            x=x,
            y1=bus_35,
            y2=bus_220,
            devices=[
                {"center": 344.0, "block": "SLD_CB_CLOSED", "type": "35kv_incomer_breaker"},
                {"center": 357.0, "block": "SLD_CT", "type": "35kv_current_transformer"},
                {"center": center_y, "block": "SLD_TX_2W", "type": "main_transformer"},
                {"center": 456.0, "block": "SLD_CT", "type": "220kv_current_transformer"},
                {"center": 469.0, "block": "SLD_CB_CLOSED", "type": "220kv_breaker"},
                {"center": 483.0, "block": "SLD_DS_CLOSED", "type": "220kv_bus_disconnector"},
            ],
            layer="E-CONDUCTOR",
            bay_id=transformer_id,
            status=str(transformer["status"]),
            section=section,
        )
        _draw_shunt_symbol(
            msp,
            main_x=x,
            main_y=447.0,
            symbol_x=x + 13.0,
            symbol_y=438.0,
            block="SLD_LA",
            layer="E-DEVICE",
            bay_id=transformer_id,
            device_type="surge_arrester",
            status=str(transformer["status"]),
            section=section,
        )
        _add_line(msp, (x, center_y), (x + 6.0, center_y), layer="E-CONDUCTOR")
        insert_symbol(
            msp,
            "SLD_CT",
            (x + 11.0, center_y),
            layer="E-SYMBOL",
            bay_id=transformer_id,
            device_type="220kv_neutral_current_transformer",
            state="closed",
            status=str(transformer["status"]),
            section=section,
            rotation=90.0,
        )
        _add_line(msp, (x + 16.0, center_y), (x + 23.0, center_y), layer="E-CONDUCTOR")
        insert_symbol(
            msp,
            "SLD_GROUND",
            (x + 23.0, center_y - 3.0),
            layer="E-SYMBOL",
            bay_id=transformer_id,
            device_type="220kv_neutral_ground",
            state="direct_grounded",
            status="in_service",
            section=section,
        )
        if baseline["neutral_grounding"]["220kv"] != "direct_grounding":
            raise ValueError("Main-transformer neutral drawing expects direct grounding")
        _add_mtext(
            msp,
            f"{transformer_id} 180MVA\n220/35kV YNd11 OLTC\nuk=14%  中性点TA直接接地",
            (x + 17.0, center_y + 18.0),
            height=2.5,
            width=70.0,
            attachment=4,
        )
        _add_mtext(
            msp,
            f"HV {_current_text(duty_hv)}\nLV {_current_text(duty_lv)}",
            (x - 11.0, center_y - 18.0),
            height=2.2,
            width=62.0,
            attachment=6,
        )


def _draw_35kv(
    msp: Any,
    layout: dict[str, Any],
    standard: dict[str, Any],
    duty_map: dict[str, float | None],
    design_inputs: dict[str, Any],
    baseline: dict[str, Any],
) -> None:
    bus_y = float(layout["level_geometry"]["bus_y"]["35kv"])
    text_height = float(standard["text_heights_mm"]["device_id"])
    interface_by_id = {
        str(item["id"]): str(item["interface"])
        for section in baseline["connection_35kv"]["sections"]
        for item in section["feeder_circuits"]
    }
    for feeder in layout["circuits"]["35kv"]["collector_feeders"]:
        x = float(feeder["x"])
        bay_id = str(feeder["id"])
        _draw_vertical_series(
            msp,
            x=x,
            y1=278.0,
            y2=bus_y,
            devices=[
                {"center": 305.0, "block": "SLD_CT", "type": "current_transformer"},
                {"center": 318.0, "block": "SLD_CB_CLOSED", "type": "withdrawable_breaker"},
            ],
            layer="E-CONDUCTOR",
            bay_id=bay_id,
            status=str(feeder["status"]),
            section=str(feeder["section"]),
        )
        insert_symbol(
            msp,
            "SLD_ARROW_DOWN",
            (x, 273.0),
            layer="E-CONDUCTOR",
            bay_id=bay_id,
            device_type="collector_terminal",
            status=str(feeder["status"]),
            section=str(feeder["section"]),
        )
        interface_note = (
            "架空+入口MOA"
            if interface_by_id[bay_id] == "overhead"
            else "电缆+ZCT"
        )
        _add_mtext(
            msp,
            f"{bay_id} {feeder['label']}\n{interface_note}\n{_current_text(duty_map.get(bay_id))}",
            (x, 264.0),
            height=text_height,
            width=32.0,
            attachment=2,
        )

    for bay in layout["circuits"]["35kv"]["reserved_bays"]:
        x = float(bay["x"])
        bay_id = str(bay["id"])
        _draw_vertical_series(
            msp,
            x=x,
            y1=278.0,
            y2=bus_y,
            devices=[
                {"center": 305.0, "block": "SLD_CT", "type": "reserved_current_transformer"},
                {"center": 318.0, "block": "SLD_CB_OPEN", "type": "reserved_breaker", "state": "open"},
            ],
            layer="E-RESERVED",
            bay_id=bay_id,
            status="reserved",
            section=str(bay["section"]),
        )
        insert_symbol(
            msp,
            "SLD_ARROW_DOWN",
            (x, 273.0),
            layer="E-RESERVED",
            bay_id=bay_id,
            device_type="reserved_terminal",
            state="open",
            status="reserved",
            section=str(bay["section"]),
        )
        _add_mtext(
            msp,
            f"{bay_id}\n预留柜位R",
            (x, 264.0),
            height=text_height,
            width=30.0,
            layer="E-RESERVED",
            attachment=2,
        )

    arrester = design_inputs["calculation_rules"]["insulation_levels_and_arresters"]["35kv"]["arrester"]
    for item in layout["circuits"]["35kv"]["voltage_transformers"]:
        x = float(item["x"])
        _add_line(msp, (x, bus_y), (x, 311.0), layer="E-CONDUCTOR")
        insert_symbol(
            msp,
            "SLD_PT",
            (x, 305.0),
            layer="E-DEVICE",
            bay_id=str(item["id"]),
            device_type="bus_voltage_transformer",
            status=str(item["status"]),
            section=str(item["section"]),
        )
        _draw_shunt_symbol(
            msp,
            main_x=x,
            main_y=bus_y,
            symbol_x=x - 14.0,
            symbol_y=305.0,
            block="SLD_LA",
            layer="E-DEVICE",
            bay_id=f"MOA-{item['section']}",
            device_type="bus_surge_arrester",
            status=str(item["status"]),
            section=str(item["section"]),
        )
        _add_mtext(
            msp,
            f"{item['label']}+MOA柜\n{arrester}",
            (x, 286.0),
            height=2.2,
            width=42.0,
            attachment=2,
        )

    # Each normally separated medium-voltage section uses the frozen course
    # assumption of a grounding transformer plus low resistance.
    grounding = design_inputs["calculation_rules"]["grounding"]["35kv"]
    for x, label_x, label_y, section in (
        (280.0, 310.0, 304.0, "35kV-I"),
        (590.0, 555.0, 275.0, "35kV-II"),
    ):
        insert_symbol(
            msp,
            "SLD_GROUNDING_TX_RESISTOR",
            (x, bus_y - 9.0),
            layer="E-CONDITIONAL",
            bay_id=f"GROUND-{section}",
            device_type="grounding_transformer_low_resistance",
            state="grounded",
            status="course_assumption",
            section=section,
        )
        _add_mtext(
            msp,
            (
                f"{float(grounding['selected_grounding_transformer_capacity_kva_each']):g}kVA ZN接地变+低电阻\n"
                f"{float(grounding['target_ground_fault_current_a']):g}A / "
                f"{float(grounding['resistor_ohm_approx']):g}Ω / "
                f"{float(grounding['short_time_s']):g}s"
            ),
            (label_x, label_y),
            height=2.3,
            width=42.0,
            layer="E-CONDITIONAL",
            attachment=2,
        )

    for incoming in layout["circuits"]["35kv"]["main_transformer_incomers"]:
        _add_mtext(
            msp,
            str(incoming["label"]),
            (float(incoming["x"]) + 6.0, bus_y + 4.0),
            height=2.2,
            width=45.0,
            attachment=7,
        )


def _draw_source_transformers(
    msp: Any,
    layout: dict[str, Any],
    baseline: dict[str, Any],
) -> None:
    bus_35 = float(layout["level_geometry"]["bus_y"]["35kv"])
    bus_10 = float(layout["level_geometry"]["bus_y"]["10kv"])
    center_y = float(layout["level_geometry"]["transformer_center_y"]["source_35_10"])
    high_bays = {
        item["id"].split("-HV")[0]: item
        for item in layout["circuits"]["35kv"]["source_transformer_bays"]
    }
    low_bays = {
        item["id"].split("-IN")[0]: item
        for item in layout["circuits"]["10kv"]["source_transformer_incomers"]
    }
    source_spec = baseline["connection_10kv"]["source_transformers"]
    for transformer in layout["transformers"]["source_35_10"]:
        transformer_id = str(transformer["id"])
        high = high_bays[transformer_id]
        low = low_bays[transformer_id]
        high_x = float(high["x"])
        low_x = float(low["x"])
        section = str(transformer["section"])
        _draw_vertical_series(
            msp,
            x=high_x,
            y1=center_y + 13.0,
            y2=bus_35,
            devices=[
                {"center": 305.0, "block": "SLD_CT", "type": "35kv_current_transformer"},
                {"center": 318.0, "block": "SLD_CB_CLOSED", "type": "35kv_source_transformer_breaker"},
            ],
            layer="E-CONDUCTOR",
            bay_id=str(high["id"]),
            status=str(high["status"]),
            section=str(high["section"]),
        )
        insert_symbol(
            msp,
            "SLD_TX_2W",
            (high_x, center_y),
            layer="E-DEVICE",
            bay_id=transformer_id,
            device_type="35_10_5kv_source_transformer",
            status=str(transformer["status"]),
            section=section,
        )
        lower_top = center_y - 13.0
        if high_x == low_x:
            _draw_vertical_series(
                msp,
                x=low_x,
                y1=bus_10,
                y2=lower_top,
                devices=[
                    {"center": 192.0, "block": "SLD_CB_CLOSED", "type": "10kv_incomer_breaker"},
                    {"center": 205.0, "block": "SLD_CT", "type": "10kv_current_transformer"},
                ],
                layer="E-CONDUCTOR",
                bay_id=str(low["id"]),
                status=str(low["status"]),
                section=str(low["section"]),
            )
        else:
            _add_polyline(
                msp,
                [(high_x, lower_top), (high_x, 212.0), (low_x, 212.0), (low_x, 210.0)],
                layer="E-CONDUCTOR",
            )
            _draw_vertical_series(
                msp,
                x=low_x,
                y1=bus_10,
                y2=210.0,
                devices=[
                    {"center": 192.0, "block": "SLD_CB_CLOSED", "type": "10kv_incomer_breaker"},
                    {"center": 204.0, "block": "SLD_CT", "type": "10kv_current_transformer"},
                ],
                layer="E-CONDUCTOR",
                bay_id=str(low["id"]),
                status=str(low["status"]),
                section=str(low["section"]),
            )
        _add_mtext(
            msp,
            (
                f"{transformer_id} {float(transformer['rated_capacity_mva']):g}MVA\n"
                f"35/10.5kV {source_spec['vector_group']}  "
                f"uk={float(transformer['short_circuit_voltage_percent']):g}%"
            ),
            (high_x + 15.0, center_y + 3.0),
            height=2.4,
            width=62.0,
            attachment=4,
        )


def _draw_10kv_and_station_service(
    msp: Any,
    layout: dict[str, Any],
    load_results: dict[str, Any],
    design_inputs: dict[str, Any],
    baseline: dict[str, Any],
) -> None:
    bus_10 = float(layout["level_geometry"]["bus_y"]["10kv"])
    bus_04 = float(layout["level_geometry"]["bus_y"]["0_4kv"])
    center_y = float(layout["level_geometry"]["transformer_center_y"]["station_service"])

    arrester = design_inputs["calculation_rules"]["insulation_levels_and_arresters"]["10kv"]["arrester"]
    for item in layout["circuits"]["10kv"]["voltage_transformers"]:
        x = float(item["x"])
        _add_line(msp, (x, bus_10), (x, 161.0), layer="E-CONDUCTOR")
        insert_symbol(
            msp,
            "SLD_PT",
            (x, 155.0),
            layer="E-DEVICE",
            bay_id=str(item["id"]),
            device_type="bus_voltage_transformer",
            status=str(item["status"]),
            section=str(item["section"]),
        )
        _draw_shunt_symbol(
            msp,
            main_x=x,
            main_y=bus_10,
            symbol_x=x + 14.0,
            symbol_y=155.0,
            block="SLD_LA",
            layer="E-DEVICE",
            bay_id=f"MOA-{item['section']}",
            device_type="bus_surge_arrester",
            status=str(item["status"]),
            section=str(item["section"]),
        )
        _add_mtext(
            msp,
            f"{item['label']}+MOA柜\n{arrester}",
            (x, 138.0),
            height=2.2,
            width=40.0,
            attachment=2,
        )

    auxiliary_by_name = {
        str(item["name"]): item for item in load_results["load_10kv"]["items"]
    }
    for group in layout["circuits"]["10kv"]["auxiliary_load_groups"]:
        x = float(group["x"])
        load_item = auxiliary_by_name[str(group["load_ref"])]
        _draw_vertical_series(
            msp,
            x=x,
            y1=145.0,
            y2=bus_10,
            devices=[
                {"center": 157.0, "block": "SLD_CT", "type": "auxiliary_load_ct"},
                {"center": 169.0, "block": "SLD_CB_CLOSED", "type": "auxiliary_load_breaker", "state": "closed"},
            ],
            layer="E-CONDUCTOR",
            bay_id=str(group["id"]),
            status=str(group["status"]),
            section=str(group["section"]),
        )
        insert_symbol(
            msp,
            "SLD_ARROW_DOWN",
            (x, 140.0),
            layer="E-CONDUCTOR",
            bay_id=str(group["id"]),
            device_type="auxiliary_load_group",
            state="closed",
            status=str(group["status"]),
            section=str(group["section"]),
        )
        _add_mtext(
            msp,
            f"{group['label']}\n电缆+ZCT\nImax={float(load_item['per_circuit_current_a']):.3f}A",
            (x, float(group.get("label_y", 132.0))),
            height=2.5,
            width=56.0,
            layer="E-TEXT",
            attachment=2,
        )

    for group in layout["circuits"]["10kv"]["reactive_compensation_feeders"]:
        x = float(group["x"])
        _draw_vertical_series(
            msp,
            x=x,
            y1=145.0,
            y2=bus_10,
            devices=[
                {"center": 157.0, "block": "SLD_CT", "type": "svg_feeder_ct"},
                {"center": 169.0, "block": "SLD_CB_CLOSED", "type": "svg_feeder_breaker", "state": "closed"},
            ],
            layer="E-CONDUCTOR",
            bay_id=str(group["id"]),
            status=str(group["status"]),
            section=str(group["section"]),
        )
        insert_symbol(
            msp,
            "SLD_ARROW_DOWN",
            (x, 140.0),
            layer="E-CONDUCTOR",
            bay_id=str(group["id"]),
            device_type="dynamic_svg",
            state="in_service",
            status=str(group["status"]),
            section=str(group["section"]),
        )
        _add_mtext(
            msp,
            f"{group['label']}\n电缆+ZCT\n动态无功补偿",
            (
                float(group.get("label_x", x)),
                float(group.get("label_y", 132.0)),
            ),
            height=2.5,
            width=48.0,
            layer="E-TEXT",
            attachment=2,
        )

    high_feeders = {
        item["id"].split("-HV")[0]: item
        for item in layout["circuits"]["10kv"]["station_service_feeders"]
    }
    low_incomers = {
        item["id"].split("-LV-IN")[0]: item
        for item in layout["circuits"]["0_4kv"]["station_service_incomers"]
    }
    station_spec = baseline["connection_0_4kv"]["station_service_transformers"]
    for transformer in layout["transformers"]["station_service"]:
        transformer_id = str(transformer["id"])
        high = high_feeders[transformer_id]
        low = low_incomers[transformer_id]
        high_x = float(high["x"])
        low_x = float(low["x"])
        _draw_vertical_series(
            msp,
            x=high_x,
            y1=150.0,
            y2=bus_10,
            devices=[
                {"center": 158.0, "block": "SLD_CT", "type": "10kv_current_transformer"},
                {"center": 170.0, "block": "SLD_CB_CLOSED", "type": "station_service_feeder_breaker"},
            ],
            layer="E-CONDUCTOR",
            bay_id=str(high["id"]),
            status=str(high["status"]),
            section=str(high["section"]),
        )
        if high_x != low_x:
            _add_polyline(
                msp,
                [(high_x, 150.0), (high_x, 146.0), (low_x, 146.0), (low_x, center_y + 13.0)],
                layer="E-CONDUCTOR",
            )
        else:
            _add_line(msp, (high_x, 150.0), (low_x, center_y + 13.0), layer="E-CONDUCTOR")
        insert_symbol(
            msp,
            "SLD_TX_2W",
            (low_x, center_y),
            layer="E-DEVICE",
            bay_id=transformer_id,
            device_type="station_service_transformer",
            state=str(low["state"]),
            status=str(transformer["status"]),
            section=str(transformer["section"]),
        )
        breaker = "SLD_CB_CLOSED" if low["state"] == "closed" else "SLD_CB_OPEN"
        layer = "E-CONDUCTOR" if low["state"] == "closed" else "E-SYMBOL"
        _draw_vertical_series(
            msp,
            x=low_x,
            y1=bus_04,
            y2=center_y - 13.0,
            devices=[
                {"center": 97.0, "block": breaker, "type": "0_4kv_incomer_acb", "state": str(low["state"])},
                {"center": 108.0, "block": "SLD_CT", "type": "0_4kv_metering_ct"},
            ],
            layer=layer,
            bay_id=str(low["id"]),
            status=str(low["status"]),
            section=str(low["section"]),
        )
        text_x = low_x + 13.0
        text_attachment = 4
        if transformer_id == "TS2":
            text_x = low_x - 13.0
            text_attachment = 6
        _add_mtext(
            msp,
            (
                f"{transformer_id} {int(transformer['rated_capacity_kva'])}kVA SCB14干式\n"
                f"10/0.4kV {station_spec['vector_group']} uk="
                f"{float(station_spec['short_circuit_voltage_percent']):g}%  "
                f"{low['state'].upper()}"
            ),
            (text_x, center_y + 4.0),
            height=2.2,
            width=54.0,
            attachment=text_attachment,
        )

    grounding = design_inputs["calculation_rules"]["grounding"]["10kv"]
    for x, label_x, section in (
        (305.0, 335.0, "10kV-I"),
        (540.0, 570.0, "10kV-II"),
    ):
        insert_symbol(
            msp,
            "SLD_GROUNDING_TX_RESISTOR",
            (x, bus_10 - 9.0),
            layer="E-CONDITIONAL",
            bay_id=f"GROUND-{section}",
            device_type="grounding_transformer_low_resistance",
            state="grounded",
            status="course_assumption",
            section=section,
        )
        _add_mtext(
            msp,
            (
                f"{float(grounding['selected_grounding_transformer_capacity_kva_each']):g}kVA ZN接地变+低电阻\n"
                f"{float(grounding['target_ground_fault_current_a']):g}A / "
                f"{float(grounding['resistor_ohm_approx']):g}Ω / "
                f"{float(grounding['short_time_s']):g}s"
            ),
            (label_x, 165.0),
            height=2.2,
            width=42.0,
            layer="E-NOTE",
            attachment=2,
        )

    for x, section, label in (
        (220.0, "0.4kV-I", "I段站用负荷"),
        (340.0, "0.4kV-I", "I段备用/检修"),
        (500.0, "0.4kV-II", "II段站用负荷"),
        (620.0, "0.4kV-II", "II段备用/检修"),
    ):
        _add_line(msp, (x, bus_04), (x, 80.0), layer="E-CONDUCTOR")
        insert_symbol(
            msp,
            "SLD_ARROW_DOWN",
            (x, 75.0),
            layer="E-CONDUCTOR",
            bay_id=f"LV-LOAD-{int(x)}",
            device_type="station_service_load_group",
            status="in_service",
            section=section,
        )
        _add_mtext(
            msp,
            label,
            (x, 69.5),
            height=2.5,
            width=50.0,
            attachment=2,
        )


def _draw_notes(msp: Any, layout: dict[str, Any]) -> None:
    spec = layout["notes_layout"]
    x = float(spec["x"])
    y = float(spec["y"])
    width = float(spec["width"])
    line_spacing = max(7.0, float(spec["line_spacing"]))
    top = y + 8.0
    bottom = top - line_spacing * (len(layout["notes"]) + 1)
    _add_rect(msp, [x - 5.0, bottom - 5.0, x + width + 2.0, top + 8.0], layer="E-TITLE")
    _add_mtext(
        msp,
        "运行方式与制图说明",
        (x, top + 3.0),
        height=3.2,
        width=width,
        layer="E-TITLE",
        attachment=1,
    )
    for index, note in enumerate(layout["notes"], start=1):
        _add_mtext(
            msp,
            f"{index}. {note['label']}",
            (x, top - index * line_spacing),
            height=2.35,
            width=width,
            layer="E-NOTE",
            attachment=1,
        )


def build_document(data: dict[str, dict[str, Any]]) -> ezdxf.document.Drawing:
    validate_project_data(data)
    layout = data["layout"]
    standard = data["standard"]
    doc = ezdxf.new("R2018", setup=False)
    _configure_document(doc, standard)
    msp = doc.modelspace()

    _draw_frame_and_title(msp, layout, standard)
    _draw_buses_and_ties(msp, layout, standard)
    _draw_220kv(msp, layout, standard, data["load_results"])
    _draw_main_transformers(msp, layout, data["load_results"], data["baseline"])
    _draw_35kv(
        msp,
        layout,
        standard,
        _duty_current_map(data["equipment_results"]),
        data["design_inputs"],
        data["baseline"],
    )
    _draw_source_transformers(msp, layout, data["baseline"])
    _draw_10kv_and_station_service(
        msp,
        layout,
        data["load_results"],
        data["design_inputs"],
        data["baseline"],
    )
    _draw_notes(msp, layout)

    return doc


def validate_document(
    doc: ezdxf.document.Drawing,
    data: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    auditor = doc.audit()
    if auditor.has_errors:
        messages = [str(error) for error in auditor.errors]
        raise ValueError(f"ezdxf audit failed: {messages}")

    msp = doc.modelspace()
    layer_zero = [entity for entity in msp if entity.dxf.layer == "0"]
    if layer_zero:
        raise ValueError(f"Modelspace contains {len(layer_zero)} entities on layer 0")

    forbidden = [
        entity.dxftype()
        for entity in msp
        if entity.dxftype() in {"IMAGE", "UNDERLAY", "ACAD_PROXY_ENTITY"}
    ]
    if forbidden:
        raise ValueError(f"Forbidden external/proxy entities found: {forbidden}")

    text_payloads: list[str] = []
    for entity in msp.query("TEXT MTEXT ATTRIB"):
        if entity.dxftype() == "MTEXT":
            text_payloads.append(entity.text)
        else:
            text_payloads.append(str(entity.dxf.text))
    if any("\ufffd" in text for text in text_payloads):
        raise ValueError("Replacement characters found in drawing text")

    required_layers = set(data["standard"]["layers"])
    missing_layers = required_layers.difference(layer.dxf.name for layer in doc.layers)
    if missing_layers:
        raise ValueError(f"Missing drawing layers: {sorted(missing_layers)}")

    required_blocks = {
        "SLD_CB_CLOSED",
        "SLD_CB_OPEN",
        "SLD_DS_CLOSED",
        "SLD_DS_OPEN",
        "SLD_ES_OPEN",
        "SLD_CT",
        "SLD_PT",
        "SLD_CVT",
        "SLD_LA",
        "SLD_TX_2W",
        "SLD_GROUND",
        "SLD_GROUNDING_TX_RESISTOR",
        "SLD_ARROW_UP",
        "SLD_ARROW_DOWN",
    }
    missing_blocks = required_blocks.difference(block.name for block in doc.blocks)
    if missing_blocks:
        raise ValueError(f"Missing drawing blocks: {sorted(missing_blocks)}")

    drawing_extents = bbox.extents(msp, fast=True)
    sheet_width = float(data["layout"]["sheet"]["width"])
    sheet_height = float(data["layout"]["sheet"]["height"])
    if drawing_extents.has_data:
        minimum = drawing_extents.extmin
        maximum = drawing_extents.extmax
        if minimum.x < 0 or minimum.y < 0 or maximum.x > sheet_width or maximum.y > sheet_height:
            raise ValueError(
                "Drawing extents exceed A1 sheet: "
                f"({minimum.x:.2f}, {minimum.y:.2f})-({maximum.x:.2f}, {maximum.y:.2f})"
            )

    return {
        "acadver": doc.dxfversion,
        "modelspace_entities": len(msp),
        "insert_count": len(msp.query("INSERT")),
        "mtext_count": len(msp.query("MTEXT")),
        "extents": [
            round(drawing_extents.extmin.x, 3),
            round(drawing_extents.extmin.y, 3),
            round(drawing_extents.extmax.x, 3),
            round(drawing_extents.extmax.y, 3),
        ],
    }


def _rounded_point(value: Any) -> list[float]:
    return [
        round(float(value.x), 6),
        round(float(value.y), 6),
        round(float(getattr(value, "z", 0.0)), 6),
    ]


def _canonical_entity(entity: Any) -> dict[str, Any]:
    entity_type = entity.dxftype()
    record: dict[str, Any] = {
        "type": entity_type,
        "layer": str(entity.dxf.get("layer", "")),
    }
    if entity_type == "LINE":
        record.update(
            start=_rounded_point(entity.dxf.start),
            end=_rounded_point(entity.dxf.end),
        )
    elif entity_type == "LWPOLYLINE":
        record.update(
            closed=bool(entity.closed),
            points=[
                [round(float(value), 6) for value in point]
                for point in entity.get_points("xyseb")
            ],
        )
    elif entity_type == "CIRCLE":
        record.update(
            center=_rounded_point(entity.dxf.center),
            radius=round(float(entity.dxf.radius), 6),
        )
    elif entity_type == "MTEXT":
        record.update(
            insert=_rounded_point(entity.dxf.insert),
            text=entity.text,
            char_height=round(float(entity.dxf.char_height), 6),
            width=round(float(entity.dxf.get("width", 0.0)), 6),
            style=str(entity.dxf.style),
            rotation=round(float(entity.dxf.get("rotation", 0.0)), 6),
            attachment=int(entity.dxf.attachment_point),
        )
    elif entity_type == "INSERT":
        record.update(
            name=str(entity.dxf.name),
            insert=_rounded_point(entity.dxf.insert),
            rotation=round(float(entity.dxf.get("rotation", 0.0)), 6),
            xscale=round(float(entity.dxf.get("xscale", 1.0)), 6),
            yscale=round(float(entity.dxf.get("yscale", 1.0)), 6),
            attributes=sorted(
                (str(attrib.dxf.tag), str(attrib.dxf.text))
                for attrib in entity.attribs
            ),
        )
    elif entity_type in {"TEXT", "ATTDEF", "ATTRIB"}:
        attribs = entity.dxfattribs()
        record.update(
            insert=_rounded_point(entity.dxf.insert),
            text=str(entity.dxf.text),
            height=round(float(entity.dxf.get("height", 0.0)), 6),
            rotation=round(float(entity.dxf.get("rotation", 0.0)), 6),
            style=str(entity.dxf.get("style", "")),
            tag=str(attribs.get("tag", "")),
            flags=int(attribs.get("flags", 0)),
        )
    else:
        record["attributes"] = {
            key: str(value)
            for key, value in sorted(entity.dxfattribs().items())
            if key not in {"handle", "owner"}
        }
    return record


def semantic_fingerprint(
    doc: ezdxf.document.Drawing,
    *,
    layer_prefixes: tuple[str, ...] = ("E-",),
    block_prefixes: tuple[str, ...] = ("SLD_",),
    linetype_names: frozenset[str] = frozenset(
        {"RESERVED", "PENDING", "CONDITIONAL"}
    ),
    style_names: frozenset[str] = frozenset({"HZTXT", "LATIN"}),
) -> str:
    """Return a stable hash that ignores DXF timestamps, GUIDs and class order."""

    modelspace = sorted(
        (_canonical_entity(entity) for entity in doc.modelspace()),
        key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True),
    )
    blocks: dict[str, list[dict[str, Any]]] = {}
    for block in doc.blocks:
        if not any(block.name.startswith(prefix) for prefix in block_prefixes):
            continue
        blocks[block.name] = sorted(
            (_canonical_entity(entity) for entity in block),
            key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True),
        )
    layers = sorted(
        ({
            "name": str(layer.dxf.name),
            "color": int(layer.dxf.color),
            "linetype": str(layer.dxf.linetype),
            "lineweight": int(layer.dxf.lineweight),
            "plot": int(layer.dxf.plot),
        }
        for layer in doc.layers
        if any(str(layer.dxf.name).startswith(prefix) for prefix in layer_prefixes)),
        key=lambda item: item["name"],
    )
    styles = sorted(
        ({
            "name": str(style.dxf.name),
            "font": str(style.dxf.font),
            "bigfont": str(style.dxf.bigfont),
            "width": round(float(style.dxf.width), 6),
            "oblique": round(float(style.dxf.oblique), 6),
        }
        for style in doc.styles
        if style.dxf.name in style_names),
        key=lambda item: item["name"],
    )
    linetypes = sorted(
        (
            {
                "name": str(linetype.dxf.name),
                "description": str(linetype.dxf.description),
                "pattern": [
                    round(float(value), 6)
                    for value in linetype.simplified_line_pattern()
                ],
            }
            for linetype in doc.linetypes
            if linetype.dxf.name in linetype_names
        ),
        key=lambda item: item["name"],
    )
    payload = {
        "acadver": doc.dxfversion,
        "insunits": int(doc.header["$INSUNITS"]),
        "layers": layers,
        "linetypes": linetypes,
        "styles": styles,
        "blocks": blocks,
        "modelspace": modelspace,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def generate_single_line(
    output_path: Path = DEFAULT_OUTPUT,
    *,
    layout_path: Path = DEFAULT_LAYOUT,
    standard_path: Path = DEFAULT_STANDARD,
    baseline_path: Path = DEFAULT_BASELINE,
    design_inputs_path: Path = DEFAULT_DESIGN_INPUTS,
    load_results_path: Path = DEFAULT_LOAD_RESULTS,
    equipment_results_path: Path = DEFAULT_EQUIPMENT_RESULTS,
) -> dict[str, Any]:
    # Fixed DXF metadata makes the text source byte-reproducible for CI drift
    # checks; AutoCAD still assigns native metadata when it saves the DWG.
    previous_fixed_metadata = ezdxf.options.write_fixed_meta_data_for_testing
    ezdxf.options.write_fixed_meta_data_for_testing = True
    try:
        data = load_project_data(
            layout_path=layout_path,
            standard_path=standard_path,
            baseline_path=baseline_path,
            design_inputs_path=design_inputs_path,
            load_results_path=load_results_path,
            equipment_results_path=equipment_results_path,
        )
        doc = build_document(data)
        summary = validate_document(doc, data)
        output_path = output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(output_path)

        reloaded = ezdxf.readfile(output_path)
        reloaded_summary = validate_document(reloaded, data)
        if summary["modelspace_entities"] != reloaded_summary["modelspace_entities"]:
            raise ValueError("DXF round-trip changed the modelspace entity count")
        summary["semantic_fingerprint"] = semantic_fingerprint(reloaded)
        summary["output"] = str(output_path)
        summary["bytes"] = output_path.stat().st_size
        return summary
    finally:
        ezdxf.options.write_fixed_meta_data_for_testing = previous_fixed_metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--verify-against",
        type=Path,
        help="Compare stable drawing semantics against an existing DXF",
    )
    args = parser.parse_args()
    summary = generate_single_line(args.output)
    if args.verify_against:
        reference_path = args.verify_against.resolve()
        if not reference_path.is_file():
            raise FileNotFoundError(f"Reference DXF not found: {reference_path}")
        generated_doc = ezdxf.readfile(args.output.resolve())
        reference_doc = ezdxf.readfile(reference_path)
        generated_fingerprint = semantic_fingerprint(generated_doc)
        reference_fingerprint = semantic_fingerprint(reference_doc)
        if generated_fingerprint != reference_fingerprint:
            raise ValueError(
                "Generated DXF semantic fingerprint differs from the committed source: "
                f"{generated_fingerprint} != {reference_fingerprint}"
            )
        summary["verified_against"] = str(reference_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
