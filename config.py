"""
config.py - Central configuration module.
Loads environment variables and sets strict system constants.
"""
import os
from dotenv import load_dotenv

# Load variables from .env file if present
load_dotenv()

# Strict single-LLM configuration (openai/gpt-oss-120b ONLY)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "openai/gpt-oss-120b"
MAX_TOOL_CALLS = 12

# Supabase PostgreSQL configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# OpenStreetMap Nominatim configuration
NOMINATIM_USER_AGENT = os.getenv("NOMINATIM_USER_AGENT", "vehicle_maintenance_agent_v1")

# Optional Google Maps / Places API configuration (if provided, enables live Google Places lookup)
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "") or os.getenv("GOOGLE_PLACES_API_KEY", "")

# Maintenance interval thresholds (in km and days)
APPROACHING_THRESHOLD_KM = 500
APPROACHING_THRESHOLD_DAYS = 30


def validate_config() -> dict:
    """
    Checks whether all essential configuration keys are set.
    Returns a dictionary summarizing the status of each key.
    """
    return {
        "groq_configured": bool(GROQ_API_KEY),
        "supabase_configured": bool(SUPABASE_URL and SUPABASE_KEY),
        "nominatim_configured": bool(NOMINATIM_USER_AGENT),
        "model": GROQ_MODEL,
        "max_tool_calls": MAX_TOOL_CALLS
    }


if __name__ == "__main__":
    print("--- Configuration Check ---")
    status = validate_config()
    for key, value in status.items():
        print(f"  {key}: {value}")
    if not status["groq_configured"]:
        print("Notice: GROQ_API_KEY is not set in .env yet (expected during initial setup).")
    if not status["supabase_configured"]:
        print("Notice: SUPABASE_URL / SUPABASE_KEY not set in .env yet (expected during initial setup).")
