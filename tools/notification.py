"""
tools/notification.py - Notification and confirmation dispatch tool.
Logs notifications to the database and dispatches live email alerts via Gmail SMTP.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import database

# Load environment variables from .env
load_dotenv()


def format_confirmation_message(
    vehicle_name: str,
    date: str,
    time: str,
    service_center_name: str,
    booking_reference: str
) -> str:
    """Create a human-readable confirmation message for a booked service appointment."""
    return (
        f"Your service appointment for {vehicle_name} is confirmed!\n"
        f"  Date: {date}\n"
        f"  Time: {time}\n"
        f"  Service Center: {service_center_name}\n"
        f"  Booking Reference: {booking_reference}"
    )


def _send_email_via_gmail(message: str, recipient_email: Optional[str] = None) -> bool:
    """Send live email notification via Gmail SMTP using credentials from .env."""
    sender_email = os.getenv("GMAIL_SENDER_EMAIL", "").strip()
    app_password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    
    # Select target recipient (explicit arg -> .env recipient -> sender -> default)
    target_email = (recipient_email or os.getenv("GMAIL_RECIPIENT_EMAIL", "") or sender_email or "jaxiver377@gmail.com").strip()

    # Skip if credentials are not configured in .env
    if not (sender_email and app_password):
        print("Notice: GMAIL_SENDER_EMAIL or GMAIL_APP_PASSWORD not set. Skipping live email.")
        return True

    try:
        # Build MIME email message
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = target_email
        msg["Subject"] = "Vehicle Service Appointment Confirmation - AutoCare AI"
        msg.attach(MIMEText(message, "plain"))

        # Connect to Gmail SMTP on port 587 with TLS
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(msg)
        print(f"[SUCCESS] Confirmation email successfully sent to {target_email}")
        return True
    except Exception as e:
        print(f"Notice: Email delivery error: {e}")
        return False


def send_notification(
    user_id: int,
    appointment_id: Optional[int],
    message: str,
    channel: str = "EMAIL",
    recipient_email: Optional[str] = None
) -> Dict[str, Any]:
    """Send a notification via email and log it to the database for audit tracking."""
    # Validate required input parameters
    if not user_id or user_id <= 0:
        return {"status": "FAILED", "notification_id": None, "message": "Invalid user_id."}
    if not message or not str(message).strip():
        return {"status": "FAILED", "notification_id": None, "message": "Notification message cannot be empty."}

    # Normalize channel name (EMAIL, SMS, IN_APP, MOCK)
    channel_type = channel.upper() if channel in {"EMAIL", "IN_APP", "SMS", "MOCK"} else "EMAIL"

    # Dispatch email if channel is EMAIL
    if channel_type == "EMAIL":
        user = database.get_user(user_id)
        db_email = user.get("email") if (user and "@example.com" not in user.get("email", "")) else None
        target_email = recipient_email or os.getenv("GMAIL_RECIPIENT_EMAIL") or db_email or os.getenv("GMAIL_SENDER_EMAIL", "jaxiver377@gmail.com")
        _send_email_via_gmail(message.strip(), target_email)

    # Persist the notification event record into the database
    res = database.create_notification(
        user_id=user_id,
        appointment_id=appointment_id,
        message=message.strip(),
        notification_type=f"BOOKING_{channel_type}"
    )
    return res


# Quick standalone test
if __name__ == "__main__":
    msg = format_confirmation_message("Tata Nexon", "2026-10-15", "10:00 AM", "ABC Motors", "BK10001")
    print(send_notification(1, 101, msg, channel="MOCK"))
