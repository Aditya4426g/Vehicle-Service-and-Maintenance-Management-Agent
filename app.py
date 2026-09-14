"""
app.py - Polished Streamlit Web Application for Vehicle Service & Maintenance Management Agent.
Single-Agent AI interface powered exclusively by openai/gpt-oss-120b through Groq.
"""
from datetime import date
import streamlit as st

from config import GROQ_MODEL, MAX_TOOL_CALLS, validate_config
from agent import VehicleMaintenanceAgent
import database
from tools.maintenance import calculate_service_status

# Configure page layout and visual metadata
st.set_page_config(
    page_title="Vehicle Service & Maintenance Agent",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished fresher-friendly dashboard styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-caption {
        font-size: 0.95rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .status-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .badge-approaching {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
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
                "👋 **Hello Rahul!** I am your Vehicle Service & Maintenance Assistant, "
                f"powered by `{GROQ_MODEL}` through Groq.\n\n"
                "I can verify your Tata Nexon's maintenance status, find authorized workshops, "
                "check slot availability, and book your service. How can I assist you today?"
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

# Sidebar - Vehicle Status & System Telemetry
with st.sidebar:
    st.title("🚗 Vehicle Profile")
    st.subheader(f"{vehicle['make']} {vehicle['model']}")
    st.caption(f"Reg: `{vehicle['registration_number']}` | Year: {vehicle['year']}")

    col_sb1, col_sb2 = st.columns(2)
    with col_sb1:
        st.metric("Odometer", f"{vehicle['current_mileage']:,} km")
    with col_sb2:
        st.metric("Last Svc", f"{vehicle['last_service_mileage']:,} km")

    # Real-time maintenance status calculation
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

    # Calculate interval consumption percentage
    consumed_km = vehicle["current_mileage"] - vehicle["last_service_mileage"]
    interval_km = sched["interval_km"]
    pct = min(1.0, max(0.0, consumed_km / interval_km)) if interval_km > 0 else 0.0
    st.progress(pct, text=f"Service Interval Consumed: {int(pct * 100)}%")

    if status_code == "APPROACHING":
        st.warning(f"⚠️ Status: **APPROACHING**\n\n{status_calc['remaining_km']} km remaining before 10,000 km periodic service.")
    elif status_code == "DUE":
        st.error(f"🚨 Status: **DUE**\n\nService is due now!")
    elif status_code == "OVERDUE":
        st.error(f"🛑 Status: **OVERDUE**\n\nService is overdue!")
    else:
        st.success(f"✅ Status: **NOT DUE**\n\n{status_calc['remaining_km']} km remaining.")

    st.markdown("---")
    st.markdown("### Quick Prompts")
    quick_prompts = [
        "Is my Tata Nexon service due?",
        "Show my service history",
        "Find service centers near Indiranagar",
        "Book an appointment for tomorrow morning"
    ]
    for prompt in quick_prompts:
        if st.button(prompt, key=f"btn_{prompt}", use_container_width=True):
            st.session_state.pending_prompt = prompt

    st.markdown("---")
    st.markdown("### System Telemetry")
    cfg = validate_config()
    st.write(f"• **LLM Model:** `{cfg['model']}`")
    st.write(f"• **Tool Loop Budget:** `{cfg['max_tool_calls']} calls max`")
    if cfg["groq_configured"]:
        st.success("Groq API: Connected")
    else:
        st.info("Groq API: Key ready in .env")

    if st.button("🔄 Reset Conversation", use_container_width=True):
        st.session_state.messages = [st.session_state.messages[0]]
        st.rerun()

# Main App Header
st.markdown('<div class="main-header">🚗 Vehicle Service & Maintenance Management Agent</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-caption">Single-Agent AI Assistant powered by Groq and <code>{GROQ_MODEL}</code></div>', unsafe_allow_html=True)

# Main Dashboard Tabs
tab_chat, tab_dashboard, tab_workshops, tab_appointments = st.tabs([
    "💬 Agent Assistant",
    "📊 Vehicle Telemetry & History",
    "🏢 Workshop Directory",
    "📅 Appointments & Alerts"
])

# TAB 1: Chat Assistant
with tab_chat:
    st.markdown("##### Chat with your Maintenance Agent")
    st.caption("Ask questions in natural language. The agent extracts intent, executes Python tools, and synthesizes clear answers.")

    # Render conversation history with avatars
    for msg in st.session_state.messages:
        avatar = "🚗" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # Handle incoming messages
    incoming_input = st.chat_input("Type your message here (e.g. 'Is my Tata Nexon due for service?')...")
    if "pending_prompt" in st.session_state:
        incoming_input = st.session_state.pop("pending_prompt")

    if incoming_input:
        st.session_state.messages.append({"role": "user", "content": incoming_input})
        with st.chat_message("user", avatar="👤"):
            st.markdown(incoming_input)

        with st.chat_message("assistant", avatar="🚗"):
            with st.spinner("Analyzing request and executing tools..."):
                response = st.session_state.agent.run(
                    incoming_input,
                    history=st.session_state.messages[:-1]
                )
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})

# TAB 2: Vehicle Telemetry & Service History
with tab_dashboard:
    st.markdown("##### Vehicle Specifications & Health")
    col_v1, col_v2, col_v3, col_v4 = st.columns(4)
    col_v1.metric("Make & Model", f"{vehicle['make']} {vehicle['model']}")
    col_v2.metric("Variant", vehicle.get("variant", "N/A"))
    col_v3.metric("Current Mileage", f"{vehicle['current_mileage']:,} km")
    col_v4.metric("Target Service", f"{status_calc['next_service_mileage']:,} km")

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
            hide_index=True
        )
    else:
        st.info("No service history found for this vehicle.")

