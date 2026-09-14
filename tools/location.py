"""
tools/location.py - OpenStreetMap Geocoding and Service Center Search Tool.
Uses Nominatim for geocoding and Overpass API for discovering nearby service centers.
Calculates distance using the Haversine formula and returns stable center_ids.
"""
import math
from typing import Dict, List, Any, Optional
import requests
from config import NOMINATIM_USER_AGENT

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
REQUEST_TIMEOUT = 8  # seconds


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two geographic coordinates using the Haversine formula.
    Returns distance in kilometers rounded to 2 decimal places.
    """
    earth_radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(earth_radius_km * c, 2)


def geocode_location(address_or_city: str) -> Dict[str, Any]:
    """
    Geocode an address or city name into latitude and longitude using Nominatim.

    Contract:
      {
        "latitude": float | None,
        "longitude": float | None,
        "display_name": str,
        "status": "SUCCESS" | "FAILED",
        "error": str | None
      }
    """
    if not address_or_city or not address_or_city.strip():
        return {
            "latitude": None,
            "longitude": None,
            "display_name": "",
            "status": "FAILED",
            "error": "Location query cannot be empty."
        }

    headers = {
        "User-Agent": NOMINATIM_USER_AGENT or "vehicle_maintenance_agent_v1"
    }
    params = {
        "q": address_or_city.strip(),
        "format": "json",
        "limit": 1
    }

    try:
        response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            return {
                "latitude": None,
                "longitude": None,
                "display_name": "",
                "status": "FAILED",
                "error": f"Nominatim API error (status code {response.status_code})."
            }

        data = response.json()
        if not data:
            return {
                "latitude": None,
                "longitude": None,
                "display_name": "",
                "status": "FAILED",
                "error": f"No coordinates found for location: '{address_or_city}'."
            }

        first_match = data[0]
        return {
            "latitude": float(first_match["lat"]),
            "longitude": float(first_match["lon"]),
            "display_name": first_match.get("display_name", address_or_city),
            "status": "SUCCESS",
            "error": None
        }

    except requests.exceptions.Timeout:
        return {
            "latitude": None,
            "longitude": None,
            "display_name": "",
            "status": "FAILED",
            "error": "Geocoding request timed out."
        }
    except requests.exceptions.RequestException as e:
        return {
            "latitude": None,
            "longitude": None,
            "display_name": "",
            "status": "FAILED",
            "error": f"Geocoding network error: {str(e)}"
        }


def search_service_centers(
    latitude: float,
    longitude: float,
    radius_km: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for car repair and service centers within radius_km using Overpass API.

    Contract:
      list[{
        "center_id": str,
        "name": str,
        "address": str,
        "latitude": float,
        "longitude": float,
        "distance_km": float
      }]
    """
    if latitude is None or longitude is None or radius_km <= 0:
        return []

    # Overpass query radius is in meters
    radius_meters = radius_km * 1000

    # Overpass QL querying automotive repair/service nodes and ways
    query = f"""
    [out:json][timeout:10];
    (
      node["shop"="car_repair"](around:{radius_meters},{latitude},{longitude});
      node["amenity"="car_wash"](around:{radius_meters},{latitude},{longitude});
      way["shop"="car_repair"](around:{radius_meters},{latitude},{longitude});
    );
    out center 10;
    """

    try:
        response = requests.post(
            OVERPASS_URL,
            data={"data": query},
            headers={"User-Agent": NOMINATIM_USER_AGENT or "vehicle_maintenance_agent_v1"},
            timeout=REQUEST_TIMEOUT
        )
        if response.status_code != 200:
            print(f"Overpass API returned status {response.status_code}")
            return []

        data = response.json()
        elements = data.get("elements", [])
        centers = []

        for elem in elements:
            tags = elem.get("tags", {})
            name = tags.get("name")
            if not name:
                # Skip unnamed nodes to present high-quality results
                continue

            # Way elements have center lat/lon; node elements have lat/lon directly
            lat = elem.get("lat") or elem.get("center", {}).get("lat")
            lon = elem.get("lon") or elem.get("center", {}).get("lon")
            if lat is None or lon is None:
                continue

            # Build stable center_id from OSM element type and ID
            osm_type = elem.get("type", "node")
            osm_id = elem.get("id")
            center_id = f"osm_{osm_type}_{osm_id}"

            # Extract address fields if present
            street = tags.get("addr:street", "")
            city = tags.get("addr:city", "")
            address = f"{street}, {city}".strip(", ") if (street or city) else "Address details available on arrival"

            dist = calculate_distance_km(latitude, longitude, float(lat), float(lon))

            centers.append({
                "center_id": center_id,
                "name": name,
                "address": address,
                "latitude": float(lat),
                "longitude": float(lon),
                "distance_km": dist
            })

        # Sort by nearest distance
        centers.sort(key=lambda x: x["distance_km"])
        return centers

    except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
        print(f"Service center search failed: {e}")
        return []


if __name__ == "__main__":
    print("--- Testing Location Tool Offline/Mock Helper ---")
    dist = calculate_distance_km(12.9716, 77.5946, 12.9352, 77.6245)
    print(f"Distance between Indiranagar and Koramangala: {dist} km")
