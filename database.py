"""
database.py - Data access layer directly powered by Supabase PostgreSQL.
Manages users, vehicles, maintenance telemetry, appointments, and notifications.
"""
import math
import re
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from config import SUPABASE_URL, SUPABASE_KEY

# -----------------------------------------------------------------------------
# Supabase Client Initialization
# -----------------------------------------------------------------------------
_supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Notice: Supabase client initialization error: {e}")


def _sb(func, default=None):
    """Safely execute a Supabase database call with error handling."""
    if _supabase_client:
        try:
            return func()
        except Exception as e:
            print(f"Database operation error: {e}")
    return default


def _calc_dist(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in kilometers between two GPS coordinates using Haversine formula."""
    r = 6371.0  # Earth's radius in km
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2.0) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    return round(r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)), 2)


# -----------------------------------------------------------------------------
# User & Vehicle Query Functions
# -----------------------------------------------------------------------------
def get_user(user_id: int = 1) -> Optional[Dict[str, Any]]:
    """Fetch user profile details by ID from Supabase."""
    res = _sb(lambda: _supabase_client.table("users").select("*").eq("id", user_id).execute())
    if res and res.data:
        return res.data[0]
    return None


def get_user_vehicles(user_id: int = 1) -> List[Dict[str, Any]]:
    """Fetch all vehicles registered under a specific user ID."""
    res = _sb(lambda: _supabase_client.table("vehicles").select("*").eq("user_id", user_id).order("id").execute())
    if res and res.data:
        return res.data
    return []


def get_vehicle_by_id(vehicle_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single vehicle record by its unique database ID."""
    res = _sb(lambda: _supabase_client.table("vehicles").select("*").eq("id", vehicle_id).execute())
    if res and res.data:
        return res.data[0]
    return None


def get_vehicle_by_name(vehicle_name: str, user_id: int = 1) -> Optional[Dict[str, Any]]:
    """Find a user's vehicle by model, make, or name."""
    return get_vehicle_info(user_id, vehicle_name)


def get_vehicle_info(user_id: int = 1, vehicle_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Find vehicle by user ID and optional name, model, label, or registration number."""
    vehicles = get_user_vehicles(user_id=user_id)
    if not vehicles:
        return None
    # Default to first vehicle if no name provided
    if not vehicle_name:
        return vehicles[0]

    vname = str(vehicle_name).lower().strip()

    # Alias mapping for intuitive colloquial matching
    alias_map = {
        "punch": ["punch", "tata punch", "second car", "vehicle b", "vechile b", "car b"],
        "nexon": ["nexon", "tata nexon", "first car", "vehicle a", "vechile a", "car a"],
        "baleno": ["baleno", "maruti baleno", "suzuki baleno", "maruti suzuki baleno"],
        "creta": ["creta", "hyundai creta", "vehicle c", "vechile c"],
        "city": ["city", "honda city", "vehicle d", "vechile d"],
    }

    # Match aliases first
    for key, aliases in alias_map.items():
        if any(a in vname for a in aliases):
            for v in vehicles:
                full = f"{v.get('make', '')} {v.get('model', '')} {v.get('label', '')}".lower()
                if key in full or key in v.get("model", "").lower():
                    return v

    # Fallback to direct substring match
    for v in vehicles:
        full_name = f"{v.get('make', '')} {v.get('model', '')}".lower()
        if (
            vname in full_name
            or vname in v.get("model", "").lower()
            or vname == v.get("label", "").lower()
            or vname in v.get("registration_number", "").lower()
        ):
            return v
    return None


# -----------------------------------------------------------------------------
# Service History & Schedule Functions
# -----------------------------------------------------------------------------
def get_service_history(vehicle_id: int) -> List[Dict[str, Any]]:
    """Retrieve historical service logs for a vehicle from Supabase."""
    res = _sb(lambda: _supabase_client.table("service_history").select("*").eq("vehicle_id", vehicle_id).order("id").execute())
    if res and res.data:
        return res.data
    return []


def get_maintenance_schedule(vehicle_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve manufacturer maintenance intervals and targets for a vehicle."""
    res = _sb(lambda: _supabase_client.table("maintenance_schedules").select("*").eq("vehicle_id", vehicle_id).execute())
    if res and res.data:
        return res.data[0]
    return None


# -----------------------------------------------------------------------------
# Service Centers & Geospatial Search
# -----------------------------------------------------------------------------
def get_service_centers() -> List[Dict[str, Any]]:
    """Retrieve all authorized service centers from Supabase."""
    res = _sb(lambda: _supabase_client.table("service_centers").select("*").execute())
    if res and res.data:
        return res.data
    return []


def get_service_centers_near(latitude: float, longitude: float, radius_km: float = 30.0, brand: Optional[str] = None) -> List[Dict[str, Any]]:
    """Find and rank service centers near GPS coordinates, optionally filtered by vehicle brand."""
    centers = get_service_centers()
    
    # Filter by brand if specified
    if brand:
        b_low = brand.strip().lower()
        centers = [c for c in centers if b_low in c.get("brand", "").lower() or b_low in c.get("name", "").lower()]

    # Calculate distance for each service center
    matched = []
    for c in centers:
        if c.get("latitude") and c.get("longitude"):
            dist = _calc_dist(latitude, longitude, float(c["latitude"]), float(c["longitude"]))
            matched.append(dict(c, distance_km=dist))

    # Sort nearest first
    matched.sort(key=lambda x: x["distance_km"])
    nearby = [c for c in matched if c["distance_km"] <= radius_km]
    return nearby if nearby else matched[:3]


def get_authorized_service_centers(brand: str, city: Optional[str] = None, latitude: Optional[float] = None, longitude: Optional[float] = None, radius_km: float = 30.0) -> List[Dict[str, Any]]:
    """Convenience helper to retrieve authorized workshops by brand and location."""
    return get_service_centers_near(latitude or 12.9716, longitude or 77.5946, radius_km, brand)


# -----------------------------------------------------------------------------
# Appointments & Collision Management
# -----------------------------------------------------------------------------
def get_appointments(vehicle_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Retrieve service appointments, optionally filtered by vehicle."""
    if vehicle_id:
        res = _sb(lambda: _supabase_client.table("appointments").select("*").eq("vehicle_id", vehicle_id).order("id").execute())
    else:
        res = _sb(lambda: _supabase_client.table("appointments").select("*").order("id").execute())
    return res.data if (res and res.data) else []


def create_appointment(vehicle_id: int, service_center_id: str, appointment_date: str, appointment_time: str, service_type: str, booking_reference: str) -> Dict[str, Any]:
    """Create a new service appointment in Supabase, preventing slot double-booking."""
    # Step 1: Pre-check for existing active appointment in the same slot
    existing = _sb(
        lambda: _supabase_client.table("appointments")
        .select("id")
        .eq("service_center_id", service_center_id)
        .eq("appointment_date", appointment_date)
        .eq("appointment_time", appointment_time)
        .neq("status", "CANCELLED")
        .execute()
    )
    if existing and existing.data:
        return {
            "status": "FAILED",
            "appointment_id": None,
            "booking_reference": None,
            "error": f"Slot {appointment_time} on {appointment_date} at {service_center_id} is already booked."
        }

    # Step 2: Insert new confirmed appointment record
    payload = {
        "vehicle_id": vehicle_id,
        "service_center_id": service_center_id,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "service_type": service_type,
        "status": "CONFIRMED",
        "booking_reference": booking_reference,
    }

    try:
        res = _supabase_client.table("appointments").insert(payload).execute()
        if res and res.data:
            return {"status": "SUCCESS", "appointment_id": res.data[0]["id"], "booking_reference": booking_reference, "error": None}
    except Exception as e:
        err_msg = str(e).lower()
        if "duplicate key" in err_msg or "unique constraint" in err_msg:
            return {"status": "FAILED", "appointment_id": None, "booking_reference": None, "error": f"Slot {appointment_time} on {appointment_date} is already booked."}
        return {"status": "FAILED", "appointment_id": None, "booking_reference": None, "error": str(e)}

    return {"status": "FAILED", "appointment_id": None, "booking_reference": None, "error": "Database insert failed"}


def cancel_appointment(booking_reference: str) -> Dict[str, Any]:
    """Cancel an appointment by booking reference to release the slot."""
    if not booking_reference:
        return {"status": "NOT_FOUND", "booking_reference": ""}

    # Check if the booking reference exists
    check = _sb(lambda: _supabase_client.table("appointments").select("id").eq("booking_reference", booking_reference).execute())
    if check and check.data:
        _sb(lambda: _supabase_client.table("appointments").update({"status": "CANCELLED"}).eq("booking_reference", booking_reference).execute())
        return {"status": "CANCELLED", "booking_reference": booking_reference}
    return {"status": "NOT_FOUND", "booking_reference": booking_reference}


# -----------------------------------------------------------------------------
# Notifications
# -----------------------------------------------------------------------------
def create_notification(user_id: int, appointment_id: Optional[int], message: str, notification_type: str = "BOOKING_CONFIRMATION") -> Dict[str, Any]:
    """Record a sent SMS/Email notification event in Supabase."""
    if not message or not str(message).strip():
        return {"status": "FAILED", "notification_id": None, "message": "Notification message cannot be empty."}

    # Verify foreign key reference for appointment_id if provided
    valid_appt_id = None
    if appointment_id:
        check = _sb(lambda: _supabase_client.table("appointments").select("id").eq("id", appointment_id).execute())
        if check and check.data:
            valid_appt_id = appointment_id

    payload = {
        "user_id": user_id,
        "appointment_id": valid_appt_id,
        "notification_type": notification_type,
        "message": message.strip(),
        "status": "SENT",
    }
    res = _sb(lambda: _supabase_client.table("notifications").insert(payload).execute())
    notif_id = res.data[0]["id"] if (res and res.data) else None
    return {"status": "SENT", "notification_id": notif_id, "message": message.strip()}


# -----------------------------------------------------------------------------
# Telemetry & Service Updates
# -----------------------------------------------------------------------------
def update_vehicle_mileage(vehicle_id: int, new_mileage: int) -> Dict[str, Any]:
    """Update current odometer reading for a vehicle in Supabase."""
    if new_mileage < 0:
        return {"status": "FAILED", "error": "Mileage cannot be negative"}
    res = _sb(lambda: _supabase_client.table("vehicles").update({"current_mileage": int(new_mileage)}).eq("id", vehicle_id).execute())
    if res and res.data:
        return {"status": "SUCCESS", "vehicle_id": vehicle_id, "current_mileage": int(new_mileage)}
    veh = get_vehicle_by_id(vehicle_id)
    if veh:
        return {"status": "SUCCESS", "vehicle_id": vehicle_id, "current_mileage": int(new_mileage)}
    return {"status": "FAILED", "error": "Vehicle not found"}


def parse_date_string(date_str: str) -> str:
    """Parse natural language or formatted date strings into standard 'YYYY-MM-DD'."""
    if not date_str or not str(date_str).strip():
        return str(date.today())
    cleaned = str(date_str).strip().lower()
    if cleaned in ["today", "now"]:
        return str(date.today())

    # Remove ordinal suffixes (1st -> 1, 2nd -> 2, etc.)
    cleaned = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", cleaned)
    cleaned = " ".join(re.sub(r"[,/]", " ", cleaned).split())
    formats = ("%Y-%m-%d", "%d-%m-%Y", "%d %m %Y", "%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y")
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(str(date_str).strip()).strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD.")


def create_service_history(
    vehicle_id: int,
    service_date: str,
    service_mileage: int,
    service_type: str = "General Service",
    description: str = "Service completed",
    cost: Optional[float] = None,
    service_center: str = "Authorized Service Center"
) -> Dict[str, Any]:
    """Record a completed maintenance service in service_history table."""
    parsed_date = parse_date_string(service_date)
    record = {
        "vehicle_id": vehicle_id,
        "service_date": parsed_date,
        "service_mileage": service_mileage,
        "service_type": service_type or "General Service",
        "description": description or "Service completed",
        "cost": float(cost or 0.0),
        "service_center": service_center or "Authorized Service Center"
    }
    res = _sb(lambda: _supabase_client.table("service_history").insert(record).execute())
    if res and res.data:
        return {"status": "SUCCESS", "service_history": res.data[0]}
    return {"status": "SUCCESS", "service_history": record}


def update_service_cost(vehicle_id: int, cost: float, service_history_id: Optional[int] = None) -> Dict[str, Any]:
    """Update service cost/bill amount in service_history table."""
    try:
        cost_val = float(cost)
    except (ValueError, TypeError):
        return {"status": "FAILED", "error": "Invalid cost amount"}

    # Update by explicit service history ID if provided
    if service_history_id:
        res = _sb(lambda: _supabase_client.table("service_history").update({"cost": cost_val}).eq("id", service_history_id).execute())
        if res and res.data:
            return {"status": "SUCCESS", "service_history": res.data[0], "message": f"Updated service cost to ₹{cost_val:,.2f}."}

    # If no specific ID, update the most recent service record for this vehicle
    hist = get_service_history(vehicle_id)
    if hist:
        latest_id = hist[-1]["id"]
        res = _sb(lambda: _supabase_client.table("service_history").update({"cost": cost_val}).eq("id", latest_id).execute())
        if res and res.data:
            return {"status": "SUCCESS", "service_history": res.data[0], "message": f"Updated latest service cost to ₹{cost_val:,.2f}."}

    return {"status": "FAILED", "error": f"No service history found for vehicle {vehicle_id}."}


def update_vehicle_service_details(vehicle_id: int, last_service_date: str, last_service_mileage: int, current_mileage: Optional[int] = None) -> Dict[str, Any]:
    """Update vehicle last service stats and keep maintenance schedule synchronized."""
    parsed_date = parse_date_string(last_service_date)
    svc_mileage = int(last_service_mileage)
    curr_mileage = int(current_mileage) if current_mileage is not None else svc_mileage
    if curr_mileage < svc_mileage:
        curr_mileage = svc_mileage

    # Update vehicle table in Supabase
    update_data = {"last_service_date": parsed_date, "last_service_mileage": svc_mileage, "current_mileage": curr_mileage}
    res = _sb(lambda: _supabase_client.table("vehicles").update(update_data).eq("id", vehicle_id).execute())

    # Synchronize corresponding maintenance schedule
    sched = get_maintenance_schedule(vehicle_id) or {"interval_km": 5000, "interval_months": 6}
    update_maintenance_schedule(vehicle_id, sched.get("interval_km", 5000), svc_mileage, parsed_date, sched.get("interval_months", 6))

    if res and res.data:
        return {"status": "SUCCESS", "vehicle": res.data[0]}
    veh = get_vehicle_by_id(vehicle_id)
    if veh:
        return {"status": "SUCCESS", "vehicle": veh}
    return {"status": "FAILED", "error": "Vehicle not found"}


def update_maintenance_schedule(vehicle_id: int, interval_km: int, last_service_mileage: int, last_service_date: str, interval_months: int = 6) -> Dict[str, Any]:
    """Update or upsert maintenance schedule record for a vehicle."""
    parsed_date = parse_date_string(last_service_date)
    sched = {
        "id": vehicle_id,
        "vehicle_id": vehicle_id,
        "service_type": "Periodic Maintenance Service",
        "interval_km": interval_km,
        "interval_months": interval_months,
        "last_service_mileage": last_service_mileage,
        "last_service_date": parsed_date
    }
    _sb(lambda: _supabase_client.table("maintenance_schedules").upsert(sched).execute())
    return {"status": "SUCCESS", "schedule": sched}


def update_service_after_completion(
    vehicle_id: int,
    service_date: str,
    next_service_interval_km: Optional[int] = None,
    service_mileage: Optional[int] = None,
    service_type: str = "General Service",
    description: str = "Service completed",
    cost: Optional[float] = None,
    service_center: str = "Authorized Service Center"
) -> Dict[str, Any]:
    """Complete service workflow: updates vehicle stats, resets schedule, and logs history."""
    vehicle = get_vehicle_by_id(vehicle_id)
    if not vehicle:
        return {"status": "FAILED", "error": f"Vehicle with ID {vehicle_id} not found."}

    if next_service_interval_km is not None and int(next_service_interval_km) <= 0:
        return {"status": "FAILED", "error": "Next service interval must be greater than 0 km."}

    # Resolve service interval
    sched_curr = get_maintenance_schedule(vehicle_id) or {"interval_km": 5000, "interval_months": 6}
    interval_km = int(next_service_interval_km) if next_service_interval_km else sched_curr.get("interval_km", 5000)

    parsed_date_str = parse_date_string(service_date)
    curr_mil = int(vehicle.get("current_mileage", 0))
    svc_mil = curr_mil if (service_mileage is None or int(service_mileage) <= 0) else int(service_mileage)
    new_curr = max(curr_mil, svc_mil)

    # 1. Update vehicle record in Supabase
    _sb(lambda: _supabase_client.table("vehicles").update({"last_service_date": parsed_date_str, "last_service_mileage": svc_mil, "current_mileage": new_curr}).eq("id", vehicle_id).execute())

    # 2. Upsert maintenance schedule in Supabase
    sched_payload = {
        "id": vehicle_id,
        "vehicle_id": vehicle_id,
        "service_type": "Periodic Maintenance Service",
        "interval_km": interval_km,
        "interval_months": 6,
        "last_service_mileage": svc_mil,
        "last_service_date": parsed_date_str
    }
    _sb(lambda: _supabase_client.table("maintenance_schedules").upsert(sched_payload).execute())

    # 3. Add to service history log in Supabase
    create_service_history(vehicle_id, parsed_date_str, svc_mil, service_type, description, cost, service_center)

    # 4. Compute updated maintenance status
    from tools.maintenance import calculate_service_status
    status_calc = calculate_service_status(new_curr, svc_mil, interval_km, parsed_date_str, 6)

    v_name = f"{vehicle.get('make', '')} {vehicle.get('model', '')}".strip()
    return {
        "status": "SUCCESS",
        "vehicle_id": vehicle_id,
        "vehicle_name": v_name,
        "label": vehicle.get("label", ""),
        "service_date": parsed_date_str,
        "service_mileage": svc_mil,
        "last_service_date": parsed_date_str,
        "last_service_mileage": svc_mil,
        "next_service_interval_km": interval_km,
        "next_service_mileage": svc_mil + interval_km,
        "current_mileage": new_curr,
        "maintenance_status": status_calc.get("status", "NOT_DUE"),
        "remaining_km": status_calc.get("remaining_km", interval_km),
        "target_service_date": status_calc.get("target_service_date", ""),
        "message": f"Service updated successfully for {v_name}."
    }


# -----------------------------------------------------------------------------
# Garage Vehicle Management (Add / Delete)
# -----------------------------------------------------------------------------
def add_vehicle(
    user_id: int = 1,
    make: str = "Tata",
    model: str = "Harrier",
    registration_number: Optional[str] = None,
    current_mileage: int = 0,
    variant: Optional[str] = None,
    year: int = 2024,
    label: Optional[str] = None
) -> Dict[str, Any]:
    """Register a new vehicle into the user's garage in Supabase."""
    vehicles = get_user_vehicles(user_id)
    next_letter = chr(ord('A') + len(vehicles)) if len(vehicles) < 26 else str(len(vehicles) + 1)
    assigned_label = label or f"Vehicle {next_letter}"
    reg_num = registration_number.strip().upper() if registration_number else f"KA-0{len(vehicles)+1}-XY-1234"

    payload = {
        "user_id": user_id,
        "label": assigned_label,
        "make": make.strip().title(),
        "model": model.strip().title(),
        "variant": variant or "Standard",
        "year": year,
        "registration_number": reg_num,
        "current_mileage": current_mileage,
        "last_service_date": str(date.today()),
        "last_service_mileage": current_mileage
    }
    res = _sb(lambda: _supabase_client.table("vehicles").insert(payload).execute())
    inserted = res.data[0] if (res and res.data) else payload
    return {"status": "SUCCESS", "vehicle": inserted, "message": f"Added {payload['make']} {payload['model']} as {assigned_label}."}


def delete_vehicle(vehicle_identifier: Any, user_id: int = 1) -> Dict[str, Any]:
    """Remove a vehicle from the garage by name, label, or database ID."""
    matched = None
    if isinstance(vehicle_identifier, int) or (isinstance(vehicle_identifier, str) and vehicle_identifier.strip().isdigit()):
        vid = int(str(vehicle_identifier).strip())
        matched = get_vehicle_by_id(vid)

    if not matched and isinstance(vehicle_identifier, str):
        matched = get_vehicle_info(user_id, vehicle_identifier)

    if not matched:
        return {"status": "ERROR", "error": f"Vehicle '{vehicle_identifier}' not found."}

    vid = matched["id"]
    _sb(lambda: _supabase_client.table("vehicles").delete().eq("id", vid).execute())
    return {"status": "SUCCESS", "deleted_vehicle": matched, "message": f"Removed {matched['make']} {matched['model']}."}


# Standalone quick connection verification
if __name__ == "__main__":
    v_list = get_user_vehicles(1)
    c_list = get_service_centers()
    print(f"Supabase connected: Loaded {len(v_list)} vehicles and {len(c_list)} service centers.")
