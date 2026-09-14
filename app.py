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
                "👋 **Hello Rahul!** How can I assist you with your **Tata Nexon** today?\n\n"
                "I can check your maintenance schedule, locate authorized Tata service centers, "
                "verify slot availability, and book your service appointments."
            )
        }
    ]

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
vehicle_map = {
    f"{v.get('label', f'Vehicle {idx+1}')}: {v['make']} {v['model']} ({v['registration_number']})": v["id"]
    for idx, v in enumerate(user_vehicles)
}

if "selected_vehicle_id" not in st.session_state:
    st.session_state.selected_vehicle_id = user_vehicles[0]["id"]

# Sidebar - Vehicle Telemetry & System Status
with st.sidebar:
    st.title("🚗 Vehicle Profile")

    current_vid = st.session_state.selected_vehicle_id
    current_idx = next((i for i, (lbl, vid) in enumerate(vehicle_map.items()) if vid == current_vid), 0)

    selected_label = st.selectbox(
        "🚘 Active Vehicle:",
        options=list(vehicle_map.keys()),
        index=current_idx,
        help="Switch active vehicle to monitor telemetry, maintenance status, and history."
    )
    st.session_state.selected_vehicle_id = vehicle_map[selected_label]
    vehicle = next((v for v in user_vehicles if v["id"] == st.session_state.selected_vehicle_id), user_vehicles[0])

    st.subheader(f"{vehicle.get('label', '')} — {vehicle['make']} {vehicle['model']}")
    st.caption(f"Reg: `{vehicle['registration_number']}` | Year: {vehicle['year']} | {vehicle.get('variant', 'Standard')}")

    col_sb1, col_sb2 = st.columns(2)
    with col_sb1:
        st.metric("Odometer", f"{vehicle['current_mileage']:,} km")
    with col_sb2:
        st.metric("Last Svc", f"{vehicle['last_service_mileage']:,} km")

    # Maintenance Calculation
    sched = database.get_maintenance_schedule(vehicle["id"]) or {"interval_km": 5000, "interval_months": 6}
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
        st.warning(f"⚠️ **Service Approaching**\n\n{status_calc['remaining_km']} km remaining before service milestone.")
    elif status_code == "DUE":
        st.error("🚨 **Service Due Today**\n\nVehicle reached scheduled service milestone.")
    elif status_code == "OVERDUE":
        st.error("🛑 **Service Overdue**\n\nImmediate maintenance recommended.")
    else:
        st.success(f"✅ **Good Standing**\n\n{status_calc['remaining_km']} km remaining until next service.")

    st.markdown("---")
    st.markdown("### Quick Prompts")
    quick_prompts = [
        f"Is my {vehicle['model']} service due?",
        "Show details of Vehicle B",
        "Show my service history",
        "Find service centers near Udaipur",
        "Book an appointment for tomorrow morning"
    ]
    for prompt in quick_prompts:
        if st.button(prompt, key=f"btn_{prompt}", use_container_width=True):
            st.session_state.pending_prompt = prompt

    st.markdown("---")
    if st.button("🔄 Reset Conversation", use_container_width=True):
        st.session_state.messages = [st.session_state.messages[0]]
        st.rerun()

# Main Application Header
st.markdown('<div class="main-title">🚗 AutoCare AI</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-title">Active Vehicle: <b>{vehicle.get("label", "Vehicle")}: {vehicle["make"]} {vehicle["model"]}</b> ({vehicle["registration_number"]})</div>', unsafe_allow_html=True)

# 3 Core Tabs (Chat Assistant, Vehicle Details, Appointments)
tab_chat, tab_dashboard, tab_appointments = st.tabs([
    "💬 Assistant",
    "📊 Vehicle Details",
    "📅 Appointments"
])

# TAB 1: Chat Assistant
with tab_chat:
    # Render Conversation History with Avatars in chronological order
    for msg in st.session_state.messages:
        avatar = "🚗" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

# TAB 2: Vehicle Telemetry & Service History
with tab_dashboard:
    st.markdown(f"##### {vehicle.get('label', 'Active Vehicle')} Specifications & Health")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Make & Model", f"{vehicle['make']} {vehicle['model']}")
    c2.metric("Variant", vehicle.get("variant", "XZ+ Petrol"))
    c3.metric("Current Odometer", f"{vehicle['current_mileage']:,} km")
    c4.metric("Next Target Service", f"{status_calc['next_service_mileage']:,} km")

    st.markdown("---")
    st.markdown("##### Historical Service Records")
    history_records = database.get_service_history(vehicle["id"])
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
        st.info(f"No past service records on file for {vehicle['make']} {vehicle['model']}.")

    st.markdown("---")
    st.markdown("##### Garage Overview — All Registered Vehicles")
    garage_cols = st.columns(len(user_vehicles))
    for idx, v in enumerate(user_vehicles):
        with garage_cols[idx]:
            is_active = (v["id"] == vehicle["id"])
            border_style = "border: 2px solid #2563EB;" if is_active else "border: 1px solid #E2E8F0;"
            badge_html = "<span style='float:right;' class='badge-status-ok'>ACTIVE</span>" if is_active else ""
            st.markdown(f"""
            <div class="metric-card" style="{border_style}">
                <b>{v.get('label', f'Vehicle {idx+1}')}: {v['make']} {v['model']}</b> {badge_html}<br>
                <span style="color: #64748B; font-size: 0.85rem;">
                    Variant: {v.get('variant', 'Standard')}<br>
                    Reg: <code>{v['registration_number']}</code><br>
                    Odometer: <b>{v['current_mileage']:,} km</b> | Last Svc: {v['last_service_mileage']:,} km
                </span>
            </div>
            """, unsafe_allow_html=True)
            if not is_active:
                if st.button(f"Select {v.get('label', v['model'])}", key=f"switch_v_{v['id']}", use_container_width=True):
                    st.session_state.selected_vehicle_id = v["id"]
                    st.rerun()

# TAB 3: Appointments
with tab_appointments:
    st.markdown("##### Scheduled Appointments")
    appts = database.get_appointments(vehicle_id=vehicle["id"])
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
        st.info("No active appointments booked yet. Ask the assistant to book a service appointment!")

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

