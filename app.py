import streamlit as st
import json
import os
from PIL import Image
import base64
from io import BytesIO

# ---------------- FILES ----------------
PID_FILE = "P&ID.png"
VALVE_FILE = "valve_icon.png"
DATA_FILE = "valves.json"

st.set_page_config(page_title="P&ID Valve Simulation", layout="wide")

# ---------------- LOAD / INIT DATA ----------------
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        valves = json.load(f)
else:
    valves = {
        "V-101": {"x": 150, "y": 150, "state": False},
        "V-102": {"x": 300, "y": 200, "state": False},
        "V-103": {"x": 400, "y": 250, "state": False},
        "V-104": {"x": 500, "y": 300, "state": False},
        "V-105": {"x": 600, "y": 350, "state": False},
        "V-201": {"x": 700, "y": 400, "state": False},
        "V-202": {"x": 800, "y": 450, "state": False},
        "V-301": {"x": 900, "y": 500, "state": False},
    }

def save_valves():
    with open(DATA_FILE, "w") as f:
        json.dump(valves, f, indent=4)

# ---------------- IMAGE HELPERS ----------------
@st.cache_data
def load_image_b64(path):
    img = Image.open(path)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

pid_b64 = load_image_b64(PID_FILE)
valve_b64 = load_image_b64(VALVE_FILE)

# ---------------- PAGE TITLE ----------------
st.markdown("<h2 style='text-align:center;'>🧭 P&ID Valve Simulation</h2>", unsafe_allow_html=True)

# ---------------- LAYOUT ----------------
col1, col2 = st.columns([4, 1], gap="large")

with col1:
    # Show background
    st.markdown(
        f"""
        <div style='position:relative; display:inline-block;'>
            <img src='data:image/png;base64,{pid_b64}' style='width:100%; height:auto; display:block;'/>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Overlay valves
    buttons_html = "<div style='position:relative; top:-600px;'>"
    for name, data in valves.items():
        color = "green" if data["state"] else "red"
        buttons_html += f"""
            <div style="position:absolute; left:{data['x']}px; top:{data['y']}px; cursor:pointer;">
                <form action="#" method="get">
                    <input type="hidden" name="valve" value="{name}">
                    <button type="submit"
                        style="
                            background:none;
                            border:none;
                            padding:0;
                            cursor:pointer;
                        ">
                        <img src='data:image/png;base64,{valve_b64}' width="40" style="filter: drop-shadow(0 0 5px {color});"/>
                    </button>
                </form>
            </div>
        """
    buttons_html += "</div>"
    st.markdown(buttons_html, unsafe_allow_html=True)

# ---------------- TOGGLE HANDLER ----------------
query_params = st.experimental_get_query_params()
if "valve" in query_params:
    v = query_params["valve"][0]
    if v in valves:
        valves[v]["state"] = not valves[v]["state"]
        save_valves()
        st.experimental_set_query_params()  # clear URL
        st.rerun()

# ---------------- SIDEBAR ----------------
st.sidebar.header("Adjust Valve Positions")
sel = st.sidebar.selectbox("Select valve", list(valves.keys()))
x = st.sidebar.number_input("X position (px)", value=valves[sel]["x"])
y = st.sidebar.number_input("Y position (px)", value=valves[sel]["y"])
if st.sidebar.button("💾 Save Position"):
    valves[sel]["x"] = int(x)
    valves[sel]["y"] = int(y)
    save_valves()
    st.sidebar.success(f"{sel} position saved!")

st.sidebar.markdown("---")
st.sidebar.info(
    "Click any valve icon on the diagram to toggle its state.\n"
    "All positions and states are saved in `valves.json`."
)
