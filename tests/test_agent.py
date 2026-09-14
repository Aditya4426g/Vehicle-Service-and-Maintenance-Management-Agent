"""
test_agent.py - Unit tests for agent.py.
Tests single-LLM enforcement (openai/gpt-oss-120b), tool schema registration,
deterministic execution dispatch, 12-call loop limit, and zero-fallback policy.
"""
from unittest.mock import patch, MagicMock
import pytest
from agent import (
    VehicleMaintenanceAgent,
    TOOL_SCHEMAS,
    execute_tool
)
from config import GROQ_MODEL, MAX_TOOL_CALLS

EXPECTED_TOOLS = [
    "get_vehicle_info",
    "get_service_history",
    "calculate_service_status",
    "geocode_location",
    "search_service_centers",
    "check_availability",
    "book_appointment",
    "cancel_appointment",
    "send_notification"
]


def test_agent_single_model_and_limit():
    """Verify strictly single model openai/gpt-oss-120b and max 12 tool loop limit."""
    agent = VehicleMaintenanceAgent()
    assert agent.model == "openai/gpt-oss-120b"
    assert agent.max_tool_calls == 12
    assert agent.model == GROQ_MODEL
    assert agent.max_tool_calls == MAX_TOOL_CALLS


def test_tool_schemas_completeness():
    """Verify all 9 tool schemas exist and have valid function schema structure."""
    registered_names = [t["function"]["name"] for t in TOOL_SCHEMAS]
    assert len(registered_names) == 9

    for tool_name in EXPECTED_TOOLS:
        assert tool_name in registered_names, f"Tool '{tool_name}' missing from TOOL_SCHEMAS"


def test_execute_tool_vehicle_info():
    """Verify execute_tool dispatch for get_vehicle_info."""
    res = execute_tool("get_vehicle_info", {"user_id": 1, "vehicle_name": "Tata Nexon"})
    assert "vehicle" in res
    assert res["vehicle"]["model"] == "Nexon"


def test_execute_tool_maintenance_calculation():
    """Verify execute_tool dispatch for calculate_service_status."""
    from datetime import date
    res = execute_tool("calculate_service_status", {
        "current_mileage": 9800,
        "last_service_mileage": 5000,
        "interval_km": 5000,
        "last_service_date": "2024-03-15",
        "interval_months": 6,
        "reference_date": date(2024, 9, 1)
    })
    assert res["status"] == "APPROACHING"
    assert res["remaining_km"] == 200


def test_execute_tool_booking_flow():
    """Verify execute_tool dispatch for availability, booking, and cancellation."""
    # 1. Check availability
    avail = execute_tool("check_availability", {"center_id": "osm_101", "date": "2026-11-01"})
    assert "available_slots" in avail
    assert len(avail["available_slots"]) > 0

    # 2. Book slot
    slot = avail["available_slots"][0]
    booking = execute_tool("book_appointment", {
        "vehicle_id": 1,
        "center_id": "osm_101",
        "date": "2026-11-01",
        "time": slot
    })
    assert booking["status"] == "SUCCESS"
    assert booking["booking_reference"].startswith("BK")

    # 3. Notification with returned appointment_id
    notif = execute_tool("send_notification", {
        "user_id": 1,
        "appointment_id": booking["appointment_id"],
        "message": "Appointment confirmed"
    })
    assert notif["status"] == "SENT"

    # 4. Cancel
    cancel = execute_tool("cancel_appointment", {"booking_reference": booking["booking_reference"]})
    assert cancel["status"] == "CANCELLED"


def test_execute_tool_unknown_name():
    """Verify execute_tool handles unknown functions gracefully."""
    res = execute_tool("unknown_fake_tool", {})
    assert "error" in res
    assert "Unknown tool" in res["error"]


def test_agent_unconfigured_message():
    """Verify agent returns informative message when API key is unset."""
    with patch("agent.GROQ_API_KEY", ""):
        agent = VehicleMaintenanceAgent()
        msg = agent.run("Is my service due?")
        assert "GROQ_API_KEY" in msg
        assert "openai/gpt-oss-120b" in msg


def test_agent_max_tool_limit_enforced():
    """Verify agent strictly terminates when hitting the 12 tool-call limit."""
    agent = VehicleMaintenanceAgent()
    agent.client = MagicMock()

    # Create mock tool call response that constantly loops
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_loop_1"
    mock_tool_call.function.name = "get_vehicle_info"
    mock_tool_call.function.arguments = '{"user_id": 1}'

    mock_msg = MagicMock()
    mock_msg.tool_calls = [mock_tool_call]
    mock_msg.content = None

    mock_choice = MagicMock()
    mock_choice.message = mock_msg

    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]

    agent.client.chat.completions.create.return_value = mock_resp

    result = agent.run("Loop test")
    assert "maximum allowed limit of 12 tool calls" in result
    # Verify API was called up to max limit and stopped
    assert agent.client.chat.completions.create.call_count == 12


def test_agent_zero_fallback_on_api_failure():
    """Verify agent does not switch models when Groq API fails."""
    agent = VehicleMaintenanceAgent()
    agent.client = MagicMock()
    agent.client.chat.completions.create.side_effect = Exception("Groq 503 Service Unavailable")

    result = agent.run("Hello")
    assert "Groq API Error" in result
    assert "No model fallback configured" in result
    assert "openai/gpt-oss-120b" in result
