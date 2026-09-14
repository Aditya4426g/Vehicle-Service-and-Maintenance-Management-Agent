"""
database.py - Python Database Layer for Supabase PostgreSQL.
Provides clean CRUD functions for vehicles, maintenance, appointments, and notifications.
Supports live Supabase client with local seed fallback for offline testing.
"""
from typing import Optional, List, Dict, Any
from config import SUPABASE_URL, SUPABASE_KEY

# Optional Supabase client initialization
_supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Warning: Failed to initialize Supabase client: {e}")
        _supabase_client = None

# In-memory local storage pre-populated with realistic seed data
# Ensures tests and offline development run reliably without network dependencies
_LOCAL_USERS: Dict[int, Dict[str, Any]] = {
    1: {
        "id": 1,
        "name": "Rahul",
        "email": "rahul@example.com",
        "phone": "+91 9876543210",
        "location": "Indiranagar, Bangalore"
    }
}

_LOCAL_VEHICLES: Dict[int, Dict[str, Any]] = {
    1: {
        "id": 1,
        "user_id": 1,
        "make": "Tata",
        "model": "Nexon",
        "variant": "XZ+ Petrol",
        "year": 2023,
        "registration_number": "KA-01-MJ-2023",
        "current_mileage": 9800,
        "last_service_date": "2024-03-15",
        "last_service_mileage": 5000
    }
}

_LOCAL_SERVICE_HISTORY: List[Dict[str, Any]] = [
    {
        "id": 1,
        "vehicle_id": 1,
        "service_date": "2023-09-10",
        "service_mileage": 1000,
        "service_type": "1st Free Inspection",
        "description": "General inspection, fluid top-up, wash",
        "cost": 0.0,
        "service_center": "ABC Motors Tata Authorized"
    },
    {
        "id": 2,
        "vehicle_id": 1,
        "service_date": "2024-03-15",
        "service_mileage": 5000,
        "service_type": "Periodic Maintenance Service",
        "description": "Engine oil change, oil filter replacement, brake inspection",
        "cost": 2850.0,
        "service_center": "XYZ Auto Care Service Center"
    }
]

_LOCAL_MAINTENANCE_SCHEDULES: Dict[int, Dict[str, Any]] = {
    1: {
        "id": 1,
        "vehicle_id": 1,
        "service_type": "Periodic Maintenance Service",
        "interval_km": 5000,
        "interval_months": 6,
        "last_service_mileage": 5000,
        "last_service_date": "2024-03-15"
    }
}

_LOCAL_SERVICE_CENTERS: Dict[str, Dict[str, Any]] = {
    "osm_101": {
        "id": 1,
        "center_id": "osm_101",
        "name": "ABC Motors Tata Authorized",
        "address": "12th Main Road, Indiranagar, Bangalore",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "phone": "+91 80 25251122"
    },
    "osm_102": {
        "id": 2,
        "center_id": "osm_102",
        "name": "XYZ Auto Care Service Center",
        "address": "80 Feet Road, Koramangala, Bangalore",
        "latitude": 12.9352,
        "longitude": 77.6245,
        "phone": "+91 80 41412233"
    },
    "osm_103": {
        "id": 3,
        "center_id": "osm_103",
        "name": "Prerana Motors Tata Service",
        "address": "Hosur Main Road, Kudlu Gate, Bangalore",
        "latitude": 12.8912,
        "longitude": 77.6411,
        "phone": "+91 80 67673344"
    }
}

_LOCAL_APPOINTMENTS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "vehicle_id": 1,
        "service_center_id": "osm_102",
        "appointment_date": "2024-03-15",
        "appointment_time": "10:00 AM",
        "service_type": "Periodic Maintenance Service",
        "status": "COMPLETED",
        "booking_reference": "BK09990"
    }
]

_LOCAL_NOTIFICATIONS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "user_id": 1,
        "appointment_id": 1,
        "notification_type": "BOOKING_CONFIRMATION",
        "message": "Your service appointment for Tata Nexon was confirmed for 15 Mar 2024 at 10:00 AM.",
        "status": "SENT"
    }
]

_appointment_id_counter = 100
_notification_id_counter = 100


