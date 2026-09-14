"""
tools/booking.py - Appointment Booking and Slot Management Tool.
Handles slot availability, appointment booking, collision prevention, and cancellations.
Backed by database.py for persistent storage.
"""
from typing import Dict, List, Any, Optional
import database

# Standard daily time slots offered by service centers
DEFAULT_SLOTS = [
    "09:00 AM",
    "10:00 AM",
    "11:00 AM",
    "02:00 PM",
    "04:00 PM"
]

_booking_counter = 10000


def _generate_booking_reference() -> str:
    """Generate a clean, unique booking reference code (e.g. BK10001)."""
    global _booking_counter
    _booking_counter += 1
    return f"BK{_booking_counter}"


def check_availability(center_id: str, date: str) -> Dict[str, Any]:
    """
    Check available appointment slots for a given service center and date.

    Contract:
      {
        "center_id": str,
        "date": str,
        "available_slots": list[str],
        "total_slots": int
      }
    """
    if not center_id or not date:
        return {
            "center_id": center_id or "",
            "date": date or "",
            "available_slots": [],
            "total_slots": 0
        }

    # Fetch existing appointments to filter out booked slots
    existing_appointments = database.get_appointments()
    booked_times = {
        appt["appointment_time"].upper()
        for appt in existing_appointments
        if appt["service_center_id"] == center_id
        and appt["appointment_date"] == date
        and appt.get("status") != "CANCELLED"
    }

    free_slots = [slot for slot in DEFAULT_SLOTS if slot.upper() not in booked_times]

    return {
        "center_id": center_id,
        "date": date,
        "available_slots": free_slots,
        "total_slots": len(free_slots)
    }


def book_appointment(
    vehicle_id: int,
    center_id: str,
    date: str,
    time: str,
    service_type: str = "Periodic Maintenance Service"
) -> Dict[str, Any]:
    """
    Book an appointment after checking availability and collision rules.

    Contract:
      {
        "status": "SUCCESS" | "FAILED",
        "appointment_id": int | None,
        "booking_reference": str | None,
        "error": str | None
      }
    """
    # 1. Parameter validation
    if not vehicle_id or not center_id or not date or not time:
        return {
            "status": "FAILED",
            "appointment_id": None,
            "booking_reference": None,
            "error": "Missing required booking fields (vehicle_id, center_id, date, and time are required)."
        }

    # 2. Check if requested time is available
    availability = check_availability(center_id, date)
    available_times_upper = [s.upper() for s in availability["available_slots"]]

    if time.upper() not in available_times_upper:
        return {
            "status": "FAILED",
            "appointment_id": None,
            "booking_reference": None,
            "error": f"Slot '{time}' on {date} at service center '{center_id}' is not available."
        }

    # 3. Generate unique booking reference
    booking_ref = _generate_booking_reference()

    # 4. Insert into database (which also enforces database-level collision checks)
    res = database.create_appointment(
        vehicle_id=vehicle_id,
        service_center_id=center_id,
        appointment_date=date,
        appointment_time=time,
        service_type=service_type,
        booking_reference=booking_ref
    )

    if res["status"] == "SUCCESS":
        return {
            "status": "SUCCESS",
            "appointment_id": res["appointment_id"],
            "booking_reference": res["booking_reference"],
            "error": None
        }
    else:
        return {
            "status": "FAILED",
            "appointment_id": None,
            "booking_reference": None,
            "error": res.get("error", "Database booking failed.")
        }


def cancel_appointment(booking_reference: str) -> Dict[str, Any]:
    """
    Cancel an existing appointment by booking reference.

    Contract:
      {
        "status": "CANCELLED" | "NOT_FOUND",
        "booking_reference": str
      }
    """
    if not booking_reference:
        return {"status": "NOT_FOUND", "booking_reference": ""}

    return database.cancel_appointment(booking_reference)


def get_appointment(booking_reference: str) -> Optional[Dict[str, Any]]:
    """Retrieve appointment details by booking reference."""
    if not booking_reference:
        return None

    appts = database.get_appointments()
    for appt in appts:
        if appt.get("booking_reference") == booking_reference:
            return appt
    return None


if __name__ == "__main__":
    print("--- Booking Tool Quick Check ---")
    slots = check_availability("osm_101", "2026-09-20")
    print(f"Available slots for osm_101: {slots['available_slots']}")
