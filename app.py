import streamlit as st
import json
from PIL import Image
import os

PID_FILE = "P&ID.png"
VALVE_FILE = "valve_icon.png"
DATA_FILE = "valves.json"

st.set_page_config(layout="wide")

# Load/save valve data
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        valves = json.load(f)
else:
    valves = {
        "valve_2": {"x": 220, "y": 150, "state": False},
        "valve_3": {"x": 300, "y": 200, "state": False},
        "valve_4": {"x": 400, "y": 250, "state": False},
        "valve_5": {"x": 500, "y": 300, "state": False},
        "valve_6": {"x": 600, "y": 350, "state": False},
    }

def save_valves():
    with open(DATA_FILE, "w") as f:
        json.dump(valves, f, indent=4)

# Load images
pid_img = Image.open(PID_FILE)
valve_img = Image.open(VALVE_FILE)

# Display P&ID
st.image(pid_img, use_column_width=True)

# Overlay valves
for name, data in valves.items():
    col1, col2 = st.columns([data['x'], 1])
    with col2:
        color = "🟢" if data["state"] else "🔴"
        if st.button(f"{color} {name}"):
            valves[name]["state"] = not valves[name]["state"]
            save_valves()
            st.experimental_rerun()

# Sidebar to adjust positions
st.sidebar.header("Adjust valve positions")
sel = st.sidebar.selectbox("Select valve", list(valves.keys()))
x = st.sidebar.number_input("X position", value=valves[sel]["x"])
y = st.sidebar.number_input("Y position", value=valves[sel]["y"])
if st.sidebar.button("💾 Save position"):
    valves[sel]["x"] = int(x)
    valves[sel]["y"] = int(y)
    save_valves()
    st.sidebar.success("Saved!")
