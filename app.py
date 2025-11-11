import streamlit as st
from PIL import Image
from streamlit_drag_and_drop import drag_and_drop
import json
import os

# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

PID_IMAGE = "P&ID.png"          # background image
VALVE_ICON = "valve_icon.png"   # valve symbol
POSITIONS_FILE = "valve_positions.json"

st.set_page_config(page_title="P&ID Simulation", layout="wide")

# ------------------------------------------------------------
# IMAGE LOADING
# ------------------------------------------------------------

@st.cache_data
def load_images():
    pid_img = Image.open(PID_IMAGE)
    valve_img = Image.open(VALVE_ICON)
    return pid_img, valve_img

pid_img, valve_img = load_images()

# ------------------------------------------------------------
# LOAD OR INITIALIZE POSITIONS / STATES
# ------------------------------------------------------------

if os.path.exists(POSITIONS_FILE):
    with open(POSITIONS_FILE, "r") as f:
        data = json.load(f)
else:
    data = {}

# Default valve coordinates (approximate)
default_positions = {
    "V-101": [150, 400],
    "V-102": [280, 410],
    "V-103": [420, 390],
    "V-104": [560, 400],
    "V-105": [710, 430],
    "V-106": [870, 460],
    "V-201": [160, 520],
    "V-202": [300, 530],
    "V-203": [450, 540],
    "V-204": [610, 550],
    "V-205": [770, 560],
    "V-301": [200, 670],
    "V-302": [350, 680],
    "V-303": [500, 690],
    "V-304": [650, 700],
    "V-305": [800, 710],
}

positions = data.get("positions", default_positions)
states = data.get("states", {tag: False for tag in positions.keys()})

# ------------------------------------------------------------
# SAVE STATE HELPER
# ------------------------------------------------------------

def save_state():
    with open(POSITIONS_FILE, "w") as f:
        json.dump({"positions": positions, "states": states}, f, indent=2)

# ------------------------------------------------------------
# PAGE HEADER
# ------------------------------------------------------------

st.markdown(
    "<h2 style='text-align:center; color:#00BFFF;'>🧭 Interactive P&ID Simulation</h2>",
    unsafe_allow_html=True
)

st.info(
    "💡 Drag the valves to position them on your P&ID. "
    "Use the sidebar toggles to open/close each valve. "
    "All positions and states are automatically saved."
)

# ------------------------------------------------------------
# BASE IMAGE DISPLAY
# ------------------------------------------------------------

st.image(PID_IMAGE, use_container_width=True)
st.divider()

# ------------------------------------------------------------
# DRAGGABLE VALVES
# ------------------------------------------------------------

st.subheader("🧩 Drag and drop valves on the P&ID")

new_positions = {}

for tag, (x, y) in positions.items():
    state = states.get(tag, False)
    color = "green" if state else "red"

    # Build small HTML valve icon with tag label
    content = f"""
        <div style='text-align:center;'>
            <img src="{VALVE_ICON}" width="40"
                 style="filter: drop-shadow(0 0 6px {color});"/>
            <br><strong style='color:white; font-size:12px;'>{tag}</strong>
        </div>
    """

    result = drag_and_drop(
        key=tag,
        draggable=True,
        initial_position={"x": x, "y": y},
        content=content,
    )

    new_positions[tag] = [result["x"], result["y"]]

# Save if valve moved
if new_positions != positions:
    positions = new_positions
    save_state()

# ------------------------------------------------------------
# SIDEBAR CONTROLS
# ------------------------------------------------------------

st.sidebar.header("Valve Controls")

for tag in sorted(positions.keys()):
    new_state = st.sidebar.toggle(f"{tag} Open", value=states.get(tag, False))
    if new_state != states.get(tag, False):
        states[tag] = new_state
        save_state()
        st.rerun()

# ------------------------------------------------------------
# SAVE ON EXIT
# ------------------------------------------------------------

save_state()

st.success("✅ All valve positions and states saved successfully.")
st.caption("Positions saved in 'valve_positions.json'")
