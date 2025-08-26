import time
import requests
import streamlit as st

API = "http://localhost:8000"

st.set_page_config(page_title="Email Agent Monitor", layout="wide")
st.title("Email Agent — Live Monitor")

col1, col2 = st.columns(2)
with col1:
    try:
        st.metric("Agent Status", requests.get(f"{API}/status").json()["state"])
    except:
        st.metric("Agent Status", "offline")
with col2:
    if st.button("Manual trigger"):
        try:
            requests.post(f"{API}/trigger-run")
        except:
            pass

st.subheader("Recent Logs")
logs_placeholder = st.empty()

st.subheader("Escalations")
esc_placeholder = st.empty()


def load_logs():
    try:
        return requests.get(f"{API}/logs?limit=50").json()
    except:
        return []


def load_escalations():
    try:
        return requests.get(f"{API}/escalations?limit=50").json()
    except:
        return []


refresh_sec = st.slider("Auto-refresh (seconds)", 2, 10, 3)

while True:
    logs = load_logs()
    escs = load_escalations()
    logs_placeholder.dataframe(logs, use_container_width=True)
    esc_placeholder.dataframe(escs, use_container_width=True)
    time.sleep(refresh_sec)
