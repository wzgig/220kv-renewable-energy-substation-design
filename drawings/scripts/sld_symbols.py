"""Reusable single-line-diagram symbols for the project DXF generator.

All block geometry is created on layer 0 so that inserted symbols inherit the
target electrical layer.  Engineering identity is stored as block attributes,
which makes the generated drawing machine-checkable without relying on colour
or nearby annotation text.
"""

from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

from ezdxf.document import Drawing
from ezdxf.layouts import BlockLayout, Modelspace


ATTRIBUTE_TAGS = (
    "BAY_ID",
    "TYPE",
    "STATE",
    "STATUS",
    "SECTION",
)


def _entity_attribs() -> dict[str, Any]:
    return {"layer": "0", "color": 0, "lineweight": -2}


def _add_hidden_attributes(block: BlockLayout) -> None:
    for index, tag in enumerate(ATTRIBUTE_TAGS):
        block.add_attdef(
            tag,
            insert=(0.0, -20.0 - index),
            text="",
            height=0.1,
            dxfattribs={"layer": "0", "flags": 1},
        )


def _add_ground_geometry(block: BlockLayout, y: float = 0.0) -> None:
    attribs = _entity_attribs()
    block.add_line((0.0, y + 3.0), (0.0, y), dxfattribs=attribs)
    block.add_line((-3.0, y), (3.0, y), dxfattribs=attribs)
    block.add_line((-2.0, y - 1.2), (2.0, y - 1.2), dxfattribs=attribs)
    block.add_line((-1.0, y - 2.4), (1.0, y - 2.4), dxfattribs=attribs)


def _add_cb(block: BlockLayout, *, open_state: bool) -> None:
    attribs = _entity_attribs()
    block.add_lwpolyline(
        [(-3.0, -4.0), (3.0, -4.0), (3.0, 4.0), (-3.0, 4.0)],
        close=True,
        dxfattribs=attribs,
    )
    if open_state:
        block.add_line((0.0, -4.0), (0.0, -1.2), dxfattribs=attribs)
        block.add_line((0.0, 1.2), (0.0, 4.0), dxfattribs=attribs)
        block.add_circle((0.0, -1.2), 0.45, dxfattribs=attribs)
        block.add_circle((0.0, 1.2), 0.45, dxfattribs=attribs)
        block.add_line((0.0, -0.8), (1.8, 1.0), dxfattribs=attribs)
    else:
        block.add_line((0.0, -4.0), (0.0, 4.0), dxfattribs=attribs)
    _add_hidden_attributes(block)


def _add_ds(block: BlockLayout, *, open_state: bool) -> None:
    attribs = _entity_attribs()
    block.add_line((0.0, -5.0), (0.0, -2.6), dxfattribs=attribs)
    block.add_line((0.0, 2.6), (0.0, 5.0), dxfattribs=attribs)
    block.add_circle((0.0, -2.3), 0.45, dxfattribs=attribs)
    block.add_circle((0.0, 2.3), 0.45, dxfattribs=attribs)
    if open_state:
        block.add_line((0.0, -1.9), (2.4, 1.9), dxfattribs=attribs)
    else:
        block.add_line((0.0, -1.9), (0.0, 1.9), dxfattribs=attribs)
    _add_hidden_attributes(block)


def _add_earthing_switch(block: BlockLayout, *, open_state: bool) -> None:
    """Draw a shunt earthing switch with its normal state made explicit."""

    attribs = _entity_attribs()
    block.add_line((0.0, 6.0), (0.0, 2.8), dxfattribs=attribs)
    block.add_circle((0.0, 2.3), 0.45, dxfattribs=attribs)
    block.add_circle((0.0, -2.0), 0.45, dxfattribs=attribs)
    if open_state:
        block.add_line((0.0, -1.6), (2.4, 1.8), dxfattribs=attribs)
    else:
        block.add_line((0.0, -1.6), (0.0, 1.8), dxfattribs=attribs)
    _add_ground_geometry(block, y=-6.0)
    block.add_line((0.0, -3.0), (0.0, -2.45), dxfattribs=attribs)
    block.add_text(
        "ES",
        height=1.5,
        dxfattribs={**attribs, "style": "LATIN"},
    ).set_placement((3.2, -0.8))
    _add_hidden_attributes(block)


def _add_ct(block: BlockLayout) -> None:
    attribs = _entity_attribs()
    block.add_line((0.0, -5.0), (0.0, 5.0), dxfattribs=attribs)
    block.add_circle((0.0, 0.0), 2.6, dxfattribs=attribs)
    block.add_text(
        "TA",
        height=1.6,
        dxfattribs={**attribs, "style": "LATIN"},
    ).set_placement((3.5, -0.8))
    _add_hidden_attributes(block)


