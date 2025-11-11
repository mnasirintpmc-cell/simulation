import streamlit as st
from PIL import Image
import json
import os

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
PID_IMAGE = "P&ID.png"
VALVE_ICON = "valve_icon.png"
POSITIONS_FILE = "valve_positions.json"

st.set_page_config(page_title="Interactive P&ID", layout="wide")

# ------------------------------------------------------------------
# LOAD IMAGES
# ------------------------------------------------------------------
@st.cache_data
def load_images():
    return Image.open(PID_IMAGE), Image.open(VALVE_ICON)

pid_img, valve_img = load_images()

# ------------------------------------------------------------------
# LOAD OR INIT STATE
# ------------------------------------------------------------------
if os.path.exists(POSITIONS_FILE):
    with open(POSITIONS_FILE, "r") as f:
        data = json.load(f)
else:
    data = {}

# Default valve list
valve_tags = [
    "V-101", "V-102", "V-103", "V-104", "V-105", "V-106",
    "V-201", "V-202", "V-203", "V-204", "V-205",
    "V-301", "V-302", "V-303", "V-304", "V-305"
]

default_positions = {tag: [100 + 80*i, 300 + 40*(i//6)] for i, tag in enumerate(valve_tags)}

positions = data.get("positions", default_positions)
states = data.get("states", {tag: False for tag in valve_tags})

# ------------------------------------------------------------------
# SAVE STATE
# ------------------------------------------------------------------
def save_state():
    with open(POSITIONS_FILE, "w") as f:
        json.dump({"positions": positions, "states": states}, f, indent=2)

# ------------------------------------------------------------------
# HEADER
# ------------------------------------------------------------------
st.markdown("<h2 style='text-align:center;color:#00BFFF;'>🧭 Interactive P&ID Dashboard</h2>", unsafe_allow_html=True)
st.info("Use the sidebar to toggle valve states. Positions are saved automatically.")

# ------------------------------------------------------------------
# SIDEBAR CONTROLS
# ------------------------------------------------------------------
st.sidebar.header("Valve Controls")
for tag in valve_tags:
    new_state = st.sidebar.toggle(f"{tag} Open", value=states.get(tag, False))
    if new_state != states.get(tag, False):
        states[tag] = new_state
        save_state()
        st.rerun()

# ------------------------------------------------------------------
# MAIN DISPLAY (Overlay simulation)
# ------------------------------------------------------------------
st.image(pid_img, use_container_width=True)
st.markdown("### 💡 Valve State Summary")

cols = st.columns(4)
for i, tag in enumerate(valve_tags):
    with cols[i % 4]:
        color = "green" if states.get(tag, False) else "red"
        st.markdown(
            f"""
            <div style="border:1px solid #555;border-radius:8px;padding:6px;margin:4px;text-align:center;">
                <b style='color:white'>{tag}</b><br>
                <span style='color:{color};font-weight:bold;'>{'OPEN' if states[tag] else 'CLOSED'}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

# ------------------------------------------------------------------
# SAVE ON EXIT
# ------------------------------------------------------------------
save_state()
st.success("✅ Valve states saved to 'valve_positions.json'")
