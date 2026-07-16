from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import ezdxf
from pypdf import PdfReader

from drawings.scripts.generate_switchyard_drawings import (
    DEFAULT_DETAIL_OUTPUT,
    DEFAULT_PLAN_OUTPUT,
    DEFAULT_SECTION_OUTPUT,
    _draw_line_bay_detail,
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
        cls.detail_doc = _draw_line_bay_detail(cls.data)
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
        cls.detail_summary = validate_document(
            cls.detail_doc,
            cls.data,
            expected_title=cls.data["layout"]["line_bay_detail"]["drawing_title"],
        )

    def test_layout_matches_frozen_220kv_scope_and_clearances(self) -> None:
        layout = self.data["layout"]
        baseline = self.data["baseline"]

        self.assertEqual(layout["plan"]["sheet"]["scale"], 200)
        self.assertEqual(layout["sections"]["sheet"]["scale"], 100)
        self.assertEqual(layout["line_bay_detail"]["sheet"]["scale"], 50)
        self.assertEqual(layout["line_bay_detail"]["drawing_id"], "SEC-220-L1-01")
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
        self.assertTrue(line_sequence["DS-LINE"]["earthing_switch"])
        detail_sequence = {
            item["id"]: item
            for item in layout["line_bay_detail"]["equipment_sequence"]
        }
        self.assertEqual(
            list(detail_sequence),
            ["BUS-SUPPORT", "DS-BUS", "CB", "CT", "DS-LINE", "CVT", "LA", "LINE-GANTRY"],
        )
        self.assertTrue(detail_sequence["DS-LINE"]["earthing_switch"])

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
        self.assertGreaterEqual(payload.count("线路侧QS+ES(NO)"), 3)

    def test_title_block_and_plan_line_labels_clear_divider_lines(self) -> None:
        for doc, title in (
            (self.plan_doc, "220kV户外AIS配电装置平面布置图"),
            (self.section_doc, "220kV户外AIS典型间隔断面图"),
            (self.detail_doc, "220kV I段L1线路间隔断面详图"),
        ):
            title_entities = [
                entity
                for entity in doc.modelspace().query("MTEXT")
                if entity.text == title
                and entity.dxf.layer == "C-TITLE"
                and abs(entity.dxf.insert.x - 711.0) < 1e-6
            ]
            self.assertEqual(len(title_entities), 1)
            self.assertAlmostEqual(title_entities[0].dxf.insert.y, 59.0)

        line_labels = [
            entity
            for entity in self.plan_doc.modelspace().query("MTEXT")
            if "northwest出线" in entity.text
        ]
        self.assertEqual(len(line_labels), 3)
        for label in line_labels:
            self.assertAlmostEqual(label.dxf.insert.y, 536.0)

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
        self.assertIn("线路侧隔离开关+常开ES", payload)
        self.assertIn("ES(NO)", payload)

    def test_line_bay_detail_contains_complete_chain_grounding_and_parameters(self) -> None:
        self.assertEqual(self.detail_summary["acadver"], "AC1032")
        self.assertGreater(self.detail_summary["modelspace_entities"], 250)
        self.assertEqual(self.detail_summary["extents"], [10.0, 10.0, 831.0, 584.0])
        payload = "\n".join(
            entity.text for entity in self.detail_doc.modelspace().query("MTEXT")
        )
        self.assertIn("220kV I段L1线路间隔断面详图", payload)
        self.assertIn("SEC-220-L1-01", payload)
        self.assertIn("220-L1-QS2/ES", payload)
        self.assertIn("ES(NO)", payload)
        self.assertIn("地下水平接地网及设备/构架接地引下线", payload)
        self.assertIn("L1线路间隔课程额定参数表", payload)
        self.assertIn("TA=1000/1A", payload)
        self.assertIn("YH10W-204/532", payload)
        self.assertIn("A1≥1.80m", payload)
        self.assertIn("A2≥2.00m", payload)
        self.assertIn("C≥4.30m", payload)
        self.assertIn("不代表全站避雷针/避雷线直击雷保护范围已完成", payload)

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
            (
                Path(DEFAULT_DETAIL_OUTPUT),
                "220kV I段L1线路间隔断面详图",
                self.detail_summary["modelspace_entities"],
            ),
        ):
            self.assertTrue(path.is_file(), f"Missing generated DXF: {path}")
            doc = ezdxf.readfile(path)
            self.assertEqual(len(doc.modelspace()), expected_count)
            expected_doc = {
                Path(DEFAULT_PLAN_OUTPUT): self.plan_doc,
                Path(DEFAULT_SECTION_OUTPUT): self.section_doc,
                Path(DEFAULT_DETAIL_OUTPUT): self.detail_doc,
            }[path]
            self.assertEqual(
                switchyard_semantic_fingerprint(doc),
                switchyard_semantic_fingerprint(expected_doc),
            )
            payload = "\n".join(entity.text for entity in doc.modelspace().query("MTEXT"))
            self.assertIn(expected_title, payload)
            self.assertNotIn("\ufffd", payload)

        for pdf_path in (
            ROOT / "drawings" / "exports" / "single_line_a1.pdf",
            ROOT / "drawings" / "exports" / "switchyard_plan_a1.pdf",
            ROOT / "drawings" / "exports" / "switchyard_section_a1.pdf",
            ROOT / "drawings" / "exports" / "switchyard_line_bay_detail_a1.pdf",
        ):
            with self.subTest(pdf=pdf_path.name):
                reader = PdfReader(pdf_path, strict=True)
                self.assertEqual(len(reader.pages), 1)
                page = reader.pages[0]
                self.assertGreater(float(page.mediabox.width), float(page.mediabox.height))
                self.assertFalse(page.get("/Annots"), "Public CAD PDF must be annotation-free")

    def test_generation_to_temporary_paths_is_repeatable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary = generate_switchyard_drawings(
                plan_output=root / "plan.dxf",
                section_output=root / "section.dxf",
                detail_output=root / "detail.dxf",
            )
            plan_fingerprint = switchyard_semantic_fingerprint(
                ezdxf.readfile(root / "plan.dxf")
            )
            section_fingerprint = switchyard_semantic_fingerprint(
                ezdxf.readfile(root / "section.dxf")
            )
            detail_fingerprint = switchyard_semantic_fingerprint(
                ezdxf.readfile(root / "detail.dxf")
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
            summary["detail"]["modelspace_entities"],
            self.detail_summary["modelspace_entities"],
        )
        self.assertEqual(
            plan_fingerprint,
            switchyard_semantic_fingerprint(self.plan_doc),
        )
        self.assertEqual(
            section_fingerprint,
            switchyard_semantic_fingerprint(self.section_doc),
        )
        self.assertEqual(
            detail_fingerprint,
            switchyard_semantic_fingerprint(self.detail_doc),
        )


if __name__ == "__main__":
    unittest.main()
