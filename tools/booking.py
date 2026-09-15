"""
tools/booking.py - Service appointment scheduling and slot management.
Prevents double booking and handles confirmations and cancellations.
"""
from typing import Dict, Any, Optional
import time
import database

# Standard available appointment slots
DEFAULT_SLOTS = ["09:00 AM", "10:00 AM", "11:00 AM", "02:00 PM", "04:00 PM"]


def _generate_booking_reference() -> str:
    """Generate a unique booking reference code."""
    return f"BK{int(time.time() * 1000) % 1000000:06d}"


def check_availability(center_id: str, date: str) -> Dict[str, Any]:
    """Check available appointment time slots for a given center and date."""
    if not center_id or not date:
        return {"center_id": center_id or "", "date": date or "", "available_slots": [], "total_slots": 0}

    # Find already booked slots that are not cancelled
    booked = {
        a["appointment_time"].upper()
        for a in database.get_appointments()
        if a.get("service_center_id") == center_id
        and a.get("appointment_date") == date
        and a.get("status") != "CANCELLED"
    }

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
    """Reserve an appointment slot if available."""
    if not (vehicle_id and center_id and date and time):
        return {"status": "FAILED", "appointment_id": None, "booking_reference": None, "error": "Missing required fields."}

    # Verify slot availability
    available = [s.upper() for s in check_availability(center_id, date)["available_slots"]]
    if time.upper() not in available:
        return {"status": "FAILED", "appointment_id": None, "booking_reference": None, "error": f"Slot '{time}' on {date} is not available."}

    # Create appointment in database
    booking_ref = _generate_booking_reference()
    res = database.create_appointment(
        vehicle_id=vehicle_id,
        service_center_id=center_id,
        appointment_date=date,
        appointment_time=time,
        service_type=service_type,
        booking_reference=booking_ref
    )
    if res.get("status") == "SUCCESS":
        try:
            from tools.notification import send_notification, format_confirmation_message
            v = database.get_vehicle_by_id(vehicle_id)
            v_name = f"{v.get('make', '')} {v.get('model', '')}".strip() if v else f"Vehicle {vehicle_id}"
            msg = format_confirmation_message(v_name, date, time, center_id, booking_ref)
            send_notification(user_id=1, appointment_id=res.get("appointment_id"), message=msg, channel="EMAIL")
        except Exception as e:
            print(f"Notice: Auto email notification error: {e}")
    return res


def cancel_appointment(booking_reference: str) -> Dict[str, Any]:
    """Cancel an appointment using its booking reference."""
    if not booking_reference:
        return {"status": "NOT_FOUND", "booking_reference": ""}
    return database.cancel_appointment(booking_reference)


def get_appointment(booking_reference: str) -> Optional[Dict[str, Any]]:
    """Look up an appointment by booking reference."""
    if not booking_reference:
        return None
    return next((a for a in database.get_appointments() if a.get("booking_reference") == booking_reference), None)


if __name__ == "__main__":
    slots = check_availability("osm_101", "2026-10-15")
    print("Available slots:", slots)
