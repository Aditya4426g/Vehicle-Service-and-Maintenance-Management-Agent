"""
tools/maintenance.py - Vehicle maintenance status calculator.
Determines if service is OVERDUE, DUE, APPROACHING, or NOT_DUE.
"""
from datetime import date, datetime
from typing import Dict, Any, Optional
import calendar
from config import APPROACHING_THRESHOLD_KM, APPROACHING_THRESHOLD_DAYS


def _add_months(source_date: date, months: int) -> date:
    """Add months to a date safely handling month lengths."""
    m = source_date.month - 1 + months
    y = source_date.year + m // 12
    m = m % 12 + 1
    max_d = calendar.monthrange(y, m)[1]
    return date(y, m, min(source_date.day, max_d))


def calculate_service_status(
    current_mileage: int,
    last_service_mileage: int,
    interval_km: int,
    last_service_date: str,
    interval_months: int,
    reference_date: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Calculate maintenance status based on mileage and elapsed time.
    Priority: OVERDUE > DUE > APPROACHING > NOT_DUE
    """
    # Validate positive numbers
    if current_mileage < 0 or last_service_mileage < 0 or interval_km <= 0 or interval_months <= 0:
        return {
            "status": "INVALID_INPUT",
            "remaining_km": 0,
            "days_remaining": 0,
            "next_service_mileage": 0,
            "target_service_date": "",
            "message": "Error: Mileage and intervals must be positive numbers."
        }

    # Parse last service date
    try:
        parsed_date = datetime.strptime(str(last_service_date).strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return {
            "status": "INVALID_INPUT",
            "remaining_km": 0,
            "days_remaining": 0,
            "next_service_mileage": 0,
            "target_service_date": "",
            "message": f"Error: Invalid date '{last_service_date}'. Expected YYYY-MM-DD."
        }

    # Determine reference date (defaults to today)
    if reference_date:
        if isinstance(reference_date, str):
            try:
                today = datetime.strptime(reference_date.strip(), "%Y-%m-%d").date()
            except ValueError:
                today = date.today()
        else:
            today = reference_date
    else:
        today = date.today()

    # Calculate target mileage and date
    next_service_mileage = last_service_mileage + interval_km
    remaining_km = next_service_mileage - current_mileage
    target_date = _add_months(parsed_date, interval_months)
    days_remaining = (target_date - today).days

    # Determine status according to priority rules
    if remaining_km < 0 or days_remaining < 0:
        status = "OVERDUE"
        msg = f"Service is OVERDUE by {abs(remaining_km)} km and {abs(days_remaining)} days."
    elif remaining_km == 0 or days_remaining == 0:
        status = "DUE"
        msg = f"Service is DUE now at {next_service_mileage} km."
    elif (0 < remaining_km <= APPROACHING_THRESHOLD_KM) or (0 < days_remaining <= APPROACHING_THRESHOLD_DAYS):
        status = "APPROACHING"
        msg = f"Service is APPROACHING: {remaining_km} km remaining ({days_remaining} days left)."
    else:
        status = "NOT_DUE"
        msg = f"Service is NOT DUE. {remaining_km} km and {days_remaining} days remaining."

    return {
        "status": status,
        "remaining_km": remaining_km,
        "days_remaining": days_remaining,
        "next_service_mileage": next_service_mileage,
        "target_service_date": target_date.isoformat(),
        "message": msg
    }


if __name__ == "__main__":
    result = calculate_service_status(9800, 5000, 5000, "2024-03-15", 6)
    print("Sample calculation:", result)
