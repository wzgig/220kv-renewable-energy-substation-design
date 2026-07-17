"""Generate the A1 220kV outdoor-AIS plan, sections and line-bay detail."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable

import ezdxf
import yaml
from ezdxf import bbox, units

try:  # Supports both package imports and direct script execution.
    from .generate_single_line import semantic_fingerprint as _base_semantic_fingerprint
except ImportError:  # pragma: no cover - exercised by direct CLI execution
    from generate_single_line import semantic_fingerprint as _base_semantic_fingerprint


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LAYOUT = PROJECT_ROOT / "drawings" / "data" / "switchyard_layout.yaml"
DEFAULT_STANDARD = (
    PROJECT_ROOT / "drawings" / "standards" / "switchyard_standard.yaml"
)
DEFAULT_BASELINE = PROJECT_ROOT / "data" / "design_baseline.yaml"
DEFAULT_PLAN_OUTPUT = PROJECT_ROOT / "drawings" / "source" / "switchyard_plan_a1.dxf"
DEFAULT_SECTION_OUTPUT = (
    PROJECT_ROOT / "drawings" / "source" / "switchyard_section_a1.dxf"
)
DEFAULT_DETAIL_OUTPUT = (
    PROJECT_ROOT / "drawings" / "source" / "switchyard_line_bay_detail_a1.dxf"
)


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as source:
        value = yaml.safe_load(source)
    if not isinstance(value, dict):
        raise ValueError(f"Expected YAML mapping in {path}")
    return value


def load_project_data(
    *,
    layout_path: Path = DEFAULT_LAYOUT,
    standard_path: Path = DEFAULT_STANDARD,
    baseline_path: Path = DEFAULT_BASELINE,
) -> dict[str, dict[str, Any]]:
    return {
        "layout": _read_yaml(layout_path),
        "standard": _read_yaml(standard_path),
        "baseline": _read_yaml(baseline_path),
    }


def validate_project_data(data: dict[str, dict[str, Any]]) -> None:
    layout = data["layout"]
    standard = data["standard"]
    baseline = data["baseline"]
    if layout.get("schema_version") != 1 or standard.get("schema_version") != 1:
        raise ValueError("Unsupported switchyard drawing schema")

    common = layout["common"]
    frozen = baseline["switchyard_220kv"]
    if common["arrangement"] != frozen["arrangement"]:
        raise ValueError("Switchyard arrangement differs from the frozen baseline")
    if int(common["altitude_m_max"]) != int(
        baseline["site_conditions"]["altitude_m_max"]
    ):
        raise ValueError("Switchyard altitude differs from the frozen baseline")
    if str(common["pollution_level"]) != str(
        baseline["site_conditions"]["pollution_level"]
    ):
        raise ValueError("Switchyard pollution level differs from the frozen baseline")
    if {
        key: int(value) for key, value in common["minimum_clearances_mm"].items()
    } != {key: int(value) for key, value in frozen["minimum_clearances_mm"].items()}:
        raise ValueError("Switchyard clearance table differs from the frozen baseline")
    for key in (
        "phase_spacing_m",
        "typical_function_center_pitch_m",
        "normal_road_width_m",
        "bus_conductor_elevation_m",
        "line_gantry_conductor_elevation_m",
        "transformer_gantry_conductor_elevation_m",
    ):
        if not math.isclose(
            float(common[key]), float(frozen[key]), rel_tol=0, abs_tol=1e-9
        ):
            raise ValueError(
                f"Switchyard geometry field {key} differs from the frozen baseline"
            )
    if list(map(float, common["plan_site_size_m"])) != list(
        map(float, frozen["plan_site_size_m"])
    ):
        raise ValueError("Switchyard site size differs from the frozen baseline")

    plan = layout["plan"]
    section = layout["sections"]
    detail = layout["line_bay_detail"]
    if int(plan["sheet"]["scale"]) != 200:
        raise ValueError("The frozen plan drawing scale is 1:200")
    if int(section["sheet"]["scale"]) != 100:
        raise ValueError("The frozen section drawing scale is 1:100")
    frozen_detail = frozen["line_bay_detail_sheet"]
    if int(detail["sheet"]["scale"]) != 50:
        raise ValueError("The frozen line-bay detail scale is 1:50")
    for key in ("format", "orientation"):
        if detail["sheet"][key] != frozen_detail[key]:
            raise ValueError(f"Line-bay detail sheet {key} differs from the baseline")
    if detail["drawing_id"] != frozen_detail["drawing_id"]:
        raise ValueError("Line-bay detail drawing number differs from the baseline")
    site = list(map(float, plan["site_boundary_m"]))
    if [site[2] - site[0], site[3] - site[1]] != list(
        map(float, common["plan_site_size_m"])
    ):
        raise ValueError("Plan boundary dimensions differ from the frozen site size")
    if plan["bus_tie"]["normal_state"] != baseline["connection_220kv"][
        "normal_bus_tie_state"
    ]:
        raise ValueError("220kV bus-tie state differs from the frozen baseline")

    expected_lines = set(baseline["connection_220kv"]["line_circuits_in_service"])
    expected_lines.update(baseline["connection_220kv"]["reserved_line_circuits"])
    actual_lines = {str(item["id"]) for item in plan["line_bays"]}
    if actual_lines != expected_lines:
        raise ValueError("Plan line bays do not match the frozen baseline")
    if {str(item["id"]) for item in plan["transformer_bays"]} != set(
        baseline["main_transformers"]["identifiers"]
    ):
        raise ValueError("Plan main-transformer bays do not match the baseline")
    if {str(item["id"]) for item in section["panels"]} != {"A-A", "B-B"}:
        raise ValueError("The section sheet must contain A-A and B-B panels")

    expected_detail_sequence = [
        ("BUS-SUPPORT", "bus_support"),
        ("DS-BUS", "disconnector"),
        ("CB", "circuit_breaker"),
        ("CT", "current_transformer"),
        ("DS-LINE", "disconnector"),
        ("CVT", "cvt"),
        ("LA", "surge_arrester"),
        ("LINE-GANTRY", "line_gantry"),
    ]
    actual_detail_sequence = [
        (str(item["id"]), str(item["kind"]))
        for item in detail["equipment_sequence"]
    ]
    if actual_detail_sequence != expected_detail_sequence:
        raise ValueError("Line-bay detail equipment sequence is incomplete")
    line_detail_devices = {
        str(item["id"]): item for item in detail["equipment_sequence"]
    }
    if not bool(line_detail_devices["DS-LINE"].get("earthing_switch")):
        raise ValueError("Line-side disconnector must include a normally-open ES")
    detail_bus_to_gantry = (
        float(line_detail_devices["LINE-GANTRY"]["x_m"])
        - float(line_detail_devices["BUS-SUPPORT"]["x_m"])
    )
    if not math.isclose(
        detail_bus_to_gantry,
        float(frozen["line_bus_to_gantry_m"]),
        rel_tol=0,
        abs_tol=1e-9,
    ):
        raise ValueError("Line-bay detail bus-to-gantry distance differs from baseline")
    if float(detail["grounding_grid_elevation_m"]) >= float(
        detail["ground_elevation_m"]
    ):
        raise ValueError("The grounding-grid elevation must be below finished grade")
    if len(detail.get("parameter_rows", [])) < 5:
        raise ValueError("Line-bay detail parameter table is incomplete")

    panels = {str(item["id"]): item for item in section["panels"]}
    line_bay = next(item for item in plan["line_bays"] if item["id"] == "L1")
    transformer_bay = next(
        item for item in plan["transformer_bays"] if item["id"] == "T1"
    )
    line_section = {
        str(item["id"]): item for item in panels["A-A"]["equipment_sequence"]
    }
    transformer_section = {
        str(item["id"]): item for item in panels["B-B"]["equipment_sequence"]
    }
    geometry_pairs = {
        "line_bus_to_gantry_m": (
            float(line_bay["gantry_y_m"]) - float(line_bay["bus_y_m"]),
            float(line_section["LINE-GANTRY"]["x_m"])
            - float(line_section["BUS-SUPPORT"]["x_m"]),
        ),
        "transformer_bus_to_gantry_m": (
            float(transformer_bay["bus_y_m"]) - float(transformer_bay["gantry_y_m"]),
            float(transformer_section["TX-GANTRY"]["x_m"])
            - float(transformer_section["BUS-SUPPORT"]["x_m"]),
        ),
        "transformer_bus_to_center_m": (
            float(transformer_bay["bus_y_m"])
            - float(transformer_bay["transformer_center_m"][1]),
            float(transformer_section["T1"]["x_m"])
            - float(transformer_section["BUS-SUPPORT"]["x_m"]),
        ),
    }
    for key, (plan_distance, section_distance) in geometry_pairs.items():
        frozen_distance = float(frozen[key])
        if not math.isclose(plan_distance, section_distance, rel_tol=0, abs_tol=1e-9):
            raise ValueError(f"Plan and section disagree on {key}")
        if not math.isclose(plan_distance, frozen_distance, rel_tol=0, abs_tol=1e-9):
            raise ValueError(f"Plan/section geometry differs from frozen {key}")

    minimum_terminal = min(
        float(item["terminal_elevation_m"])
        for panel in section["panels"]
        for item in panel["equipment_sequence"]
        if item["kind"] not in {"main_transformer"}
    )
    if minimum_terminal * 1000 < float(common["minimum_clearances_mm"]["C"]):
        raise ValueError("A section terminal elevation violates clearance C")
    if float(common["phase_spacing_m"]) * 1000 < float(
        common["minimum_clearances_mm"]["A2"]
    ):
        raise ValueError("Configured phase spacing violates clearance A2")
    l1_center = float(plan["line_bays"][0]["center_x_m"])
    t1_center = float(plan["transformer_bays"][0]["center_x_m"])
    if not math.isclose(
        t1_center - l1_center,
        float(common["typical_function_center_pitch_m"]),
        rel_tol=0,
        abs_tol=1e-9,
    ):
        raise ValueError("The L1-T1 functional pitch differs from the frozen basis")


def _lineweight_hundredths(value_mm: float) -> int:
    supported = [5, 9, 13, 15, 18, 20, 25, 30, 35, 40, 50, 53, 60, 70, 80, 90, 100]
    target = round(float(value_mm) * 100)
    return min(supported, key=lambda item: abs(item - target))


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
        doc.linetypes.add(
            name,
            description=str(spec["description"]),
            pattern=[sum(abs(value) for value in pattern), *pattern],
        )

    for name, spec in standard["layers"].items():
        layer = doc.layers.get(name) if name in doc.layers else doc.layers.add(name)
        layer.dxf.color = int(spec["aci_color"])
        layer.dxf.linetype = str(spec["linetype"])
        layer.dxf.lineweight = _lineweight_hundredths(float(spec["lineweight_mm"]))
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


def _add_line(
    msp: Any,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    layer: str,
) -> Any:
    return msp.add_line(start, end, dxfattribs={"layer": layer})


def _add_polyline(
    msp: Any,
    points: Iterable[tuple[float, float]],
    *,
    layer: str,
    closed: bool = False,
) -> Any:
    return msp.add_lwpolyline(
        list(points),
        close=closed,
        dxfattribs={"layer": layer},
    )


def _add_spline(
    msp: Any,
    points: Iterable[tuple[float, float]],
    *,
    layer: str,
) -> Any:
    return msp.add_spline(fit_points=list(points), dxfattribs={"layer": layer})


def _add_rect(msp: Any, bounds: Iterable[float], *, layer: str) -> Any:
    x1, y1, x2, y2 = map(float, bounds)
    return _add_polyline(
        msp,
        [(x1, y1), (x2, y1), (x2, y2), (x1, y2)],
        layer=layer,
        closed=True,
    )


def _add_circle(
    msp: Any,
    center: tuple[float, float],
    radius: float,
    *,
    layer: str,
) -> Any:
    return msp.add_circle(center, radius, dxfattribs={"layer": layer})


def _add_mtext(
    msp: Any,
    text: str,
    insert: tuple[float, float],
    *,
    height: float,
    width: float = 0.0,
    layer: str = "C-TEXT",
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


def _add_tick(msp: Any, point: tuple[float, float], *, layer: str = "C-DIM") -> None:
    x, y = point
    _add_line(msp, (x - 1.5, y - 1.5), (x + 1.5, y + 1.5), layer=layer)


def _dimension_horizontal(
    msp: Any,
    x1: float,
    x2: float,
    object_y: float,
    dimension_y: float,
    label: str,
) -> None:
    _add_line(msp, (x1, object_y), (x1, dimension_y), layer="C-DIM")
    _add_line(msp, (x2, object_y), (x2, dimension_y), layer="C-DIM")
    _add_line(msp, (x1, dimension_y), (x2, dimension_y), layer="C-DIM")
    _add_tick(msp, (x1, dimension_y))
    _add_tick(msp, (x2, dimension_y))
    _add_mtext(
        msp,
        label,
        ((x1 + x2) / 2, dimension_y + 2.0),
        height=2.5,
        width=abs(x2 - x1),
        layer="C-DIM",
        attachment=8,
    )


def _dimension_vertical(
    msp: Any,
    y1: float,
    y2: float,
    object_x: float,
    dimension_x: float,
    label: str,
) -> None:
    _add_line(msp, (object_x, y1), (dimension_x, y1), layer="C-DIM")
    _add_line(msp, (object_x, y2), (dimension_x, y2), layer="C-DIM")
    _add_line(msp, (dimension_x, y1), (dimension_x, y2), layer="C-DIM")
    _add_tick(msp, (dimension_x, y1))
    _add_tick(msp, (dimension_x, y2))
    _add_mtext(
        msp,
        label,
        (dimension_x - 2.0, (y1 + y2) / 2),
        height=2.5,
        width=abs(y2 - y1),
        layer="C-DIM",
        attachment=8,
        rotation=90,
    )


def _draw_arrow(
    msp: Any,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    layer: str,
) -> None:
    _add_line(msp, start, end, layer=layer)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    length = 4.0
    for offset in (2.55, -2.55):
        wing = (
            end[0] + length * math.cos(angle + offset),
            end[1] + length * math.sin(angle + offset),
        )
        _add_line(msp, end, wing, layer=layer)


def _draw_frame_and_title(
    msp: Any,
    standard: dict[str, Any],
    *,
    drawing_title: str,
    drawing_id: str,
    scale_label: str,
) -> None:
    defaults = standard["sheet_defaults"]
    _add_rect(msp, [10, 10, 831, 584], layer="C-FRAME")
    _add_rect(msp, defaults["frame_bounds"], layer="C-FRAME")
    _add_rect(msp, defaults["title_block_bounds"], layer="C-TITLE")
    for y in (24, 38, 52):
        _add_line(msp, (651, y), (831, y), layer="C-TITLE")
    for x in (711, 751, 771, 791):
        _add_line(msp, (x, 10), (x, 24), layer="C-TITLE")
    _add_line(msp, (771, 38), (771, 66), layer="C-TITLE")

    _add_mtext(msp, drawing_title, (711, 59), height=4.2, width=116, layer="C-TITLE")
    _add_mtext(msp, f"图号 {drawing_id}", (801, 59), height=2.6, width=56, layer="C-TITLE")
    _add_mtext(msp, "第1张 共1张", (801, 45), height=2.6, width=56, layer="C-TITLE")
    _add_mtext(msp, "220kV新能源汇集变电所电气一次部分", (741, 31), height=2.8, width=174, layer="C-TITLE")
    _add_mtext(msp, "课程设计", (681, 17), height=2.5, width=56, layer="C-TITLE")
    _add_mtext(msp, "设计：", (731, 17), height=2.3, width=36, layer="C-TITLE")
    _add_mtext(msp, "校核：", (771, 17), height=2.3, width=36, layer="C-TITLE")
    _add_mtext(msp, f"比例 {scale_label}", (811, 17), height=2.3, width=36, layer="C-TITLE")


class Mapper:
    def __init__(self, origin_mm: Iterable[float], scale: float) -> None:
        self.origin_x, self.origin_y = map(float, origin_mm)
        self.factor = 1000.0 / float(scale)

    def point(self, x_m: float, y_m: float) -> tuple[float, float]:
        return (
            self.origin_x + float(x_m) * self.factor,
            self.origin_y + float(y_m) * self.factor,
        )

    def length(self, value_m: float) -> float:
        return float(value_m) * self.factor

    def bounds(self, values_m: Iterable[float]) -> list[float]:
        x1, y1, x2, y2 = map(float, values_m)
        p1 = self.point(x1, y1)
        p2 = self.point(x2, y2)
        return [p1[0], p1[1], p2[0], p2[1]]


def _draw_plan_device_triplet(
    msp: Any,
    mapper: Mapper,
    center_x_m: float,
    center_y_m: float,
    kind: str,
    *,
    layer: str,
    orientation: str = "vertical",
    earthing_switch: bool = False,
) -> None:
    phase_offsets = (-4.0, 0.0, 4.0)
    for offset in phase_offsets:
        x_m = center_x_m + offset if orientation == "vertical" else center_x_m
        y_m = center_y_m if orientation == "vertical" else center_y_m + offset
        x, y = mapper.point(x_m, y_m)
        if kind == "circuit_breaker":
            size = mapper.length(0.75)
            _add_rect(msp, [x - size, y - size, x + size, y + size], layer=layer)
            _add_line(msp, (x - size, y), (x + size, y), layer=layer)
        elif kind == "disconnector":
            radius = mapper.length(0.35)
            _add_circle(msp, (x, y), radius, layer=layer)
            _add_line(msp, (x - radius, y - radius), (x + radius, y + radius), layer=layer)
            if earthing_switch:
                pivot = (x + mapper.length(0.85), y - mapper.length(0.85))
                blade_tip = (x + mapper.length(0.22), y - mapper.length(0.20))
                ground_tip = (pivot[0], pivot[1] - mapper.length(0.55))
                _add_circle(msp, pivot, mapper.length(0.16), layer=layer)
                _add_line(msp, pivot, blade_tip, layer=layer)
                _add_line(msp, pivot, ground_tip, layer=layer)
                half = mapper.length(0.28)
                _add_line(
                    msp,
                    (ground_tip[0] - half, ground_tip[1]),
                    (ground_tip[0] + half, ground_tip[1]),
                    layer=layer,
                )
        elif kind in {"current_transformer", "cvt"}:
            _add_circle(msp, (x, y), mapper.length(0.55), layer=layer)
            if kind == "cvt":
                _add_circle(msp, (x, y), mapper.length(0.22), layer=layer)
        elif kind == "surge_arrester":
            r = mapper.length(0.6)
            _add_polyline(
                msp,
                [(x, y + r), (x + r, y), (x, y - r), (x - r, y)],
                layer=layer,
                closed=True,
            )
        else:
            _add_circle(msp, (x, y), mapper.length(0.4), layer=layer)


def _draw_plan(data: dict[str, dict[str, Any]]) -> ezdxf.document.Drawing:
    layout = data["layout"]
    standard = data["standard"]
    plan = layout["plan"]
    common = layout["common"]
    doc = ezdxf.new("R2018", setup=False)
    _configure_document(doc, standard)
    msp = doc.modelspace()
    _draw_frame_and_title(
        msp,
        standard,
        drawing_title=plan["drawing_title"],
        drawing_id=plan["drawing_id"],
        scale_label=plan["sheet"]["scale_label"],
    )
    mapper = Mapper(plan["paper_origin_mm"], plan["sheet"]["scale"])

    _add_mtext(
        msp,
        plan["drawing_title"],
        (420.5, 565),
        height=6.0,
        width=600,
        layer="C-TITLE",
    )
    site = mapper.bounds(plan["site_boundary_m"])
    _add_rect(msp, site, layer="C-BOUNDARY")
    inset = float(plan["fence_inset_m"])
    x1, y1, x2, y2 = map(float, plan["site_boundary_m"])
    _add_rect(msp, mapper.bounds([x1 + inset, y1 + inset, x2 - inset, y2 - inset]), layer="C-FENCE")
    _add_rect(msp, mapper.bounds(plan["ais_area_m"]), layer="C-CENTER")
    _add_mtext(
        msp,
        "220kV户外AIS区",
        mapper.point(72.5, 84.0),
        height=3.0,
        width=220,
        layer="C-TEXT",
    )

    for road in plan["roads"]:
        bounds = list(map(float, road["bounds_m"]))
        _add_rect(msp, mapper.bounds(bounds), layer="C-ROAD")
        if road["kind"] == "loop":
            width = float(road["width_m"])
            _add_rect(
                msp,
                mapper.bounds(
                    [bounds[0] + width, bounds[1] + width, bounds[2] - width, bounds[3] - width]
                ),
                layer="C-ROAD",
            )
        _add_mtext(
            msp,
            f"{road['width_m']}m检修道路",
            mapper.point((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2),
            height=2.3,
            width=90,
            layer="C-ROAD",
        )

    for building in plan["buildings"]:
        bounds = mapper.bounds(building["bounds_m"])
        _add_rect(msp, bounds, layer="C-BUILDING")
        _add_mtext(
            msp,
            building["label"],
            ((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2),
            height=2.8,
            width=bounds[2] - bounds[0] - 4,
            layer="C-BUILDING",
        )

    phase_offsets = (-4.0, 0.0, 4.0)
    for bus in plan["bus_sections"]:
        for offset in phase_offsets:
            _add_line(
                msp,
                mapper.point(bus["x_m"][0], float(bus["center_y_m"]) + offset),
                mapper.point(bus["x_m"][1], float(bus["center_y_m"]) + offset),
                layer="C-BUS",
            )
        _add_mtext(
            msp,
            f"{bus['section']} 三相管形母线",
            mapper.point(sum(bus["x_m"]) / 2, float(bus["center_y_m"]) + 7.0),
            height=2.8,
            width=180,
            layer="C-TEXT",
        )

    tie = plan["bus_tie"]
    tie_start, tie_end = map(float, tie["x_m"])
    tie_span = tie_end - tie_start
    tie_center = (tie_start + tie_end) / 2
    tie_devices = [
        (tie_start + tie_span * 0.18, "disconnector"),
        (tie_start + tie_span * 0.35, "current_transformer"),
        (tie_center, "circuit_breaker"),
        (tie_start + tie_span * 0.65, "current_transformer"),
        (tie_start + tie_span * 0.82, "disconnector"),
    ]
    for phase in phase_offsets:
        y_m = float(tie["center_y_m"]) + phase
        _add_line(msp, mapper.point(tie["x_m"][0], y_m), mapper.point(tie["x_m"][1], y_m), layer="C-CONDUCTOR")
    for x_m, kind in tie_devices:
        _draw_plan_device_triplet(
            msp,
            mapper,
            x_m,
            float(tie["center_y_m"]),
            kind,
            layer="C-EQUIPMENT",
            orientation="horizontal",
        )
    cb_x, cb_y = mapper.point(tie_center, float(tie["center_y_m"]))
    for offset in (-mapper.length(4.0), 0.0, mapper.length(4.0)):
        _add_line(msp, (cb_x - 3, cb_y + offset - 2), (cb_x + 3, cb_y + offset + 2), layer="C-EQUIPMENT")
        _add_line(msp, (cb_x - 3, cb_y + offset + 2), (cb_x + 3, cb_y + offset - 2), layer="C-EQUIPMENT")
    _add_mtext(msp, "220kV分段间隔\n正常断开", mapper.point(tie_center, 66), height=2.7, width=80, layer="C-TEXT")

    for bay in plan["line_bays"]:
        conductor_layer = "C-RESERVED" if bay["status"] == "reserved" else "C-CONDUCTOR"
        equipment_layer = "C-RESERVED" if bay["status"] == "reserved" else "C-EQUIPMENT"
        text_layer = "C-RESERVED" if bay["status"] == "reserved" else "C-TEXT"
        cx = float(bay["center_x_m"])
        bus_y = float(bay["bus_y_m"])
        gantry_y = float(bay["gantry_y_m"])
        for offset, bus_offset in zip(phase_offsets, phase_offsets):
            _add_polyline(
                msp,
                [mapper.point(cx + offset, bus_y + bus_offset), mapper.point(cx + offset, gantry_y)],
                layer=conductor_layer,
            )
        for y_m, kind, has_es in (
            (62, "disconnector", False),
            (66, "circuit_breaker", False),
            (70, "current_transformer", False),
            (74, "disconnector", True),
            (77, "cvt", False),
            (80, "surge_arrester", False),
        ):
            _draw_plan_device_triplet(
                msp,
                mapper,
                cx,
                y_m,
                kind,
                layer=equipment_layer,
                earthing_switch=has_es,
            )
        _add_mtext(
            msp,
            "线路侧QS+ES(NO)",
            mapper.point(cx + 7.2, 74),
            height=2.0,
            width=mapper.length(11),
            layer=text_layer,
            attachment=4,
        )
        gantry_x, gantry_y_paper = mapper.point(cx, gantry_y)
        _add_line(msp, (gantry_x - mapper.length(5), gantry_y_paper), (gantry_x + mapper.length(5), gantry_y_paper), layer="C-STRUCTURE" if conductor_layer != "C-RESERVED" else conductor_layer)
        _draw_arrow(
            msp,
            mapper.point(cx, gantry_y + 0.5),
            mapper.point(cx - 2.8, gantry_y + 3.0),
            layer=conductor_layer,
        )
        _add_mtext(
            msp,
            f"{bay['label']}\n{bay['direction']}出线",
            mapper.point(cx, 88.4),
            height=2.5,
            width=80,
            layer=text_layer,
            attachment=2,
        )

    tx_size = layout["device_envelopes"]["main_transformer"]["plan_footprint_m"]
    for bay in plan["transformer_bays"]:
        cx = float(bay["center_x_m"])
        bus_y = float(bay["bus_y_m"])
        gantry_y = float(bay["gantry_y_m"])
        for offset, bus_offset in zip(phase_offsets, phase_offsets):
            _add_polyline(
                msp,
                [mapper.point(cx + offset, bus_y + bus_offset), mapper.point(cx + offset, gantry_y)],
                layer="C-CONDUCTOR",
            )
        for y_m, kind in (
            (49, "disconnector"),
            (45, "circuit_breaker"),
            (40.5, "current_transformer"),
            (36, "surge_arrester"),
        ):
            _draw_plan_device_triplet(msp, mapper, cx, y_m, kind, layer="C-EQUIPMENT")
        gx, gy = mapper.point(cx, gantry_y)
        _add_line(msp, (gx - mapper.length(5), gy), (gx + mapper.length(5), gy), layer="C-STRUCTURE")
        tx_cx, tx_cy = map(float, bay["transformer_center_m"])
        _add_polyline(msp, [mapper.point(cx, gantry_y), mapper.point(tx_cx, tx_cy + 5.0)], layer="C-CONDUCTOR")
        width_m, height_m = map(float, tx_size)
        bounds = mapper.bounds([tx_cx - width_m / 2, tx_cy - height_m / 2, tx_cx + width_m / 2, tx_cy + height_m / 2])
        _add_rect(msp, bounds, layer="C-EQUIPMENT")
        for offset in (-3.0, 0.0, 3.0):
            x, y = mapper.point(tx_cx + offset, tx_cy + height_m / 2)
            _add_circle(msp, (x, y), mapper.length(0.45), layer="C-EQUIPMENT")
        _add_mtext(
            msp,
            f"{bay['label']}\n180MVA 220/35kV",
            mapper.point(tx_cx, tx_cy),
            height=2.6,
            width=mapper.length(width_m - 1),
            layer="C-TEXT",
        )

    for item in plan["bus_voltage_transformers"]:
        cx, cy = map(float, item["center_m"])
        bus = next(value for value in plan["bus_sections"] if value["section"] == item["section"])
        _add_line(msp, mapper.point(cx, float(bus["center_y_m"]) - 4), mapper.point(cx, cy), layer="C-CONDUCTOR")
        _draw_plan_device_triplet(msp, mapper, cx, cy, "cvt", layer="C-EQUIPMENT")
        _add_mtext(msp, item["label"], mapper.point(cx, cy - 3), height=2.3, width=60, layer="C-TEXT")

    for mark in plan["section_marks"]:
        coordinate = float(mark["coordinate_m"])
        if mark["axis"] == "y":
            ranges = mark.get("ranges_m", [mark.get("range_m")])
            for start, end in ranges:
                _add_line(msp, mapper.point(coordinate, float(start)), mapper.point(coordinate, float(end)), layer="C-CENTER")
            end = max(float(value[1]) for value in ranges)
            _add_mtext(msp, mark["id"], mapper.point(coordinate, end + 1), height=2.6, width=30, layer="C-TEXT")
        else:
            start, end = map(float, mark["range_m"])
            _add_line(msp, mapper.point(start, coordinate), mapper.point(end, coordinate), layer="C-CENTER")

    north = mapper.point(139, 74)
    _draw_arrow(msp, north, (north[0], north[1] + mapper.length(8)), layer="C-TEXT")
    _add_mtext(msp, "N", (north[0], north[1] + mapper.length(10)), height=4.0, width=20, layer="C-TEXT")

    _dimension_horizontal(msp, site[0], site[2], site[1], site[1] - 12, "145.0m")
    _dimension_vertical(msp, site[1], site[3], site[2], site[2] + 12, "90.0m")
    x_l1 = mapper.point(float(plan["line_bays"][0]["center_x_m"]), 0)[0]
    x_t1 = mapper.point(float(plan["transformer_bays"][0]["center_x_m"]), 0)[0]
    pitch = float(plan["transformer_bays"][0]["center_x_m"]) - float(plan["line_bays"][0]["center_x_m"])
    _dimension_horizontal(msp, x_l1, x_t1, mapper.point(0, 82)[1], mapper.point(0, 85)[1], f"{pitch:.1f}m")
    first_bus = plan["bus_sections"][0]
    _dimension_horizontal(
        msp,
        mapper.point(float(first_bus["x_m"][0]), 0)[0],
        mapper.point(float(first_bus["x_m"][1]), 0)[0],
        mapper.point(0, 55)[1],
        mapper.point(0, 46)[1],
        f"I段母线{float(first_bus['x_m'][1]) - float(first_bus['x_m'][0]):.1f}m",
    )

    clearance = common["minimum_clearances_mm"]
    _add_mtext(
        msp,
        (
            "220kV屋外最小净距（课程表7-2，mm）\n"
            f"A1={clearance['A1']}  A2={clearance['A2']}  B1={clearance['B1']}  "
            f"B2={clearance['B2']}  C={clearance['C']}  D={clearance['D']}"
        ),
        (45, 552),
        height=2.6,
        width=360,
        layer="C-NOTE",
        attachment=1,
    )
    note_box = mapper.bounds([55, 25, 85, 45])
    _add_rect(msp, note_box, layer="C-NOTE")
    _add_mtext(
        msp,
        "设计说明",
        ((note_box[0] + note_box[2]) / 2, note_box[3] - 5),
        height=3.0,
        width=note_box[2] - note_box[0] - 6,
        layer="C-NOTE",
        attachment=8,
    )
    for index, note in enumerate(plan["notes"], start=1):
        _add_mtext(
            msp,
            f"{index}. {note}",
            (note_box[0] + 5, note_box[3] - 13 - (index - 1) * 13.0),
            height=2.1,
            width=note_box[2] - note_box[0] - 10,
            layer="C-NOTE",
            attachment=1,
        )
    return doc


def _draw_foundation(msp: Any, mapper: Mapper, x_m: float, width_m: float = 1.4) -> None:
    x1, y1 = mapper.point(x_m - width_m / 2, -0.15)
    x2, y2 = mapper.point(x_m + width_m / 2, 0.25)
    _add_rect(msp, [x1, y1, x2, y2], layer="C-FOUNDATION")


def _draw_section_ground_symbol(
    msp: Any,
    mapper: Mapper,
    x_m: float,
    y_m: float,
    *,
    layer: str = "C-CONDUCTOR",
) -> None:
    stem_top = mapper.point(x_m, y_m + 0.45)
    stem_bottom = mapper.point(x_m, y_m)
    _add_line(msp, stem_top, stem_bottom, layer=layer)
    for index, half_width in enumerate((0.45, 0.30, 0.16)):
        y = y_m - index * 0.16
        left = mapper.point(x_m - half_width, y)
        right = mapper.point(x_m + half_width, y)
        _add_line(msp, left, right, layer=layer)


def _draw_insulator_stack(
    msp: Any,
    mapper: Mapper,
    x_m: float,
    top_m: float,
    *,
    layer: str = "C-EQUIPMENT",
    base_m: float = 0.25,
) -> None:
    x, y1 = mapper.point(x_m, base_m)
    _, y2 = mapper.point(x_m, top_m)
    _add_line(msp, (x, y1), (x, y2), layer=layer)
    for elevation in [base_m + value * (top_m - base_m) / 8 for value in range(1, 8)]:
        cx, cy = mapper.point(x_m, elevation)
        half = mapper.length(0.28)
        _add_line(msp, (cx - half, cy), (cx + half, cy), layer=layer)


def _draw_section_equipment(
    msp: Any,
    mapper: Mapper,
    item: dict[str, Any],
    *,
    aligned: bool = False,
) -> tuple[float, float]:
    kind = str(item["kind"])
    x_m = float(item["x_m"])
    terminal = float(item["terminal_elevation_m"])
    layer = "C-EQUIPMENT"
    _draw_foundation(msp, mapper, x_m, 2.0 if kind == "main_transformer" else 1.4)

    if kind == "bus_support":
        _draw_insulator_stack(msp, mapper, x_m, terminal)
        x, y = mapper.point(x_m, terminal)
        _add_circle(msp, (x, y), mapper.length(0.18), layer="C-BUS")
    elif kind == "disconnector":
        for offset in (-0.8, 0.8):
            _draw_insulator_stack(msp, mapper, x_m + offset, terminal - 0.4)
        left = mapper.point(x_m - 0.8, terminal - 0.4)
        right = mapper.point(x_m + 0.8, terminal - 0.4 if aligned else terminal)
        _add_line(msp, left, right, layer=layer)
        if bool(item.get("earthing_switch")):
            live_contact = mapper.point(x_m + 0.8, terminal - 0.4)
            ground_pivot = mapper.point(x_m + 2.0, 1.25)
            open_blade_tip = mapper.point(x_m + 1.2, terminal - 1.15)
            _add_circle(msp, live_contact, mapper.length(0.10), layer=layer)
            _add_circle(msp, ground_pivot, mapper.length(0.10), layer=layer)
            _add_line(msp, ground_pivot, open_blade_tip, layer=layer)
            _draw_section_ground_symbol(msp, mapper, x_m + 2.0, 0.35, layer=layer)
            _add_line(
                msp,
                ground_pivot,
                mapper.point(x_m + 2.0, 0.80),
                layer=layer,
            )
            _add_mtext(
                msp,
                "ES(NO)",
                mapper.point(x_m + 2.5, 2.0),
                height=2.0,
                width=mapper.length(3.0),
                layer="C-TEXT",
                attachment=4,
            )
    elif kind == "circuit_breaker":
        for offset in (-0.65, 0.65):
            _draw_insulator_stack(msp, mapper, x_m + offset, terminal)
        x1, y1 = mapper.point(x_m - 0.9, 1.4)
        x2, y2 = mapper.point(x_m + 0.9, 3.0)
        _add_rect(msp, [x1, y1, x2, y2], layer=layer)
        _add_line(msp, mapper.point(x_m - 0.65, terminal), mapper.point(x_m + 0.65, terminal), layer=layer)
    elif kind in {"current_transformer", "cvt"}:
        _draw_insulator_stack(msp, mapper, x_m, terminal)
        x1, y1 = mapper.point(x_m - 0.75, 1.0)
        x2, y2 = mapper.point(x_m + 0.75, 2.5)
        _add_rect(msp, [x1, y1, x2, y2], layer=layer)
        if kind == "cvt":
            x, y = mapper.point(x_m, 3.0)
            _add_circle(msp, (x, y), mapper.length(0.55), layer=layer)
    elif kind == "surge_arrester":
        _draw_insulator_stack(msp, mapper, x_m, terminal)
        _add_polyline(
            msp,
            [
                mapper.point(x_m - 0.7, 0.5),
                mapper.point(x_m + 0.7, 0.5),
                mapper.point(x_m + 0.35, 2.0),
                mapper.point(x_m - 0.35, 2.0),
            ],
            layer=layer,
            closed=True,
        )
    elif kind in {"line_gantry", "transformer_gantry"}:
        for offset in (-1.6, 1.6):
            _add_line(msp, mapper.point(x_m + offset, 0), mapper.point(x_m + offset, terminal + 1.0), layer="C-STRUCTURE")
        _add_line(msp, mapper.point(x_m - 2.2, terminal + 1.0), mapper.point(x_m + 2.2, terminal + 1.0), layer="C-STRUCTURE")
        _add_line(msp, mapper.point(x_m - 1.6, 0), mapper.point(x_m + 1.6, terminal + 1.0), layer="C-STRUCTURE")
    elif kind == "main_transformer":
        _add_rect(msp, mapper.bounds([x_m - 5.0, 0.25, x_m + 5.0, 5.7]), layer=layer)
        for offset in (-2.2, 0.0, 2.2):
            _draw_insulator_stack(msp, mapper, x_m + offset, terminal, base_m=5.7)
        _add_mtext(msp, "T1/T2\n180MVA", mapper.point(x_m, 3.0), height=2.8, width=mapper.length(8), layer="C-TEXT")
    else:
        raise ValueError(f"Unsupported section equipment kind: {kind}")

    _add_mtext(
        msp,
        item["label"],
        mapper.point(x_m, 0.75),
        height=2.1,
        width=mapper.length(3.8 if kind != "main_transformer" else 8.0),
        layer="C-TEXT",
        attachment=2,
    )
    if item.get("equipment_no"):
        _add_mtext(
            msp,
            str(item["equipment_no"]),
            mapper.point(x_m, terminal + 0.7),
            height=2.0,
            width=mapper.length(5.0),
            layer="C-TEXT",
            attachment=2,
        )
    return mapper.point(x_m, terminal - 0.4 if aligned and kind == "disconnector" else terminal)


def _section_ports(mapper: Mapper, item: dict[str, Any]) -> tuple[tuple[float, float], tuple[float, float]]:
    x_m = float(item["x_m"])
    terminal = float(item["terminal_elevation_m"])
    kind = str(item["kind"])
    if kind == "disconnector":
        elevation = terminal - 0.4
        return mapper.point(x_m - 0.8, elevation), mapper.point(x_m + 0.8, elevation)
    if kind == "circuit_breaker":
        return mapper.point(x_m - 0.65, terminal), mapper.point(x_m + 0.65, terminal)
    point = mapper.point(x_m, terminal)
    return point, point


def _connect_section_chain(
    msp: Any,
    mapper: Mapper,
    items: list[dict[str, Any]],
) -> None:
    for left_item, right_item in zip(items, items[1:]):
        _, start = _section_ports(mapper, left_item)
        end, _ = _section_ports(mapper, right_item)
        dx = end[0] - start[0]
        _add_spline(
            msp,
            [start, (start[0] + dx * 0.35, start[1]), (start[0] + dx * 0.65, end[1]), end],
            layer="C-CONDUCTOR",
        )


def _draw_section_shunt_branches(
    msp: Any,
    mapper: Mapper,
    panel: dict[str, Any],
) -> None:
    items = {str(item["id"]): item for item in panel["equipment_sequence"]}
    branch_ids = [item_id for item_id in ("CVT", "LA") if item_id in items]
    if not branch_ids:
        return
    source = items["DS-LINE"] if "DS-LINE" in items else items["CT"]
    _, source_port = _section_ports(mapper, source)
    branch_elevation = max(source_port[1], *(mapper.point(0, float(items[item_id]["terminal_elevation_m"]))[1] for item_id in branch_ids)) + mapper.length(0.8)
    junction = (source_port[0], branch_elevation)
    _add_line(msp, source_port, junction, layer="C-CONDUCTOR")
    _add_circle(msp, source_port, mapper.length(0.10), layer="C-CONDUCTOR")
    for item_id in branch_ids:
        terminal = mapper.point(float(items[item_id]["x_m"]), float(items[item_id]["terminal_elevation_m"]))
        _add_polyline(msp, [junction, (terminal[0], branch_elevation), terminal], layer="C-CONDUCTOR")
        _add_circle(msp, terminal, mapper.length(0.08), layer="C-CONDUCTOR")


def _draw_section_panel(
    msp: Any,
    panel: dict[str, Any],
    scale: float,
    common: dict[str, Any],
) -> None:
    mapper = Mapper(panel["paper_origin_mm"], scale)
    width_m = float(panel["width_m"])
    ground_y = mapper.point(0, 0)[1]
    _add_line(msp, mapper.point(0, 0), mapper.point(width_m, 0), layer="C-FOUNDATION")
    _add_mtext(
        msp,
        panel["title"],
        mapper.point(width_m / 2, 22.5),
        height=4.0,
        width=mapper.length(width_m),
        layer="C-TITLE",
    )
    _add_mtext(msp, "±0.000", mapper.point(0.5, 0.3), height=2.4, width=45, layer="C-DIM", attachment=1)

    terminal_points = [
        _draw_section_equipment(msp, mapper, item, aligned=True)
        for item in panel["equipment_sequence"]
    ]
    shunt_ids = {"CVT", "LA"}
    series_items = [item for item in panel["equipment_sequence"] if str(item["id"]) not in shunt_ids]
    _connect_section_chain(msp, mapper, series_items)
    _draw_section_shunt_branches(msp, mapper, panel)
    if panel["id"] == "A-A":
        _, last = _section_ports(mapper, series_items[-1])
        _draw_arrow(msp, last, (last[0] + 35, last[1] + 18), layer="C-CONDUCTOR")

    equipment_x = [float(item["x_m"]) for item in panel["equipment_sequence"]]
    for index, (left, right) in enumerate(zip(equipment_x, equipment_x[1:])):
        _dimension_horizontal(
            msp,
            mapper.point(left, 0)[0],
            mapper.point(right, 0)[0],
            ground_y,
            mapper.point(0, -1.3 - (index % 2) * 0.8)[1],
            f"{right-left:.1f}",
        )
    _dimension_horizontal(
        msp,
        mapper.point(0, 0)[0],
        mapper.point(width_m, 0)[0],
        ground_y,
        mapper.point(0, -2.4)[1],
        f"总长 {width_m:.1f}m",
    )
    _dimension_vertical(
        msp,
        ground_y,
        mapper.point(0, common["bus_conductor_elevation_m"])[1],
        mapper.point(2, 0)[0],
        mapper.point(-1.0, 0)[0],
        f"母线 +{float(common['bus_conductor_elevation_m']):.1f}m",
    )
    highest = max(float(item["terminal_elevation_m"]) for item in panel["equipment_sequence"])
    _dimension_vertical(
        msp,
        ground_y,
        mapper.point(0, highest)[1],
        mapper.point(width_m - 2, 0)[0],
        mapper.point(width_m + 1.0, 0)[0],
        f"最高 +{highest:.1f}m",
    )
    c_m = float(common["minimum_clearances_mm"]["C"]) / 1000
    _dimension_vertical(
        msp,
        ground_y,
        mapper.point(0, c_m)[1],
        mapper.point(4.0, 0)[0],
        mapper.point(3.0, 0)[0],
        f"C≥{c_m:.2f}m",
    )

    inset_y = 18.5
    phase_x = [5.0, 9.0, 13.0]
    for x_m in phase_x:
        _add_circle(msp, mapper.point(x_m, inset_y), mapper.length(0.18), layer="C-BUS")
    _dimension_horizontal(
        msp,
        mapper.point(phase_x[0], 0)[0],
        mapper.point(phase_x[1], 0)[0],
        mapper.point(0, inset_y)[1],
        mapper.point(0, inset_y - 1.3)[1],
        "4.0m",
    )
    _dimension_horizontal(
        msp,
        mapper.point(phase_x[1], 0)[0],
        mapper.point(phase_x[2], 0)[0],
        mapper.point(0, inset_y)[1],
        mapper.point(0, inset_y - 1.3)[1],
        "4.0m",
    )
    _add_mtext(msp, "三相母线横向间距示意", mapper.point(9, 20.5), height=2.4, width=120, layer="C-NOTE")


def _draw_sections(data: dict[str, dict[str, Any]]) -> ezdxf.document.Drawing:
    layout = data["layout"]
    standard = data["standard"]
    section = layout["sections"]
    common = layout["common"]
    doc = ezdxf.new("R2018", setup=False)
    _configure_document(doc, standard)
    msp = doc.modelspace()
    _draw_frame_and_title(
        msp,
        standard,
        drawing_title=section["drawing_title"],
        drawing_id=section["drawing_id"],
        scale_label=section["sheet"]["scale_label"],
    )
    _add_mtext(msp, section["drawing_title"], (420.5, 565), height=6.0, width=600, layer="C-TITLE")
    for panel in section["panels"]:
        _draw_section_panel(msp, panel, section["sheet"]["scale"], common)

    clearance = common["minimum_clearances_mm"]
    _add_mtext(
        msp,
        (
            "220kV屋外最小净距（课程表7-2，mm）\n"
            f"A1={clearance['A1']}  A2={clearance['A2']}  B1={clearance['B1']}  "
            f"B2={clearance['B2']}  C={clearance['C']}  D={clearance['D']}"
        ),
        (45, 535),
        height=2.8,
        width=360,
        layer="C-NOTE",
        attachment=1,
    )
    for index, note in enumerate(section["notes"], start=1):
        _add_mtext(
            msp,
            f"{index}. {note}",
            (405, 535 - (index - 1) * 8.0),
            height=2.5,
            width=405,
            layer="C-NOTE",
            attachment=1,
        )
    _add_line(msp, (410, 90), (410, 455), layer="C-CENTER")
    return doc


def _draw_detail_parameter_table(
    msp: Any,
    rows: list[list[str]],
) -> None:
    bounds = [45.0, 470.0, 410.0, 542.0]
    x1, y1, x2, y2 = bounds
    label_x = x1 + 92.0
    header_height = 10.0
    row_height = (y2 - y1 - header_height) / len(rows)
    _add_rect(msp, bounds, layer="C-NOTE")
    _add_line(msp, (x1, y2 - header_height), (x2, y2 - header_height), layer="C-NOTE")
    _add_line(msp, (label_x, y1), (label_x, y2 - header_height), layer="C-NOTE")
    _add_mtext(
        msp,
        "L1线路间隔课程额定参数表",
        ((x1 + x2) / 2, y2 - header_height / 2),
        height=3.0,
        width=x2 - x1 - 6,
        layer="C-NOTE",
    )
    for index, row in enumerate(rows):
        if len(row) != 2:
            raise ValueError("Detail parameter rows must contain label and value")
        top = y2 - header_height - index * row_height
        bottom = top - row_height
        if index < len(rows) - 1:
            _add_line(msp, (x1, bottom), (x2, bottom), layer="C-NOTE")
        _add_mtext(
            msp,
            str(row[0]),
            ((x1 + label_x) / 2, (top + bottom) / 2),
            height=2.1,
            width=label_x - x1 - 4,
            layer="C-NOTE",
        )
        _add_mtext(
            msp,
            str(row[1]),
            (label_x + 4, (top + bottom) / 2),
            height=2.0,
            width=x2 - label_x - 8,
            layer="C-NOTE",
            attachment=4,
        )


def _draw_line_bay_detail(
    data: dict[str, dict[str, Any]],
) -> ezdxf.document.Drawing:
    layout = data["layout"]
    standard = data["standard"]
    detail = layout["line_bay_detail"]
    common = layout["common"]
    doc = ezdxf.new("R2018", setup=False)
    _configure_document(doc, standard)
    msp = doc.modelspace()
    _draw_frame_and_title(
        msp,
        standard,
        drawing_title=detail["drawing_title"],
        drawing_id=detail["drawing_id"],
        scale_label=detail["sheet"]["scale_label"],
    )
    _add_mtext(
        msp,
        detail["drawing_title"],
        (420.5, 565),
        height=6.0,
        width=600,
        layer="C-TITLE",
    )

    mapper = Mapper(detail["paper_origin_mm"], detail["sheet"]["scale"])
    width_m = float(detail["width_m"])
    ground_y = mapper.point(0, float(detail["ground_elevation_m"]))[1]
    grid_elevation = float(detail["grounding_grid_elevation_m"])
    grid_y = mapper.point(0, grid_elevation)[1]
    _add_line(msp, mapper.point(0, 0), mapper.point(width_m, 0), layer="C-FOUNDATION")
    _add_mtext(
        msp,
        "±0.000",
        mapper.point(0.3, 0.35),
        height=2.4,
        width=42,
        layer="C-DIM",
        attachment=1,
    )

    terminal_points = [
        _draw_section_equipment(msp, mapper, item)
        for item in detail["equipment_sequence"]
    ]
    _add_polyline(msp, terminal_points, layer="C-CONDUCTOR")
    last = terminal_points[-1]
    _draw_arrow(msp, last, (last[0] + 34, last[1] + 18), layer="C-CONDUCTOR")

    grid_start = mapper.point(0.5, grid_elevation)
    grid_end = mapper.point(width_m - 0.5, grid_elevation)
    _add_line(msp, grid_start, grid_end, layer="C-FOUNDATION")
    for item in detail["equipment_sequence"]:
        x_m = float(item["x_m"])
        _add_line(
            msp,
            mapper.point(x_m, 0.0),
            mapper.point(x_m, grid_elevation),
            layer="C-FOUNDATION",
        )
        _add_circle(
            msp,
            mapper.point(x_m, grid_elevation),
            mapper.length(0.08),
            layer="C-FOUNDATION",
        )
    _add_mtext(
        msp,
        "地下水平接地网及设备/构架接地引下线（连接示意）",
        mapper.point(width_m / 2, grid_elevation + 0.18),
        height=2.1,
        width=mapper.length(22),
        layer="C-NOTE",
        attachment=8,
    )

    equipment_x = [float(item["x_m"]) for item in detail["equipment_sequence"]]
    for left, right in zip(equipment_x, equipment_x[1:]):
        _dimension_horizontal(
            msp,
            mapper.point(left, 0)[0],
            mapper.point(right, 0)[0],
            ground_y,
            mapper.point(0, -1.35)[1],
            f"{right-left:.1f}",
        )
    _dimension_horizontal(
        msp,
        mapper.point(0, 0)[0],
        mapper.point(width_m, 0)[0],
        ground_y,
        mapper.point(0, -2.4)[1],
        f"总长 {width_m:.1f}m",
    )
    _dimension_vertical(
        msp,
        ground_y,
        mapper.point(0, common["bus_conductor_elevation_m"])[1],
        mapper.point(2, 0)[0],
        mapper.point(-1.2, 0)[0],
        f"管母 +{float(common['bus_conductor_elevation_m']):.1f}m",
    )
    _dimension_vertical(
        msp,
        ground_y,
        mapper.point(0, common["line_gantry_conductor_elevation_m"])[1],
        mapper.point(width_m - 3, 0)[0],
        mapper.point(width_m + 1.2, 0)[0],
        f"构架 +{float(common['line_gantry_conductor_elevation_m']):.1f}m",
    )
    c_m = float(common["minimum_clearances_mm"]["C"]) / 1000
    _dimension_vertical(
        msp,
        ground_y,
        mapper.point(0, c_m)[1],
        mapper.point(4.2, 0)[0],
        mapper.point(3.2, 0)[0],
        f"C≥{c_m:.2f}m",
    )

    inset_y = 15.8
    phase_x = [4.0, 8.0, 12.0]
    for x_m in phase_x:
        _add_circle(msp, mapper.point(x_m, inset_y), mapper.length(0.16), layer="C-BUS")
    for left, right in zip(phase_x, phase_x[1:]):
        _dimension_horizontal(
            msp,
            mapper.point(left, 0)[0],
            mapper.point(right, 0)[0],
            mapper.point(0, inset_y)[1],
            mapper.point(0, inset_y - 1.15)[1],
            "4.0m",
        )
    _add_mtext(
        msp,
        f"A2≥{float(common['minimum_clearances_mm']['A2'])/1000:.2f}m；采用相间4.0m",
        mapper.point(8.0, inset_y + 0.75),
        height=2.2,
        width=mapper.length(12),
        layer="C-NOTE",
    )
    a1_m = float(common["minimum_clearances_mm"]["A1"]) / 1000
    live_x = 16.0
    earth_x = live_x + a1_m
    _add_circle(msp, mapper.point(live_x, inset_y), mapper.length(0.16), layer="C-BUS")
    _add_line(
        msp,
        mapper.point(earth_x, inset_y - 0.65),
        mapper.point(earth_x, inset_y + 0.65),
        layer="C-STRUCTURE",
    )
    _dimension_horizontal(
        msp,
        mapper.point(live_x, 0)[0],
        mapper.point(earth_x, 0)[0],
        mapper.point(0, inset_y)[1],
        mapper.point(0, inset_y - 1.15)[1],
        f"A1≥{a1_m:.2f}m",
    )

    _draw_detail_parameter_table(msp, detail["parameter_rows"])
    note_bounds = [425.0, 470.0, 815.0, 542.0]
    _add_rect(msp, note_bounds, layer="C-NOTE")
    _add_mtext(
        msp,
        "设计说明与边界",
        ((note_bounds[0] + note_bounds[2]) / 2, note_bounds[3] - 6),
        height=3.0,
        width=note_bounds[2] - note_bounds[0] - 8,
        layer="C-NOTE",
        attachment=8,
    )
    for index, note in enumerate(detail["notes"], start=1):
        _add_mtext(
            msp,
            f"{index}. {note}",
            (note_bounds[0] + 5, note_bounds[3] - 14 - (index - 1) * 13.5),
            height=2.05,
            width=note_bounds[2] - note_bounds[0] - 10,
            layer="C-NOTE",
            attachment=1,
        )
    return doc


def validate_document(
    doc: ezdxf.document.Drawing,
    data: dict[str, dict[str, Any]],
    *,
    expected_title: str,
) -> dict[str, Any]:
    auditor = doc.audit()
    if auditor.has_errors:
        raise ValueError(f"ezdxf audit failed: {[str(error) for error in auditor.errors]}")
    msp = doc.modelspace()
    if any(entity.dxf.layer == "0" for entity in msp):
        raise ValueError("Switchyard drawing contains modelspace entities on layer 0")
    forbidden = [
        entity.dxftype()
        for entity in msp
        if entity.dxftype() in {"IMAGE", "UNDERLAY", "ACAD_PROXY_ENTITY"}
    ]
    if forbidden:
        raise ValueError(f"Forbidden external/proxy entities found: {forbidden}")
    text_payload = "\n".join(entity.text for entity in msp.query("MTEXT"))
    if expected_title not in text_payload:
        raise ValueError(f"Drawing title is missing: {expected_title}")
    if "\ufffd" in text_payload:
        raise ValueError("Replacement character found in switchyard drawing text")

    extents = bbox.extents(msp, fast=True)
    if extents.has_data:
        if (
            extents.extmin.x < 0
            or extents.extmin.y < 0
            or extents.extmax.x > 841
            or extents.extmax.y > 594
        ):
            raise ValueError(
                "Switchyard drawing extents exceed A1 sheet: "
                f"({extents.extmin.x:.2f}, {extents.extmin.y:.2f})-"
                f"({extents.extmax.x:.2f}, {extents.extmax.y:.2f})"
            )
    return {
        "acadver": doc.dxfversion,
        "modelspace_entities": len(msp),
        "mtext_count": len(msp.query("MTEXT")),
        "line_count": len(msp.query("LINE")),
        "polyline_count": len(msp.query("LWPOLYLINE")),
        "circle_count": len(msp.query("CIRCLE")),
        "extents": [
            round(extents.extmin.x, 3),
            round(extents.extmin.y, 3),
            round(extents.extmax.x, 3),
            round(extents.extmax.y, 3),
        ],
    }


def switchyard_semantic_fingerprint(doc: ezdxf.document.Drawing) -> str:
    """Hash drawing semantics while ignoring DXF metadata and class ordering."""

    return _base_semantic_fingerprint(
        doc,
        layer_prefixes=("C-",),
        block_prefixes=(),
        linetype_names=frozenset({"CENTER", "RESERVED"}),
        style_names=frozenset({"HZTXT", "LATIN"}),
    )


def generate_switchyard_drawings(
    *,
    layout_path: Path = DEFAULT_LAYOUT,
    standard_path: Path = DEFAULT_STANDARD,
    baseline_path: Path = DEFAULT_BASELINE,
    plan_output: Path = DEFAULT_PLAN_OUTPUT,
    section_output: Path = DEFAULT_SECTION_OUTPUT,
    detail_output: Path = DEFAULT_DETAIL_OUTPUT,
) -> dict[str, Any]:
    previous_fixed_metadata = ezdxf.options.write_fixed_meta_data_for_testing
    ezdxf.options.write_fixed_meta_data_for_testing = True
    try:
        data = load_project_data(
            layout_path=layout_path,
            standard_path=standard_path,
            baseline_path=baseline_path,
        )
        validate_project_data(data)
        plan_doc = _draw_plan(data)
        section_doc = _draw_sections(data)
        detail_doc = _draw_line_bay_detail(data)
        plan_summary = validate_document(
            plan_doc, data, expected_title=data["layout"]["plan"]["drawing_title"]
        )
        section_summary = validate_document(
            section_doc,
            data,
            expected_title=data["layout"]["sections"]["drawing_title"],
        )
        detail_summary = validate_document(
            detail_doc,
            data,
            expected_title=data["layout"]["line_bay_detail"]["drawing_title"],
        )
        for doc, path, summary in (
            (plan_doc, plan_output, plan_summary),
            (section_doc, section_output, section_summary),
            (detail_doc, detail_output, detail_summary),
        ):
            path = path.resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            doc.saveas(path)
            reloaded = ezdxf.readfile(path)
            if len(reloaded.modelspace()) != len(doc.modelspace()):
                raise ValueError(f"DXF round-trip changed entity count: {path}")
            summary["semantic_fingerprint"] = switchyard_semantic_fingerprint(reloaded)
        plan_summary.update(output=str(plan_output.resolve()), bytes=plan_output.resolve().stat().st_size)
        section_summary.update(output=str(section_output.resolve()), bytes=section_output.resolve().stat().st_size)
        detail_summary.update(output=str(detail_output.resolve()), bytes=detail_output.resolve().stat().st_size)
        return {"plan": plan_summary, "section": section_summary, "detail": detail_summary}
    finally:
        ezdxf.options.write_fixed_meta_data_for_testing = previous_fixed_metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT)
    parser.add_argument("--standard", type=Path, default=DEFAULT_STANDARD)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--plan-output", type=Path, default=DEFAULT_PLAN_OUTPUT)
    parser.add_argument("--section-output", type=Path, default=DEFAULT_SECTION_OUTPUT)
    parser.add_argument("--detail-output", type=Path, default=DEFAULT_DETAIL_OUTPUT)
    parser.add_argument(
        "--verify-against",
        nargs=3,
        type=Path,
        metavar=("PLAN_DXF", "SECTION_DXF", "DETAIL_DXF"),
        help="Compare stable drawing semantics against committed plan, section and detail DXFs",
    )
    args = parser.parse_args()
    summary = generate_switchyard_drawings(
        layout_path=args.layout,
        standard_path=args.standard,
        baseline_path=args.baseline,
        plan_output=args.plan_output,
        section_output=args.section_output,
        detail_output=args.detail_output,
    )
    if args.verify_against:
        references = {
            "plan": args.verify_against[0].resolve(),
            "section": args.verify_against[1].resolve(),
            "detail": args.verify_against[2].resolve(),
        }
        for label, reference_path in references.items():
            if not reference_path.is_file():
                raise FileNotFoundError(f"Reference {label} DXF not found: {reference_path}")
            reference = ezdxf.readfile(reference_path)
            reference_fingerprint = switchyard_semantic_fingerprint(reference)
            if summary[label]["semantic_fingerprint"] != reference_fingerprint:
                raise ValueError(
                    f"Generated {label} DXF differs semantically from {reference_path}"
                )
        summary["verification"] = "semantic_match"
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
