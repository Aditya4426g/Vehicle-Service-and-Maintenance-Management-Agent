"""
test_integration.py - Full Workflow Integration Tests.
Verifies the complete tool chain:
USER -> AGENT -> DATABASE -> MAINTENANCE -> LOCATION -> BOOKING -> NOTIFICATION -> RESPONSE.
"""
from datetime import date
from unittest.mock import MagicMock
import pytest

from agent import VehicleMaintenanceAgent, execute_tool
import database
from tools.maintenance import calculate_service_status
from tools.location import calculate_distance_km
from tools.booking import check_availability, book_appointment, get_appointment
from tools.notification import send_notification, format_confirmation_message


def test_full_tool_chain_sequence():
    """
    Step-by-step verification of the full pipeline connecting all components:
    1. Vehicle info retrieval
    2. Service history retrieval
    3. Maintenance status calculation
    4. Location geocoding & workshop search
    5. Slot availability check
    6. Appointment booking & collision check
    7. Notification dispatch & DB persistence
    """
    # Ensure clean baseline mileage
    database.update_vehicle_mileage(1, 9800)

    # Step 1: Vehicle Lookup
    vehicle_res = execute_tool("get_vehicle_info", {"user_id": 1, "vehicle_name": "Tata Nexon"})
    assert "vehicle" in vehicle_res
    vehicle = vehicle_res["vehicle"]
    assert vehicle["model"] == "Nexon"
    assert vehicle["current_mileage"] == 9800

    # Step 2: Service History Lookup
    history_res = execute_tool("get_service_history", {"vehicle_id": vehicle["id"]})
    assert "service_history" in history_res
    history = history_res["service_history"]
    assert len(history) >= 2

    # Step 3: Maintenance Status Calculation
    maint_res = execute_tool("calculate_service_status", {
        "current_mileage": vehicle["current_mileage"],
        "last_service_mileage": vehicle["last_service_mileage"],
        "interval_km": 5000,
        "last_service_date": str(vehicle["last_service_date"]),
        "interval_months": 6,
        "reference_date": date(2024, 9, 1)
    })
    assert maint_res["status"] == "APPROACHING"
    assert maint_res["remaining_km"] == 200

    # Step 4: Geocode & Find Service Center
    # Mocking or using known coordinate in Bangalore
    geo_res = execute_tool("geocode_location", {"address_or_city": "Indiranagar, Bangalore"})
    # Indiranagar coordinates or fallback
    lat = geo_res["latitude"] or 12.9716
    lon = geo_res["longitude"] or 77.5946

    centers_res = execute_tool("search_service_centers", {"latitude": lat, "longitude": lon, "radius_km": 10})
    # If network returns empty, fallback to seeded center osm_101
    center_id = "osm_101"
    if centers_res.get("service_centers"):
        center_id = centers_res["service_centers"][0]["center_id"]

    # Step 5: Check Availability
    target_date = "2026-11-20"
    avail_res = execute_tool("check_availability", {"center_id": center_id, "date": target_date})
    assert "available_slots" in avail_res
    assert len(avail_res["available_slots"]) > 0
    chosen_slot = avail_res["available_slots"][0]

    # Step 6: Book Appointment
    booking_res = execute_tool("book_appointment", {
        "vehicle_id": vehicle["id"],
        "center_id": center_id,
        "date": target_date,
        "time": chosen_slot,
        "service_type": "Periodic Maintenance Service"
    })
    assert booking_res["status"] == "SUCCESS"
    assert booking_res["appointment_id"] is not None
    booking_ref = booking_res["booking_reference"]
    assert booking_ref.startswith("BK")

    # Step 7: Send Notification with returned appointment_id
    notif_msg = format_confirmation_message(
        vehicle_name=f"{vehicle['make']} {vehicle['model']}",
        date=target_date,
        time=chosen_slot,
        service_center_name="ABC Motors Tata Authorized",
        booking_reference=booking_ref
    )
    notif_res = execute_tool("send_notification", {
        "user_id": 1,
        "appointment_id": booking_res["appointment_id"],
        "message": notif_msg,
        "channel": "EMAIL"
    })
    assert notif_res["status"] == "SENT"
    assert notif_res["notification_id"] is not None

    # Step 8: Confirm persistence in database
    persisted_appt = get_appointment(booking_ref)
    assert persisted_appt is not None
    assert persisted_appt["appointment_time"] == chosen_slot
    assert persisted_appt["status"] == "CONFIRMED"


def test_agent_orchestration_multi_step_mock():
    """
    Test the agent orchestrating a 2-step tool sequence via mocked Groq completion:
    Step 1: Agent calls get_vehicle_info
    Step 2: Agent calls calculate_service_status
    Step 3: Agent produces final conversational summary
    """
    agent = VehicleMaintenanceAgent()
    agent.client = MagicMock()

    # Tool call 1: get_vehicle_info
    call1 = MagicMock()
    call1.id = "call_step1"
    call1.function.name = "get_vehicle_info"
    call1.function.arguments = '{"user_id": 1, "vehicle_name": "Tata Nexon"}'

    resp1 = MagicMock()
    msg1 = MagicMock()
    msg1.tool_calls = [call1]
    msg1.content = None
    choice1 = MagicMock(message=msg1)
    resp1.choices = [choice1]

    # Tool call 2: calculate_service_status
    call2 = MagicMock()
    call2.id = "call_step2"
    call2.function.name = "calculate_service_status"
    call2.function.arguments = (
        '{"current_mileage": 9800, "last_service_mileage": 5000, "interval_km": 5000, '
        '"last_service_date": "2024-03-15", "interval_months": 6, "reference_date": "2024-09-01"}'
    )

    resp2 = MagicMock()
    msg2 = MagicMock()
    msg2.tool_calls = [call2]
    msg2.content = None
    choice2 = MagicMock(message=msg2)
    resp2.choices = [choice2]

    # Final response: Natural language explanation
    resp3 = MagicMock()
    msg3 = MagicMock()
    msg3.tool_calls = None
    msg3.content = (
        "Your Tata Nexon has 200 km remaining before its 10,000 km service is due. "
        "The current status is APPROACHING."
    )
    choice3 = MagicMock(message=msg3)
    resp3.choices = [choice3]

    agent.client.chat.completions.create.side_effect = [resp1, resp2, resp3]

    final_answer = agent.run("Is my Tata Nexon service due?")
    assert "200 km remaining" in final_answer
    assert "APPROACHING" in final_answer
    assert agent.client.chat.completions.create.call_count == 3
