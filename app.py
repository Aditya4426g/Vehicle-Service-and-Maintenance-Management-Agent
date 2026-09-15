"""
app.py - Simple, High-Visibility Automotive Telemetry Dashboard & AI Maintenance Assistant.
Features Side Navbar Navigation for effortless switching between Assistant, Telemetry, and Appointments.
Single-Agent architecture powered exclusively by Groq and openai/gpt-oss-120b.
"""
from datetime import date
from typing import Dict, Any, Optional
import re
import streamlit as st

from config import GROQ_MODEL, MAX_TOOL_CALLS, validate_config
from agent import VehicleMaintenanceAgent
import database
from tools.maintenance import calculate_service_status
from tools.location import geocode_location, search_service_centers, detect_current_location


def sanitize_chat_message(text: str) -> str:
    """Strip personal organization IDs, raw dictionaries, and token metrics from chat display."""
    if not isinstance(text, str):
        return text

    # Check for leaked Groq rate limit dictionary or message
    if "tokens per day" in text.lower() or "org_" in text or "rate_limit_exceeded" in text:
        wait_match = re.search(r"try again in ([\d\w\.]+)", text, re.IGNORECASE)
        retry_msg = f" Please try again in {wait_match.group(1)}." if wait_match else " Please try again in a few moments."
        return f"Rate limit reached (429). The AI service is temporarily busy.{retry_msg} (Strict zero-fallback policy: openai/gpt-oss-120b only)."

    # Strip any organization IDs, API keys, and billing URLs
    scrubbed = re.sub(r"org_[a-zA-Z0-9_-]+", "[REDACTED_ORG]", text)
    scrubbed = re.sub(r"gsk_[a-zA-Z0-9_-]+", "[REDACTED_KEY]", scrubbed)
    scrubbed = re.sub(r"https://console\.groq\.com\S*", "", scrubbed)
    return scrubbed

