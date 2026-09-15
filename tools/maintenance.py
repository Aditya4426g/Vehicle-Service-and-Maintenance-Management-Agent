"""
tools/maintenance.py - Vehicle maintenance status calculator.
Determines if service is OVERDUE, DUE, APPROACHING, or NOT_DUE using deterministic rules.
"""
from datetime import date, datetime
from typing import Dict, Any, Optional
import calendar
from config import APPROACHING_THRESHOLD_KM, APPROACHING_THRESHOLD_DAYS


def _add_months(source_date: date, months: int) -> date:
    """Add months to a date safely, properly handling leap years and month lengths."""
    m = source_date.month - 1 + months
    y = source_date.year + m // 12
    m = m % 12 + 1
    # Cap day to the max valid days for the resulting month (e.g., Feb 28/29)
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
    Calculate vehicle maintenance status based on mileage and elapsed time.
    Priority hierarchy: OVERDUE > DUE > APPROACHING > NOT_DUE.
    """
    # Step 1: Validate numeric inputs are non-negative
    if current_mileage < 0 or last_service_mileage < 0 or interval_km <= 0 or interval_months <= 0:
        return {
            "status": "INVALID_INPUT",
            "remaining_km": 0,
            "days_remaining": 0,
            "next_service_mileage": 0,
            "target_service_date": "",
            "message": "Error: Mileage and intervals must be positive numbers."
        }

    # Step 2: Parse and validate the last service date string
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

    # Step 3: Determine the reference comparison date (defaults to today)
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

    # Step 4: Calculate target mileage and target service date
    next_service_mileage = last_service_mileage + interval_km
    remaining_km = next_service_mileage - current_mileage
    target_date = _add_months(parsed_date, interval_months)
    days_remaining = (target_date - today).days

    # Step 5: Evaluate maintenance status by priority
    # 1. OVERDUE: Exceeded either kilometer interval or date deadline
    if remaining_km < 0 or days_remaining < 0:
        status = "OVERDUE"
        msg = f"Service is OVERDUE by {abs(remaining_km)} km and {abs(days_remaining)} days."
    # 2. DUE: Reached exact interval threshold today
    elif remaining_km == 0 or days_remaining == 0:
        status = "DUE"
        msg = f"Service is DUE now at {next_service_mileage} km."
    # 3. APPROACHING: Within warning threshold (default: <= 500 km or <= 30 days)
    elif (0 < remaining_km <= APPROACHING_THRESHOLD_KM) or (0 < days_remaining <= APPROACHING_THRESHOLD_DAYS):
        status = "APPROACHING"
        msg = f"Service is APPROACHING: {remaining_km} km remaining ({days_remaining} days left)."
    # 4. NOT_DUE: Sufficient kilometers and time remain before next service
    else:
        status = "NOT_DUE"
        msg = f"Service is NOT DUE. {remaining_km} km and {days_remaining} days remaining."

    # Return structured status dictionary
    return {
        "status": status,
        "remaining_km": remaining_km,
        "days_remaining": days_remaining,
        "next_service_mileage": next_service_mileage,
        "target_service_date": target_date.isoformat(),
        "message": msg
    }


# Quick standalone test
if __name__ == "__main__":
    result = calculate_service_status(9800, 5000, 5000, "2024-03-15", 6)
    print("Sample calculation:", result)
