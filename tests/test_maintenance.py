"""
test_maintenance.py - Unit tests for tools/maintenance.py.
Tests all 4 statuses (NOT_DUE, APPROACHING, DUE, OVERDUE), boundary values, priority rules, and error handling.
"""
from datetime import date
import pytest
from tools.maintenance import calculate_service_status


def test_approaching_status_demo_scenario():
    """
    Test main demo persona:
    Tata Nexon: last service = 5000 km, interval = 5000 km -> next = 10000 km.
    current = 9800 km -> remaining = 200 km.
    Target date: 2024-03-15 + 6 months -> 2024-09-15.
    With reference date 2024-09-01 (14 days remaining), status must be APPROACHING.
    """
    res = calculate_service_status(
        current_mileage=9800,
        last_service_mileage=5000,
        interval_km=5000,
        last_service_date="2024-03-15",
        interval_months=6,
        reference_date=date(2024, 9, 1)
    )
    assert res["status"] == "APPROACHING"
    assert res["remaining_km"] == 200
    assert res["next_service_mileage"] == 10000
    assert res["days_remaining"] == 14
    assert "200 km remaining" in res["message"]


def test_not_due_status():
    """Verify NOT_DUE when remaining km > 500 and days remaining > 30."""
    res = calculate_service_status(
        current_mileage=6000,
        last_service_mileage=5000,
        interval_km=5000,
        last_service_date="2024-03-15",
        interval_months=6,
        reference_date=date(2024, 4, 15)  # 5 months / ~153 days remaining
    )
    assert res["status"] == "NOT_DUE"
    assert res["remaining_km"] == 4000
    assert res["days_remaining"] > 30


def test_due_status_exact_mileage():
    """Verify DUE when current mileage equals next service mileage (remaining = 0)."""
    res = calculate_service_status(
        current_mileage=10000,
        last_service_mileage=5000,
        interval_km=5000,
        last_service_date="2024-03-15",
        interval_months=6,
        reference_date=date(2024, 6, 1)  # date not due, but mileage is 0 km left
    )
    assert res["status"] == "DUE"
    assert res["remaining_km"] == 0


def test_due_status_exact_date():
    """Verify DUE when days remaining equals 0."""
    res = calculate_service_status(
        current_mileage=7000,
        last_service_mileage=5000,
        interval_km=5000,
        last_service_date="2024-03-15",
        interval_months=6,
        reference_date=date(2024, 9, 15)  # Target date exactly
    )
    assert res["status"] == "DUE"
    assert res["days_remaining"] == 0


def test_overdue_status_mileage():
    """Verify OVERDUE when current mileage exceeds next service mileage."""
    res = calculate_service_status(
        current_mileage=10250,
        last_service_mileage=5000,
        interval_km=5000,
        last_service_date="2024-03-15",
        interval_months=6,
        reference_date=date(2024, 6, 1)
    )
    assert res["status"] == "OVERDUE"
    assert res["remaining_km"] == -250
    assert "250 km" in res["message"]


def test_overdue_status_date():
    """Verify OVERDUE when target service date has passed."""
    res = calculate_service_status(
        current_mileage=7000,
        last_service_mileage=5000,
        interval_km=5000,
        last_service_date="2024-03-15",
        interval_months=6,
        reference_date=date(2024, 10, 1)  # 16 days overdue
    )
    assert res["status"] == "OVERDUE"
    assert res["days_remaining"] < 0
    assert "days" in res["message"]


def test_priority_overdue_over_approaching():
    """
    Verify status priority: OVERDUE beats APPROACHING.
    Mileage is approaching (300 km left), but date is overdue -> must be OVERDUE.
    """
    res = calculate_service_status(
        current_mileage=9700,
        last_service_mileage=5000,
        interval_km=5000,
        last_service_date="2024-03-15",
        interval_months=6,
        reference_date=date(2024, 10, 1)  # Date is past due
    )
    assert res["status"] == "OVERDUE"


def test_boundaries_500km_and_501km():
    """Test exact mileage boundary: 500 km is APPROACHING, 501 km is NOT_DUE."""
    # Exactly 500 km remaining
    res_500 = calculate_service_status(
        current_mileage=9500,
        last_service_mileage=5000,
        interval_km=5000,
        last_service_date="2024-03-15",
        interval_months=6,
        reference_date=date(2024, 5, 1)
    )
    assert res_500["remaining_km"] == 500
    assert res_500["status"] == "APPROACHING"

    # Exactly 501 km remaining
    res_501 = calculate_service_status(
        current_mileage=9499,
        last_service_mileage=5000,
        interval_km=5000,
        last_service_date="2024-03-15",
        interval_months=6,
        reference_date=date(2024, 5, 1)
    )
    assert res_501["remaining_km"] == 501
    assert res_501["status"] == "NOT_DUE"


def test_invalid_input_handling():
    """Verify invalid mileage, zero intervals, and invalid date formats."""
    # Negative mileage
    neg_res = calculate_service_status(-100, 5000, 5000, "2024-03-15", 6)
    assert neg_res["status"] == "INVALID_INPUT"

    # Zero interval
    zero_res = calculate_service_status(9800, 5000, 0, "2024-03-15", 6)
    assert zero_res["status"] == "INVALID_INPUT"

    # Invalid date string
    date_res = calculate_service_status(9800, 5000, 5000, "invalid-date", 6)
    assert date_res["status"] == "INVALID_INPUT"
