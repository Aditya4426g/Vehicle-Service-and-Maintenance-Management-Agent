"""
config.py - Application configuration and settings.
Loads environment variables from .env and sets project defaults.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# AI Model Configuration (Groq)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "openai/gpt-oss-120b"
MAX_TOOL_CALLS = 12

# Supabase Database Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Location & Map APIs
NOMINATIM_USER_AGENT = os.getenv("NOMINATIM_USER_AGENT", "vehicle_maintenance_agent_v1")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "") or os.getenv("GOOGLE_PLACES_API_KEY", "")

# Maintenance thresholds (km and days before service is marked approaching)
APPROACHING_THRESHOLD_KM = 500
APPROACHING_THRESHOLD_DAYS = 30


def validate_config() -> dict:
    """Check if required API keys and settings are present."""
    return {
        "groq_configured": bool(GROQ_API_KEY),
        "supabase_configured": bool(SUPABASE_URL and SUPABASE_KEY),
        "nominatim_configured": bool(NOMINATIM_USER_AGENT),
        "model": GROQ_MODEL,
        "max_tool_calls": MAX_TOOL_CALLS,
    }


if __name__ == "__main__":
    print("Configuration Status:", validate_config())