def _add_voltage_transformer(block: BlockLayout, label: str) -> None:
    attribs = _entity_attribs()
    block.add_line((0.0, 6.0), (0.0, 3.0), dxfattribs=attribs)
    block.add_circle((0.0, 0.8), 2.8, dxfattribs=attribs)
    block.add_circle((0.0, -3.6), 2.8, dxfattribs=attribs)
    block.add_text(
        label,
        height=1.5,
        dxfattribs={**attribs, "style": "LATIN"},
    ).set_placement((3.8, -1.2))
    _add_ground_geometry(block, y=-7.0)
    block.add_line((0.0, -6.4), (0.0, -4.8), dxfattribs=attribs)
    _add_hidden_attributes(block)


def _add_la(block: BlockLayout) -> None:
    attribs = _entity_attribs()
    block.add_line((0.0, 6.0), (0.0, 3.0), dxfattribs=attribs)
    block.add_lwpolyline(
        [(0.0, 3.0), (-1.8, 1.8), (1.8, 0.6), (-1.8, -0.6), (1.8, -1.8), (0.0, -3.0)],
        dxfattribs=attribs,
    )
    _add_ground_geometry(block, y=-6.0)
    block.add_line((0.0, -3.0), (0.0, -3.0), dxfattribs=attribs)
    _add_hidden_attributes(block)


def _add_star_connection(
    block: BlockLayout,
    center: tuple[float, float],
    *,
    neutral: bool,
) -> None:
    """Draw the IEC single-line star winding marker inside a winding circle."""

    attribs = _entity_attribs()
    cx, cy = center
    radius = 2.8
    for angle_deg in (90.0, 210.0, 330.0):
        angle = math.radians(angle_deg)
        block.add_line(
            (cx, cy),
            (cx + radius * math.cos(angle), cy + radius * math.sin(angle)),
            dxfattribs=attribs,
        )
    if neutral:
        block.add_line((cx, cy), (cx + 4.2, cy), dxfattribs=attribs)
        block.add_text(
            "N",
            height=1.35,
            dxfattribs={**attribs, "style": "LATIN"},
        ).set_placement((cx + 4.45, cy - 0.65))


def _add_delta_connection(block: BlockLayout, center: tuple[float, float]) -> None:
    """Draw the IEC single-line delta winding marker inside a winding circle."""

    attribs = _entity_attribs()
    cx, cy = center
    radius = 2.8
    points = []
    for angle_deg in (90.0, 210.0, 330.0):
        angle = math.radians(angle_deg)
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    block.add_lwpolyline(points, close=True, dxfattribs=attribs)


def _add_transformer(
    block: BlockLayout,
    *,
    high_connection: str,
    low_connection: str,
) -> None:
    attribs = _entity_attribs()
    block.add_line((0.0, 13.0), (0.0, 9.7), dxfattribs=attribs)
    block.add_circle((0.0, 4.7), 5.2, dxfattribs=attribs)
    block.add_circle((0.0, -4.7), 5.2, dxfattribs=attribs)
    if high_connection == "YN":
        _add_star_connection(block, (0.0, 4.7), neutral=True)
    elif high_connection == "D":
        _add_delta_connection(block, (0.0, 4.7))
    else:
        raise ValueError(f"Unsupported transformer high-side connection: {high_connection}")
    if low_connection == "yn":
        _add_star_connection(block, (0.0, -4.7), neutral=True)
    elif low_connection == "d":
        _add_delta_connection(block, (0.0, -4.7))
    else:
        raise ValueError(f"Unsupported transformer low-side connection: {low_connection}")
    block.add_line((0.0, -9.7), (0.0, -13.0), dxfattribs=attribs)
    _add_hidden_attributes(block)


def _add_ground(block: BlockLayout) -> None:
    _add_ground_geometry(block)
    _add_hidden_attributes(block)


