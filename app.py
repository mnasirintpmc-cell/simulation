import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import io
import time

# -----------------------------------------------------------
# --- PAGE CONFIGURATION
# -----------------------------------------------------------
st.set_page_config(page_title="Dry Gas P&ID Simulator", layout="wide")

# -----------------------------------------------------------
# --- LOAD IMAGE
# -----------------------------------------------------------
try:
    image = Image.open("P&ID.png")
except FileNotFoundError:
    st.error("❌ Could not load 'P&ID.png'. Please make sure it’s in the same folder as app.py.")
    st.stop()

# -----------------------------------------------------------
# --- COMPONENT DEFINITIONS
# -----------------------------------------------------------
valves = ["V-100","V-200","V-300","V-400","V-500","V-600","V-800"]
regulators = ["PCV-100","PCV-200","PCV-300","PCV-400","PCV-501"]
transducers = ["PT-100","PT-200","PT-300","PT-400","PT-500","PT-600"]
flow_meters = ["MFM-100","MFM-200","MFM-300","MFM-400","MFC-1","MFC-2"]

# Initial states
if "states" not in st.session_state:
    st.session_state.states = {tag: False for tag in valves + regulators}
    st.session_state.pressure = 100.0   # bar
    st.session_state.flow = 50.0        # slpm

# -----------------------------------------------------------
# --- SIDEBAR CONTROLS
# -----------------------------------------------------------
st.sidebar.header("Valve & Regulator Control Panel")

st.sidebar.subheader("Valves")
for tag in valves:
    st.session_state.states[tag] = st.sidebar.toggle(f"{tag}", st.session_state.states[tag])

st.sidebar.subheader("Regulators")
for tag in regulators:
    st.session_state.states[tag] = st.sidebar.toggle(f"{tag}", st.session_state.states[tag])

st.sidebar.markdown("---")
if st.sidebar.button("Reset System"):
    for tag in st.session_state.states:
        st.session_state.states[tag] = False
    st.session_state.pressure = 100.0
    st.session_state.flow = 50.0

# -----------------------------------------------------------
# --- SIMULATION LOGIC
# -----------------------------------------------------------
open_valves = sum(st.session_state.states[v] for v in valves)
open_regs = sum(st.session_state.states[r] for r in regulators)

# Very simple model
pressure_drop = open_valves * 5 + open_regs * 2   # bar drop
flow_increase = open_valves * 20 + open_regs * 10 # slpm increase

pressure = max(0, 100 - pressure_drop)
flow = min(1000, 50 + flow_increase)

st.session_state.pressure = pressure
st.session_state.flow = flow

# -----------------------------------------------------------
# --- MAIN LAYOUT
# -----------------------------------------------------------
col1, col2 = st.columns([1.2, 1])

# --- LEFT: P&ID image ---
with col1:
    st.image(image, caption="Process & Instrumentation Diagram", use_column_width=True)

# --- RIGHT: Live readings ---
with col2:
    st.subheader("System Readings")
    st.metric("Total Pressure", f"{pressure:.1f} bar")
    st.metric("Total Flow", f"{flow:.1f} SLPM")

    st.subheader("Component States")
    df = pd.DataFrame({
        "Component": list(st.session_state.states.keys()),
        "State": ["OPEN" if s else "CLOSED" for s in st.session_state.states.values()]
    })
    st.dataframe(df, hide_index=True, use_container_width=True)

# -----------------------------------------------------------
# --- TREND CHART
# -----------------------------------------------------------
st.markdown("### 📈 Pressure & Flow Trend")

if "trend" not in st.session_state:
    st.session_state.trend = pd.DataFrame(columns=["time", "pressure", "flow"])

# Append current reading
new_row = pd.DataFrame({"time":[time.time()], "pressure":[pressure], "flow":[flow]})
st.session_state.trend = pd.concat([st.session_state.trend, new_row], ignore_index=True)
if len(st.session_state.trend) > 100:
    st.session_state.trend = st.session_state.trend.iloc[-100:]

fig, ax1 = plt.subplots()
ax1.plot(st.session_state.trend["time"], st.session_state.trend["pressure"], label="Pressure (bar)")
ax1.set_ylabel("Pressure (bar)")
ax2 = ax1.twinx()
ax2.plot(st.session_state.trend["time"], st.session_state.trend["flow"], color="orange", label="Flow (SLPM)")
ax2.set_ylabel("Flow (SLPM)")
plt.title("Pressure & Flow Over Time")
st.pyplot(fig)

# -----------------------------------------------------------
# --- END
# -----------------------------------------------------------
st.markdown("---")
st.caption("Instant P&ID Simulation • Valves, Regulators, and Readings • Streamlit Cloud Compatible")
