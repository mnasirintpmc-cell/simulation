import streamlit as st
import json
import os
from PIL import Image
import base64
from io import BytesIO

# ---------------------------------------------------------------------
# FILES
# ---------------------------------------------------------------------
PID_FILE = "P&ID.png"
VALVE_FILE = "valve_icon.png"
DATA_FILE = "valves.json"

st.set_page_config(page_title="P&ID Valve Simulation", layout="wide")

# ---------------------------------------------------------------------
# LOAD / INIT DATA
# ---------------------------------------------------------------------
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        valves = json.load(f)
else:
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

# ---------------------------------------------------------------------
# IMAGE HELPERS
# ---------------------------------------------------------------------
@st.cache_data
def load_image_b64(path):
    img = Image.open(path)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

pid_b64 = load_image_b64(PID_FILE)
valve_b64 = load_image_b64(VALVE_FILE)

# ---------------------------------------------------------------------
# MAIN TITLE
# ---------------------------------------------------------------------
st.markdown("<h2 style='text-align:center;'>🧭 P&ID Valve Simulation</h2>", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# LAYOUT
# ---------------------------------------------------------------------
col1, col2 = st.columns([4, 1], gap="large")

with col1:
    # background container
    st.markdown(
        f"""
        <div style='position:relative; display:inline-block;'>
            <img src='data:image/png;base64,{pid_b64}' style='width:100%; height:auto; display:block;'/>
        </div>
        """,
        unsafe_allow_html=True
    )

    # overlay Streamlit buttons as absolute positioned HTML
    buttons_html = "<div style='position:relative; top:-900px;'>"
    for name, data in valves.items():
        color = "green" if data["state"] else "red"
        buttons_html += f"""
            <div style="position:absolute; left:{data['x']}px; top:{data['y']}px;">
                <form action="#" method="get">
                    <input type="hidden" name="valve" value="{name}">
                    <button type="submit"
                        style="
                            background-color:{color};
                            color:white;
                            width:30px;
                            height:30px;
                            border:none;
                            border-radius:50%;
                            font-size:12px;
                            font-weight:bold;
                            cursor:pointer;
                            ">
                        {name.split('-')[-1]}
                    </button>
                </form>
            </div>
        """
    buttons_html += "</div>"
    st.markdown(buttons_html, unsafe_allow_html=True)

# ---------------------------------------------------------------------
# TOGGLE HANDLER
# ---------------------------------------------------------------------
query_params = st.query_params
if "valve" in query_params:
    v = query_params["valve"]
    if v in valves:
        valves[v]["state"] = not valves[v]["state"]
        save_valves()
        st.query_params.clear()
        st.rerun()

# ---------------------------------------------------------------------
# SIDEBAR CONTROLS
# ---------------------------------------------------------------------
with col2:
    st.subheader("Valve Position Setup")
    sel = st.selectbox("Select valve", list(valves.keys()))
    x = st.number_input("X position (px)", value=valves[sel]["x"])
    y = st.number_input("Y position (px)", value=valves[sel]["y"])
    if st.button("💾 Save Position"):
        valves[sel]["x"] = int(x)
        valves[sel]["y"] = int(y)
        save_valves()
        st.success(f"{sel} position saved.")
    st.markdown("---")
    st.info("Click any valve on the diagram to toggle it.\n"
            "Valve positions and states are stored in `valves.json`.")
