import streamlit as st
from PIL import Image, ImageDraw
import random
import time
import pandas as pd

# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(page_title="Dry Gas HMI Simulation", layout="wide")
st.title("🧠 Dry Gas P&ID Simulation HMI")

# -----------------------------
# Load the P&ID image
# -----------------------------
try:
    background = Image.open("P&ID.png")
except FileNotFoundError:
    st.error("❌ Could not find 'P&ID.png' — make sure it's in the same folder as app.py")
    st.stop()

# -----------------------------
# Define instrument positions (based on your drawing)
# Adjust x,y manually to match valve/sensor positions
# -----------------------------
components = {
    "V-101": {"type": "valve", "x": 300, "y": 400, "status": False},
    "V-102": {"type": "valve", "x": 600, "y": 420, "status": False},
    "PT-101": {"type": "pressure", "x": 450, "y": 380, "value": 1.2},
    "PI-101": {"type": "flow", "x": 700, "y": 380, "value": 0.0},
}

# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.header("Valve Controls")

for name, comp in components.items():
    if comp["type"] == "valve":
        components[name]["status"] = st.sidebar.toggle(f"{name} Open/Close", value=comp["status"])

simulate = st.sidebar.button("▶ Run Simulation")

# -----------------------------
# Simulation logic
# -----------------------------
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=["Time", "Valve", "Pressure", "Flow"])

if simulate:
    for name, comp in components.items():
        if comp["type"] == "pressure":
            comp["value"] = round(random.uniform(0.8, 3.5), 2)
        if comp["type"] == "flow":
            open_valves = sum(1 for c in components.values() if c.get("status"))
            comp["value"] = round(open_valves * random.uniform(2.0, 5.0), 2)

    new_data = []
    for name, comp in components.items():
        if comp["type"] in ["pressure", "flow"]:
            new_data.append({
                "Time": pd.Timestamp.now(),
                "Valve": name,
                "Pressure": components["PT-101"]["value"],
                "Flow": components["PI-101"]["value"]
            })
    st.session_state.history = pd.concat([st.session_state.history, pd.DataFrame(new_data)], ignore_index=True)

# -----------------------------
# Draw overlay on P&ID
# -----------------------------
canvas = background.copy()
draw = ImageDraw.Draw(canvas)

for name, comp in components.items():
    x, y = comp["x"], comp["y"]

    if comp["type"] == "valve":
        color = "green" if comp["status"] else "red"
        draw.ellipse((x-15, y-15, x+15, y+15), fill=color, outline="black")
        draw.text((x-20, y+20), name, fill="white")
    elif comp["type"] == "pressure":
        draw.text((x, y), f"{name}: {comp['value']} bar", fill="yellow")
    elif comp["type"] == "flow":
        draw.text((x, y), f"{name}: {comp['value']} slpm", fill="cyan")

st.image(canvas, caption="Live P&ID Simulation", use_container_width=True)

# -----------------------------
# Trend charts
# -----------------------------
st.markdown("---")
st.subheader("📈 Trend Data")

if len(st.session_state.history) > 0:
    st.line_chart(st.session_state.history[["Pressure"]])
    st.line_chart(st.session_state.history[["Flow"]])
else:
    st.info("No trend data yet. Click ▶ Run Simulation to start.")
