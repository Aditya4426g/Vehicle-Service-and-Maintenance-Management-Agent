"""
test_location.py - Unit tests for tools/location.py.
Uses mocked API responses to deterministically test geocoding, radius search, distance math, and timeouts.
"""
from unittest.mock import patch, MagicMock
import requests
import pytest
from tools.location import (
    calculate_distance_km,
    geocode_location,
    search_service_centers
)


def test_calculate_distance_km():
    """Verify Haversine distance between Bangalore Indiranagar and Koramangala (~5.2 km)."""
    # Indiranagar: 12.9716, 77.5946; Koramangala: 12.9352, 77.6245
    distance = calculate_distance_km(12.9716, 77.5946, 12.9352, 77.6245)
    assert 4.5 <= distance <= 6.0
    # Same point distance should be 0.0
    assert calculate_distance_km(12.9716, 77.5946, 12.9716, 77.5946) == 0.0


@patch("tools.location.requests.get")
def test_geocode_location_success(mock_get):
    """Verify successful geocoding with Nominatim mock."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "lat": "12.9715987",
            "lon": "77.5945627",
            "display_name": "Bengaluru, Bangalore Urban, Karnataka, India"
        }
    ]
    mock_get.return_value = mock_resp

    res = geocode_location("Bangalore")
    assert res["status"] == "SUCCESS"
    assert res["latitude"] == pytest.approx(12.9715987)
    assert res["longitude"] == pytest.approx(77.5945627)
    assert "Bengaluru" in res["display_name"]
    assert res["error"] is None


@patch("tools.location.requests.get")
def test_geocode_location_empty_result(mock_get):
    """Verify geocoding when location query yields no results."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = []
    mock_get.return_value = mock_resp

    res = geocode_location("UnknownPlaceXYZ123")
    assert res["status"] == "FAILED"
    assert res["latitude"] is None
    assert "No coordinates found" in res["error"]


def test_geocode_location_empty_input():
    """Verify empty or whitespace string input."""
    res = geocode_location("   ")
    assert res["status"] == "FAILED"
    assert "cannot be empty" in res["error"]


@patch("tools.location.requests.get")
def test_geocode_location_timeout(mock_get):
    """Verify graceful handling of API request timeout."""
    mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

    res = geocode_location("Bangalore")
    assert res["status"] == "FAILED"
    assert "timed out" in res["error"]


@patch("tools.location.requests.post")
def test_search_service_centers_success(mock_post):
    """Verify Overpass API parsing, stable center_id, and distance sorting."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "elements": [
            {
                "type": "node",
                "id": 1234567,
                "lat": 12.9720,
                "lon": 77.5950,
                "tags": {
                    "name": "ABC Motors Tata Authorized",
                    "addr:street": "12th Main Road",
                    "addr:city": "Bangalore"
                }
            },
            {
                "type": "node",
                "id": 7654321,
                "lat": 12.9800,
                "lon": 77.6000,
                "tags": {
                    "name": "XYZ Auto Care Service Center",
                    "addr:street": "80 Feet Road",
                    "addr:city": "Bangalore"
                }
            }
        ]
    }
    mock_post.return_value = mock_resp

    centers = search_service_centers(12.9716, 77.5946, radius_km=5)
    assert len(centers) == 2

    # Check stable center_id contract
    assert centers[0]["center_id"] == "osm_node_1234567"
    assert centers[0]["name"] == "ABC Motors Tata Authorized"
    assert "12th Main Road" in centers[0]["address"]
    assert centers[0]["distance_km"] < centers[1]["distance_km"]


@patch("tools.location.requests.get")
@patch("tools.location.requests.post")
def test_search_service_centers_api_failure(mock_post, mock_get):
    """Verify Overpass API failure returns empty list without crashing when fallbacks fail."""
    mock_post.side_effect = requests.exceptions.RequestException("Overpass 504 Gateway Timeout")
    mock_get.side_effect = requests.exceptions.RequestException("Nominatim network timeout")

    centers = search_service_centers(12.9716, 77.5946, radius_km=5, fallback_database=False)
    assert centers == []


@patch("tools.location.requests.get")
@patch("tools.location.requests.post")
def test_search_service_centers_live_nominatim_fallback(mock_post, mock_get):
    """Verify live Nominatim search fallback when Overpass times out."""
    mock_post.side_effect = requests.exceptions.Timeout("Overpass timeout")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "osm_type": "node",
            "osm_id": 12402760709,
            "name": "Tata Motor",
            "lat": "24.5549",
            "lon": "73.6921",
            "display_name": "Tata Motor, NH 8, Udaipur, Rajasthan"
        }
    ]
    mock_get.return_value = mock_resp

    centers = search_service_centers(24.5787, 73.6862, radius_km=30)
    assert len(centers) >= 1
    assert any("Tata" in c["name"] for c in centers)


def test_search_service_centers_invalid_coords():
    """Verify invalid coordinates return empty list immediately."""
    assert search_service_centers(None, None) == []
    assert search_service_centers(12.9716, 77.5946, radius_km=-5) == []
