from __future__ import annotations

import copy
import math
import unittest
from pathlib import Path

from calculations.load_and_transformers.calculate import calculate_design, load_config


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "design_inputs.yaml"


class LoadAndTransformerCalculationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config(INPUT_PATH)
        cls.result = calculate_design(cls.config)

    def test_35kv_aggregate_applies_simultaneity_and_loss_once(self) -> None:
        result = self.result["load_35kv"]

        self.assertAlmostEqual(result["gross_apparent_mva"], 280.9881847476, places=9)
        self.assertAlmostEqual(result["after_simultaneity_mva"], 266.9387755102, places=9)
        self.assertAlmostEqual(result["with_losses_mva"], 280.2857142857, places=9)

    def test_35kv_circuit_current_uses_full_item_maximum_not_group_simultaneity(self) -> None:
        items = {item["name"]: item for item in self.result["load_35kv"]["items"]}

        self.assertAlmostEqual(items["wind_farm_A"]["per_circuit_current_a"], 364.6422752777, places=8)
        self.assertAlmostEqual(items["pv_plant_A"]["per_circuit_current_a"], 530.2196349701, places=8)
        self.assertFalse(items["pv_plant_A"]["simultaneity_applied_to_circuit"])

    def test_10kv_aggregate_and_bus_current(self) -> None:
        result = self.result["load_10kv"]

        self.assertAlmostEqual(result["gross_apparent_mva"], 2.09150326797, places=9)
        self.assertAlmostEqual(result["with_losses_mva"], 1.75686274510, places=9)
        self.assertAlmostEqual(result["bus_current_a"], 101.4325178812, places=8)

    def test_main_transformer_loading_and_n_minus_one(self) -> None:
        result = self.result["main_transformer"]

        self.assertAlmostEqual(result["total_required_mva"], 280.2857142857, places=9)
        self.assertAlmostEqual(result["normal_loading_percent"], 77.8571428571, places=8)
        self.assertAlmostEqual(result["n_minus_one_supply_percent"], 64.2201834862, places=8)
        self.assertAlmostEqual(result["n_minus_one_shortfall_mva"], 100.2857142857, places=8)
        self.assertAlmostEqual(
            result["sensitivity_including_10kv"]["total_required_mva"],
            282.0425770308,
            places=9,
        )
        self.assertAlmostEqual(
            result["sensitivity_including_10kv"]["normal_loading_percent"],
            78.3451602863,
            places=8,
        )
        self.assertAlmostEqual(
            result["rated_current_a"]["220kv"],
            180 / (math.sqrt(3) * 220) * 1000,
            places=8,
        )

    def test_reactive_compensation_and_t10_are_frozen_from_p_q_calculation(self) -> None:
        compensation = self.result["reactive_compensation"]
        transformer = self.result["auxiliary_transformer"]

        self.assertAlmostEqual(
            compensation["calculated_required_mvar_35kv_only"],
            21.3029347587,
            places=9,
        )
        self.assertAlmostEqual(
            compensation[
                "calculated_required_mvar_conservative_with_10kv_auxiliary"
            ],
            21.8874616330,
            places=9,
        )
        self.assertEqual(compensation["selected_total_mvar"], 24.0)
        self.assertAlmostEqual(
            compensation["final_conservative_power_factor"],
            0.9814653698,
            places=9,
        )
        self.assertEqual(transformer["rated_capacity_mva_each"], 31.5)
        self.assertAlmostEqual(
            transformer["n_minus_one_full_absorbing_loading_percent"],
            79.1664488056,
            places=9,
        )
        self.assertAlmostEqual(
            transformer["rated_current_with_1_05_margin_a"]["35kv"],
            545.5960043842,
            places=8,
        )

    def test_station_service_excludes_110kv_items_and_selects_200kva(self) -> None:
        result = self.result["station_service"]

        self.assertAlmostEqual(result["continuous_applicable_kw"], 96.3, places=8)
        self.assertAlmostEqual(result["short_time_applicable_kw"], 89.0, places=8)
        self.assertAlmostEqual(result["explicit_frequent_kw"], 81.2, places=8)
        self.assertAlmostEqual(result["explicit_infrequent_kw"], 68.1, places=8)
        self.assertAlmostEqual(result["frequency_unspecified_kw"], 36.0, places=8)
        self.assertAlmostEqual(result["base_required_kva"], 162.6625, places=8)
        self.assertAlmostEqual(result["worst_frequent_required_kva"], 192.9125, places=8)
        self.assertEqual(result["recommended_each_transformer_kva"], 200)
        self.assertEqual(
            result["normal_operation"],
            "one_transformer_in_service_bus_tie_closed_other_transformer_dark_standby",
        )
        self.assertEqual(
            set(result["excluded_items"]),
            {"110kv_switchyard_supply", "110kv_breaker_winter_heating"},
        )

    def test_invalid_power_factor_is_rejected(self) -> None:
        invalid = copy.deepcopy(self.config)
        invalid["loads_35kv"]["items"][0]["power_factor"] = 0

        with self.assertRaisesRegex(ValueError, "power factor"):
            calculate_design(invalid)

    def test_svg_unit_sum_must_match_selected_total(self) -> None:
        invalid = copy.deepcopy(self.config)
        invalid["loads_10kv"]["reactive_compensation"]["units"][0][
            "rated_mvar"
        ] = 11

        with self.assertRaisesRegex(ValueError, "do not add up"):
            calculate_design(invalid)


if __name__ == "__main__":
    unittest.main()
