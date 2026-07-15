from __future__ import annotations

import unittest
from pathlib import Path

import ezdxf

from drawings.scripts.generate_single_line import (
    DEFAULT_OUTPUT,
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
        self.assertTrue(
            any(
                record.get("BAY_ID") == "SVG-1"
                and record.get("TYPE") == "dynamic_svg"
                for record in records
            )
        )
        for bay_id in ("GROUND-35kV-I", "GROUND-35kV-II", "GROUND-10kV-I", "GROUND-10kV-II"):
            self.assertTrue(
                any(
                    record.get("BAY_ID") == bay_id
                    and record.get("TYPE") == "grounding_transformer_low_resistance"
                    and record.get("STATUS") == "course_assumption"
                    for record in records
                )
            )
        self.assertTrue(
            any(
                record.get("BAY_ID") == "TS1-LV-IN"
                and record.get("TYPE") == "0_4kv_incomer_acb"
                and record.get("STATE") == "closed"
                for record in records
            )
        )
        self.assertTrue(
            any(
                record.get("BAY_ID") == "TS2-LV-IN"
                and record.get("TYPE") == "0_4kv_incomer_acb"
                and record.get("STATE") == "open"
                for record in records
            )
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
        self.assertIn("0.4kV母联正常闭合", payload)
        self.assertIn("31.5MVA", payload)
        self.assertIn("SVG-1 ±12Mvar", payload)
        self.assertGreaterEqual(payload.count("正常367.780A"), 2)
        self.assertGreaterEqual(payload.count("N-1需735.559A（须限发）"), 2)
        self.assertIn("站用电备用电源", payload)
        self.assertIn("无功补偿及冷却", payload)
        self.assertIn("集控通信及监控", payload)
        self.assertGreaterEqual(payload.count("接地变+小电阻"), 4)
        self.assertNotIn("接地方式P", payload)
        self.assertNotIn("Sn=P", payload)
        self.assertNotIn("\ufffd", payload)
        self.assertNotIn(str(ROOT), path.read_text(encoding="utf-8", errors="ignore"))


if __name__ == "__main__":
    unittest.main()
