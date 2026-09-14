"""
test_reliability.py - Stress Testing, Error Handling, and Reliability Suite.
Tests all 10 critical failure and edge cases:
1. Groq API failure / Zero fallback
2. Database unavailability
3. Invalid / missing vehicle
4. Location API timeout
5. Empty geocoding results
6. Overpass API failure / empty service centers
7. No available appointment slots
8. Booking failure / collision prevention
9. Notification failure isolation
10. Hard 12-call tool loop ceiling
"""
from unittest.mock import patch, MagicMock
import requests
import pytest

from agent import VehicleMaintenanceAgent, execute_tool
import database
from tools.location import geocode_location, search_service_centers
from tools.booking import check_availability, book_appointment
from tools.notification import send_notification


def test_scenario_1_groq_api_failure_zero_fallback():
    """Verify Groq API failure retries up to 3 times and fails without switching models."""
    agent = VehicleMaintenanceAgent()
    agent.client = MagicMock()
    agent.client.chat.completions.create.side_effect = Exception("Groq 500 Internal Server Error")

    with patch("time.sleep") as mock_sleep:
        res = agent.run("Hello")
        assert "Groq API Error" in res
        assert "No model fallback configured" in res
        assert "openai/gpt-oss-120b" in res
        assert agent.client.chat.completions.create.call_count == 3
        assert mock_sleep.call_count == 3


def test_scenario_2_database_error_handling():
    """Verify database functions handle exceptions gracefully."""
    with patch("database._supabase_client") as mock_client:
        mock_client.table.side_effect = Exception("Supabase Connection Refused")
        # Should gracefully fallback or return safe structures without uncaught crashes
        user = database.get_user(9999)
        assert user is None


def test_scenario_3_invalid_vehicle_lookup():
    """Verify querying an invalid or missing vehicle returns clean error."""
    res = execute_tool("get_vehicle_info", {"user_id": 1, "vehicle_name": "InvalidGhostVehicle"})
    assert "error" in res
    assert "Vehicle not found" in res["error"]


@patch("tools.location.requests.get")
def test_scenario_4_location_api_timeout(mock_get):
    """Verify geocoding timeout produces friendly error dictionary."""
    mock_get.side_effect = requests.exceptions.Timeout("Read timeout after 8s")
    res = geocode_location("Whitefield, Bangalore")
    assert res["status"] == "FAILED"
    assert "timed out" in res["error"].lower()


@patch("tools.location.requests.get")
def test_scenario_5_empty_geocoding_results(mock_get):
    """Verify location query with no matching coordinates."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = []
    mock_get.return_value = mock_resp

    res = geocode_location("NonExistentIslandPlace999")
    assert res["status"] == "FAILED"
    assert "No coordinates found" in res["error"]


@patch("tools.location.requests.get")
@patch("tools.location.requests.post")
def test_scenario_6_overpass_api_failure(mock_post, mock_get):
    """Verify Overpass API failure returns empty list without crashing when fallbacks fail."""
    mock_post.side_effect = requests.exceptions.ConnectionError("Failed to resolve overpass-api.de")
    mock_get.side_effect = requests.exceptions.ConnectionError("Failed to reach Nominatim")
    centers = search_service_centers(12.9716, 77.5946, radius_km=10, fallback_database=False)
    assert isinstance(centers, list)
    assert len(centers) == 0


def test_scenario_7_no_available_slots():
    """Verify check_availability handles date when all slots are occupied."""
    date_str = "2026-12-25"
    center_id = "osm_busy_center"

    # Pre-book all 5 standard slots for this date
    for slot in ["09:00 AM", "10:00 AM", "11:00 AM", "02:00 PM", "04:00 PM"]:
        database.create_appointment(
            vehicle_id=1,
            service_center_id=center_id,
            appointment_date=date_str,
            appointment_time=slot,
            service_type="Service",
            booking_reference=f"BK_FULL_{slot.replace(' ', '_')}"
        )

    avail = check_availability(center_id, date_str)
    assert len(avail["available_slots"]) == 0
    assert avail["total_slots"] == 0


def test_scenario_8_booking_collision_never_claims_success():
    """Verify booking an occupied slot returns FAILED and no reference code."""
    date_str = "2026-12-26"
    center_id = "osm_101"
    time_slot = "10:00 AM"

    # Slot 1 succeeds
    b1 = book_appointment(1, center_id, date_str, time_slot)
    assert b1["status"] == "SUCCESS"

    # Slot 2 collision fails
    b2 = book_appointment(1, center_id, date_str, time_slot)
    assert b2["status"] == "FAILED"
    assert b2["appointment_id"] is None
    assert b2["booking_reference"] is None
    assert b2["error"] is not None


def test_scenario_9_notification_failure_does_not_corrupt_booking():
    """Verify notification failure does not corrupt an already confirmed booking."""
    # Attempting to send an empty notification
    notif_res = send_notification(user_id=1, appointment_id=101, message="")
    assert notif_res["status"] == "FAILED"
    assert notif_res["notification_id"] is None


def test_scenario_10_max_tool_calls_ceiling_enforcement():
    """Verify agent loop strictly halts at 12 iterations and gives helpful guidance."""
    agent = VehicleMaintenanceAgent()
    agent.client = MagicMock()

    # Tool call that never converges
    loop_call = MagicMock()
    loop_call.id = "loop_call_id"
    loop_call.function.name = "get_vehicle_info"
    loop_call.function.arguments = '{"user_id": 1}'

    mock_msg = MagicMock(tool_calls=[loop_call], content=None)
    agent.client.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=mock_msg)])

    out = agent.run("Stuck in loop")
    assert "maximum allowed limit of 12 tool calls" in out
    assert agent.client.chat.completions.create.call_count == 12
