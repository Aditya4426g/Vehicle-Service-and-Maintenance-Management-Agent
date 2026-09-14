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
        "phone": "+91 80 25251122",
        "rating": 4.8
    },
    "osm_102": {
        "id": 2,
        "center_id": "osm_102",
        "name": "XYZ Auto Care Service Center",
        "address": "80 Feet Road, Koramangala, Bangalore",
        "latitude": 12.9352,
        "longitude": 77.6245,
        "phone": "+91 80 41412233",
        "rating": 4.7
    },
    "osm_103": {
        "id": 3,
        "center_id": "osm_103",
        "name": "Prerana Motors Tata Service",
        "address": "Hosur Main Road, Kudlu Gate, Bangalore",
        "latitude": 12.8912,
        "longitude": 77.6411,
        "phone": "+91 80 67673344",
        "rating": 4.6
    },
    "osm_udaipur_101": {
        "id": 4,
        "center_id": "osm_udaipur_101",
        "name": "Tata Motors Authorized Service - National Motors",
        "address": "NH 8, Near Pratap Nagar Chauraha, Transport Nagar, Udaipur, Rajasthan 313001",
        "latitude": 24.5550,
        "longitude": 73.6922,
        "phone": "+91 294 2490111",
        "rating": 4.8
    },
    "osm_udaipur_102": {
        "id": 5,
        "center_id": "osm_udaipur_102",
        "name": "Tata Motors Passenger Car Service - Mewar Motors",
        "address": "Madri Industrial Area, Road No. 3, Udaipur, Rajasthan 313003",
        "latitude": 24.5710,
        "longitude": 73.7380,
        "phone": "+91 294 2492345",
        "rating": 4.6
    },
    "osm_udaipur_103": {
        "id": 6,
        "center_id": "osm_udaipur_103",
        "name": "Tata Authorized Service Hub - City Center",
        "address": "Goverdhan Vilas, Sector 14, Udaipur, Rajasthan 313002",
        "latitude": 24.5420,
        "longitude": 73.6950,
        "phone": "+91 294 2487890",
        "rating": 4.5
    },
    "osm_jaipur_101": {
        "id": 7,
        "center_id": "osm_jaipur_101",
        "name": "Tata Motors Authorized Service - Roshan Motors",
        "address": "Tonk Road, Near Glass Factory, Jaipur, Rajasthan 302015",
        "latitude": 26.8500,
        "longitude": 75.8000,
        "phone": "+91 141 2701122",
        "rating": 4.7
    },
    "osm_jodhpur_101": {
        "id": 8,
        "center_id": "osm_jodhpur_101",
        "name": "Tata Motors Authorized Service - Marwar Motors",
        "address": "Pal Road, Heavy Industrial Area, Jodhpur, Rajasthan 342003",
        "latitude": 26.2600,
        "longitude": 73.0100,
        "phone": "+91 291 2741122",
        "rating": 4.6
    },
    "osm_delhi_101": {
        "id": 9,
        "center_id": "osm_delhi_101",
        "name": "Tata Motors Authorized Service - SAB Motors",
        "address": "B-1/E-23, Mathura Road, Mohan Cooperative Industrial Estate, New Delhi 110044",
        "latitude": 28.5200,
        "longitude": 77.2900,
        "phone": "+91 11 41671122",
        "rating": 4.8
    },
    "osm_gurgaon_101": {
        "id": 10,
        "center_id": "osm_gurgaon_101",
        "name": "Tata Motors Authorized Workshop - Arya Motors",
        "address": "Sector 14, Old Delhi Gurgaon Road, Gurugram, Haryana 122001",
        "latitude": 28.4700,
        "longitude": 77.0500,
        "phone": "+91 124 4561122",
        "rating": 4.7
    },
    "osm_mumbai_101": {
        "id": 11,
        "center_id": "osm_mumbai_101",
        "name": "Tata Motors Authorized Service - Wasan Motors",
        "address": "Swastik Park, Sion Trombay Road, Chembur, Mumbai, Maharashtra 400071",
        "latitude": 19.0550,
        "longitude": 72.8900,
        "phone": "+91 22 25221122",
        "rating": 4.7
    },
    "osm_pune_101": {
        "id": 12,
        "center_id": "osm_pune_101",
        "name": "Tata Motors Passenger Car Service - Concorde Motors",
        "address": "Wakdewadi, Shivajinagar, Pune, Maharashtra 411003",
        "latitude": 18.5400,
        "longitude": 73.8450,
        "phone": "+91 20 66011122",
        "rating": 4.7
    },
    "osm_ahmedabad_101": {
        "id": 13,
        "center_id": "osm_ahmedabad_101",
        "name": "Tata Motors Authorized Service - Cargo Motors",
        "address": "Near YMCA Club, S.G. Highway, Makarba, Ahmedabad, Gujarat 380051",
        "latitude": 23.0100,
        "longitude": 72.5000,
        "phone": "+91 79 40011122",
        "rating": 4.8
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


def get_service_centers() -> List[Dict[str, Any]]:
    """Retrieve all authorized service centers."""
    if _supabase_client:
        try:
            res = _supabase_client.table("service_centers").select("*").execute()
            if res.data:
                return res.data
        except Exception as e:
            print(f"Supabase error in get_service_centers: {e}")
    return list(_LOCAL_SERVICE_CENTERS.values())


def get_service_centers_near(latitude: float, longitude: float, radius_km: float = 30.0) -> List[Dict[str, Any]]:
    """Retrieve service centers sorted by Haversine distance from coordinates."""
    import math

    def _calc_dist(lat1, lon1, lat2, lon2):
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2.0) ** 2
            + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return round(R * c, 2)

    centers = get_service_centers()
    matched = []
    for c in centers:
        c_lat = c.get("latitude")
        c_lon = c.get("longitude")
        if c_lat is not None and c_lon is not None:
            dist = _calc_dist(latitude, longitude, float(c_lat), float(c_lon))
            item = dict(c)
            item["distance_km"] = dist
            matched.append(item)

    matched.sort(key=lambda x: x["distance_km"])
    within_radius = [c for c in matched if c["distance_km"] <= radius_km]
    if within_radius:
        return within_radius

    # If no centers exist within the strict radius, always return top 2 closest centers
    return matched[:2]


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
