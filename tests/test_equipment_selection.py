from __future__ import annotations

import copy
import math
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
        self.assertEqual(
            groups["35-grounding-transformer-feeders"]["continuous"]["status"],
            "known_course_target",
        )
        self.assertEqual(
            groups["35-grounding-transformer-feeders"]["continuous"][
                "required_current_a"
            ],
            400.0,
        )
        self.assertEqual(
            groups["10-grounding-transformer-feeders"]["continuous"][
                "required_current_a"
            ],
            200.0,
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

    def test_220kv_bus_section_uses_frozen_conservative_duty(self) -> None:
        selections = {item["id"]: item for item in self.result["selections"]}
        bus_section = selections["SEL-CB-220-BS"]

        self.assertEqual(
            bus_section["duty"]["continuous"]["status"], "known_conservative"
        )
        self.assertAlmostEqual(
            bus_section["duty"]["continuous"]["required_current_a"],
            735.5592390584715,
            places=9,
        )
        self.assertAlmostEqual(
            bus_section["duty"]["fault"]["conditional_rms_ka"],
            7.384571960617697,
            places=9,
        )
        self.assertAlmostEqual(
            bus_section["duty"]["fault"]["course_total_peak_sensitivity_ka"],
            18.798051274246124,
            places=9,
        )
        thermal_check = next(
            check
            for check in bus_section["numeric_checks"]
            if check["id"] == "thermal_energy"
        )
        self.assertAlmostEqual(thermal_check["required"], 59.985093345695205, places=9)
        self.assertEqual(bus_section["numeric_precheck_status"], "provisional_pass")
        self.assertEqual(bus_section["final_selection_status"], "pending")

    def test_indoor_35kv_basis_and_10kv_2500a_target_are_explicit(self) -> None:
        selections = {item["id"]: item for item in self.result["selections"]}
        incomer_35 = selections["SEL-SWGR-35-IN"]
        incomer_10 = selections["SEL-SWGR-10-IN"]
        ambient_check = next(
            check
            for check in incomer_35["final_checks"]
            if check["id"] == "ambient_temperature"
        )

        self.assertEqual(ambient_check["status"], "pass")
        self.assertEqual(ambient_check["required"], 40.0)
        self.assertEqual(incomer_35["final_selection_status"], "pending")
        self.assertEqual(incomer_10["candidate"]["id"], "TARGET-SWGR-10-2500")
        self.assertEqual(incomer_10["candidate"]["ratings"]["continuous_current_a"], 2500)
        indoor_switchgear = [
            item
            for item in selections.values()
            if item["candidate"]["kind"] == "switchgear"
        ]
        self.assertTrue(indoor_switchgear)
        for item in indoor_switchgear:
            with self.subTest(selection=item["id"]):
                check = next(
                    check
                    for check in item["final_checks"]
                    if check["id"] == "ambient_temperature"
                )
                self.assertEqual(check["status"], "pass")
                self.assertEqual(check["required"], 40.0)

    def test_course_busbar_checks_are_reproducible(self) -> None:
        completion = self.result["course_completion"]
        busbars = {item["id"]: item for item in completion["busbars"]}
        bus_220 = busbars["BUS-220-TUBE-100-90"]
        bus_35 = busbars["BUS-35-3X125X10"]
        bus_10 = busbars["BUS-10-2X125X10"]

        self.assertEqual(completion["course_precheck_status"], "provisional_pass")
        self.assertEqual(completion["final_engineering_status"], "pending")
        self.assertAlmostEqual(
            bus_220["calculated"]["current_correction_factor"],
            0.8027729719194864,
            places=12,
        )
        self.assertAlmostEqual(
            bus_220["calculated"]["corrected_ampacity_a"],
            1605.5459438389728,
            places=9,
        )
        self.assertAlmostEqual(
            bus_220["calculated"]["dynamic"]["calculated_bending_stress_mpa"],
            10.047657499080398,
            places=9,
        )
        self.assertEqual(
            bus_220["calculated"]["dynamic"]["calculation_phase_spacing_m"],
            3.0,
        )
        self.assertEqual(
            bus_220["calculated"]["dynamic"][
                "frozen_layout_phase_spacing_m"
            ],
            4.0,
        )
        self.assertAlmostEqual(
            bus_220["calculated"]["corona"][
                "critical_disruptive_phase_voltage_kv"
            ],
            330.4443137555403,
            places=9,
        )
        self.assertEqual(bus_35["calculated"]["cross_section_area_mm2"], 3750.0)
        self.assertEqual(bus_35["calculated"]["corrected_ampacity_a"], 4194.0)
        self.assertEqual(bus_10["calculated"]["cross_section_area_mm2"], 2500.0)
        self.assertEqual(bus_10["calculated"]["corrected_ampacity_a"], 3282.0)
        self.assertEqual(bus_35["dynamic_check"]["status"], "pending")
        self.assertEqual(bus_10["dynamic_check"]["status"], "pending")
        self.assertNotIn("dynamic", bus_35["calculated"])
        self.assertNotIn("dynamic", bus_10["calculated"])
        self.assertEqual(
            bus_35["engineering_pending_checks"][0]["status"], "pending"
        )
        self.assertEqual(
            bus_10["engineering_pending_checks"][0]["status"], "pending"
        )
        self.assertTrue(
            all(
                item["course_precheck_status"] == "provisional_pass"
                for item in busbars.values()
            )
        )

    def test_moa_continuous_voltage_and_protection_margins_pass(self) -> None:
        arresters = {
            item["id"]: item
            for item in self.result["course_completion"]["surge_arresters"]
        }

        self.assertEqual(arresters["MOA-220"]["model"], "YH10W-204/532")
        self.assertAlmostEqual(
            arresters["MOA-220"]["calculated"][
                "required_continuous_voltage_kv"
            ],
            145.49226783578573,
            places=9,
        )
        self.assertAlmostEqual(
            arresters["MOA-220"]["calculated"]["protection_ratio"],
            950 / 532,
            places=12,
        )
        self.assertAlmostEqual(
            arresters["MOA-35"]["calculated"][
                "continuous_voltage_margin_kv"
            ],
            0.3,
            places=12,
        )
        self.assertAlmostEqual(
            arresters["MOA-10"]["calculated"]["protection_ratio"],
            75 / 45,
            places=12,
        )
        self.assertTrue(
            all(
                item["course_precheck_status"] == "provisional_pass"
                for item in arresters.values()
            )
        )
        overhead_coverage = arresters["MOA-35"]["interface_coverage"][0]
        self.assertEqual(overhead_coverage["id"], "MOA-35-OHL-ENTRY")
        self.assertEqual(
            set(overhead_coverage["covered_circuit_groups"]),
            {"35-feeder-wind-A", "35-feeder-wind-B"},
        )
        self.assertEqual(
            set(overhead_coverage["covered_members"]),
            set(self.design_inputs["system"]["collector_35kv"]["circuit_interfaces"]["overhead"]),
        )
        self.assertEqual(
            set(overhead_coverage["resolved_group_members"]),
            set(overhead_coverage["covered_members"]),
        )
        self.assertEqual(
            overhead_coverage["coverage_check_status"], "provisional_pass"
        )

    def test_supplementary_tables_keep_ordering_boundary(self) -> None:
        supplementary = self.result["course_completion"]["supplementary"]
        current_transformers = supplementary["current_transformers"]

        self.assertIn("not purchase specifications", supplementary["ordering_boundary"])
        self.assertEqual(len(current_transformers), 8)
        self.assertEqual(len(supplementary["voltage_transformers"]), 3)
        self.assertEqual(
            len(supplementary["zero_sequence_current_transformers"]), 2
        )
        self.assertEqual(len(supplementary["insulators_and_bushings"]), 3)
        self.assertEqual(len(supplementary["earthing_switches"]), 3)
        self.assertTrue(
            all(
                item["course_precheck_status"] == "provisional_pass"
                for item in current_transformers
                if item["id"] != "CT-220-TRANSFORMER-NEUTRAL"
            )
        )
        self.assertTrue(
            all(
                item["course_precheck_status"] == "provisional_pass"
                for item in supplementary["earthing_switches"]
            )
        )
        self.assertTrue(
            all(
                item["final_engineering_status"].startswith("pending_")
                for item in current_transformers
            )
        )
        neutral_ct = next(
            item
            for item in current_transformers
            if item["id"] == "CT-220-TRANSFORMER-NEUTRAL"
        )
        self.assertEqual(neutral_ct["ratio"], "600/1A")
        self.assertIn("restricted-earth-fault", " ".join(neutral_ct["cores"]))
        self.assertEqual(neutral_ct["course_precheck_status"], "pending")
        self.assertIsNone(
            neutral_ct["requirements"]["required_continuous_current_a"]
        )
        self.assertIsNone(
            neutral_ct["requirements"]["required_short_circuit_rms_ka"]
        )
        self.assertTrue(neutral_ct["exclude_from_course_precheck"])

        zcts = {
            item["id"]: item
            for item in supplementary["zero_sequence_current_transformers"]
        }
        zct_35 = zcts["ZCT-35-CABLE-FEEDERS"]
        zct_10 = zcts["ZCT-10-CABLE-FEEDERS"]
        self.assertEqual(
            set(zct_35["covered_members"]),
            set(self.design_inputs["system"]["collector_35kv"]["circuit_interfaces"]["cable"]),
        )
        self.assertEqual(zct_35["target_primary_residual_current_a"], 400)
        self.assertEqual(zct_10["target_primary_residual_current_a"], 200)
        self.assertEqual(zct_35["course_precheck_status"], "provisional_pass")
        self.assertEqual(zct_10["course_precheck_status"], "provisional_pass")

        for item in supplementary["insulators_and_bushings"]:
            with self.subTest(insulator_bushing=item["id"]):
                check_ids = {check["id"] for check in item["checks"]}
                self.assertIn("insulator_bushing_liwv", check_ids)
                self.assertIn("bushing_continuous_current", check_ids)
                self.assertIn("bushing_thermal_energy", check_ids)
                self.assertIn("bushing_dynamic_current", check_ids)
                self.assertEqual(item["course_precheck_status"], "provisional_pass")
                self.assertTrue(item["engineering_pending_checks"])
                self.assertTrue(
                    all(
                        check["status"] == "pending"
                        for check in item["engineering_pending_checks"]
                    )
                )

    def test_reactor_and_high_voltage_fuse_decisions_are_explicit(self) -> None:
        decisions = self.result["course_completion"]["design_decisions"]
        reactor = decisions["current_limiting_reactor"]
        checks = {item["voltage_class"]: item for item in reactor["checks"]}

        self.assertEqual(reactor["decision"], "not_required_on_course_fault_level")
        self.assertEqual(reactor["course_precheck_status"], "provisional_pass")
        self.assertAlmostEqual(
            checks["v35"]["required_fault_current_ka"], 16.290983445518524
        )
        self.assertAlmostEqual(
            checks["v10"]["required_fault_current_ka"], 15.6380944196
        )
        self.assertEqual(
            checks["v35"]["selected_switchgear_breaking_current_ka"], 31.5
        )
        self.assertEqual(
            decisions["high_voltage_fuse"]["decision"],
            "not_a_main_circuit_selection_item",
        )

        interlock = self.result["course_completion"][
            "grounding_source_interlock"
        ]
        self.assertEqual(interlock["course_precheck_status"], "provisional_pass")
        for level in interlock["voltage_levels"]:
            with self.subTest(grounding_interlock=level["voltage_class"]):
                self.assertEqual(level["normal_sources_in_service"], 2)
                self.assertEqual(level["transfer_sources_in_service"], 1)
                self.assertEqual(level["restored_sources_in_service"], 2)
                self.assertIn("two_grounding_sources", level["prohibited_state"])
                self.assertTrue(
                    all(
                        check["status"] == "provisional_pass"
                        for check in level["checks"]
                    )
                )

        packages = {
            item["id"]: item
            for item in self.result["course_completion"][
                "grounding_transformer_resistor_packages"
            ]
        }
        package_35 = packages["GRD-PKG-35"]
        package_10 = packages["GRD-PKG-10"]
        self.assertAlmostEqual(
            package_35["calculated"]["resistance_ohm"],
            35_000 / (math.sqrt(3) * 400),
            places=12,
        )
        self.assertAlmostEqual(
            package_35["calculated"]["short_time_equivalent_power_mva"],
            35 / math.sqrt(3) * 400 / 1000,
            places=12,
        )
        self.assertAlmostEqual(
            package_35["calculated"][
                "minimum_transformer_capacity_kva_at_overload_factor"
            ],
            35 / math.sqrt(3) * 400 / 10,
            places=12,
        )
        self.assertEqual(package_35["selected_transformer_capacity_kva_each"], 1000)
        self.assertAlmostEqual(
            package_10["calculated"]["resistance_ohm"],
            10_000 / (math.sqrt(3) * 200),
            places=12,
        )
        self.assertAlmostEqual(
            package_10["calculated"]["short_time_equivalent_power_mva"],
            10 / math.sqrt(3) * 200 / 1000,
            places=12,
        )
        self.assertAlmostEqual(
            package_10["calculated"][
                "minimum_transformer_capacity_kva_at_overload_factor"
            ],
            10 / math.sqrt(3) * 200 / 10,
            places=12,
        )
        self.assertEqual(package_10["selected_transformer_capacity_kva_each"], 200)
        for key, package_id in (("35kv", "GRD-PKG-35"), ("10kv", "GRD-PKG-10")):
            with self.subTest(grounding_data_alignment=key):
                package = packages[package_id]
                input_grounding = self.design_inputs["calculation_rules"][
                    "grounding"
                ][key]
                baseline_package = self.baseline["neutral_grounding"][
                    "equipment_packages"
                ][key]
                self.assertEqual(
                    input_grounding["target_ground_fault_current_a"],
                    package["target_ground_fault_current_a"],
                )
                self.assertEqual(
                    input_grounding["short_time_s"], package["short_time_s"]
                )
                self.assertEqual(
                    input_grounding[
                        "selected_grounding_transformer_capacity_kva_each"
                    ],
                    package["selected_transformer_capacity_kva_each"],
                )
                self.assertEqual(
                    baseline_package["identifiers"], package["source_ids"]
                )
                self.assertEqual(
                    baseline_package["quantity"], package["quantity"]
                )
        for package in packages.values():
            with self.subTest(grounding_package=package["id"]):
                self.assertEqual(package["quantity"], 2)
                self.assertEqual(package["grounding_transformer_connection"], "ZN_neutral_forming")
                self.assertIn("neutral_zero_sequence_overcurrent", package["protection_functions"])
                self.assertEqual(package["course_precheck_status"], "provisional_pass")
                self.assertEqual(package["candidate"]["evidence_status"], "target_only")
                self.assertIn("manufacturer", package["candidate"]["final_vendor_boundary"])

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

        selection = copy.deepcopy(self.selection)
        duplicate = copy.deepcopy(selection["selections"][0])
        duplicate["id"] = "SEL-CB-220-LINE-DUPLICATE"
        selection["selections"].append(duplicate)
        with self.assertRaisesRegex(ValueError, "duplicate selection assignment"):
            validate_configuration(selection, self.catalog)

    def test_invalid_course_completion_group_reference_is_rejected(self) -> None:
        selection = copy.deepcopy(self.selection)
        selection["course_completion"]["busbars"][0]["circuit_groups"] = [
            "MISSING"
        ]

        with self.assertRaisesRegex(ValueError, "unknown circuit group"):
            validate_configuration(selection, self.catalog)

        selection = copy.deepcopy(self.selection)
        selection["course_completion"]["surge_arresters"][1][
            "interface_coverage"
        ][0]["covered_circuit_groups"] = ["MISSING"]
        with self.assertRaisesRegex(ValueError, "unknown circuit group"):
            validate_configuration(selection, self.catalog)

        selection = copy.deepcopy(self.selection)
        zct = selection["course_completion"]["supplementary"][
            "zero_sequence_current_transformers"
        ][0]
        zct["covered_members"].append(zct["covered_members"][0])
        with self.assertRaisesRegex(ValueError, "covered members must be non-empty and unique"):
            validate_configuration(selection, self.catalog)

        selection = copy.deepcopy(self.selection)
        selection["course_completion"]["supplementary"][
            "zero_sequence_current_transformers"
        ][0]["covered_members"][0] = "ILLEGAL-CABLE-INTERFACE"
        with self.assertRaisesRegex(ValueError, "outside its circuit groups"):
            calculate_equipment_screening(
                selection=selection,
                catalog=self.catalog,
                load_result=self.load_result,
                short_circuit=self.short_circuit,
                baseline=self.baseline,
                design_inputs=self.design_inputs,
            )

        selection = copy.deepcopy(self.selection)
        selection["course_completion"]["grounding_transformer_resistor_packages"][0][
            "feeder_switchgear_selection_id"
        ] = "SEL-SWGR-10-GT"
        with self.assertRaisesRegex(ValueError, "does not cover"):
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
        self.assertIn("10kV进线及母联升级为2500A目标", summary)
        self.assertIn("YH10W-204/532", summary)
        self.assertIn("校核相距3.0m≤布置4.0m", summary)
        self.assertIn("CT课程选择与动热稳定预校核", summary)
        self.assertIn("课程方案不设置", summary)
        self.assertIn("高压熔断器：不作为主回路设备选型", summary)
        self.assertIn("不是订货规范", summary)
        self.assertIn("母联合闸且两套接地源并联", summary)
        self.assertIn("10倍短时过载最小容量", summary)
        self.assertIn("8.083", summary)
        self.assertIn("ZCT-35-CABLE-FEEDERS", summary)
        self.assertIn("机械动稳定明确保持pending", summary)
        self.assertIn("最终选型总状态：`pending`", summary)


if __name__ == "__main__":
    unittest.main()
