"""
app.py - Modern Automotive Telemetry Dashboard & AI Maintenance Assistant.
Single-Agent architecture powered exclusively by Groq and openai/gpt-oss-120b.
"""
from datetime import date
import streamlit as st

from config import GROQ_MODEL, MAX_TOOL_CALLS, validate_config
from agent import VehicleMaintenanceAgent
import database
from tools.maintenance import calculate_service_status
from tools.location import geocode_location, search_service_centers

# Page configuration
st.set_page_config(
    page_title="AutoCare AI - Vehicle Maintenance Assistant",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern Design System (CSS)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.025em;
        background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 50%, #0284C7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.15rem;
    }

    .sub-title {
        color: #64748B;
        font-size: 0.95rem;
        margin-bottom: 1.25rem;
    }

    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        margin-bottom: 0.75rem;
    }

    .workshop-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 0.85rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
    }
    .workshop-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.07);
        border-color: #93C5FD;
    }

    .badge-status-due {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.78rem;
    }
    .badge-status-approaching {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.78rem;
    }
    .badge-status-ok {
        background-color: #D1FAE5;
        color: #065F46;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.78rem;
    }
    .booking-voucher {
        background: linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%);
        border: 1px dashed #94A3B8;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }

    /* Fixed bottom container spacing so messages never get obscured */
    .block-container {
        padding-bottom: 110px !important;
    }

    /* Floating ChatGPT style input bar */
    [data-testid="stChatInput"] {
        border-radius: 16px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08) !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Agent in session state
if "agent" not in st.session_state:
    st.session_state.agent = VehicleMaintenanceAgent()

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "👋 **Hello Rahul!** I am your **Vehicle Service & Maintenance Assistant**, "
                f"powered by `{GROQ_MODEL}` through Groq.\n\n"
                "I can analyze your **Tata Nexon's** maintenance schedule, discover authorized workshops "
                "across India, verify real-time slot availability, and confirm your service booking. "
                "How can I help you today?"
            )
        }
    ]

# Fetch baseline vehicle data for Rahul (Vehicle ID 1)
vehicle = database.get_vehicle_info(user_id=1, vehicle_name="Tata Nexon") or {
    "make": "Tata",
    "model": "Nexon",
    "variant": "XZ+ Petrol",
    "year": 2023,
    "registration_number": "KA-01-MJ-2023",
    "current_mileage": 9800,
    "last_service_date": "2024-03-15",
    "last_service_mileage": 5000
}

# Sidebar - Vehicle Telemetry & System Status
with st.sidebar:
    st.title("🚗 Vehicle Profile")
    st.subheader(f"{vehicle['make']} {vehicle['model']}")
    st.caption(f"Reg: `{vehicle['registration_number']}` | Year: {vehicle['year']} | {vehicle.get('variant', 'XZ+ Petrol')}")

    col_sb1, col_sb2 = st.columns(2)
    with col_sb1:
        st.metric("Odometer", f"{vehicle['current_mileage']:,} km")
    with col_sb2:
        st.metric("Last Svc", f"{vehicle['last_service_mileage']:,} km")

    # Maintenance Calculation
    sched = database.get_maintenance_schedule(1) or {"interval_km": 5000, "interval_months": 6}
    status_calc = calculate_service_status(
        current_mileage=vehicle["current_mileage"],
        last_service_mileage=vehicle["last_service_mileage"],
        interval_km=sched["interval_km"],
        last_service_date=str(vehicle["last_service_date"]),
        interval_months=sched["interval_months"],
        reference_date=date(2024, 9, 1)
    )

    st.markdown("### Service Health")
    status_code = status_calc["status"]

    # Calculate interval consumption
    consumed_km = vehicle["current_mileage"] - vehicle["last_service_mileage"]
    interval_km = sched["interval_km"]
    pct = min(1.0, max(0.0, consumed_km / interval_km)) if interval_km > 0 else 0.0
    st.progress(pct, text=f"Service Interval Consumed: {int(pct * 100)}%")

    if status_code == "APPROACHING":
        st.warning(f"⚠️ **Service Approaching**\n\n{status_calc['remaining_km']} km remaining before 10,000 km minor service.")
    elif status_code == "DUE":
        st.error("🚨 **Service Due Today**\n\nVehicle reached scheduled service milestone.")
    elif status_code == "OVERDUE":
        st.error("🛑 **Service Overdue**\n\nImmediate maintenance recommended.")
    else:
        st.success(f"✅ **Good Standing**\n\n{status_calc['remaining_km']} km remaining until next service.")

    st.markdown("---")
    st.markdown("### Quick Prompts")
    quick_prompts = [
        "Is my Tata Nexon service due?",
        "Show my service history",
        "Find service centers near Udaipur, Rajasthan",
        "Find service centers near Indiranagar, Bangalore",
        "Book an appointment for tomorrow morning"
    ]
    for prompt in quick_prompts:
        if st.button(prompt, key=f"btn_{prompt}", use_container_width=True):
            st.session_state.pending_prompt = prompt

    st.markdown("---")
    st.markdown("### System Telemetry")
    cfg = validate_config()
    st.write(f"• **AI Engine:** `{cfg['model']}`")
    st.write(f"• **Tool Budget:** `{cfg['max_tool_calls']} calls max`")
    if cfg["groq_configured"]:
        st.success("Groq API: Connected")
    else:
        st.info("Groq API: Local Simulation")

    if st.button("🔄 Reset Conversation", use_container_width=True):
        st.session_state.messages = [st.session_state.messages[0]]
        st.rerun()

