from __future__ import annotations

from typing import Any


STATUS_PRECEDENCE = {
    "not_applicable": 0,
    "pass": 1,
    "provisional_pass": 2,
    "pending": 3,
    "fail": 4,
}


def combine_status(statuses: list[str]) -> str:
    relevant = [status for status in statuses if status != "not_applicable"]
    if not relevant:
        return "not_applicable"
    return max(relevant, key=lambda status: STATUS_PRECEDENCE[status])


def minimum_check(
    *,
    check_id: str,
    required: float | None,
    available: float | None,
    unit: str,
    provisional: bool,
    note: str,
) -> dict[str, Any]:
    if required is None or available is None:
        return {
            "id": check_id,
            "status": "pending",
            "required": required,
            "available": available,
            "unit": unit,
            "margin": None,
            "note": note,
        }

    required_value = float(required)
    available_value = float(available)
    passed = available_value + 1e-12 >= required_value
    return {
        "id": check_id,
        "status": (
            "provisional_pass" if passed and provisional else "pass"
        )
        if passed
        else "fail",
        "required": required_value,
        "available": available_value,
        "unit": unit,
        "margin": available_value - required_value,
        "note": note,
    }


def pending_check(check_id: str, note: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": "pending",
        "required": None,
        "available": None,
        "unit": None,
        "margin": None,
        "note": note,
    }


def not_applicable_check(check_id: str, note: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": "not_applicable",
        "required": None,
        "available": None,
        "unit": None,
        "margin": None,
        "note": note,
    }