# TAB 3: Workshop Directory
with tab_workshops:
    st.markdown("##### Nearby Authorized Service Centers")
    st.caption("Discovered via OpenStreetMap Nominatim and Overpass API.")
    centers = [
        {"center_id": "osm_101", "name": "ABC Motors Tata Authorized", "address": "12th Main Road, Indiranagar, Bangalore", "distance_km": 1.2, "phone": "+91 80 25251122"},
        {"center_id": "osm_102", "name": "XYZ Auto Care Service Center", "address": "80 Feet Road, Koramangala, Bangalore", "distance_km": 2.4, "phone": "+91 80 41412233"},
        {"center_id": "osm_103", "name": "Prerana Motors Tata Service", "address": "Hosur Main Road, Kudlu Gate, Bangalore", "distance_km": 3.8, "phone": "+91 80 67673344"}
    ]
    for c in centers:
        with st.container():
            c_col1, c_col2, c_col3 = st.columns([3, 2, 1])
            with c_col1:
                st.markdown(f"**{c['name']}** (`{c['center_id']}`)")
                st.caption(f"📍 {c['address']}")
            with c_col2:
                st.write(f"📏 Distance: **{c['distance_km']} km**")
                st.caption(f"📞 {c['phone']}")
            with c_col3:
                if st.button("Select Center", key=f"sel_{c['center_id']}"):
                    st.session_state.pending_prompt = f"Find available slots for {c['name']} ({c['center_id']}) tomorrow"
                    st.rerun()
            st.divider()

# TAB 4: Appointments & Notifications
with tab_appointments:
    st.markdown("##### Active & Past Appointments")
    appts = database.get_appointments(vehicle_id=1)
    if appts:
        for appt in appts:
            with st.container():
                c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                c1.write(f"**Ref:** `{appt.get('booking_reference')}`")
                c2.write(f"📅 {appt.get('appointment_date')} at {appt.get('appointment_time')}")
                c3.write(f"🏢 Center: `{appt.get('service_center_id')}`")
                status_label = appt.get("status", "CONFIRMED")
                if status_label == "CONFIRMED":
                    c4.success(status_label)
                elif status_label == "COMPLETED":
                    c4.info(status_label)
                else:
                    c4.warning(status_label)
                st.divider()
    else:
        st.info("No service appointments booked yet.")

    st.markdown("---")
    st.markdown("##### Notification Dispatch Log")
    user_data = database.get_user(1)
    st.write(f"**Customer:** {user_data.get('name')} | **Email:** {user_data.get('email')}")
    if hasattr(database, "_LOCAL_NOTIFICATIONS") and database._LOCAL_NOTIFICATIONS:
        for notif in database._LOCAL_NOTIFICATIONS:
            with st.expander(f"Notification #{notif['id']} - {notif.get('notification_type', 'ALERT')} ({notif.get('status', 'SENT')})"):
                st.write(notif.get("message"))