# Page configuration
st.set_page_config(
    page_title="AutoCare AI - Vehicle Maintenance Assistant",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# High-Visibility, Clean & Simple Design System (CSS)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #0F172A;
    }

    /* Clean, high-contrast header */
    .app-header {
        padding: 0.5rem 0 1rem 0;
        border-bottom: 2px solid #E2E8F0;
        margin-bottom: 1.25rem;
    }
    .main-title {
        font-family: 'Outfit', sans-serif;
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #1E3A8A;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .sub-title {
        color: #94A3B8;
        font-size: 0.95rem;
        font-weight: 500;
        margin-top: 0.3rem;
    }

    /* Sleek, Compact Side Navbar Radio Styling */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] {
        background-color: #F8FAFC !important;
        border: 1.5px solid #CBD5E1 !important;
        border-radius: 8px !important;
        padding: 0.45rem 0.75rem !important;
        cursor: pointer !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        color: #1E293B !important;
        margin-bottom: 0.2rem !important;
        transition: all 0.15s ease !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover {
        background-color: #EFF6FF !important;
        border-color: #2563EB !important;
        color: #1D4ED8 !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
        background-color: #EFF6FF !important;
        border-color: #2563EB !important;
        border-width: 2px !important;
        color: #1D4ED8 !important;
        font-weight: 700 !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
        display: none !important;
    }

    /* High-contrast, easy-to-read cards */
    .info-card {
        background: #FFFFFF;
        border: 1.5px solid #CBD5E1;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
    }

    /* Status Badges with crisp contrast */
    .status-badge {
        display: inline-block;
        padding: 0.35rem 0.85rem;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 0.02em;
    }
    .badge-approaching {
        background-color: #FEF3C7;
        color: #92400E;
        border: 1.5px solid #F59E0B;
    }
    .badge-due {
        background-color: #FEE2E2;
        color: #991B1B;
        border: 1.5px solid #EF4444;
    }
    .badge-ok {
        background-color: #D1FAE5;
        color: #065F46;
        border: 1.5px solid #10B981;
    }

    /* Modern Appointment Voucher Cards (Unified Container with Integrated Actions) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.voucher-header) {
        background: #1E293B !important;
        border: 1.5px solid #334155 !important;
        border-radius: 14px !important;
        padding: 0.75rem 1rem !important;
        margin-bottom: 1.25rem !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25) !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.voucher-header):hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(59, 130, 246, 0.2) !important;
        border-color: #475569 !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.badge-confirmed) {
        border-left: 5px solid #10B981 !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.badge-cancelled) {
        border-left: 5px solid #EF4444 !important;
        opacity: 0.88;
    }
    .voucher-card {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0.25rem 0 !important;
        margin: 0 !important;
    }
    .voucher-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #334155;
        padding-bottom: 0.75rem;
        margin-bottom: 0.9rem;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    .voucher-ref {
        font-family: 'Outfit', sans-serif;
        font-size: 1.18rem;
        font-weight: 700;
        color: #60A5FA !important;
        letter-spacing: 0.02em;
    }
    .voucher-details-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 0.75rem;
        margin-bottom: 0.25rem;
    }
    .voucher-chip {
        background: #0F172A;
        border: 1px solid #334155;
        border-radius: 9px;
        padding: 0.65rem 0.85rem;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 84px;
    }
    .voucher-chip-title {
        color: #94A3B8;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.2rem;
    }
    .voucher-chip-val {
        color: #F8FAFC;
        font-size: 0.92rem;
        font-weight: 600;
        line-height: 1.35;
    }
    .voucher-chip-sub {
        color: #94A3B8;
        font-size: 0.78rem;
        margin-top: 0.2rem;
    }
    .badge-confirmed {
        background: rgba(16, 185, 129, 0.2) !important;
        color: #34D399 !important;
        border: 1.5px solid rgba(52, 211, 153, 0.5) !important;
        padding: 0.3rem 0.8rem !important;
        border-radius: 9999px !important;
        font-size: 0.82rem !important;
        font-weight: 700 !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 0.35rem !important;
    }
    .badge-cancelled {
        background: rgba(239, 68, 68, 0.18) !important;
        color: #F87171 !important;
        border: 1.5px solid rgba(248, 113, 113, 0.45) !important;
        padding: 0.3rem 0.8rem !important;
        border-radius: 9999px !important;
        font-size: 0.82rem !important;
        font-weight: 700 !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 0.35rem !important;
    }

    /* Quick Action Buttons */
    div[data-testid="stHorizontalBlock"] .stButton > button {
        border: 1.5px solid #CBD5E1 !important;
        background-color: #F8FAFC !important;
        color: #1E293B !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        transition: all 0.15s ease !important;
    }
    div[data-testid="stHorizontalBlock"] .stButton > button:hover {
        border-color: #2563EB !important;
        background-color: #EFF6FF !important;
        color: #1D4ED8 !important;
    }

    /* Fixed bottom container spacing */
    .block-container {
        padding-bottom: 120px !important;
        max-width: 1200px;
    }

    /* High visibility chat input */
    [data-testid="stChatInput"] {
        border-radius: 14px !important;
        border: 2px solid #94A3B8 !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08) !important;
        background-color: #FFFFFF !important;
    }
    [data-testid="stChatInput"]:focus-within {
        border-color: #2563EB !important;
    }

    /* Global scrollbar and width protection - NO horizontal scrolling anywhere */
    html, body, [data-testid="stAppViewContainer"], .main, .block-container {
        overflow-x: hidden !important;
        max-width: 100% !important;
    }

    /* Fixed sidebar width - applied ONLY to the outer section */
    section[data-testid="stSidebar"] {
        width: 340px !important;
        min-width: 340px !important;
        max-width: 340px !important;
        overflow-x: hidden !important;
    }

    /* Inner sidebar containers fit 100% without overflowing */
    [data-testid="stSidebarContent"],
    [data-testid="stSidebarUserContent"] {
        width: 100% !important;
        max-width: 100% !important;
        min-width: 0 !important;
        box-sizing: border-box !important;
        overflow-x: hidden !important;
    }

    /* Metrics visible with clean formatting */
    [data-testid="stMetricValue"], 
    [data-testid="stMetricValue"] > div,
    [data-testid="stMetricLabel"],
    [data-testid="stMetricLabel"] > div {
        overflow: visible !important;
        text-overflow: unset !important;
        white-space: nowrap !important;
    }
</style>
""", unsafe_allow_html=True)

def get_welcome_message(v: Dict[str, Any]) -> str:
    """Generate dynamic greeting tailored to the selected vehicle."""
    car_name = f"{v.get('make', '')} {v.get('model', '')}".strip()
    return (
        f"👋 **Hello Rahul!** How can I assist you with your **{car_name}** today?\n\n"
        "• **Check Maintenance Status**: Ask if service is due or approaching.\n"
        "• **Locate Service Centers**: Find authorized workshops near you.\n"
        "• **Book Appointments**: Check slot availability and reserve a time."
    )


# Initialize Agent in session state
if "agent" not in st.session_state:
    st.session_state.agent = VehicleMaintenanceAgent()

# Automatically detect user's current location
if "user_location" not in st.session_state:
    st.session_state.user_location = detect_current_location()

# Multi-Vehicle Support
user_vehicles = database.get_user_vehicles(user_id=1)
if not user_vehicles:
    user_vehicles = [
        database.get_vehicle_info(user_id=1) or {
            "id": 1,
            "label": "Vehicle A",
            "make": "Tata",
            "model": "Nexon",
            "variant": "XZ+ Petrol",
            "year": 2023,
            "registration_number": "KA-01-MJ-2023",
            "current_mileage": 9800,
            "last_service_date": "2024-03-15",
            "last_service_mileage": 5000
        }
    ]

# Multi-Vehicle Selection Options
vehicle_map = {}
for idx, v in enumerate(user_vehicles):
    lbl = v.get("label") or f"Vehicle {idx+1}"
    vehicle_map[f"{lbl}: {v['make']} {v['model']}"] = v["id"]

if "selected_vehicle_id" not in st.session_state:
    st.session_state.selected_vehicle_id = user_vehicles[0]["id"]
if "last_active_vehicle_id" not in st.session_state:
    st.session_state.last_active_vehicle_id = st.session_state.selected_vehicle_id

initial_active_v = next((v for v in user_vehicles if v["id"] == st.session_state.selected_vehicle_id), user_vehicles[0])

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": get_welcome_message(initial_active_v)
        }
    ]

# ==============================================================================
# SIDEBAR - Side Navbar Navigation & Vehicle Profile
# ==============================================================================
with st.sidebar:
    st.markdown("""
    <style>
        /* Exact sidebar width (335px) on outer section only */
        section[data-testid="stSidebar"] {
            width: 335px !important;
            min-width: 335px !important;
            max-width: 335px !important;
            overflow: hidden !important;
        }
        /* Inner containers fit 100% with NO horizontal or vertical scroll */
        [data-testid="stSidebarContent"],
        [data-testid="stSidebarUserContent"] {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
            padding: 0.65rem 0.85rem !important;
            scrollbar-width: none !important;
            -ms-overflow-style: none !important;
        }
        [data-testid="stSidebarContent"]::-webkit-scrollbar {
            display: none !important;
        }
        [data-testid="stSidebar"] * {
            box-sizing: border-box !important;
            max-width: 100% !important;
        }
        /* Clean typography and proper heading spacing without overlap */
        [data-testid="stSidebar"] h1 {
            font-size: 1.35rem !important;
            margin: 0.25rem 0 0.6rem 0 !important;
            padding: 0 !important;
            line-height: 1.3 !important;
        }
        [data-testid="stSidebar"] h3 {
            font-size: 1.02rem !important;
            margin: 0.6rem 0 0.35rem 0 !important;
            padding: 0 !important;
            line-height: 1.3 !important;
        }
        [data-testid="stSidebar"] h4 {
            font-size: 0.92rem !important;
            margin: 0.5rem 0 0.3rem 0 !important;
            padding: 0 !important;
            line-height: 1.3 !important;
        }
        [data-testid="stSidebar"] hr {
            margin: 0.45rem 0 !important;
        }
        /* Sleek, compact navigation buttons */
        [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {
            display: flex;
            flex-direction: column;
            gap: 0.15rem;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] {
            background-color: #F8FAFC !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 6px !important;
            padding: 0.28rem 0.55rem !important;
            cursor: pointer !important;
            font-weight: 600 !important;
            font-size: 0.85rem !important;
            color: #1E293B !important;
            margin-bottom: 0.1rem !important;
            transition: all 0.15s ease !important;
            width: 100% !important;
            display: flex !important;
            align-items: center !important;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover {
            background-color: #EFF6FF !important;
            border-color: #2563EB !important;
            color: #1D4ED8 !important;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
            background-color: #EFF6FF !important;
            border-color: #2563EB !important;
            border-width: 2px !important;
            color: #1D4ED8 !important;
            font-weight: 700 !important;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
            display: none !important;
        }
        /* Ensure selectbox text and tooltips fit cleanly */
        [data-testid="stSidebar"] [data-baseweb="select"] {
            width: 100% !important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] * {
            font-size: 0.9rem !important;
        }
        /* Compact metrics */
        [data-testid="stSidebar"] [data-testid="stMetric"] {
            padding: 0.1rem 0 !important;
        }
        [data-testid="stMetricValue"],
        [data-testid="stMetricValue"] > div,
        div[data-testid="stMetricValue"],
        div[data-testid="stMetricValue"] > div {
            font-size: 1.05rem !important;
            line-height: 1.2 !important;
            overflow: visible !important;
            text-overflow: clip !important;
            white-space: nowrap !important;
        }
        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] > div,
        [data-testid="stMetricLabel"] p {
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            overflow: visible !important;
            text-overflow: clip !important;
            white-space: nowrap !important;
            margin-bottom: 0.05rem !important;
        }
        /* Compact alert and progress bar */
        [data-testid="stSidebar"] [data-testid="stAlert"] {
            padding: 0.35rem 0.65rem !important;
            margin: 0.15rem 0 !important;
        }
        [data-testid="stSidebar"] [data-testid="stAlert"] p {
            font-size: 0.8rem !important;
            line-height: 1.25 !important;
            margin: 0 !important;
        }
        [data-testid="stSidebar"] [data-testid="stProgress"] {
            margin: 0.15rem 0 !important;
        }
        [data-testid="stSidebar"] .stButton > button {
            padding: 0.3rem 0.6rem !important;
            font-size: 0.84rem !important;
            margin-top: 0.1rem !important;
        }
        [data-testid="column"] {
            overflow: visible !important;
        }
    </style>
    """, unsafe_allow_html=True)
    st.title("🚗 Vehicle Profile")

    # Navigation Menu in Side Navbar
    st.markdown("### 🧭 Navigation")
    NAV_OPTIONS = ["💬 Assistant", "📊 Vehicle Details", "📅 Appointments"]
    if "nav_page" not in st.session_state:
        st.session_state.nav_page = NAV_OPTIONS[0]

    current_nav_idx = NAV_OPTIONS.index(st.session_state.nav_page) if st.session_state.nav_page in NAV_OPTIONS else 0
    selected_nav = st.radio(
        "Navigation Options",
        options=NAV_OPTIONS,
        index=current_nav_idx,
        key="side_nav_radio",
        label_visibility="collapsed"
    )
    st.session_state.nav_page = selected_nav

    st.markdown("---")
    st.markdown("### 🚘 Active Vehicle")

    current_vid = st.session_state.selected_vehicle_id
    current_idx = next((i for i, (lbl, vid) in enumerate(vehicle_map.items()) if vid == current_vid), 0)

    selected_label = st.selectbox(
        "Choose Vehicle:",
        options=list(vehicle_map.keys()),
        index=current_idx,
        help="Select a vehicle to inspect its telemetry, maintenance status, and appointments."
    )
    new_selected_vid = vehicle_map[selected_label]
    vehicle = next((v for v in user_vehicles if v["id"] == new_selected_vid), user_vehicles[0])

    # Auto-refresh chat and update greeting when a different car is selected
    if new_selected_vid != st.session_state.get("last_active_vehicle_id"):
        st.session_state.selected_vehicle_id = new_selected_vid
        st.session_state.last_active_vehicle_id = new_selected_vid
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": get_welcome_message(vehicle)
            }
        ]
        st.rerun()

    st.session_state.selected_vehicle_id = new_selected_vid

    # Ensure single greeting message always matches the currently active car
    if len(st.session_state.messages) == 1 and st.session_state.messages[0]["role"] == "assistant":
        if "👋" in st.session_state.messages[0]["content"]:
            st.session_state.messages[0]["content"] = get_welcome_message(vehicle)

    st.markdown(f"**{vehicle.get('label', '')} — {vehicle['make']} {vehicle['model']}**")
    st.caption(f"Plate: **`{vehicle['registration_number']}`** | Year: **{vehicle['year']}**")

    # Primary High-Visibility Metrics
    col_sb1, col_sb2 = st.columns(2)
    with col_sb1:
        st.metric(label="Odometer", value=f"{vehicle['current_mileage']:,} km")
    with col_sb2:
        st.metric(label="Last Svc", value=f"{vehicle['last_service_mileage']:,} km")

    # Maintenance Calculation
    sched = database.get_maintenance_schedule(vehicle["id"]) or {"interval_km": 5000, "interval_months": 6}
    status_calc = calculate_service_status(
        current_mileage=vehicle["current_mileage"],
        last_service_mileage=vehicle["last_service_mileage"],
        interval_km=sched["interval_km"],
        last_service_date=str(vehicle["last_service_date"]),
        interval_months=sched.get("interval_months", 6),
        reference_date=date.today()
    )

    st.markdown("#### 🛠️ Service Health")
    status_code = status_calc["status"]

    consumed_km = max(0, vehicle["current_mileage"] - vehicle["last_service_mileage"])
    interval_km = sched.get("interval_km", 5000)
    pct = min(1.0, max(0.0, consumed_km / interval_km)) if interval_km > 0 else 0.0
    st.progress(pct, text=f"Interval Consumed: {int(pct * 100)}%")

    days_rem = status_calc.get("days_remaining", 0)
    days_txt = f"{days_rem} days left" if days_rem >= 0 else f"{abs(days_rem)} days overdue"

    if status_code == "APPROACHING":
        st.warning(f"⚠️ **Service Approaching**\n\n**{status_calc['remaining_km']} km remaining** ({days_txt}).")
    elif status_code == "DUE":
        st.error(f"🚨 **Service Due Today**\n\nMilestone reached ({status_calc['remaining_km']} km remaining).")
    elif status_code == "OVERDUE":
        st.error(f"🛑 **Service Overdue**\n\nImmediate maintenance recommended ({status_calc['remaining_km']} km / {days_txt}).")
    else:
        st.success(f"✅ **Good Standing**\n\n**{status_calc['remaining_km']} km remaining** ({days_txt}).")

    st.markdown("---")
    if st.button("🔄 Clear Chat & Reset", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": get_welcome_message(vehicle)
            }
        ]
        st.rerun()

# ==============================================================================
# MAIN PAGE - Header
# ==============================================================================
loc_info = st.session_state.get("user_location", {})
loc_display = loc_info.get("city", "Bengaluru")

st.markdown(f"""
<div class="app-header">
    <div class="main-title">🚗 AutoCare AI &nbsp;<span style="font-size: 1.15rem; font-weight: 500; color: #64748B;">• {st.session_state.nav_page}</span></div>
    <div class="sub-title">Active Vehicle: <b>{vehicle.get('label', 'Vehicle')}: {vehicle['make']} {vehicle['model']}</b> &nbsp;•&nbsp; Registration: <code>{vehicle['registration_number']}</code> &nbsp;•&nbsp; 📍 Location: <span class="status-badge badge-ok" style="font-size:0.75rem; padding: 2px 8px; font-weight: 600;">{loc_display} (Auto-Detected)</span></div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# VIEW 1: Chat Assistant & Quick Actions
# ==============================================================================
if st.session_state.nav_page == "💬 Assistant":
    # High-Visibility Quick Action Chips
    st.markdown("##### ⚡ Quick Prompts:")
    q_col1, q_col2, q_col3, q_col4 = st.columns(4)
    with q_col1:
        if st.button("🔍 Check Service Due", use_container_width=True):
            st.session_state.pending_prompt = f"Is my {vehicle['make']} {vehicle['model']} due for service?"
            st.rerun()
    with q_col2:
        if st.button("📍 Find Service Centers", use_container_width=True):
            st.session_state.pending_prompt = f"Find nearby authorized {vehicle['make']} service centers automatically using my current location."
            st.rerun()
    with q_col3:
        if st.button("⏰ Check Available Slots", use_container_width=True):
            st.session_state.pending_prompt = "Check tomorrow's availability for service."
            st.rerun()
    with q_col4:
        if st.button("📅 Book 10 AM Slot", use_container_width=True):
            st.session_state.pending_prompt = "Book the 10 AM slot for tomorrow."
            st.rerun()

    st.markdown("---")

    # Render Conversation History
    for msg in st.session_state.messages:
        avatar = "🚗" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            content = sanitize_chat_message(msg["content"])
            if "Rate limit reached" in content or "Groq API Error" in content:
                st.warning(f"⚠️ **AI Assistant Notice**: {content}")
            else:
                st.markdown(content)

    # Chat Input ONLY rendered in Assistant page
    user_input = st.chat_input(f"Type your question here (e.g. 'Is my {vehicle['make']} {vehicle['model']} due for service?' or 'Find nearby {vehicle['make']} service centers')...")

    # Check if a quick prompt was triggered
    if "pending_prompt" in st.session_state:
        user_input = st.session_state.pop("pending_prompt")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.spinner("Analyzing request and checking telemetry..."):
            response = st.session_state.agent.run(
                user_input,
                history=st.session_state.messages[:-1],
                selected_vehicle_id=vehicle["id"]
            )
        clean_response = sanitize_chat_message(response)
        st.session_state.messages.append({"role": "assistant", "content": clean_response})
        st.rerun()

# ==============================================================================
# VIEW 2: Vehicle Telemetry & Garage Overview
# ==============================================================================
elif st.session_state.nav_page == "📊 Vehicle Details":
    st.markdown(f"#### 🚘 {vehicle.get('label', 'Active Vehicle')}: {vehicle['make']} {vehicle['model']} Specifications")
    
    # 4 Key Metrics with high contrast
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Model & Make", f"{vehicle['make']} {vehicle['model']}")
    c2.metric("Variant", vehicle.get("variant", "Standard"))
    c3.metric("Current Odometer", f"{vehicle['current_mileage']:,} km")
    c4.metric("Next Service Due At", f"{status_calc['next_service_mileage']:,} km")

    # Quick Telemetry & Maintenance Sync
    with st.expander("⚡ Update Telemetry / Record Completed Service / Cost", expanded=False):
        sync_tab1, sync_tab2, sync_tab3 = st.tabs(["🔄 Update Odometer & Date", "🛠️ Record Completed Service", "💰 Update Service Cost"])
        
        with sync_tab1:
            with st.form("quick_telemetry_form", clear_on_submit=False):
                st.caption(f"Sync odometer and service dates for **{vehicle['make']} {vehicle['model']}**.")
                tf_c1, tf_c2 = st.columns(2)
                with tf_c1:
                    new_odo = st.number_input("Current Odometer Reading (km)", min_value=0, value=int(vehicle["current_mileage"]), step=50, key="quick_odo_input")
                    new_last_svc_km = st.number_input("Last Service Mileage (km)", min_value=0, value=int(vehicle["last_service_mileage"]), step=50, key="quick_last_km_input")
                with tf_c2:
                    curr_svc_date = str(vehicle.get("last_service_date", date.today()))
                    new_svc_date = st.text_input("Last Service Date (YYYY-MM-DD)", value=curr_svc_date, help="Enter service date in YYYY-MM-DD format (or 'today')", key="quick_svc_date_input")
                    new_int_km = st.number_input("Service Interval (km)", min_value=1000, value=int(sched.get("interval_km", 5000)), step=500, key="quick_int_km_input")
                
                if st.form_submit_button("💾 Save & Synchronize Telemetry", use_container_width=True, type="primary"):
                    try:
                        database.update_vehicle_service_details(
                            vehicle_id=vehicle["id"],
                            last_service_date=new_svc_date,
                            last_service_mileage=int(new_last_svc_km),
                            current_mileage=int(new_odo)
                        )
                        database.update_maintenance_schedule(
                            vehicle_id=vehicle["id"],
                            interval_km=int(new_int_km),
                            last_service_mileage=int(new_last_svc_km),
                            last_service_date=new_svc_date
                        )
                        st.toast("Vehicle telemetry synchronized successfully!", icon="✅")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Sync error: {ex}")
        
        with sync_tab2:
            with st.form("record_service_form", clear_on_submit=True):
                st.caption(f"Log a completed maintenance service for **{vehicle['make']} {vehicle['model']}**.")
                rf_c1, rf_c2 = st.columns(2)
                with rf_c1:
                    svc_rec_date = st.text_input("Service Date (YYYY-MM-DD)", value=str(date.today()), key="rec_svc_date")
                    svc_rec_km = st.number_input("Odometer at Service (km)", min_value=0, value=int(vehicle["current_mileage"]), step=100, key="rec_svc_km")
                    svc_rec_type = st.selectbox("Service Type", options=["Periodic Maintenance Service", "General Inspection", "Oil & Filter Change", "Major Service", "Brake & Tire Service"], key="rec_svc_type")
                with rf_c2:
                    svc_rec_interval = st.number_input("Next Service Interval (km)", min_value=1000, value=int(sched.get("interval_km", 5000)), step=500, key="rec_svc_interval")
                    svc_rec_center = st.text_input("Workshop / Service Center", value="Authorized Service Center", key="rec_svc_center")
                    svc_rec_cost = st.number_input("Service Cost (INR)", min_value=0.0, value=3500.0, step=100.0, key="rec_svc_cost")
                
                if st.form_submit_button("✅ Record Service & Reset Interval", use_container_width=True, type="primary"):
                    try:
                        res = database.update_service_after_completion(
                            vehicle_id=vehicle["id"],
                            service_date=svc_rec_date,
                            next_service_interval_km=int(svc_rec_interval),
                            service_mileage=int(svc_rec_km),
                            service_type=svc_rec_type,
                            description=f"{svc_rec_type} completed at {svc_rec_km} km",
                            cost=float(svc_rec_cost),
                            service_center=svc_rec_center
                        )
                        st.toast(res.get("message", "Service recorded successfully!"), icon="✅")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error recording service: {ex}")

        with sync_tab3:
            with st.form("update_cost_form", clear_on_submit=False):
                st.caption(f"Update invoice or service expense in the database for **{vehicle['make']} {vehicle['model']}**.")
                hist_items = database.get_service_history(vehicle["id"])
                if hist_items:
                    cost_options = {f"Service #{h['id']} ({h['service_date']} - {h['service_type']}) — Current: ₹{float(h.get('cost', 0)):,.2f}": h["id"] for h in hist_items}
                    selected_h_label = st.selectbox("Select Service Record to Update:", options=list(cost_options.keys()))
                    selected_h_id = cost_options[selected_h_label]
                    curr_h_cost = next((float(h.get("cost", 0.0) or 0.0) for h in hist_items if h["id"] == selected_h_id), 0.0)
                    new_cost_val = st.number_input("Updated Cost (INR)", min_value=0.0, value=curr_h_cost, step=100.0, key="update_cost_input")
                    if st.form_submit_button("💰 Save Cost to Database", use_container_width=True, type="primary"):
                        c_res = database.update_service_cost(vehicle["id"], new_cost_val, selected_h_id)
                        if c_res.get("status") == "SUCCESS":
                            st.toast(c_res.get("message", "Cost updated successfully!"), icon="✅")
                            st.rerun()
                        else:
                            st.error(c_res.get("error", "Failed to update cost."))
                else:
                    st.info("No service history entries found yet to update cost.")

    st.markdown("---")

    st.markdown("#### 📜 Service History Records")
    history_records = database.get_service_history(vehicle["id"])
    if history_records:
        st.dataframe(
            history_records,
            column_config={
                "id": "ID",
                "service_date": "Service Date",
                "service_mileage": "Odometer (km)",
                "service_type": "Type",
                "description": "Work Done",
                "cost": st.column_config.NumberColumn("Cost (INR)", format="₹%.2f"),
                "service_center": "Workshop"
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info(f"No past service records logged yet for {vehicle['make']} {vehicle['model']}.")

    st.markdown("---")
    st.markdown("#### 🏠 Garage Overview (All Vehicles)")
    
    COLS_PER_ROW = 3
    for row_start in range(0, len(user_vehicles), COLS_PER_ROW):
        row_vehicles = user_vehicles[row_start:row_start + COLS_PER_ROW]
        cols = st.columns(COLS_PER_ROW)
        for col_idx, v in enumerate(row_vehicles):
            with cols[col_idx]:
                with st.container(border=True):
                    is_active = (v["id"] == vehicle["id"])
                    v_label = v.get("label") or f"Vehicle {v['id']}"
                    v_reg = v["registration_number"]
                    v_var = v.get("variant", "Standard")
                    v_yr = v.get("year", 2023)
                    v_curr = f"{v['current_mileage']:,} km"
                    v_last = f"{v['last_service_mileage']:,} km"

                    # Header with label, model title and ACTIVE badge
                    header_c1, header_c2 = st.columns([3, 1])
                    with header_c1:
                        st.caption(v_label.upper())
                        st.markdown(f"#### {v['make']} {v['model']}")
                    with header_c2:
                        if is_active:
                            st.markdown('<span class="status-badge badge-ok" style="font-size: 0.72rem; padding: 0.2rem 0.5rem; float: right;">ACTIVE</span>', unsafe_allow_html=True)

                    st.markdown(f"Plate: ` {v_reg} ` &nbsp;|&nbsp; {v_var} ({v_yr})")
                    st.divider()

                    m1, m2 = st.columns(2)
                    m1.metric("Odometer", v_curr)
                    m2.metric("Last Svc", v_last)

                    st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

                    if is_active:
                        st.button("✓ Currently Active", key=f"active_v_{v['id']}", disabled=True, use_container_width=True)
                    else:
                        btn_c1, btn_c2 = st.columns([4, 1])
                        with btn_c1:
                            if st.button(f"Switch to {v['model']}", key=f"switch_v_{v['id']}", use_container_width=True):
                                st.session_state.selected_vehicle_id = v["id"]
                                st.session_state.last_active_vehicle_id = v["id"]
                                st.session_state.messages = [
                                    {
                                        "role": "assistant",
                                        "content": get_welcome_message(v)
                                    }
                                ]
                                st.rerun()
                        with btn_c2:
                            if st.button("🗑️", key=f"del_v_{v['id']}", help=f"Delete {v['model']}", use_container_width=True):
                                database.delete_vehicle(v["id"])
                                st.rerun()

    # Add Vehicle Form
    with st.expander("➕ Register New Vehicle to Garage"):
        with st.form("add_vehicle_form", clear_on_submit=True):
            f1, f2 = st.columns(2)
            with f1:
                form_make = st.text_input("Make", value="Tata")
                form_model = st.text_input("Model", placeholder="e.g. Harrier, Safari, Curvv")
                form_variant = st.text_input("Variant", placeholder="e.g. Adventure Plus")
            with f2:
                form_reg = st.text_input("Registration Plate", placeholder="e.g. KA-03-TR-9012")
                form_km = st.number_input("Current Odometer (km)", min_value=0, value=2000, step=100)
                form_year = st.number_input("Year", min_value=2015, max_value=2026, value=2024)
            if st.form_submit_button("Register Vehicle", use_container_width=True):
                if form_model:
                    res = database.add_vehicle(
                        user_id=1,
                        make=form_make,
                        model=form_model,
                        registration_number=form_reg if form_reg else None,
                        current_mileage=int(form_km),
                        variant=form_variant,
                        year=int(form_year)
                    )
                    st.success(res["message"])
                    st.rerun()
                else:
                    st.error("Please specify at least the vehicle model.")

# ==============================================================================
# VIEW 3: Appointments & Service Vouchers
# ==============================================================================
elif st.session_state.nav_page == "📅 Appointments":
    st.markdown("### 📅 Service Appointments & Vouchers")
    st.caption(f"Manage active and past maintenance service bookings for **{vehicle.get('label', vehicle['model'])}** ({vehicle['make']} {vehicle['model']} • `{vehicle['registration_number']}`).")

    # Service Centers Cache for Workshop Details
    all_centers = database.get_service_centers()
    center_map = {c.get("center_id"): c for c in all_centers}

    # Fetch Appointments for Active Vehicle
    appts_all = database.get_appointments(vehicle_id=vehicle["id"])

    # Metrics Summary
    total_count = len(appts_all)
    confirmed_count = sum(1 for a in appts_all if a.get("status") == "CONFIRMED")
    cancelled_count = sum(1 for a in appts_all if a.get("status") == "CANCELLED")

    # Clean, Perfectly Aligned Top Controls Row
    top_col_filter, top_col_stats, top_col_btn = st.columns([2.5, 3.5, 2])
    with top_col_filter:
        status_filter = st.selectbox(
            "Filter Status:",
            options=["All Statuses", "CONFIRMED", "CANCELLED"],
            key="appt_status_filter"
        )
    with top_col_stats:
        st.markdown(
            f"<div style='padding-top: 1.85rem; font-size: 0.9rem; color: #94A3B8;'>"
            f"<b>{total_count}</b> booking(s) • "
            f"<span style='color: #34D399; font-weight: 600;'>● {confirmed_count} Confirmed</span> • "
            f"<span style='color: #F87171; font-weight: 600;'>● {cancelled_count} Cancelled</span>"
            f"</div>",
            unsafe_allow_html=True
        )
    with top_col_btn:
        st.markdown("<div style='padding-top: 1.65rem;'>", unsafe_allow_html=True)
        if st.button("➕ Book New Service", use_container_width=True, type="primary"):
            st.session_state.nav_page = "💬 Assistant"
            st.session_state.pending_prompt = f"I would like to book a service appointment for my {vehicle['make']} {vehicle['model']}."
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # Apply Status Filter
    if status_filter != "All Statuses":
        appts = [a for a in appts_all if a.get("status", "").upper() == status_filter]
    else:
        appts = appts_all

    if appts:
        for appt in appts:
            ref = appt.get("booking_reference", "N/A")
            status_val = appt.get("status", "CONFIRMED").upper()
            veh_name = f"{vehicle.get('make', '')} {vehicle.get('model', '')} ({vehicle.get('registration_number', '')})"

            # Lookup Workshop Info
            cid = appt.get("service_center_id", "")
            sc_info = center_map.get(cid, {})
            sc_name = sc_info.get("name", cid or "Authorized Service Center")
            sc_addr = sc_info.get("address", sc_info.get("city", "Bangalore, India"))
            sc_phone = sc_info.get("phone", "Contact via Service Desk")
            sc_rating = sc_info.get("rating", 4.7)

            badge_html = (
                f'<span class="badge-confirmed">● CONFIRMED</span>'
                if status_val == "CONFIRMED"
                else f'<span class="badge-cancelled">● CANCELLED</span>'
            )

            # Each booking in its own self-contained, bordered box
            with st.container(border=True):
                st.markdown(f"""
                <div class="voucher-card">
                    <div class="voucher-header">
                        <div>
                            <span style="color: #94A3B8; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">SERVICE APPOINTMENT VOUCHER</span><br>
                            <span class="voucher-ref">🎫 Ref: {ref}</span>
                            <span style="margin-left: 0.75rem; font-size: 0.82rem; color: #CBD5E1; background: rgba(51, 65, 85, 0.6); padding: 0.2rem 0.6rem; border-radius: 6px;">🚗 {veh_name}</span>
                        </div>
                        <div>
                            {badge_html}
                        </div>
                    </div>
                    <div class="voucher-details-grid">
                        <div class="voucher-chip">
                            <div class="voucher-chip-title">📅 DATE & TIME</div>
                            <div class="voucher-chip-val">📅 {appt.get('appointment_date')}</div>
                            <div class="voucher-chip-sub">⏰ Slot: <b>{appt.get('appointment_time')}</b></div>
                        </div>
                        <div class="voucher-chip">
                            <div class="voucher-chip-title">🏢 AUTHORIZED WORKSHOP</div>
                            <div class="voucher-chip-val">{sc_name}</div>
                            <div class="voucher-chip-sub">📍 {sc_addr} • ⭐ {sc_rating}</div>
                        </div>
                        <div class="voucher-chip">
                            <div class="voucher-chip-title">🔧 SERVICE SCOPE</div>
                            <div class="voucher-chip-val">{appt.get('service_type', 'Periodic Maintenance Service')}</div>
                            <div class="voucher-chip-sub">📞 {sc_phone}</div>
                        </div>
                        <div class="voucher-chip">
                            <div class="voucher-chip-title">🆔 WORKSHOP CODE</div>
                            <div class="voucher-chip-val"><code>{cid}</code></div>
                            <div class="voucher-chip-sub">Status: <b style="color: {'#34D399' if status_val == 'CONFIRMED' else '#F87171'};">{status_val}</b></div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Integrated Bottom Action Footer inside the Card Box
                st.markdown("<div style='border-top: 1px solid #334155; margin: 0.75rem 0 0.5rem 0;'></div>", unsafe_allow_html=True)
                if status_val == "CONFIRMED":
                    foot_left, foot_act = st.columns([4.2, 1.5])
                    with foot_left:
                        st.markdown(f"<div style='color: #94A3B8; font-size: 0.84rem; padding-top: 0.35rem;'>💡 Booking is active. Show voucher ref <b>`{ref}`</b> at workshop reception.</div>", unsafe_allow_html=True)
                    with foot_act:
                        if st.button("❌ Cancel Booking", key=f"cancel_btn_{ref}", use_container_width=True):
                            database.cancel_appointment(ref)
                            st.toast(f"Appointment {ref} cancelled.", icon="✅")
                            st.rerun()
                else:
                    st.markdown("<div style='color: #F87171; font-size: 0.84rem; padding: 0.2rem 0;'>⚠️ This appointment has been cancelled.</div>", unsafe_allow_html=True)

                st.markdown("<div style='margin-bottom: 0.2rem;'></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background: #1E293B; border: 1.5px dashed #475569; border-radius: 14px; padding: 2.5rem; text-align: center; margin-top: 1rem;">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">📅</div>
            <h4 style="color: #F8FAFC; margin-bottom: 0.3rem;">No Appointments Found</h4>
            <p style="color: #94A3B8; font-size: 0.9rem; max-width: 480px; margin: 0 auto 1.25rem auto;">
                There are no {status_filter.lower() if status_filter != 'All Statuses' else ''} appointments recorded for {vehicle.get('label', vehicle['model'])}.
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("💬 Ask Assistant to Book Service", key="empty_book_btn", type="primary"):
            st.session_state.nav_page = "💬 Assistant"
            st.session_state.pending_prompt = f"Help me book a maintenance appointment for my {vehicle['make']} {vehicle['model']}."
            st.rerun()
