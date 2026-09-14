"""
test_booking.py - Unit tests for tools/booking.py.
Tests availability checking, successful booking, collision rejection, reference format, cancellation, and retrieval.
"""
import pytest
from tools.booking import (
    check_availability,
    book_appointment,
    cancel_appointment,
    get_appointment
)


def test_check_availability():
    """Verify standard slots are available for a new future date."""
    res = check_availability("osm_101", "2026-10-15")
    assert res["center_id"] == "osm_101"
    assert res["date"] == "2026-10-15"
    assert len(res["available_slots"]) == 5
    assert "09:00 AM" in res["available_slots"]
    assert "10:00 AM" in res["available_slots"]


def test_book_appointment_success():
    """Verify successful appointment booking returns reference, appointment_id, and SUCCESS status."""
    res = book_appointment(
        vehicle_id=1,
        center_id="osm_101",
        date="2026-10-15",
        time="09:00 AM",
        service_type="Periodic Maintenance Service"
    )
    assert res["status"] == "SUCCESS"
    assert res["appointment_id"] is not None
    assert res["booking_reference"].startswith("BK")
    assert res["error"] is None

    # Verify slot is no longer available
    availability_after = check_availability("osm_101", "2026-10-15")
    assert "09:00 AM" not in availability_after["available_slots"]
    assert len(availability_after["available_slots"]) == 4


def test_booking_collision_rejection():
    """Verify that booking the exact same occupied slot is strictly rejected."""
    # Attempt booking "09:00 AM" again on the same date and center
    collision_res = book_appointment(
        vehicle_id=1,
        center_id="osm_101",
        date="2026-10-15",
        time="09:00 AM",
        service_type="Periodic Maintenance Service"
    )
    assert collision_res["status"] == "FAILED"
    assert collision_res["appointment_id"] is None
    assert "not available" in collision_res["error"].lower() or "already booked" in collision_res["error"].lower()


def test_book_appointment_missing_fields():
    """Verify validation when required parameters are missing."""
    res = book_appointment(
        vehicle_id=None,
        center_id="",
        date="2026-10-15",
        time="10:00 AM"
    )
    assert res["status"] == "FAILED"
    assert "Missing required" in res["error"]


def test_booking_cancellation_and_slot_freed():
    """Verify that canceling an appointment updates status and frees the slot."""
    # Book 11:00 AM
    booking = book_appointment(
        vehicle_id=1,
        center_id="osm_102",
        date="2026-10-20",
        time="11:00 AM",
        service_type="Periodic Maintenance Service"
    )
    ref = booking["booking_reference"]
    assert booking["status"] == "SUCCESS"

    # Cancel booking
    cancel_res = cancel_appointment(ref)
    assert cancel_res["status"] == "CANCELLED"
    assert cancel_res["booking_reference"] == ref

    # Verify get_appointment confirms CANCELLED
    appt = get_appointment(ref)
    assert appt is not None
    assert appt["status"] == "CANCELLED"

    # Verify slot is free again
    availability = check_availability("osm_102", "2026-10-20")
    assert "11:00 AM" in availability["available_slots"]


def test_cancel_non_existent_appointment():
    """Verify cancelling an unknown reference returns NOT_FOUND."""
    res = cancel_appointment("NON_EXISTENT_REF_999")
    assert res["status"] == "NOT_FOUND"


def test_get_appointment_not_found():
    """Verify retrieving an unknown reference returns None."""
    assert get_appointment("NON_EXISTENT_REF_999") is None
    assert get_appointment("") is None
