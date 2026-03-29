import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import time

BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(layout="wide")

st.markdown("""
<style>
body { background-color: #0f172a; color: white; }
.stApp { background-color: #0f172a; }
.block-container { padding-top: 1rem; }
.alert-box {
    padding: 10px;
    border-radius: 10px;
    margin-bottom: 5px;
    animation: pulse 1.5s infinite;
}
@keyframes pulse {
    0% {opacity: 1;}
    50% {opacity: 0.6;}
    100% {opacity: 1;}
}
iframe {
    border-radius: 15px;
    border: 1px solid #1e293b;
}
</style>
""", unsafe_allow_html=True)

if "incidents" not in st.session_state:
    st.session_state.incidents = {}

if "alerts" not in st.session_state:
    st.session_state.alerts = []

try:
    res = requests.get(f"{BASE_URL}/all_incidents", timeout=5)
    all_data = res.json()

    if isinstance(all_data, list):
        for item in all_data:
            incident_id = item["id"]

            if incident_id not in st.session_state.incidents:
                st.session_state.incidents[incident_id] = {
                    "type": item["type"],
                    "lat": item["lat"],
                    "lon": item["lon"],
                    "status": "pending"
                }
except Exception:
    st.error("⚠ Failed to fetch incidents from server")

for incident_id in list(st.session_state.incidents.keys()):
    try:
        res = requests.get(f"{BASE_URL}/check_status/{incident_id}", timeout=5)
        status = res.json().get("status", "pending")

        old_status = st.session_state.incidents[incident_id]["status"]

        if old_status != status:
            st.session_state.alerts.append(f"{incident_id} → {status}")

        st.session_state.incidents[incident_id]["status"] = status
    except Exception:
        pass

st.title("🚨 DISTRIBUTED DISPATCH SYSTEM")
st.caption("FastAPI + RabbitMQ + Redis + Postgres")

m = folium.Map(location=[12.9716, 77.5946], zoom_start=13)
cluster = MarkerCluster().add_to(m)

for incident_id, data in st.session_state.incidents.items():
    color = "red"
    if data["status"] == "dispatched":
        color = "blue"
    elif data["status"] == "resolved":
        color = "green"

    folium.Marker(
        [data["lat"], data["lon"]],
        popup=f"{incident_id} - {data['type']} ({data['status']})",
        icon=folium.Icon(color=color)
    ).add_to(cluster)

map_data = st_folium(m, height=500, use_container_width=True)

if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]

    st.success(f"📍 Location: {lat:.4f}, {lon:.4f}")

    incident_type = st.selectbox(
        "Emergency Type",
        ["Fire", "Medical", "Police"]
    )

    if st.button("🚨 Send Emergency"):
        try:
            res = requests.post(
                f"{BASE_URL}/report_emergency",
                params={
                    "incident_type": incident_type,
                    "lat": lat,
                    "lon": lon,
                    "desc": "Streamlit Alert"
                },
                timeout=5
            )

            data = res.json()

            if "incident_id" in data:
                st.session_state.incidents[data["incident_id"]] = {
                    "type": incident_type,
                    "lat": lat,
                    "lon": lon,
                    "status": "pending"
                }
                st.success(f"Incident Created: {data['incident_id']}")
            else:
                st.error(f"Failed to create incident: {data}")
        except Exception as e:
            st.error(f"Backend request failed: {e}")

st.sidebar.title("📡 Live Alerts")

active = sum(1 for i in st.session_state.incidents.values() if i["status"] != "resolved")
resolved = sum(1 for i in st.session_state.incidents.values() if i["status"] == "resolved")

st.sidebar.metric("Active", active)
st.sidebar.metric("Resolved", resolved)

st.sidebar.markdown("---")

for alert in st.session_state.alerts[-5:]:
    st.sidebar.markdown(
        f'<div class="alert-box" style="background:#1e293b;border-left:4px solid #ef4444;">🚨 {alert}</div>',
        unsafe_allow_html=True
    )

st.subheader("📋 Incident Log")

for incident_id, data in st.session_state.incidents.items():
    if data["status"] == "pending":
        st.warning(f"{incident_id} - {data['type']} (Pending)")
    elif data["status"] == "dispatched":
        st.info(f"{incident_id} - {data['type']} (Dispatched)")
    elif data["status"] == "resolved":
        st.success(f"{incident_id} - {data['type']} (Resolved)")

time.sleep(2)
st.rerun()