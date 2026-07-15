from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


class DesignBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inputs = yaml.safe_load(
            (ROOT / "data" / "design_inputs.yaml").read_text(encoding="utf-8")
        )
        cls.baseline = yaml.safe_load(
            (ROOT / "data" / "design_baseline.yaml").read_text(encoding="utf-8")
        )

    def test_35kv_sections_have_six_unique_feeders_each(self) -> None:
        sections = self.baseline["connection_35kv"]["sections"]
        feeder_ids = [
            feeder["id"]
            for section in sections
            for feeder in section["feeder_circuits"]
        ]

        self.assertEqual([len(section["feeder_circuits"]) for section in sections], [6, 6])
        self.assertEqual(len(feeder_ids), 12)
        self.assertEqual(len(feeder_ids), len(set(feeder_ids)))
        self.assertEqual([section["reserved_bays"] for section in sections], [1, 1])

    def test_35kv_allocated_active_power_matches_source_data(self) -> None:
        source_items = {
            item["name"]: item for item in self.inputs["loads_35kv"]["items"]
        }
        calculated_section_power = []
        for section in self.baseline["connection_35kv"]["sections"]:
            active_power_mw = 0.0
            for feeder in section["feeder_circuits"]:
                source = source_items[feeder["source_key"]]
                active_power_mw += source["active_power_mw"] / source["circuits"]
            calculated_section_power.append(active_power_mw)
            self.assertAlmostEqual(
                active_power_mw,
                section["allocated_active_power_mw"],
                places=9,
            )

        self.assertEqual(calculated_section_power, [130.0, 140.0])
        self.assertAlmostEqual(
            sum(calculated_section_power),
            self.inputs["loads_35kv"]["total_installed_active_power_mw"],
            places=9,
        )

    def test_transformer_and_bus_baseline_matches_taskbook(self) -> None:
        transformers = self.baseline["main_transformers"]

        self.assertEqual(transformers["count"], 2)
        self.assertEqual(transformers["rated_capacity_mva_each"], 180)
        self.assertEqual(transformers["voltage_ratio_kv"], [220, 35])
        self.assertEqual(
            self.baseline["connection_220kv"]["scheme"],
            "single_bus_sectionalized",
        )
        self.assertEqual(
            self.baseline["connection_35kv"]["bus_tie_normal_state"],
            "open",
        )
        self.assertEqual(
            self.baseline["connection_0_4kv"]["station_service_transformers"][
                "rated_capacity_kva_each"
            ],
            200,
        )


if __name__ == "__main__":
    unittest.main()
