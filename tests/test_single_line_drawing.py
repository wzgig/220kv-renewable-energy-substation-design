from __future__ import annotations

import unittest
from pathlib import Path

import ezdxf

from drawings.scripts.generate_single_line import (
    DEFAULT_OUTPUT,
    DEVICE_HALF_LENGTH,
    build_document,
    load_project_data,
    semantic_fingerprint,
    validate_document,
    validate_project_data,
)
from drawings.scripts.sld_symbols import semantic_attributes


ROOT = Path(__file__).resolve().parents[1]


class SingleLineDrawingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_project_data()
        validate_project_data(cls.data)
        cls.doc = build_document(cls.data)
        cls.summary = validate_document(cls.doc, cls.data)

    def test_layout_sets_match_frozen_baseline(self) -> None:
        layout = self.data["layout"]
        baseline = self.data["baseline"]

        expected_feeders = {
            feeder["id"]
            for section in baseline["connection_35kv"]["sections"]
            for feeder in section["feeder_circuits"]
        }
        actual_feeders = {
            feeder["id"]
            for feeder in layout["circuits"]["35kv"]["collector_feeders"]
        }
        self.assertEqual(actual_feeders, expected_feeders)
        self.assertEqual(len(actual_feeders), 12)

        expected_auxiliary_loads = {
            item["name"] for item in self.data["load_results"]["load_10kv"]["items"]
        }
        actual_auxiliary_loads = {
            item["load_ref"]
            for item in layout["circuits"]["10kv"]["auxiliary_load_groups"]
        }
        self.assertEqual(actual_auxiliary_loads, expected_auxiliary_loads)
        self.assertEqual(len(actual_auxiliary_loads), 3)
        self.assertEqual(
            {item["id"] for item in layout["circuits"]["35kv"]["source_transformer_bays"]},
            {"T10-1-HV", "T10-2-HV"},
        )
        self.assertEqual(
            {item["id"] for item in layout["circuits"]["35kv"]["reserved_bays"]},
            {"R1", "R2"},
        )

    def test_bus_tie_and_dark_standby_states_are_unambiguous(self) -> None:
        layout = self.data["layout"]
        tie_states = {item["id"]: item["state"] for item in layout["ties"]}
        self.assertEqual(
            tie_states,
            {
                "TIE-220": "open",
                "TIE-35": "open",
                "TIE-10": "open",
                "TIE-0P4": "closed",
            },
        )
        incomers = layout["circuits"]["0_4kv"]["station_service_incomers"]
        self.assertEqual([item["state"] for item in incomers].count("closed"), 1)
        self.assertEqual([item["state"] for item in incomers].count("open"), 1)

        grounding = self.data["design_inputs"]["calculation_rules"]["grounding"]
        self.assertEqual(
            grounding["35kv"]["selected_grounding_transformer_capacity_kva_each"],
            1000,
        )
        self.assertEqual(
            grounding["10kv"]["selected_grounding_transformer_capacity_kva_each"],
            200,
        )
        self.assertEqual(grounding["35kv"]["source_count"], 2)
        self.assertEqual(grounding["10kv"]["source_count"], 2)
        self.assertIn("both_section_grounding_sources_in_parallel", grounding["35kv"]["prohibited_state"])
        self.assertIn("both_section_grounding_sources_in_parallel", grounding["10kv"]["prohibited_state"])

    def test_dxf_structure_is_a1_r2018_without_layer_zero_entities(self) -> None:
        self.assertEqual(self.summary["acadver"], "AC1032")
        self.assertGreater(self.summary["modelspace_entities"], 300)
        self.assertGreater(self.summary["insert_count"], 100)
        self.assertEqual(self.summary["extents"], [10.0, 10.0, 831.0, 584.0])
        self.assertFalse(
            [entity for entity in self.doc.modelspace() if entity.dxf.layer == "0"]
        )
        self.assertEqual(self.doc.header["$INSUNITS"], 4)
        hz_style = self.doc.styles.get("HZTXT")
        self.assertEqual(hz_style.dxf.font.lower(), "txt.shx")
        self.assertEqual(hz_style.dxf.bigfont.lower(), "gbcbig.shx")

    def test_reserved_and_svg_bays_use_expected_layers(self) -> None:
        inserts = self.doc.modelspace().query("INSERT")
        by_bay: dict[str, set[str]] = {}
        for insert in inserts:
            attrs = semantic_attributes(insert)
            bay_id = attrs.get("BAY_ID", "")
            by_bay.setdefault(bay_id, set()).add(insert.dxf.layer)

        for bay_id in ("L3", "R1", "R2"):
            self.assertEqual(by_bay[bay_id], {"E-RESERVED"})
        for bay_id in ("SVG-1", "SVG-2"):
            self.assertEqual(by_bay[bay_id], {"E-CONDUCTOR"})

    def test_key_equipment_semantics_survive_block_attributes(self) -> None:
        inserts = self.doc.modelspace().query("INSERT")
        records = [semantic_attributes(insert) for insert in inserts]

        self.assertTrue(
            any(
                record.get("BAY_ID") == "T10-1-HV"
                and record.get("TYPE") == "35kv_source_transformer_breaker"
                for record in records
            )
        )

    def test_protection_grounding_and_reserved_bay_semantics_are_complete(self) -> None:
        inserts = list(self.doc.modelspace().query("INSERT"))
        records = [
            (insert.dxf.name, semantic_attributes(insert)) for insert in inserts
        ]
        semantic_records = [attrs for _, attrs in records]

        for bay_id in ("L1", "L2", "L3"):
            self.assertTrue(
                any(
                    block == "SLD_ES_OPEN"
                    and attrs.get("BAY_ID") == bay_id
                    and attrs.get("TYPE") == "line_earthing_switch"
                    and attrs.get("STATE") == "open"
                    for block, attrs in records
                )
            )

        l3_disconnectors = [
            (block, attrs)
            for block, attrs in records
            if attrs.get("BAY_ID") == "L3"
            and attrs.get("TYPE") in {"bus_disconnector", "line_disconnector"}
        ]
        self.assertEqual(len(l3_disconnectors), 2)
        self.assertTrue(
            all(
                block == "SLD_DS_OPEN" and attrs.get("STATE") == "open"
                for block, attrs in l3_disconnectors
            )
        )

        neutral_cts = [
            attrs
            for _, attrs in records
            if attrs.get("TYPE") == "220kv_neutral_current_transformer"
        ]
        self.assertEqual({attrs.get("BAY_ID") for attrs in neutral_cts}, {"T1", "T2"})

        bus_moas = [
            attrs for _, attrs in records if attrs.get("TYPE") == "bus_surge_arrester"
        ]
        self.assertEqual(
            {attrs.get("BAY_ID") for attrs in bus_moas},
            {"MOA-35kV-I", "MOA-35kV-II", "MOA-10kV-I", "MOA-10kV-II"},
        )

        grounding_blocks = [
            (block, attrs)
            for block, attrs in records
            if attrs.get("TYPE") == "grounding_transformer_low_resistance"
        ]
        self.assertEqual(len(grounding_blocks), 4)
        self.assertTrue(
            all(
                block == "SLD_GROUNDING_TX_RESISTOR"
                and attrs.get("STATE") == "grounded"
                for block, attrs in grounding_blocks
            )
        )
        self.assertTrue(
            any(
                record.get("BAY_ID") == "SVG-1"
                and record.get("TYPE") == "dynamic_svg"
                for record in semantic_records
            )
        )
        for bay_id in ("GROUND-35kV-I", "GROUND-35kV-II", "GROUND-10kV-I", "GROUND-10kV-II"):
            self.assertTrue(
                any(
                    record.get("BAY_ID") == bay_id
                    and record.get("TYPE") == "grounding_transformer_low_resistance"
                    and record.get("STATUS") == "course_assumption"
                    for record in semantic_records
                )
            )
        self.assertTrue(
            any(
                record.get("BAY_ID") == "TS1-LV-IN"
                and record.get("TYPE") == "0_4kv_incomer_acb"
                and record.get("STATE") == "closed"
                for record in semantic_records
            )
        )
        self.assertTrue(
            any(
                record.get("BAY_ID") == "TS2-LV-IN"
                and record.get("TYPE") == "0_4kv_incomer_acb"
                and record.get("STATE") == "open"
                for record in semantic_records
            )
        )

    def test_line_earthing_switch_taps_are_on_line_side_of_disconnectors(self) -> None:
        modelspace = self.doc.modelspace()
        expected_bays = {"L1", "L2", "L3"}
        circuit_x = {
            str(circuit["id"]): float(circuit["x"])
            for circuit in self.data["layout"]["circuits"]["220kv"]["lines"]
        }
        earthing_switches = {}
        line_disconnectors = {}
        for insert in modelspace.query("INSERT"):
            attrs = semantic_attributes(insert)
            bay_id = attrs.get("BAY_ID", "")
            if attrs.get("TYPE") == "line_earthing_switch":
                earthing_switches[bay_id] = insert
            elif attrs.get("TYPE") == "line_disconnector":
                line_disconnectors[bay_id] = insert

        self.assertEqual(set(earthing_switches), expected_bays)
        self.assertEqual(set(line_disconnectors), expected_bays)
        branch_polylines = [
            [(float(x), float(y)) for x, y in polyline.get_points("xy")]
            for polyline in modelspace.query("LWPOLYLINE")
        ]

        for bay_id in sorted(expected_bays):
            earthing_switch = earthing_switches[bay_id]
            symbol_x = float(earthing_switch.dxf.insert.x)
            symbol_y = float(earthing_switch.dxf.insert.y)
            main_x = circuit_x[bay_id]
            matching_branches = [
                points
                for points in branch_polylines
                if len(points) == 3
                and abs(points[0][0] - main_x) < 1e-9
                and abs(points[1][0] - symbol_x) < 1e-9
                and abs(points[2][0] - symbol_x) < 1e-9
                and abs(points[0][1] - points[1][1]) < 1e-9
                and abs(points[2][1] - (symbol_y + 6.0)) < 1e-9
            ]
            self.assertEqual(
                len(matching_branches),
                1,
                f"{bay_id} ES branch geometry must connect to its symbol",
            )

            tap_y = matching_branches[0][0][1]
            line_disconnector = line_disconnectors[bay_id]
            line_side_terminal_y = (
                float(line_disconnector.dxf.insert.y)
                + DEVICE_HALF_LENGTH[line_disconnector.dxf.name]
            )
            self.assertGreater(
                tap_y,
                line_side_terminal_y,
                f"{bay_id} ES tap must be beyond the line-side QS terminal",
            )

    def test_committed_dxf_round_trip_and_chinese_text(self) -> None:
        path = Path(DEFAULT_OUTPUT)
        self.assertTrue(path.is_file(), f"Missing generated DXF: {path}")
        doc = ezdxf.readfile(path)
        summary = validate_document(doc, self.data)
        self.assertEqual(summary["acadver"], "AC1032")
        self.assertEqual(semantic_fingerprint(doc), semantic_fingerprint(self.doc))

        payload = "\n".join(entity.text for entity in doc.modelspace().query("MTEXT"))
        self.assertIn("220kV新能源汇集变电所电气主接线简图", payload)
        self.assertIn("220kV分段断路器（常断）", payload)
        self.assertIn("0.4kV母联正常闭合", payload)
        self.assertIn("31.5MVA", payload)
        self.assertIn("SVG-1 ±12Mvar", payload)
        self.assertGreaterEqual(payload.count("正常367.780A"), 2)
        self.assertGreaterEqual(payload.count("N-1需735.559A（须限发）"), 2)
        self.assertIn("站用电备用电源", payload)
        self.assertIn("无功补偿及冷却", payload)
        self.assertIn("集控通信及监控", payload)
        self.assertGreaterEqual(payload.count("接地变+低电阻"), 4)
        self.assertGreaterEqual(payload.count("1000kVA ZN接地变+低电阻"), 2)
        self.assertGreaterEqual(payload.count("200kVA ZN接地变+低电阻"), 2)
        self.assertGreaterEqual(payload.count("400A / 50.5Ω / 10s"), 2)
        self.assertGreaterEqual(payload.count("200A / 28.9Ω / 10s"), 2)
        self.assertGreaterEqual(payload.count("架空+入口MOA"), 7)
        self.assertGreaterEqual(payload.count("电缆+ZCT"), 10)
        self.assertGreaterEqual(payload.count("YH5WZ-51/134"), 2)
        self.assertGreaterEqual(payload.count("YH5WZ-17/45"), 2)
        self.assertIn("中性点TA直接接地", payload)
        self.assertIn("35/10.5kV YNd11", payload)
        self.assertIn("SCB14干式", payload)
        self.assertIn("7回35kV架空入口设MOA", payload)
        self.assertIn("禁止母联合闸且两套并联", payload)
        self.assertIn("本方案不设限流电抗器", payload)
        self.assertNotIn("接地方式P", payload)
        self.assertNotIn("Sn=P", payload)
        self.assertNotIn("\ufffd", payload)
        self.assertNotIn(str(ROOT), path.read_text(encoding="utf-8", errors="ignore"))


if __name__ == "__main__":
    unittest.main()
