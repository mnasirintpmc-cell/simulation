import streamlit as st
import json
import os

# --- FILE SETUP ---
DATA_FILE = "valves.json"
BACKGROUND_IMAGE = "pid_diagram.png"  # Replace with your actual P&ID image name

# --- LOAD / INIT STATE ---
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        valves = json.load(f)
else:
    valves = {
        "valve_1": {"x": 100, "y": 120, "state": "Closed"},
        "valve_2": {"x": 220, "y": 150, "state": "Closed"},
        "valve_3": {"x": 300, "y": 200, "state": "Closed"},
        "valve_4": {"x": 400, "y": 250, "state": "Closed"},
        "valve_5": {"x": 500, "y": 300, "state": "Closed"},
        "valve_6": {"x": 600, "y": 350, "state": "Closed"},
        "valve_7": {"x": 700, "y": 400, "state": "Closed"},
        "valve_8": {"x": 800, "y": 450, "state": "Closed"},
    }

# --- FUNCTIONS ---
def save_positions():
    with open(DATA_FILE, "w") as f:
        json.dump(valves, f, indent=4)

def toggle_valve(key):
    valves[key]["state"] = "Open" if valves[key]["state"] == "Closed" else "Closed"
    save_positions()

# --- PAGE CONFIG ---
st.set_page_config(page_title="P&ID Valve Layout", layout="wide")
st.title("🧭 P&ID Valve Layout Editor")

# --- SIDEBAR ---
st.sidebar.header("Valve Settings")
selected_valve = st.sidebar.selectbox("Select a valve to move:", list(valves.keys()))
x = st.sidebar.number_input("X position", value=valves[selected_valve]["x"])
y = st.sidebar.number_input("Y position", value=valves[selected_valve]["y"])
if st.sidebar.button("Update Position"):
    valves[selected_valve]["x"] = x
    valves[selected_valve]["y"] = y
    save_positions()
    st.sidebar.success("Position updated and saved!")

# --- MAIN AREA ---
st.markdown(
    f"""
    <div style='position: relative; display: inline-block;'>
        <img src='{BACKGROUND_IMAGE}' style='width: 100%; height: auto;'>
    """,
    unsafe_allow_html=True
)

# --- DRAW VALVES ON TOP OF IMAGE ---
for key, v in valves.items():
    button_html = f"""
        <button 
            style="
                position: absolute;
                left: {v['x']}px;
                top: {v['y']}px;
                width: 30px;
                height: 30px;
                border-radius: 50%;
                border: none;
                cursor: pointer;
                background-color: {'green' if v['state'] == 'Open' else 'red'};
                color: white;
                font-size: 10px;
            "
            onclick="fetch('/?toggle={key}', {{method:'POST'}})">
            {key.split('_')[-1]}
        </button>
    """
    st.markdown(button_html, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
