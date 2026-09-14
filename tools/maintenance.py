"""
tools/maintenance.py - Deterministic Vehicle Maintenance Status Calculator.
Calculates service status using mileage and date intervals.
Follows strict priority: OVERDUE > DUE > APPROACHING > NOT_DUE.
"""
from datetime import date, datetime
from typing import Dict, Any, Optional
import calendar

from config import APPROACHING_THRESHOLD_KM, APPROACHING_THRESHOLD_DAYS


def _add_months(source_date: date, months: int) -> date:
    """Helper to add calendar months to a date without external dependencies."""
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    # Clamp day to the maximum valid day of that month (e.g. leap years / 30-day months)
    max_day = calendar.monthrange(year, month)[1]
    day = min(source_date.day, max_day)
    return date(year, month, day)


def calculate_service_status(
    current_mileage: int,
    last_service_mileage: int,
    interval_km: int,
    last_service_date: str,
    interval_months: int,
    reference_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Calculate deterministic vehicle service status.

    Status Priority:
      OVERDUE > DUE > APPROACHING > NOT_DUE

    Rules:
      1. remaining_km < 0 or days_remaining < 0 -> OVERDUE
      2. remaining_km == 0 or days_remaining == 0 -> DUE
      3. 0 < remaining_km <= 500 or 0 < days_remaining <= 30 -> APPROACHING
      4. Otherwise -> NOT_DUE

    Returns:
      {
        "status": "NOT_DUE" | "APPROACHING" | "DUE" | "OVERDUE",
        "remaining_km": int,
        "days_remaining": int,
        "next_service_mileage": int,
        "target_service_date": str,
        "message": str
      }
    """
    # 1. Input Validation
    if current_mileage < 0 or last_service_mileage < 0 or interval_km <= 0 or interval_months <= 0:
        return {
            "status": "INVALID_INPUT",
            "remaining_km": 0,
            "days_remaining": 0,
            "next_service_mileage": 0,
            "target_service_date": "",
            "message": "Error: Mileage and intervals must be positive numbers."
        }

    try:
        parsed_last_date = datetime.strptime(last_service_date.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return {
            "status": "INVALID_INPUT",
            "remaining_km": 0,
            "days_remaining": 0,
            "next_service_mileage": 0,
            "target_service_date": "",
            "message": f"Error: Invalid date format for '{last_service_date}'. Expected YYYY-MM-DD."
        }

    today = reference_date if reference_date is not None else date.today()

    # 2. Mileage Calculation
    next_service_mileage = last_service_mileage + interval_km
    remaining_km = next_service_mileage - current_mileage

    # 3. Date Calculation
    target_date = _add_months(parsed_last_date, interval_months)
    days_remaining = (target_date - today).days

    # 4. Status Evaluation by Strict Priority
    if remaining_km < 0 or days_remaining < 0:
        status = "OVERDUE"
        if remaining_km < 0 and days_remaining < 0:
            msg = f"Service is OVERDUE by {abs(remaining_km)} km and {abs(days_remaining)} days."
        elif remaining_km < 0:
            msg = f"Service is OVERDUE by {abs(remaining_km)} km (target was {next_service_mileage} km)."
        else:
            msg = f"Service is OVERDUE by {abs(days_remaining)} days (target date was {target_date.isoformat()})."

    elif remaining_km == 0 or days_remaining == 0:
        status = "DUE"
        if remaining_km == 0 and days_remaining == 0:
            msg = f"Service is DUE today at exactly {next_service_mileage} km."
        elif remaining_km == 0:
            msg = f"Service is DUE now: vehicle reached target mileage of {next_service_mileage} km."
        else:
            msg = f"Service is DUE today ({target_date.isoformat()})."

    elif (0 < remaining_km <= APPROACHING_THRESHOLD_KM) or (0 < days_remaining <= APPROACHING_THRESHOLD_DAYS):
        status = "APPROACHING"
        reasons = []
        if 0 < remaining_km <= APPROACHING_THRESHOLD_KM:
            reasons.append(f"{remaining_km} km remaining before {next_service_mileage} km")
        if 0 < days_remaining <= APPROACHING_THRESHOLD_DAYS:
            reasons.append(f"{days_remaining} days remaining before {target_date.isoformat()}")
        msg = f"Service is APPROACHING: {', '.join(reasons)}."

    else:
        status = "NOT_DUE"
        msg = (
            f"Service is NOT DUE. Vehicle has {remaining_km} km and "
            f"{days_remaining} days remaining until next periodic service."
        )

    return {
        "status": status,
        "remaining_km": remaining_km,
        "days_remaining": days_remaining,
        "next_service_mileage": next_service_mileage,
        "target_service_date": target_date.isoformat(),
        "message": msg
    }


if __name__ == "__main__":
    # Quick demo calculation
    demo = calculate_service_status(
        current_mileage=9800,
        last_service_mileage=5000,
        interval_km=5000,
        last_service_date="2024-03-15",
        interval_months=6,
        reference_date=date(2024, 9, 1)
    )
    print("--- Maintenance Calculation Verification ---")
    for k, v in demo.items():
        print(f"  {k}: {v}")
