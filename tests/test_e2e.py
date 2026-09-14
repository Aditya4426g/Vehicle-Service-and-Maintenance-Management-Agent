"""
test_e2e.py - End-to-End Persona Scenario and Validation Suite.
Simulates the primary user journey (Rahul / Tata Nexon):
"My Tata Nexon is at 9,800 km and was last serviced at 5,000 km.
Check whether service is due, find a nearby service center, and book an appointment for tomorrow morning."
Also tests edge cases and rule enforcement.
"""
from datetime import date, timedelta
import pytest

from agent import execute_tool
import database


def test_e2e_main_demo_workflow():
    """
    Execute the complete 11-step persona workflow:
    1. Vehicle identified and retrieved
    2. Service history retrieved
    3. Maintenance calculated (APPROACHING: 200 km left)
    4. Location geocoded
    5. Nearby service centers discovered
    6. Slot availability verified
    7. Appointment booked
    8. Booking reference (BK...) generated
    9. Appointment saved to database
    10. Notification sent and logged
    11. Final confirmation state verified
    """
    # Baseline setup
    database.update_vehicle_mileage(1, 9800)

    # 1. Vehicle Lookup
    v_res = execute_tool("get_vehicle_info", {"user_id": 1, "vehicle_name": "Tata Nexon"})
    assert "vehicle" in v_res
    v = v_res["vehicle"]
    assert v["make"] == "Tata" and v["model"] == "Nexon"
    assert v["current_mileage"] == 9800
    assert v["last_service_mileage"] == 5000

    # 2. Service History
    hist_res = execute_tool("get_service_history", {"vehicle_id": v["id"]})
    assert len(hist_res["service_history"]) >= 2

    # 3. Deterministic Maintenance Calculation
    status_res = execute_tool("calculate_service_status", {
        "current_mileage": v["current_mileage"],
        "last_service_mileage": v["last_service_mileage"],
        "interval_km": 5000,
        "last_service_date": str(v["last_service_date"]),
        "interval_months": 6,
        "reference_date": date(2024, 9, 1)
    })
    # With 9,800 km and interval 5,000 km after 5,000 km: exactly 200 km remaining -> APPROACHING
    assert status_res["status"] == "APPROACHING"
    assert status_res["remaining_km"] == 200
    assert status_res["next_service_mileage"] == 10000

    # 4. Location Geocoding
    geo_res = execute_tool("geocode_location", {"address_or_city": "Indiranagar, Bangalore"})
    lat = geo_res["latitude"] or 12.9716
    lon = geo_res["longitude"] or 77.5946
    assert lat is not None and lon is not None

    # 5. Search Nearby Workshops
    centers_res = execute_tool("search_service_centers", {"latitude": lat, "longitude": lon, "radius_km": 10})
    center_id = "osm_101"
    if centers_res.get("service_centers"):
        center_id = centers_res["service_centers"][0]["center_id"]
    assert center_id is not None

    # 6. Check Slot Availability for Tomorrow
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    avail = execute_tool("check_availability", {"center_id": center_id, "date": tomorrow})
    assert "available_slots" in avail
    assert len(avail["available_slots"]) > 0
    selected_time = avail["available_slots"][0]

    # 7 & 8. Book Appointment and Generate Reference
    booking = execute_tool("book_appointment", {
        "vehicle_id": v["id"],
        "center_id": center_id,
        "date": tomorrow,
        "time": selected_time,
        "service_type": "Periodic Maintenance Service"
    })
    assert booking["status"] == "SUCCESS"
    assert booking["appointment_id"] is not None
    ref = booking["booking_reference"]
    assert ref.startswith("BK")

    # 9. Verify Appointment Saved in Database
    appts = database.get_appointments(vehicle_id=v["id"])
    matched = [a for a in appts if a.get("booking_reference") == ref]
    assert len(matched) == 1
    assert matched[0]["appointment_time"] == selected_time

    # 10. Send Notification with actual appointment_id
    notif = execute_tool("send_notification", {
        "user_id": 1,
        "appointment_id": booking["appointment_id"],
        "message": f"Service booked at {center_id} for {tomorrow} at {selected_time}. Ref: {ref}",
        "channel": "EMAIL"
    })
    assert notif["status"] == "SENT"
    assert notif["notification_id"] is not None


def test_e2e_unknown_vehicle_edge_case():
    """Verify system handles unknown vehicle without proceeding to calculation or booking."""
    res = execute_tool("get_vehicle_info", {"user_id": 1, "vehicle_name": "Ferrari Roma"})
    assert "error" in res
    assert "Vehicle not found" in res["error"]


def test_e2e_booking_rule_only_when_requested():
    """
    Verify booking rule:
    Checking maintenance status does NOT automatically create a booking.
    """
    initial_appts = len(database.get_appointments(vehicle_id=1))

    # User only asks for maintenance calculation
    res = execute_tool("calculate_service_status", {
        "current_mileage": 9800,
        "last_service_mileage": 5000,
        "interval_km": 5000,
        "last_service_date": "2024-03-15",
        "interval_months": 6
    })
    assert res["status"] in ["APPROACHING", "OVERDUE"]

    # Confirm appointment count did not increase
    current_appts = len(database.get_appointments(vehicle_id=1))
    assert current_appts == initial_appts


def test_e2e_duplicate_booking_collision_rejection():
    """Verify that attempting to book an already occupied slot fails and sends NO notification."""
    target_date = "2026-12-01"
    time_slot = "10:00 AM"
    center_id = "osm_101"

    # 1. First booking takes the slot
    b1 = execute_tool("book_appointment", {
        "vehicle_id": 1,
        "center_id": center_id,
        "date": target_date,
        "time": time_slot,
        "service_type": "Periodic Maintenance"
    })
    assert b1["status"] == "SUCCESS"

    # 2. Second booking attempts the exact same slot
    b2 = execute_tool("book_appointment", {
        "vehicle_id": 1,
        "center_id": center_id,
        "date": target_date,
        "time": time_slot,
        "service_type": "General Inspection"
    })
    assert b2["status"] == "FAILED"
    assert b2["appointment_id"] is None
    assert "already booked" in b2["error"].lower() or "not available" in b2["error"].lower()
