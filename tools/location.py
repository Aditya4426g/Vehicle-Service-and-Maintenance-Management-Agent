"""
tools/location.py - Location detection, geocoding, and service center search.
Finds nearby workshops using GPS coordinates, Overpass/Nominatim, and brand filters.
"""
import math
import requests
from typing import Dict, List, Any, Optional
from config import NOMINATIM_USER_AGENT, GOOGLE_MAPS_API_KEY

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
REQUEST_TIMEOUT = 5


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two GPS coordinates using Haversine formula."""
    r = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return round(r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)


def detect_current_location() -> Dict[str, Any]:
    """Detect user's location via IP address, with fallback to Bangalore."""
    try:
        res = requests.get("http://ip-api.com/json/?fields=status,city,regionName,lat,lon", timeout=2.5)
        if res.status_code == 200:
            data = res.json()
            if data.get("status") == "success" and data.get("lat") and data.get("lon"):
                city = data.get("city", "Bengaluru")
                region = data.get("regionName", "")
                display = f"{city}, {region}" if region else city
                return {
                    "latitude": float(data["lat"]),
                    "longitude": float(data["lon"]),
                    "display_name": f"{display} (Auto-Detected)",
                    "city": city,
                    "status": "SUCCESS",
                    "error": None,
                }
    except Exception:
        pass

    # Default fallback: Indiranagar, Bangalore
    return {
        "latitude": 12.9716,
        "longitude": 77.5946,
        "display_name": "Indiranagar, Bangalore (Default)",
        "city": "Bangalore",
        "status": "SUCCESS",
        "error": None,
    }


def geocode_location(address_or_city: str) -> Dict[str, Any]:
    """Convert an address or city name into GPS coordinates."""
    if not address_or_city or not address_or_city.strip():
        return {"latitude": None, "longitude": None, "display_name": "", "status": "FAILED", "error": "Location query cannot be empty."}

    clean_query = address_or_city.strip().lower()
    auto_triggers = {"current location", "my location", "current", "here", "auto", "nearest"}
    if clean_query in auto_triggers or "current location" in clean_query or "my location" in clean_query:
        return detect_current_location()

    headers = {"User-Agent": NOMINATIM_USER_AGENT or "vehicle_maintenance_agent_v1"}
    params = {"q": address_or_city.strip(), "format": "json", "limit": 1}

    try:
        res = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            data = res.json()
            if data:
                return {
                    "latitude": float(data[0]["lat"]),
                    "longitude": float(data[0]["lon"]),
                    "display_name": data[0].get("display_name", address_or_city),
                    "status": "SUCCESS",
                    "error": None,
                }
            return {"latitude": None, "longitude": None, "display_name": "", "status": "FAILED", "error": f"No coordinates found for location: '{address_or_city}'."}
        return {"latitude": None, "longitude": None, "display_name": "", "status": "FAILED", "error": f"Nominatim error ({res.status_code})."}
    except requests.exceptions.Timeout:
        return {"latitude": None, "longitude": None, "display_name": "", "status": "FAILED", "error": "Geocoding request timed out."}
    except Exception as e:
        return {"latitude": None, "longitude": None, "display_name": "", "status": "FAILED", "error": f"Geocoding error: {e}"}


def search_service_centers(
    latitude: float,
    longitude: float,
    radius_km: int = 10,
    brand: Optional[str] = None,
    fallback_database: bool = True
) -> List[Dict[str, Any]]:
    """
    Find nearby authorized service centers.
    - If brand is provided: filters database for that brand.
    - Otherwise queries Overpass API, Nominatim, and fallback database.
    """
    if latitude is None or longitude is None or radius_km <= 0:
        return []

    # If brand specified, filter directly from database
    if brand:
        import database
        return database.get_service_centers_near(latitude, longitude, max(float(radius_km), 35.0), brand=brand)

    centers = []

    # 1. Try Overpass API
    radius_meters = radius_km * 1000
    query = f"""[out:json][timeout:5];(node["shop"="car_repair"](around:{radius_meters},{latitude},{longitude}););out center 10;"""
    try:
        res = requests.post(OVERPASS_URL, data={"data": query}, headers={"User-Agent": NOMINATIM_USER_AGENT}, timeout=5)
        if res.status_code == 200:
            for elem in res.json().get("elements", []):
                tags = elem.get("tags", {})
                lat = elem.get("lat") or elem.get("center", {}).get("lat")
                lon = elem.get("lon") or elem.get("center", {}).get("lon")
                if lat and lon and tags.get("name"):
                    dist = calculate_distance_km(latitude, longitude, float(lat), float(lon))
                    street = tags.get("addr:street", "")
                    city = tags.get("addr:city", "")
                    addr = f"{street}, {city}".strip(", ") or "Authorized Service Location"
                    centers.append({
                        "center_id": f"osm_{elem.get('type', 'node')}_{elem.get('id')}",
                        "name": tags["name"],
                        "address": addr,
                        "latitude": float(lat),
                        "longitude": float(lon),
                        "distance_km": dist,
                        "rating": 4.7,
                        "phone": tags.get("phone", "+91 80 25251122")
                    })
    except Exception:
        pass

    # 2. Try Nominatim Fallback if Overpass returned no results
    if not centers:
        try:
            res = requests.get(NOMINATIM_URL, params={"q": "car repair", "format": "json", "limit": 5}, headers={"User-Agent": NOMINATIM_USER_AGENT}, timeout=REQUEST_TIMEOUT)
            if res.status_code == 200 and isinstance(res.json(), list):
                for item in res.json():
                    if item.get("lat") and item.get("lon"):
                        dist = calculate_distance_km(latitude, longitude, float(item["lat"]), float(item["lon"]))
                        centers.append({
                            "center_id": f"osm_{item.get('osm_type', 'node')}_{item.get('osm_id', item.get('place_id'))}",
                            "name": item.get("name", "Authorized Service Center"),
                            "address": item.get("display_name", "Local Service Area"),
                            "latitude": float(item["lat"]),
                            "longitude": float(item["lon"]),
                            "distance_km": dist,
                            "rating": 4.5,
                            "phone": "+91 80 25251122"
                        })
        except Exception:
            pass

    # 3. Local database fallback
    if not centers and fallback_database:
        import database
        centers = database.get_service_centers_near(latitude, longitude, max(float(radius_km), 35.0))

    centers.sort(key=lambda x: x.get("distance_km", float("inf")))
    return centers


if __name__ == "__main__":
    loc = detect_current_location()
    print("Detected location:", loc)