def _add_grounding_transformer_resistor(block: BlockLayout) -> None:
    """Draw a grounding transformer followed by a neutral resistor and earth."""

    attribs = _entity_attribs()
    block.add_line((0.0, 9.0), (0.0, 6.6), dxfattribs=attribs)
    block.add_circle((0.0, 4.0), 2.8, dxfattribs=attribs)
    block.add_circle((0.0, 0.0), 2.8, dxfattribs=attribs)
    block.add_lwpolyline(
        [(-1.7, 5.2), (0.0, 4.0), (-1.7, 2.8), (1.7, 4.0)],
        dxfattribs=attribs,
    )
    _add_star_connection(block, (0.0, 0.0), neutral=True)
    block.add_text(
        "ZN",
        height=1.4,
        dxfattribs={**attribs, "style": "LATIN"},
    ).set_placement((3.5, 1.1))
    block.add_line((0.0, -2.8), (0.0, -3.6), dxfattribs=attribs)
    block.add_lwpolyline(
        [
            (0.0, -3.6),
            (-1.6, -4.2),
            (1.6, -4.8),
            (-1.6, -5.4),
            (1.6, -6.0),
            (0.0, -7.0),
        ],
        dxfattribs=attribs,
    )
    block.add_text(
        "R",
        height=1.4,
        dxfattribs={**attribs, "style": "LATIN"},
    ).set_placement((2.4, -5.8))
    _add_ground_geometry(block, y=-10.0)
    _add_hidden_attributes(block)


def _add_arrow(block: BlockLayout, *, upward: bool) -> None:
    attribs = _entity_attribs()
    if upward:
        block.add_line((0.0, -5.0), (0.0, 4.0), dxfattribs=attribs)
        block.add_lwpolyline([(-2.0, 2.0), (0.0, 5.0), (2.0, 2.0)], dxfattribs=attribs)
    else:
        block.add_line((0.0, 5.0), (0.0, -4.0), dxfattribs=attribs)
        block.add_lwpolyline([(-2.0, -2.0), (0.0, -5.0), (2.0, -2.0)], dxfattribs=attribs)
    _add_hidden_attributes(block)


def _add_terminal(block: BlockLayout) -> None:
    attribs = _entity_attribs()
    block.add_line((0.0, -4.0), (0.0, 4.0), dxfattribs=attribs)
    block.add_circle((0.0, 0.0), 0.8, dxfattribs=attribs)
    _add_hidden_attributes(block)


def ensure_symbol_blocks(doc: Drawing) -> None:
    """Create the reusable block library if it is not already present."""

    builders = {
        "SLD_CB_CLOSED": lambda block: _add_cb(block, open_state=False),
        "SLD_CB_OPEN": lambda block: _add_cb(block, open_state=True),
        "SLD_DS_CLOSED": lambda block: _add_ds(block, open_state=False),
        "SLD_DS_OPEN": lambda block: _add_ds(block, open_state=True),
        "SLD_ES_OPEN": lambda block: _add_earthing_switch(block, open_state=True),
        "SLD_CT": _add_ct,
        "SLD_PT": lambda block: _add_voltage_transformer(block, "TV"),
        "SLD_CVT": lambda block: _add_voltage_transformer(block, "CVT"),
        "SLD_LA": _add_la,
        "SLD_TX_YND11": lambda block: _add_transformer(
            block, high_connection="YN", low_connection="d"
        ),
        "SLD_TX_DYN11": lambda block: _add_transformer(
            block, high_connection="D", low_connection="yn"
        ),
        "SLD_GROUND": _add_ground,
        "SLD_GROUNDING_TX_RESISTOR": _add_grounding_transformer_resistor,
        "SLD_ARROW_UP": lambda block: _add_arrow(block, upward=True),
        "SLD_ARROW_DOWN": lambda block: _add_arrow(block, upward=False),
        "SLD_TERMINAL": _add_terminal,
    }
    for name, builder in builders.items():
        if name in doc.blocks:
            continue
        block = doc.blocks.new(name=name, base_point=(0.0, 0.0))
        builder(block)


def insert_symbol(
    msp: Modelspace,
    name: str,
    insert: tuple[float, float],
    *,
    layer: str,
    bay_id: str,
    device_type: str,
    state: str = "closed",
    status: str = "in_service",
    section: str = "",
    rotation: float = 0.0,
) -> Any:
    """Insert a symbol and attach stable semantic attributes."""

    block_ref = msp.add_blockref(
        name,
        insert,
        dxfattribs={"layer": layer, "rotation": rotation},
    )
    block_ref.add_auto_attribs(
        {
            "BAY_ID": bay_id,
            "TYPE": device_type,
            "STATE": state,
            "STATUS": status,
            "SECTION": section,
        }
    )
    return block_ref


def semantic_attributes(block_ref: Any) -> Mapping[str, str]:
    """Return block attributes as an uppercase-key mapping for validation."""

    return {attrib.dxf.tag.upper(): attrib.dxf.text for attrib in block_ref.attribs}
