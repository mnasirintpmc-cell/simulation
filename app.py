import streamlit as st
import pandas as pd
import time
from PIL import Image

# -----------------------------
# Load P&ID background
# -----------------------------
st.set_page_config(page_title="P&ID Valve Simulation", layout="wide")

st.title("🧪 Dry Gas Simulation – P&ID Interactive Demo")

# Try to load the P&ID image
try:
    image = Image.open("P&ID.png")
    st.image(image, caption="Plant P&ID Diagram", use_container_width=True)
except FileNotFoundError:
    st.error("❌ Could not load 'P&ID.png'. Please make sure it’s in the same folder as app.py.")
    st.stop()

st.markdown("---")

# -----------------------------
# Define valves and sensors
# -----------------------------
valves = {
    "V-101": {"status": False, "pressure": 1.2, "flow": 0.0},
    "V-102": {"status": False, "pressure": 1.0, "flow": 0.0},
    "V-201": {"status": False, "pressure": 2.3, "flow": 0.0},
    "V-301": {"status": False, "pressure": 3.5, "flow": 0.0},
    "V-401": {"status": False, "pressure": 4.2, "flow": 0.0},
}

# -----------------------------
# Sidebar – Control valves
# -----------------------------
st.sidebar.header("Valve Control Panel")

for tag, data in valves.items():
    new_state = st.sidebar.toggle(f"{tag} Open/Close", value=data["status"])
    valves[tag]["status"] = new_state

st.sidebar.markdown("---")
simulate = st.sidebar.button("▶ Start Simulation")

# -----------------------------
# Simulation logic
# -----------------------------
if "trend" not in st.session_state:
    st.session_state.trend = pd.DataFrame(columns=["Valve", "Pressure", "Flow", "Timestamp"])

if simulate:
    with st.spinner("Simulating flow & pressure..."):
        time.sleep(1.5)

        # update readings
        new_data = []
        for tag, v in valves.items():
            if v["status"]:
                v["flow"] = round(5 + 10 * v["pressure"], 2)
                v["pressure"] = round(v["pressure"] + 0.2, 2)
            else:
                v["flow"] = 0
                v["pressure"] = max(0.5, v["pressure"] - 0.1)

            new_data.append({
                "Valve": tag,
                "Pressure": v["pressure"],
                "Flow": v["flow"],
                "Timestamp": pd.Timestamp.now()
            })

        st.session_state.trend = pd.concat([st.session_state.trend, pd.DataFrame(new_data)], ignore_index=True)

# -----------------------------
# Display live table
# -----------------------------
st.subheader("📋 Live Valve Data")
df = pd.DataFrame([{**{"Valve": k}, **v} for k, v in valves.items()])
st.dataframe(df, use_container_width=True)

# -----------------------------
# Trend visualization
# -----------------------------
st.subheader("📈 Pressure & Flow Trends")

if len(st.session_state.trend) > 0:
    selected_valves = st.multiselect("Select valves to display", valves.keys(), default=list(valves.keys()))
    filtered = st.session_state.trend[st.session_state.trend["Valve"].isin(selected_valves)]

    st.line_chart(
        filtered.pivot(index="Timestamp", columns="Valve", values="Pressure"),
        use_container_width=True,
    )
    st.line_chart(
        filtered.pivot(index="Timestamp", columns="Valve", values="Flow"),
        use_container_width=True,
    )
else:
    st.info("No simulation data yet. Click ▶ Start Simulation to begin.")

st.markdown("---")
st.caption("Built with ❤️ using Streamlit")