# Main Application Header
st.markdown('<div class="main-title">🚗 AutoCare AI — Vehicle Service & Maintenance Agent</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-title">Autonomous Automotive Assistant powered by Groq and <code>{GROQ_MODEL}</code></div>', unsafe_allow_html=True)

# 4 Core Dashboard Tabs
tab_chat, tab_dashboard, tab_workshops, tab_appointments = st.tabs([
    "💬 Agent Assistant",
    "📊 Vehicle Telemetry & History",
    "🏢 Workshop Directory",
    "📅 Appointments & Alerts"
])

# TAB 1: Chat Assistant
with tab_chat:
    st.markdown("##### Chat with your AI Maintenance Agent")
    st.caption("Ask maintenance questions in plain English. The agent determines intent, executes deterministic Python tools, and returns structured answers.")

    # Render Conversation History with Avatars in chronological order
    for msg in st.session_state.messages:
        avatar = "🚗" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

# TAB 2: Vehicle Telemetry & Service History
with tab_dashboard:
    st.markdown("##### Vehicle Specifications & Health")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Make & Model", f"{vehicle['make']} {vehicle['model']}")
    c2.metric("Variant", vehicle.get("variant", "XZ+ Petrol"))
    c3.metric("Current Odometer", f"{vehicle['current_mileage']:,} km")
    c4.metric("Next Target Service", f"{status_calc['next_service_mileage']:,} km")

    st.markdown("---")
    st.markdown("##### Historical Service Records")
    history_records = database.get_service_history(1)
    if history_records:
        st.dataframe(
            history_records,
            column_config={
                "id": "Record ID",
                "service_date": "Date",
                "service_mileage": "Odometer (km)",
                "service_type": "Service Type",
                "description": "Details",
                "cost": st.column_config.NumberColumn("Cost (INR)", format="₹%.2f"),
                "service_center": "Authorized Workshop"
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No past service records on file.")

# TAB 3: Interactive Live Workshop Directory
with tab_workshops:
    st.markdown("##### Live Authorized Service Center Finder")
    st.caption("Enter any city, landmark, or region to search for authorized Tata workshops with live distances and verified contacts.")

    # Location Search Controls
    loc_col1, loc_col2 = st.columns([3, 1])
    with loc_col1:
        search_query = st.text_input(
            "Search City or Area",
            value="Udaipur, Rajasthan",
            placeholder="e.g. Udaipur, Bangalore, Jaipur, Mumbai, Delhi..."
        )
    with loc_col2:
        radius_filter = st.slider("Search Radius (km)", min_value=5, max_value=50, value=30, step=5)

    # Preset City Quick Buttons
    st.write("**Quick Locations:**")
    quick_cities = ["Udaipur, Rajasthan", "Indiranagar, Bangalore", "Jaipur, Rajasthan", "Mumbai, Maharashtra", "Delhi NCR"]
    q_cols = st.columns(len(quick_cities))
    for idx, city in enumerate(quick_cities):
        if q_cols[idx].button(city, key=f"city_btn_{city}", use_container_width=True):
            search_query = city

    # Live Geocoding & Workshop Lookup
    with st.spinner(f"Discovering authorized service centers near '{search_query}'..."):
        geo = geocode_location(search_query)
        if geo.get("status") == "SUCCESS" and geo.get("latitude"):
            lat = geo["latitude"]
            lon = geo["longitude"]
            discovered = search_service_centers(lat, lon, radius_km=radius_filter)
        else:
            discovered = database.get_service_centers_near(24.5787, 73.6862, radius_km=radius_filter)

    st.markdown(f"**Found {len(discovered)} Authorized Centers near `{search_query}`:**")
    st.markdown("---")

    for c in discovered:
        with st.container():
            col_info, col_contact, col_action = st.columns([3, 2, 1])
            with col_info:
                st.markdown(f"##### {c.get('name', 'Authorized Workshop')}")
                st.caption(f"📍 {c.get('address', 'Address on file')}")
                st.write(f"⭐ Rating: **{c.get('rating', 4.7)} / 5.0**")
            with col_contact:
                st.write(f"📏 Distance: **{c.get('distance_km', 2.5)} km** away")
                st.write(f"📞 Contact: `{c.get('phone', '+91 294 2490111')}`")
                st.caption(f"Center ID: `{c.get('center_id')}`")
            with col_action:
                if st.button("📅 Book Here", key=f"book_dir_{c.get('center_id')}", use_container_width=True):
                    st.session_state.pending_prompt = f"Check availability for {c.get('name')} ({c.get('center_id')}) tomorrow morning"
                    st.rerun()
            st.divider()

# TAB 4: Appointments & Notifications
with tab_appointments:
    st.markdown("##### Active & Scheduled Service Appointments")
    appts = database.get_appointments(vehicle_id=1)
    if appts:
        for appt in appts:
            with st.container():
                st.markdown(f"""
                <div class="booking-voucher">
                    <span style="font-size: 1.1rem; font-weight: 700; color: #1E3A8A;">Booking Reference: {appt.get('booking_reference')}</span>
                    <span style="float: right;" class="badge-status-ok">{appt.get('status', 'CONFIRMED')}</span>
                    <p style="margin-top: 0.5rem; color: #475569;">
                        📅 <b>Date & Time:</b> {appt.get('appointment_date')} at {appt.get('appointment_time')}<br>
                        🏢 <b>Service Center:</b> <code>{appt.get('service_center_id')}</code><br>
                        🔧 <b>Service Type:</b> {appt.get('service_type', 'Periodic Maintenance Service')}
                    </p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No active appointments booked yet.")

    st.markdown("---")
    st.markdown("##### Multi-Channel Dispatch Audit Trail")
    user_data = database.get_user(1) or {"name": "Rahul", "email": "rahul@example.com", "phone": "+91 9876543210"}
    st.write(f"**Customer:** {user_data.get('name')} | **Email:** `{user_data.get('email')}` | **Mobile:** `{user_data.get('phone')}`")

    if hasattr(database, "_LOCAL_NOTIFICATIONS") and database._LOCAL_NOTIFICATIONS:
        for notif in database._LOCAL_NOTIFICATIONS:
            with st.expander(f"Notification #{notif['id']} — {notif.get('notification_type', 'CONFIRMATION')} [{notif.get('status', 'SENT')}]"):
                st.write(notif.get("message"))

# ==============================================================================
# ChatGPT-Style Fixed Bottom Chat Input
# Root-level st.chat_input anchors fixed to the bottom viewport across the app
# ==============================================================================
user_input = st.chat_input("Type your question here (e.g. 'Find Tata service centers in Udaipur' or 'Book a slot for tomorrow')...")
if "pending_prompt" in st.session_state:
    user_input = st.session_state.pop("pending_prompt")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("Analyzing request and executing tools..."):
        response = st.session_state.agent.run(
            user_input,
            history=st.session_state.messages[:-1]
        )
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