def get_user(user_id: int = 1) -> Optional[Dict[str, Any]]:
    """Retrieve user details by user_id."""
    if _supabase_client:
        try:
            res = _supabase_client.table("users").select("*").eq("id", user_id).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            print(f"Supabase error in get_user: {e}")
    return _LOCAL_USERS.get(user_id)


def get_vehicle_info(user_id: int = 1, vehicle_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieve vehicle details matching user_id and optional vehicle name.
    Returns: {id, make, model, current_mileage, last_service_date, last_service_mileage, ...}
    """
    if _supabase_client:
        try:
            query = _supabase_client.table("vehicles").select("*").eq("user_id", user_id)
            res = query.execute()
            if res.data:
                if vehicle_name:
                    vname = vehicle_name.lower().strip()
                    for v in res.data:
                        full_name = f"{v.get('make', '')} {v.get('model', '')}".lower()
                        if vname in full_name or v.get('model', '').lower() in vname:
                            return v
                return res.data[0]
        except Exception as e:
            print(f"Supabase error in get_vehicle_info: {e}")

    # Local fallback search
    for v in _LOCAL_VEHICLES.values():
        if v["user_id"] == user_id:
            if vehicle_name:
                vname = vehicle_name.lower().strip()
                full_name = f"{v['make']} {v['model']}".lower()
                if vname in full_name or v["model"].lower() in vname:
                    return v
            else:
                return v
    return None


def get_vehicle_by_name(vehicle_name: str, user_id: int = 1) -> Optional[Dict[str, Any]]:
    """Retrieve vehicle specifically by name/model."""
    return get_vehicle_info(user_id=user_id, vehicle_name=vehicle_name)


def get_service_history(vehicle_id: int) -> List[Dict[str, Any]]:
    """Retrieve historical service records for a vehicle."""
    if _supabase_client:
        try:
            res = _supabase_client.table("service_history").select("*").eq("vehicle_id", vehicle_id).order("service_date").execute()
            if res.data:
                return res.data
        except Exception as e:
            print(f"Supabase error in get_service_history: {e}")

    return [s for s in _LOCAL_SERVICE_HISTORY if s["vehicle_id"] == vehicle_id]


def get_maintenance_schedule(vehicle_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve maintenance interval schedule for a vehicle."""
    if _supabase_client:
        try:
            res = _supabase_client.table("maintenance_schedules").select("*").eq("vehicle_id", vehicle_id).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            print(f"Supabase error in get_maintenance_schedule: {e}")

    return _LOCAL_MAINTENANCE_SCHEDULES.get(vehicle_id)


def get_appointments(vehicle_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Retrieve all appointments or filtered by vehicle_id."""
    if _supabase_client:
        try:
            query = _supabase_client.table("appointments").select("*")
            if vehicle_id:
                query = query.eq("vehicle_id", vehicle_id)
            res = query.execute()
            if res.data:
                return res.data
        except Exception as e:
            print(f"Supabase error in get_appointments: {e}")

    if vehicle_id:
        return [a for a in _LOCAL_APPOINTMENTS if a["vehicle_id"] == vehicle_id]
    return list(_LOCAL_APPOINTMENTS)


def create_appointment(
    vehicle_id: int,
    service_center_id: str,
    appointment_date: str,
    appointment_time: str,
    service_type: str,
    booking_reference: str
) -> Dict[str, Any]:
    """
    Create a new appointment with slot collision verification.
    Output Contract: {status: 'SUCCESS'|'FAILED', appointment_id, booking_reference, error}
    """
    global _appointment_id_counter

    # 1. Collision check: center + date + time
    existing = get_appointments()
    for appt in existing:
        if (
            appt["service_center_id"] == service_center_id
            and appt["appointment_date"] == appointment_date
            and appt["appointment_time"].upper() == appointment_time.upper()
            and appt.get("status") != "CANCELLED"
        ):
            return {
                "status": "FAILED",
                "appointment_id": None,
                "booking_reference": None,
                "error": f"Slot {appointment_time} on {appointment_date} at {service_center_id} is already booked."
            }

    # 2. Insert into Supabase if connected
    if _supabase_client:
        try:
            payload = {
                "vehicle_id": vehicle_id,
                "service_center_id": service_center_id,
                "appointment_date": appointment_date,
                "appointment_time": appointment_time,
                "service_type": service_type,
                "status": "CONFIRMED",
                "booking_reference": booking_reference
            }
            res = _supabase_client.table("appointments").insert(payload).execute()
            if res.data:
                return {
                    "status": "SUCCESS",
                    "appointment_id": res.data[0]["id"],
                    "booking_reference": booking_reference,
                    "error": None
                }
        except Exception as e:
            return {
                "status": "FAILED",
                "appointment_id": None,
                "booking_reference": None,
                "error": f"Database insertion failed: {e}"
            }

    # 3. Local fallback persistence
    _appointment_id_counter += 1
    new_appt = {
        "id": _appointment_id_counter,
        "vehicle_id": vehicle_id,
        "service_center_id": service_center_id,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "service_type": service_type,
        "status": "CONFIRMED",
        "booking_reference": booking_reference
    }
    _LOCAL_APPOINTMENTS.append(new_appt)
    return {
        "status": "SUCCESS",
        "appointment_id": new_appt["id"],
        "booking_reference": booking_reference,
        "error": None
    }


def cancel_appointment(booking_reference: str) -> Dict[str, Any]:
    """
    Cancel an appointment by booking_reference.
    Output Contract: {status: 'CANCELLED'|'NOT_FOUND', booking_reference}
    """
    if _supabase_client:
        try:
            res = _supabase_client.table("appointments").update({"status": "CANCELLED"}).eq("booking_reference", booking_reference).execute()
            if res.data:
                return {"status": "CANCELLED", "booking_reference": booking_reference}
            return {"status": "NOT_FOUND", "booking_reference": booking_reference}
        except Exception as e:
            print(f"Supabase error in cancel_appointment: {e}")

    for appt in _LOCAL_APPOINTMENTS:
        if appt["booking_reference"] == booking_reference:
            appt["status"] = "CANCELLED"
            return {"status": "CANCELLED", "booking_reference": booking_reference}

    return {"status": "NOT_FOUND", "booking_reference": booking_reference}


def create_notification(
    user_id: int,
    appointment_id: Optional[int],
    message: str,
    notification_type: str = "BOOKING_CONFIRMATION"
) -> Dict[str, Any]:
    """
    Create a notification record associated with an appointment.
    Output Contract: {status: 'SENT'|'FAILED', notification_id, message}
    """
    global _notification_id_counter

    if not message:
        return {"status": "FAILED", "notification_id": None, "message": "Notification message cannot be empty."}

    if _supabase_client:
        try:
            payload = {
                "user_id": user_id,
                "appointment_id": appointment_id,
                "notification_type": notification_type,
                "message": message,
                "status": "SENT"
            }
            res = _supabase_client.table("notifications").insert(payload).execute()
            if res.data:
                return {
                    "status": "SENT",
                    "notification_id": res.data[0]["id"],
                    "message": message
                }
        except Exception as e:
            return {"status": "FAILED", "notification_id": None, "message": f"Database notification insert failed: {e}"}

    _notification_id_counter += 1
    new_notif = {
        "id": _notification_id_counter,
        "user_id": user_id,
        "appointment_id": appointment_id,
        "notification_type": notification_type,
        "message": message,
        "status": "SENT"
    }
    _LOCAL_NOTIFICATIONS.append(new_notif)
    return {
        "status": "SENT",
        "notification_id": new_notif["id"],
        "message": message
    }


def update_vehicle_mileage(vehicle_id: int, new_mileage: int) -> Dict[str, Any]:
    """Update current mileage for a vehicle."""
    if new_mileage < 0:
        return {"status": "FAILED", "error": "Mileage cannot be negative"}

    if _supabase_client:
        try:
            res = _supabase_client.table("vehicles").update({"current_mileage": new_mileage}).eq("id", vehicle_id).execute()
            if res.data:
                return {"status": "SUCCESS", "vehicle_id": vehicle_id, "current_mileage": new_mileage}
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    if vehicle_id in _LOCAL_VEHICLES:
        _LOCAL_VEHICLES[vehicle_id]["current_mileage"] = new_mileage
        return {"status": "SUCCESS", "vehicle_id": vehicle_id, "current_mileage": new_mileage}

    return {"status": "FAILED", "error": "Vehicle not found"}
