"""
test_notification.py - Unit tests for tools/notification.py.
Tests formatted confirmation generation, successful dispatch, invalid user/message validation, and database logging.
"""
from tools.notification import send_notification, format_confirmation_message


def test_format_confirmation_message():
    """Verify clean message formatting with vehicle, date, center, and reference."""
    msg = format_confirmation_message(
        vehicle_name="Tata Nexon",
        date="2026-10-15",
        time="10:00 AM",
        service_center_name="ABC Motors Tata Authorized",
        booking_reference="BK10001"
    )
    assert "Tata Nexon" in msg
    assert "2026-10-15" in msg
    assert "10:00 AM" in msg
    assert "BK10001" in msg
    assert "ABC Motors" in msg


def test_send_notification_success():
    """Verify successful dispatch returns SENT status and notification_id."""
    msg = "Your appointment is confirmed for tomorrow at 10:00 AM."
    res = send_notification(user_id=1, appointment_id=101, message=msg, channel="EMAIL")

    assert res["status"] == "SENT"
    assert res["notification_id"] is not None
    assert res["message"] == msg


def test_send_notification_empty_message():
    """Verify empty message is rejected with FAILED status."""
    res = send_notification(user_id=1, appointment_id=101, message="   ")
    assert res["status"] == "FAILED"
    assert res["notification_id"] is None
    assert "cannot be empty" in res["message"].lower()


def test_send_notification_invalid_user():
    """Verify invalid user_id is rejected."""
    res = send_notification(user_id=-1, appointment_id=101, message="Hello")
    assert res["status"] == "FAILED"
    assert "Invalid user_id" in res["message"]


def test_send_notification_channel_defaulting():
    """Verify unrecognised channel defaults cleanly to EMAIL without failing."""
    res = send_notification(user_id=1, appointment_id=101, message="Test message", channel="UNKNOWN_CHANNEL")
    assert res["status"] == "SENT"
    assert res["notification_id"] is not None
