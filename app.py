import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw
import pytesseract
import plotly.express as px

# ------------------------------------
# PAGE CONFIG
# ------------------------------------
st.set_page_config(page_title="P&ID Valve Simulator", layout="wide")
st.title("🛠️ P&ID Valve Simulation Tool (with OCR Detection)")

# ------------------------------------
# LOAD BASE IMAGE
# ------------------------------------
try:
    base_img = Image.open("P&ID.png").convert("RGB")
except Exception as e:
    st.error("❌ Could not load 'P&ID.png'. Please make sure it’s in the same folder as app.py.")
    st.stop()

# ------------------------------------
# OCR: DETECT VALVE TAGS
# ------------------------------------
st.subheader("🔍 Detecting valve tags from P&ID...")

ocr_data = pytesseract.image_to_data(base_img, output_type=pytesseract.Output.DICT)

valves_detected = []
for i, text in enumerate(ocr_data['text']):
    if text.strip() != "" and text.upper().startswith("V"):  # detect V1, V2, V101, etc.
        x = ocr_data['left'][i]
        y = ocr_data['top'][i]
        w = ocr_data['width'][i]
        h = ocr_data['height'][i]
        valves_detected.append({
            "id": text.strip(),
            "x": x,
            "y": y,
            "w": w,
            "h": h
        })

st.write(f"✅ Detected {len(valves_detected)} valves: {[v['id'] for v in valves_detected]}")

# ------------------------------------
# INIT SESSION STATE
# ------------------------------------
if 'valves' not in st.session_state:
    st.session_state['valves'] = []
if 'data' not in st.session_state:
    st.session_state['data'] = pd.DataFrame(columns=["Valve ID", "Status", "Flow (SLPM)", "Pressure (bar)", "Temperature (°C)"])

# ------------------------------------
# LOAD VALVES FROM OCR
# ------------------------------------
if len(st.session_state['valves']) == 0 and len(valves_detected) > 0:
    for v in valves_detected:
        st.session_state['valves'].append({
            "id": v['id'],
            "x": int(v['x'] / base_img.width * 100),
            "y": int(v['y'] / base_img.height * 100),
            "status": "Closed"
        })
        new_row = {
            "Valve ID": v['id'],
            "Status": "Closed",
            "Flow (SLPM)": 0,
            "Pressure (bar)": 0,
            "Temperature (°C)": 25
        }
        st.session_state['data'] = pd.concat([st.session_state['data'], pd.DataFrame([new_row])], ignore_index=True)

# ------------------------------------
# SIDEBAR CONTROLS
# ------------------------------------
st.sidebar.header("⚙️ Valve Controls")

if len(st.session_state['valves']) == 0:
    st.sidebar.info("No valves detected. Add manually.")
else:
    st.sidebar.success(f"{len(st.session_state['valves'])} valves loaded from P&ID")

# Toggle valve states
for valve in st.session_state['valves']:
    if st.sidebar.button(f"{valve['id']} - {valve['status']}"):
        valve['status'] = "Open" if valve['status'] == "Closed" else "Closed"
        st.session_state['data'].loc[
            st.session_state['data']['Valve ID'] == valve['id'], "Status"
        ] = valve['status']

        # simulate flow and pressure
        if valve['status'] == "Open":
            flow = np.random.uniform(10, 100)
            pressure = np.random.uniform(1, 5)
            temp = np.random.uniform(20, 40)
        else:
            flow = 0
            pressure = np.random.uniform(0.9, 1.1)
            temp = np.random.uniform(20, 25)

        st.session_state['data'].loc[
            st.session_state['data']['Valve ID'] == valve['id'],
            ["Flow (SLPM)", "Pressure (bar)", "Temperature (°C)"]
        ] = [flow, pressure, temp]

# ------------------------------------
# DRAW IMAGE WITH VALVES
# ------------------------------------
img = base_img.copy()
draw = ImageDraw.Draw(img)
w, h = img.size

for valve in st.session_state['valves']:
    x = int(valve['x'] / 100 * w)
    y = int(valve['y'] / 100 * h)
    color = "green" if valve['status'] == "Open" else "red"
    r = 15
    draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=color)
    draw.text((x + 20, y - 10), valve['id'], fill="white")

st.image(img, caption="🧩 P&ID with Detected Valves", use_container_width=True)

# ------------------------------------
# EDITABLE TABLE
# ------------------------------------
st.subheader("📊 Valve Data Table (Editable)")
edited_data = st.data_editor(st.session_state['data'], num_rows="dynamic", key="data_editor")
st.session_state['data'] = edited_data

# ------------------------------------
# DOWNLOAD CSV
# ------------------------------------
st.download_button(
    label="💾 Download CSV",
    data=st.session_state['data'].to_csv(index=False).encode('utf-8'),
    file_name="valve_simulation_data.csv",
    mime="text/csv"
)

# ------------------------------------
# TRENDS
# ------------------------------------
st.divider()
st.subheader("📈 Valve Trends")

if not st.session_state['data'].empty:
    selected_valve = st.selectbox("Select Valve for Trend", st.session_state['data']["Valve ID"].unique())
    valve_data = st.session_state['data'][st.session_state['data']["Valve ID"] == selected_valve]

    c1, c2, c3 = st.columns(3)

    with c1:
        fig_flow = px.bar(valve_data, x="Valve ID", y="Flow (SLPM)", title="Flow (SLPM)", color="Flow (SLPM)")
        st.plotly_chart(fig_flow, use_container_width=True)

    with c2:
        fig_pressure = px.bar(valve_data, x="Valve ID", y="Pressure (bar)", title="Pressure (bar)", color="Pressure (bar)")
        st.plotly_chart(fig_pressure, use_container_width=True)

    with c3:
        fig_temp = px.bar(valve_data, x="Valve ID", y="Temperature (°C)", title="Temperature (°C)", color="Temperature (°C)")
        st.plotly_chart(fig_temp, use_container_width=True)
else:
    st.info("No data to plot yet. Add or toggle valves to generate data.")
