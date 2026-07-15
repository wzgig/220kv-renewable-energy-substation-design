from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

import yaml

from calculations.short_circuit.calculate import (
    calculate_short_circuit,
    parallel_equivalent,
    write_outputs,
)


ROOT = Path(__file__).resolve().parents[1]


class ShortCircuitCalculationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inputs = yaml.safe_load(
            (ROOT / "data" / "design_inputs.yaml").read_text(encoding="utf-8")
        )
        cls.baseline = yaml.safe_load(
            (ROOT / "data" / "design_baseline.yaml").read_text(encoding="utf-8")
        )
        cls.result = calculate_short_circuit(cls.inputs, cls.baseline)

    def test_220kv_source_paths_and_parallel_equivalent(self) -> None:
        paths = self.result["network"]["source_paths_220kv_pu"]

        self.assertAlmostEqual(paths["source_1"], 0.0695967233774, places=11)
        self.assertAlmostEqual(paths["source_2"], 0.0867722117202, places=11)
        self.assertAlmostEqual(
            self.result["network"]["parallel_source_equivalent_220kv_pu"],
            0.0386205969374,
            places=11,
        )

    def test_220kv_closed_bus_tie_fault(self) -> None:
        point = self.result["points"]["SC-220-BUS-CLOSED"]

        self.assertAlmostEqual(
            point["grid_symmetrical_current_ka"], 6.4996886655, places=9
        )
        self.assertAlmostEqual(
            point["grid_peak_current_ka"], 16.5455061515, places=9
        )
        self.assertEqual(point["operating_status"], "maximum_base_case")
        self.assertEqual(
            point["normal_operation_status"],
            "conditional_pending_system_parallel_permission",
        )

    def test_35kv_normal_and_parallel_sensitivity(self) -> None:
        normal = self.result["points"]["SC-35-I-220-CLOSED"]
        parallel = self.result["points"]["SC-35-BOTH-TRANSFORMERS-SENSITIVITY"]

        self.assertAlmostEqual(
            normal["grid_symmetrical_current_ka"], 13.4057381537, places=9
        )
        self.assertAlmostEqual(
            parallel["grid_symmetrical_current_ka"],
            20.1318085949,
            places=9,
        )
        self.assertEqual(
            parallel["normal_operation_status"],
            "not_permitted_non_normal_sensitivity",
        )

    def test_renewable_current_contribution_uses_section_allocation(self) -> None:
        section_1 = self.result["points"]["SC-35-I-220-CLOSED"][
            "renewable_contribution_sensitivity_ka"
        ]
        section_2 = self.result["points"]["SC-35-II-220-CLOSED"][
            "renewable_contribution_sensitivity_ka"
        ]

        self.assertAlmostEqual(section_1["minimum"], 2.4538050876, places=9)
        self.assertAlmostEqual(section_1["maximum"], 2.6768782774, places=9)
        self.assertAlmostEqual(section_2["minimum"], 2.6448081842, places=9)
        self.assertAlmostEqual(section_2["maximum"], 2.8852452918, places=9)

        separate = self.result["points"]["SC-35-I-220-SEPARATE"]
        self.assertAlmostEqual(
            separate["conservative_total_symmetrical_current_range_ka"][
                "maximum"
            ],
            13.2649116259,
            places=9,
        )

    def test_10kv_result_remains_pending_without_source_transformer_rating(self) -> None:
        pending = self.result["pending_points"]["10kv_bus"]

        self.assertEqual(pending["status"], "pending_input")
        self.assertIn("rated capacity", pending["reason"])

    def test_non_null_10kv_rating_never_silently_drops_result(self) -> None:
        baseline = copy.deepcopy(self.baseline)
        baseline["connection_10kv"]["source_transformers"][
            "rated_capacity_mva_each"
        ] = 20

        result = calculate_short_circuit(self.inputs, baseline)

        self.assertEqual(
            result["pending_points"]["10kv_bus"]["status"],
            "not_implemented",
        )

    def test_invalid_multiplier_range_and_reactance_are_rejected(self) -> None:
        inputs = copy.deepcopy(self.inputs)
        inputs["calculation_rules"]["renewable_short_circuit_contribution"][
            "sensitivity_multiplier_range"
        ] = [1.2, 1.1]

        with self.assertRaises(ValueError):
            calculate_short_circuit(inputs, self.baseline)
        with self.assertRaises(ValueError):
            parallel_equivalent(0.1, 0.0)

    def test_generated_outputs_expose_scope_and_conservative_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = write_outputs(self.result, directory)
            summary = paths[2].read_text(encoding="utf-8")

        self.assertIn("任务书标幺制X-only初算方法", summary)
        self.assertIn("正常运行许可", summary)
        self.assertIn("16.083kA", summary)
        self.assertIn("16.291kA", summary)
        self.assertIn("峰值列仅含电网贡献", summary)


if __name__ == "__main__":
    unittest.main()
