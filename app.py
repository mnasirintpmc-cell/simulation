import streamlit as st
import json
import os
from PIL import Image
import base64
from io import BytesIO

# --- FILES ---
PID_FILE = "P&ID.png"
VALVE_FILE = "valve_icon.png"
DATA_FILE = "valves.json"

st.set_page_config(page_title="P&ID Valve Simulation", layout="wide")

# --- LOAD OR INIT DATA ---
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        valves = json.load(f)
else:
    # Default valve positions (you can adjust)
    valves = {
        "V-101": {"x": 150, "y": 400, "state": False},
        "V-102": {"x": 300, "y": 420, "state": False},
        "V-103": {"x": 500, "y": 440, "state": False},
        "V-104": {"x": 650, "y": 460, "state": False},
        "V-105": {"x": 800, "y": 480, "state": False},
        "V-201": {"x": 950, "y": 500, "state": False},
        "V-202": {"x": 1100, "y": 520, "state": False},
        "V-301": {"x": 1250, "y": 540, "state": False},
    }

def save_valves():
    with open(DATA_FILE, "w") as f:
        json.dump(valves, f, indent=4)

# --- ENCODE IMAGE FOR HTML ---
def img_to_base64(path):
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

pid_b64 = img_to_base64(PID_FILE)
valve_b64 = img_to_base64(VALVE_FILE)

# --- PAGE TITLE ---
st.markdown("<h2 style='text-align:center;'>🧭 P&ID Valve Control Simulation</h2>", unsafe_allow_html=True)

# --- BUILD HTML ---
html = f"""
<div style='
    position: relative;
    display: inline-block;
    margin: auto;
'>
    <img src="data:image/png;base64,{pid_b64}" style="width:100%; height:auto; display:block;"/>
"""

for name, data in valves.items():
    color = "drop-shadow(0 0 5px green)" if data["state"] else "drop-shadow(0 0 5px red)"
    html += f"""
    <div 
        style="position: absolute; left:{data['x']}px; top:{data['y']}px; cursor:pointer;" 
        onclick="toggleValve('{name}')"
    >
        <img src="data:image/png;base64,{valve_b64}" width="30" style="filter: {color};"/>
        <div style="color:white; text-align:center; font-weight:bold;">{name}</div>
    </div>
    """

html += """
</div>

<script>
function toggleValve(tag) {
    window.parent.postMessage({type:'toggle', valve: tag}, '*');
}
</script>
"""

# --- DISPLAY ---
st.components.v1.html(html, height=900, scrolling=True)

# --- TOGGLE HANDLER ---
if "toggle_valve" not in st.session_state:
    st.session_state.toggle_valve = None

msg = st.experimental_get_query_params().get("valve", [None])[0]
if msg and msg in valves:
    valves[msg]["state"] = not valves[msg]["state"]
    save_valves()
    st.experimental_set_query_params()  # clear URL params
    st.rerun()

# --- SIDEBAR: Position Adjustment ---
st.sidebar.header("Adjust Valve Positions")
valve_name = st.sidebar.selectbox("Select valve:", list(valves.keys()))
x = st.sidebar.number_input("X position (px):", value=valves[valve_name]["x"])
y = st.sidebar.number_input("Y position (px):", value=valves[valve_name]["y"])
if st.sidebar.button("💾 Save Position"):
    valves[valve_name]["x"] = int(x)
    valves[valve_name]["y"] = int(y)
    save_valves()
    st.sidebar.success("Position saved!")

st.sidebar.markdown("---")
st.sidebar.info("Click valves directly on the diagram to toggle their state.\nAll data is stored in `valves.json`.")
