from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from calculations.equipment_selection.calculate import (
    calculate_equipment_screening,
)
from calculations.equipment_selection.checks import minimum_check
from calculations.equipment_selection.models import (
    load_json,
    load_yaml,
    validate_configuration,
)
from calculations.equipment_selection.report import write_outputs


ROOT = Path(__file__).resolve().parents[1]


class EquipmentSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.selection = load_yaml(ROOT / "data" / "equipment_selection.yaml")
        cls.catalog = load_yaml(ROOT / "data" / "equipment_catalog.yaml")
        cls.load_result = load_json(
            ROOT / "calculations" / "results" / "load_and_transformer_results.json"
        )
        cls.short_circuit = load_json(
            ROOT
            / "calculations"
            / "results"
            / "short_circuit"
            / "short_circuit_results.json"
        )
        cls.baseline = load_yaml(ROOT / "data" / "design_baseline.yaml")
        cls.design_inputs = load_yaml(ROOT / "data" / "design_inputs.yaml")
        cls.result = calculate_equipment_screening(
            selection=cls.selection,
            catalog=cls.catalog,
            load_result=cls.load_result,
            short_circuit=cls.short_circuit,
            baseline=cls.baseline,
            design_inputs=cls.design_inputs,
        )

    def test_section_currents_follow_actual_feeder_allocation(self) -> None:
        sections = self.result["duty_registry"]["section_allocated_currents"]

        self.assertAlmostEqual(
            sections["35kV-I"]["installed_base_current_a"],
            2230.731897835627,
            places=9,
        )
        self.assertAlmostEqual(
            sections["35kV-II"]["installed_base_current_a"],
            2404.371076539274,
            places=9,
        )
        self.assertNotAlmostEqual(
            sections["35kV-I"]["installed_base_current_a"],
            self.load_result["load_35kv"]["equal_bus_section_current_a"],
            places=3,
        )

    def test_key_continuous_duties_are_traceable(self) -> None:
        groups = self.result["duty_registry"]["circuit_groups"]

        self.assertAlmostEqual(
            groups["220-line-bays"]["continuous"]["required_current_a"],
            735.5592390584715,
            places=9,
        )
        self.assertAlmostEqual(
            groups["220-transformer-bays"]["continuous"][
                "required_current_a"
            ],
            495.99636762199674,
            places=9,
        )
        self.assertAlmostEqual(
            groups["35-transformer-incomers"]["continuous"][
                "required_current_a"
            ],
            3117.691453623979,
            places=9,
        )
        self.assertAlmostEqual(
            groups["35-feeder-storage"]["continuous"]["required_current_a"],
            546.9634129164876,
            places=9,
        )

    def test_all_twelve_35kv_feeders_resolve_once(self) -> None:
        groups = self.result["duty_registry"]["circuit_groups"]
        feeder_group_ids = [
            "35-feeder-wind-A",
            "35-feeder-wind-B",
            "35-feeder-pv-A",
            "35-feeder-pv-B",
            "35-feeder-storage",
        ]
        members = [
            member
            for group_id in feeder_group_ids
            for member in groups[group_id]["members"]
        ]

        self.assertEqual(len(members), 12)
        self.assertEqual(len(set(members)), 12)

    def test_fault_scenario_gating_keeps_prohibited_case_advisory(self) -> None:
        profiles = self.result["duty_registry"]["fault_profiles"]
        profile_35 = profiles["35_bus"]

        self.assertAlmostEqual(
            profile_35["mandatory_rms_ka"], 13.264911625868273, places=9
        )
        self.assertAlmostEqual(
            profile_35["conditional_rms_ka"], 16.290983445518524, places=9
        )
        self.assertAlmostEqual(
            profile_35["advisory_rms_ka"], 25.693932164155918, places=9
        )
        self.assertAlmostEqual(
            profile_35["course_total_peak_sensitivity_ka"],
            41.47007351948617,
            places=9,
        )
        self.assertFalse(profile_35["final_peak_scope_complete"])

    def test_220kv_and_10kv_course_converter_scope_is_explicit(self) -> None:
        profiles = self.result["duty_registry"]["fault_profiles"]

        self.assertIn("renewable", profiles["220_bus"]["rms_scope"])
        self.assertFalse(profiles["220_bus"]["final_breaking_scope_complete"])
        self.assertIn("svg", profiles["10_bus"]["rms_scope"])
        self.assertAlmostEqual(
            profiles["10_bus"]["provisional_required_rms_ka"],
            15.6380944196,
            places=9,
        )
        self.assertAlmostEqual(
            profiles["10_bus"]["advisory_rms_ka"],
            28.4723215137,
            places=9,
        )

    def test_target_ratings_only_provisionally_pass_numeric_checks(self) -> None:
        selections = {item["id"]: item for item in self.result["selections"]}
        incomer = selections["SEL-SWGR-35-IN"]

        self.assertEqual(incomer["numeric_precheck_status"], "provisional_pass")
        self.assertEqual(incomer["final_selection_status"], "pending")
        current_check = next(
            check
            for check in incomer["numeric_checks"]
            if check["id"] == "continuous_current"
        )
        self.assertAlmostEqual(current_check["margin"], 32.308546376021, places=9)

    def test_current_correction_factor_is_applied_once(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        candidate = next(
            item
            for item in catalog["candidates"]
            if item["id"] == "TARGET-SWGR-35-3150"
        )
        candidate["service_conditions"]["current_correction_factor"] = 0.98

        result = calculate_equipment_screening(
            selection=self.selection,
            catalog=catalog,
            load_result=self.load_result,
            short_circuit=self.short_circuit,
            baseline=self.baseline,
            design_inputs=self.design_inputs,
        )
        selections = {item["id"]: item for item in result["selections"]}
        incomer = selections["SEL-SWGR-35-IN"]
        current_check = next(
            check
            for check in incomer["numeric_checks"]
            if check["id"] == "continuous_current"
        )

        self.assertAlmostEqual(current_check["available"], 3087.0, places=9)
        self.assertEqual(current_check["status"], "fail")

    def test_pending_bus_section_flow_propagates(self) -> None:
        selections = {item["id"]: item for item in self.result["selections"]}
        bus_section = selections["SEL-CB-220-BS"]

        self.assertEqual(bus_section["numeric_precheck_status"], "pending")
        self.assertEqual(bus_section["final_selection_status"], "pending")

    def test_auxiliary_transformer_and_svg_duties_are_known(self) -> None:
        groups = self.result["duty_registry"]["circuit_groups"]
        duty = groups["35-aux-transformer-feeders"]["continuous"]

        self.assertEqual(duty["status"], "known")
        self.assertAlmostEqual(duty["required_current_a"], 545.5960043842, places=8)
        self.assertEqual(
            groups["35-aux-transformer-feeders"]["members"],
            ["T10-1-HV", "T10-2-HV"],
        )
        self.assertAlmostEqual(
            groups["10-transformer-incomers"]["continuous"]["required_current_a"],
            1909.5860153447,
            places=8,
        )
        self.assertAlmostEqual(
            groups["10-svg-feeders"]["continuous"]["required_current_a"],
            692.8203230276,
            places=8,
        )

    def test_10kv_switchgear_and_thermal_i2t_prechecks_pass(self) -> None:
        selections = {item["id"]: item for item in self.result["selections"]}
        incomer = selections["SEL-SWGR-10-IN"]
        thermal = next(
            check for check in incomer["numeric_checks"] if check["id"] == "thermal_energy"
        )

        self.assertEqual(incomer["numeric_precheck_status"], "provisional_pass")
        self.assertEqual(thermal["status"], "provisional_pass")
        self.assertAlmostEqual(thermal["required"], 269.0049967841, places=8)
        self.assertAlmostEqual(thermal["available"], 3969.0, places=8)

    def test_minimum_check_boundary(self) -> None:
        equal = minimum_check(
            check_id="equal",
            required=100.0,
            available=100.0,
            unit="A",
            provisional=False,
            note="boundary",
        )
        below = minimum_check(
            check_id="below",
            required=100.0,
            available=99.999,
            unit="A",
            provisional=False,
            note="boundary",
        )

        self.assertEqual(equal["status"], "pass")
        self.assertEqual(below["status"], "fail")

    def test_invalid_assignment_reference_is_rejected(self) -> None:
        selection = copy.deepcopy(self.selection)
        selection["selections"][0]["candidate_id"] = "MISSING"

        with self.assertRaisesRegex(ValueError, "unknown candidate"):
            validate_configuration(selection, self.catalog)

    def test_duplicate_yaml_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.yaml"
            path.write_text("item: 1\nitem: 2\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate YAML key"):
                load_yaml(path)

    def test_generated_outputs_preserve_pending_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = write_outputs(self.result, directory)
            summary = paths[2].read_text(encoding="utf-8")

        self.assertIn("35kV条件性预校核", summary)
        self.assertIn("25.694kA仅作禁止方式提示", summary)
        self.assertIn("热稳定采用后备保护1.00s", summary)
        self.assertIn("10kV采用2×±12Mvar SVG", summary)
        self.assertIn("最终选型总状态：`pending`", summary)


if __name__ == "__main__":
    unittest.main()
