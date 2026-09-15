"""
tools/location.py - Location detection, geocoding, and service center search.
Finds nearby workshops using GPS coordinates and brand filters.
"""
import math
import requests
from typing import Dict, List, Any, Optional
from config import NOMINATIM_USER_AGENT, GOOGLE_MAPS_API_KEY

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
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
        return {"latitude": None, "longitude": None, "display_name": "", "status": "FAILED", "error": "Query cannot be empty."}

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
        return {"latitude": None, "longitude": None, "display_name": "", "status": "FAILED", "error": f"Location '{address_or_city}' not found."}
    except Exception as e:
        return {"latitude": None, "longitude": None, "display_name": "", "status": "FAILED", "error": f"Geocoding error: {e}"}


def search_service_centers(
    latitude: float,
    longitude: float,
    radius_km: int = 10,
    brand: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Find nearby authorized service centers sorted by distance.
    If brand is provided, filters strictly for that vehicle brand.
    """
    if latitude is None or longitude is None:
        return []

    # Local database search with brand filter (primary source)
    import database
    centers = database.get_service_centers_near(
        latitude=latitude,
        longitude=longitude,
        radius_km=max(float(radius_km), 35.0),
        brand=brand
    )
    return centers


if __name__ == "__main__":
    loc = detect_current_location()
    print("Detected location:", loc)
    centers = search_service_centers(loc["latitude"], loc["longitude"], radius_km=15, brand="Tata")
    print(f"Found {len(centers)} service centers.")
