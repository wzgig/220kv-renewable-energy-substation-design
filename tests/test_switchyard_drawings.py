from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import ezdxf

from drawings.scripts.generate_switchyard_drawings import (
    DEFAULT_PLAN_OUTPUT,
    DEFAULT_SECTION_OUTPUT,
    _draw_plan,
    _draw_sections,
    generate_switchyard_drawings,
    load_project_data,
    switchyard_semantic_fingerprint,
    validate_document,
    validate_project_data,
)


ROOT = Path(__file__).resolve().parents[1]


class SwitchyardDrawingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_project_data()
        validate_project_data(cls.data)
        cls.plan_doc = _draw_plan(cls.data)
        cls.section_doc = _draw_sections(cls.data)
        cls.plan_summary = validate_document(
            cls.plan_doc,
            cls.data,
            expected_title=cls.data["layout"]["plan"]["drawing_title"],
        )
        cls.section_summary = validate_document(
            cls.section_doc,
            cls.data,
            expected_title=cls.data["layout"]["sections"]["drawing_title"],
        )

    def test_layout_matches_frozen_220kv_scope_and_clearances(self) -> None:
        layout = self.data["layout"]
        baseline = self.data["baseline"]

        self.assertEqual(layout["plan"]["sheet"]["scale"], 200)
        self.assertEqual(layout["sections"]["sheet"]["scale"], 100)
        self.assertEqual(layout["plan"]["bus_tie"]["normal_state"], "open")
        self.assertEqual(
            layout["common"]["minimum_clearances_mm"],
            baseline["switchyard_220kv"]["minimum_clearances_mm"],
        )
        self.assertEqual(
            layout["common"]["typical_function_center_pitch_m"],
            baseline["switchyard_220kv"]["typical_function_center_pitch_m"],
        )
        self.assertEqual(
            layout["common"]["plan_site_size_m"],
            baseline["switchyard_220kv"]["plan_site_size_m"],
        )
        self.assertEqual(
            {item["id"] for item in layout["plan"]["line_bays"]},
            {"L1", "L2", "L3"},
        )
        self.assertEqual(
            {item["id"] for item in layout["plan"]["transformer_bays"]},
            {"T1", "T2"},
        )
        self.assertGreaterEqual(
            layout["common"]["phase_spacing_m"] * 1000,
            layout["common"]["minimum_clearances_mm"]["A2"],
        )
        line_bay = next(item for item in layout["plan"]["line_bays"] if item["id"] == "L1")
        transformer_bay = next(
            item for item in layout["plan"]["transformer_bays"] if item["id"] == "T1"
        )
        panels = {item["id"]: item for item in layout["sections"]["panels"]}
        line_sequence = {item["id"]: item for item in panels["A-A"]["equipment_sequence"]}
        transformer_sequence = {
            item["id"]: item for item in panels["B-B"]["equipment_sequence"]
        }
        self.assertEqual(
            line_bay["gantry_y_m"] - line_bay["bus_y_m"],
            line_sequence["LINE-GANTRY"]["x_m"] - line_sequence["BUS-SUPPORT"]["x_m"],
        )
        self.assertEqual(
            transformer_bay["bus_y_m"] - transformer_bay["gantry_y_m"],
            transformer_sequence["TX-GANTRY"]["x_m"]
            - transformer_sequence["BUS-SUPPORT"]["x_m"],
        )
        self.assertEqual(
            transformer_bay["bus_y_m"] - transformer_bay["transformer_center_m"][1],
            transformer_sequence["T1"]["x_m"]
            - transformer_sequence["BUS-SUPPORT"]["x_m"],
        )

    def test_plan_is_a1_and_contains_reserved_and_dimension_semantics(self) -> None:
        self.assertEqual(self.plan_summary["acadver"], "AC1032")
        self.assertGreater(self.plan_summary["modelspace_entities"], 280)
        self.assertEqual(self.plan_summary["extents"], [10.0, 10.0, 831.0, 584.0])
        self.assertTrue(
            any(entity.dxf.layer == "C-RESERVED" for entity in self.plan_doc.modelspace())
        )
        payload = "\n".join(entity.text for entity in self.plan_doc.modelspace().query("MTEXT"))
        self.assertIn("220kV户外AIS配电装置平面布置图", payload)
        self.assertIn("正常断开", payload)
        self.assertIn("145.0m", payload)
        self.assertIn("设计说明", payload)

    def test_section_contains_two_typical_bays_and_clearance_dimensions(self) -> None:
        self.assertEqual(self.section_summary["acadver"], "AC1032")
        self.assertGreater(self.section_summary["modelspace_entities"], 390)
        self.assertEqual(self.section_summary["extents"], [10.0, 10.0, 831.0, 584.0])
        payload = "\n".join(entity.text for entity in self.section_doc.modelspace().query("MTEXT"))
        self.assertIn("线路间隔断面 A-A", payload)
        self.assertIn("主变间隔断面 B-B", payload)
        self.assertIn("C≥4.30m", payload)
        self.assertIn("180MVA", payload)
        self.assertIn("4.0m", payload)
        self.assertIn("课程设计假设：海拔≤1000m、污秽d级", payload)
        self.assertIn("DL/T 5352-2018", payload)

    def test_committed_dxf_files_round_trip_without_missing_chinese(self) -> None:
        for path, expected_title, expected_count in (
            (
                Path(DEFAULT_PLAN_OUTPUT),
                "220kV户外AIS配电装置平面布置图",
                self.plan_summary["modelspace_entities"],
            ),
            (
                Path(DEFAULT_SECTION_OUTPUT),
                "220kV户外AIS典型间隔断面图",
                self.section_summary["modelspace_entities"],
            ),
        ):
            self.assertTrue(path.is_file(), f"Missing generated DXF: {path}")
            doc = ezdxf.readfile(path)
            self.assertEqual(len(doc.modelspace()), expected_count)
            expected_doc = self.plan_doc if path == Path(DEFAULT_PLAN_OUTPUT) else self.section_doc
            self.assertEqual(
                switchyard_semantic_fingerprint(doc),
                switchyard_semantic_fingerprint(expected_doc),
            )
            payload = "\n".join(entity.text for entity in doc.modelspace().query("MTEXT"))
            self.assertIn(expected_title, payload)
            self.assertNotIn("\ufffd", payload)

    def test_generation_to_temporary_paths_is_repeatable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary = generate_switchyard_drawings(
                plan_output=root / "plan.dxf",
                section_output=root / "section.dxf",
            )
            plan_fingerprint = switchyard_semantic_fingerprint(
                ezdxf.readfile(root / "plan.dxf")
            )
            section_fingerprint = switchyard_semantic_fingerprint(
                ezdxf.readfile(root / "section.dxf")
            )
        self.assertEqual(
            summary["plan"]["modelspace_entities"],
            self.plan_summary["modelspace_entities"],
        )
        self.assertEqual(
            summary["section"]["modelspace_entities"],
            self.section_summary["modelspace_entities"],
        )
        self.assertEqual(
            plan_fingerprint,
            switchyard_semantic_fingerprint(self.plan_doc),
        )
        self.assertEqual(
            section_fingerprint,
            switchyard_semantic_fingerprint(self.section_doc),
        )


if __name__ == "__main__":
    unittest.main()
