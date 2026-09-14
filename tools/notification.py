"""
tools/notification.py - Notification and Confirmation Tool.
Handles logging and database persistence of appointment confirmations and service alerts.
Supports mock notification dispatch (Email / In-App) without requiring paid SMS gateways.
"""
from typing import Dict, Any, Optional
import database


def format_confirmation_message(
    vehicle_name: str,
    date: str,
    time: str,
    service_center_name: str,
    booking_reference: str
) -> str:
    """Helper to generate a clean, professional appointment confirmation message."""
    return (
        f"Your service appointment for {vehicle_name} is confirmed!\n"
        f"  Date: {date}\n"
        f"  Time: {time}\n"
        f"  Service Center: {service_center_name}\n"
        f"  Booking Reference: {booking_reference}"
    )


def send_notification(
    user_id: int,
    appointment_id: Optional[int],
    message: str,
    channel: str = "EMAIL"
) -> Dict[str, Any]:
    """
    Dispatch and log an appointment notification.

    Contract:
      {
        "status": "SENT" | "FAILED",
        "notification_id": int | None,
        "message": str
      }
    """
    # 1. Input validation
    if not user_id or user_id <= 0:
        return {
            "status": "FAILED",
            "notification_id": None,
            "message": "Notification failed: Invalid user_id."
        }

    if not message or not message.strip():
        return {
            "status": "FAILED",
            "notification_id": None,
            "message": "Notification failed: Message cannot be empty."
        }

    valid_channels = ["EMAIL", "IN_APP", "SMS", "MOCK"]
    selected_channel = channel.upper() if channel else "EMAIL"
    if selected_channel not in valid_channels:
        selected_channel = "EMAIL"

    # 2. Mock dispatch / console notification log
    print(f"\n[NOTIFICATION DISPATCH ({selected_channel})]")
    print(f"To User ID: {user_id} | Appointment ID: {appointment_id}")
    print(f"Content:\n{message}")
    print("-------------------------------------------\n")

    # 3. Persist notification to database layer
    db_res = database.create_notification(
        user_id=user_id,
        appointment_id=appointment_id,
        message=message.strip(),
        notification_type=f"BOOKING_{selected_channel}"
    )

    if db_res["status"] == "SENT":
        return {
            "status": "SENT",
            "notification_id": db_res["notification_id"],
            "message": message.strip()
        }
    else:
        return {
            "status": "FAILED",
            "notification_id": None,
            "message": db_res.get("message", "Database notification recording failed.")
        }


if __name__ == "__main__":
    print("--- Notification Tool Check ---")
    msg = format_confirmation_message(
        vehicle_name="Tata Nexon",
        date="2026-10-15",
        time="10:00 AM",
        service_center_name="ABC Motors Tata Authorized",
        booking_reference="BK10001"
    )
    result = send_notification(user_id=1, appointment_id=101, message=msg, channel="EMAIL")
    print(f"Result: {result}")
