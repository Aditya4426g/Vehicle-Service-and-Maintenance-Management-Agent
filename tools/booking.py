"""
tools/booking.py - Service appointment scheduling and slot management.
Prevents double booking and handles confirmations and cancellations.
"""
from typing import Dict, Any, Optional
import time
import database

# Standard daily time slots available for booking
DEFAULT_SLOTS = ["09:00 AM", "10:00 AM", "11:00 AM", "02:00 PM", "04:00 PM"]


def _generate_booking_reference() -> str:
    """Generate a unique human-readable booking reference code (e.g., BK123456)."""
    # Use millisecond timestamp modulo 1,000,000 to keep it short and unique
    return f"BK{int(time.time() * 1000) % 1000000:06d}"


def check_availability(center_id: str, date: str) -> Dict[str, Any]:
    """Check available appointment time slots for a given center and date."""
    # Validate required inputs
    if not center_id or not date:
        return {"center_id": center_id or "", "date": date or "", "available_slots": [], "total_slots": 0}

    # Retrieve all active (non-cancelled) bookings for this center and date
    booked = {
        a["appointment_time"].upper()
        for a in database.get_appointments()
        if a.get("service_center_id") == center_id
        and a.get("appointment_date") == date
        and a.get("status") != "CANCELLED"
    }

    # Filter out already booked slots from the standard slot list
    free_slots = [s for s in DEFAULT_SLOTS if s.upper() not in booked]
    return {
        "center_id": center_id,
        "date": date,
        "available_slots": free_slots,
        "total_slots": len(free_slots),
    }


def book_appointment(
    vehicle_id: int,
    center_id: str,
    date: str,
    time: str,
    service_type: str = "Periodic Maintenance Service"
) -> Dict[str, Any]:
    """Reserve an appointment slot if available and dispatch a confirmation notification."""
    # Step 1: Ensure all mandatory parameters are provided
    if not (vehicle_id and center_id and date and time):
        return {"status": "FAILED", "appointment_id": None, "booking_reference": None, "error": "Missing required fields."}

    # Step 2: Verify the requested time slot is actually free
    available = [s.upper() for s in check_availability(center_id, date)["available_slots"]]
    if time.upper() not in available:
        return {"status": "FAILED", "appointment_id": None, "booking_reference": None, "error": f"Slot '{time}' on {date} is not available."}

    # Step 3: Generate reference code and persist the booking to the database
    booking_ref = _generate_booking_reference()
    res = database.create_appointment(
        vehicle_id=vehicle_id,
        service_center_id=center_id,
        appointment_date=date,
        appointment_time=time,
        service_type=service_type,
        booking_reference=booking_ref
    )

    # Step 4: If booking was saved, send an automatic email confirmation
    if res.get("status") == "SUCCESS":
        try:
            from tools.notification import send_notification, format_confirmation_message
            v = database.get_vehicle_by_id(vehicle_id)
            v_name = f"{v.get('make', '')} {v.get('model', '')}".strip() if v else f"Vehicle {vehicle_id}"
            msg = format_confirmation_message(v_name, date, time, center_id, booking_ref)
            send_notification(user_id=1, appointment_id=res.get("appointment_id"), message=msg, channel="EMAIL")
        except Exception as e:
            # Continue even if notification delivery encounters an issue
            print(f"Notice: Auto email notification error: {e}")
    return res


def cancel_appointment(booking_reference: str) -> Dict[str, Any]:
    """Cancel an existing appointment using its booking reference."""
    if not booking_reference:
        return {"status": "NOT_FOUND", "booking_reference": ""}
    # Delegate cancellation to database layer to free up slot
    return database.cancel_appointment(booking_reference)


def get_appointment(booking_reference: str) -> Optional[Dict[str, Any]]:
    """Look up an appointment by its unique booking reference code."""
    if not booking_reference:
        return None
    # Search active appointments matching reference
    return next((a for a in database.get_appointments() if a.get("booking_reference") == booking_reference), None)


# Quick standalone test
if __name__ == "__main__":
    slots = check_availability("osm_101", "2026-10-15")
    print("Available slots:", slots)
