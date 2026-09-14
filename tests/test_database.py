"""
test_database.py - Unit tests for database.py CRUD layer.
Tests reads, writes, appointment collision prevention, cancellation, and error handling.
"""
import pytest
from database import (
    get_user,
    get_vehicle_info,
    get_vehicle_by_name,
    get_service_history,
    get_maintenance_schedule,
    get_appointments,
    create_appointment,
    cancel_appointment,
    create_notification,
    update_vehicle_mileage
)


def test_get_user():
    """Verify user retrieval for Rahul."""
    user = get_user(1)
    assert user is not None
    assert user["name"] == "Rahul"
    assert user["email"] == "rahul@example.com"


def test_get_vehicle_info():
    """Verify vehicle details retrieval for Tata Nexon."""
    vehicle = get_vehicle_info(1)
    assert vehicle is not None
    assert vehicle["make"] == "Tata"
    assert vehicle["model"] == "Nexon"
    assert vehicle["current_mileage"] == 9800
    assert vehicle["last_service_mileage"] == 5000


def test_get_vehicle_by_name():
    """Verify lookup by vehicle model name."""
    v1 = get_vehicle_by_name("Nexon", user_id=1)
    assert v1 is not None
    assert v1["model"] == "Nexon"

    v2 = get_vehicle_by_name("NonExistentCar", user_id=1)
    assert v2 is None


def test_get_service_history():
    """Verify retrieval of past service records."""
    history = get_service_history(1)
    assert isinstance(history, list)
    assert len(history) >= 2
    assert history[0]["service_mileage"] == 1000
    assert history[1]["service_mileage"] == 5000


def test_get_maintenance_schedule():
    """Verify retrieval of vehicle maintenance intervals."""
    schedule = get_maintenance_schedule(1)
    assert schedule is not None
    assert schedule["interval_km"] == 5000
    assert schedule["interval_months"] == 6


def test_create_appointment_and_collision():
    """Verify appointment creation and double-booking collision rejection."""
    # 1. First booking on a free slot
    ref = "BK10001"
    res1 = create_appointment(
        vehicle_id=1,
        service_center_id="osm_101",
        appointment_date="2026-09-20",
        appointment_time="11:00 AM",
        service_type="Periodic Maintenance Service",
        booking_reference=ref
    )
    assert res1["status"] == "SUCCESS"
    assert res1["booking_reference"] == ref
    assert res1["appointment_id"] is not None

    # 2. Collision attempt on the same center, date, and time
    res2 = create_appointment(
        vehicle_id=1,
        service_center_id="osm_101",
        appointment_date="2026-09-20",
        appointment_time="11:00 AM",
        service_type="General Checkup",
        booking_reference="BK10002"
    )
    assert res2["status"] == "FAILED"
    assert res2["appointment_id"] is None
    assert "already booked" in res2["error"].lower()


def test_cancel_appointment():
    """Verify appointment cancellation by booking reference."""
    ref = "BK_TO_CANCEL"
    create_appointment(
        vehicle_id=1,
        service_center_id="osm_103",
        appointment_date="2026-09-25",
        appointment_time="02:00 PM",
        service_type="Periodic Maintenance",
        booking_reference=ref
    )

    cancel_res = cancel_appointment(ref)
    assert cancel_res["status"] == "CANCELLED"

    not_found_res = cancel_appointment("NON_EXISTENT_REF")
    assert not_found_res["status"] == "NOT_FOUND"


def test_create_notification():
    """Verify creation of notification linked to an appointment."""
    res = create_notification(
        user_id=1,
        appointment_id=101,
        message="Your service appointment is confirmed for tomorrow at 10:00 AM."
    )
    assert res["status"] == "SENT"
    assert res["notification_id"] is not None

    # Empty message failure
    empty_res = create_notification(user_id=1, appointment_id=101, message="")
    assert empty_res["status"] == "FAILED"


def test_update_vehicle_mileage():
    """Verify updating vehicle mileage and negative input rejection."""
    res1 = update_vehicle_mileage(1, 9850)
    assert res1["status"] == "SUCCESS"
    assert res1["current_mileage"] == 9850

    # Negative mileage check
    res2 = update_vehicle_mileage(1, -100)
    assert res2["status"] == "FAILED"

    # Restore baseline mileage for subsequent test isolation
    update_vehicle_mileage(1, 9800)
