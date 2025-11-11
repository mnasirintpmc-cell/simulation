import streamlit as st
from PIL import Image
import json
import base64
import os

# --- File Paths ---
PID_IMAGE = "P&ID.png"
VALVE_ICON = "valve_icon.png"
POSITIONS_FILE = "valve_positions.json"

# --- Load images ---
@st.cache_data
def load_images():
    pid_img = Image.open(PID_IMAGE)
    valve_img = Image.open(VALVE_ICON)
    return pid_img, valve_img

pid_img, valve_img = load_images()

# --- Initialize session states ---
if "positions" not in st.session_state:
    if os.path.exists(POSITIONS_FILE):
        with open(POSITIONS_FILE, "r") as f:
            st.session_state.positions = json.load(f)
    else:
        st.session_state.positions = {
            "V-101": [150, 400],
            "V-102": [300, 420],
            "V-103": [500, 440],
            "V-301": [700, 460],
            "V-302": [900, 480],
        }

if "states" not in st.session_state:
    st.session_state.states = {tag: False for tag in st.session_state.positions.keys()}

# --- Save positions & states ---
def save_state():
    with open(POSITIONS_FILE, "w") as f:
        json.dump(st.session_state.positions, f)

# --- Helper to encode image for HTML display ---
def get_base64(image):
    from io import BytesIO
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

pid_b64 = get_base64(pid_img)
valve_b64 = get_base64(valve_img)

# --- Build HTML for overlay ---
html = f"""
<div style='position: relative; display: inline-block;'>
    <img src='data:image/png;base64,{pid_b64}' style='width:100%; height:auto;'/>
"""

# Dynamic overlay of valves + toggles
for tag, (x, y) in st.session_state.positions.items():
    state = st.session_state.states.get(tag, False)
    color = "green" if state else "red"
    html += f"""
    <div style='position: absolute; left:{x}px; top:{y}px;'>
        <img src="data:image/png;base64,{valve_b64}" width="30" style="filter: drop-shadow(0 0 5px {color});"/>
        <label style="color:white; font-weight:bold; margin-left:5px;">{tag}</label><br>
        <input type="checkbox" id="{tag}" {'checked' if state else ''} 
               onclick="toggleValve('{tag}')"/>
    </div>
    """

html += """
</div>
<script>
function toggleValve(tag) {
    window.parent.postMessage({type:'toggle', valve:tag}, '*');
}
</script>
"""

# --- Streamlit UI ---
st.markdown("<h3 style='text-align:center;'>P&ID Simulation Control Panel</h3>", unsafe_allow_html=True)
st.components.v1.html(html, height=800, scrolling=True)

# --- Listen for toggle events ---
message = st.experimental_get_query_params().get("msg", [""])[0]
if message:
    st.write(message)

# --- Manual toggle fallback (streamlit sync) ---
for tag in st.session_state.positions.keys():
    new_state = st.sidebar.toggle(tag, value=st.session_state.states[tag])
    if new_state != st.session_state.states[tag]:
        st.session_state.states[tag] = new_state
        save_state()
        st.rerun()
