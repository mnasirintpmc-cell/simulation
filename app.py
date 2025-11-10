# app.py
import streamlit as st
import pandas as pd
import numpy as np
import time
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
from io import BytesIO

# -----------------------
# Page config
# -----------------------
st.set_page_config(page_title="P&ID Live Simulator", layout="wide")
st.title("🔁 P&ID Live Simulation — Dynamic (Option B)")

# -----------------------
# Configuration / Tags
# -----------------------
# Hard-coded tags from your P&ID (you can edit/add as needed)
VALVE_TAGS = [
    "V-101","V-102","V-103","V-104","V-301","V-302","V-501","V-601",
    "CV-1","CV-2","CV-3","CV-4",
    "MPV-1","MPV-6","MPV-7","MPV-8",
    # Add more tags here if needed
]

SENSOR_TAGS = [
    "PT-101","PT-102","PT-103","PT-104","PT-105","PT-601","PT-602"
]

FLOW_TAGS = [
    "MFM-100","MFM-200","MFM-300","MFM-400","MFC-1/2"
]

# Nominal values for simulation (you can tune per tag)
DEFAULT_NOMINAL = {}
for t in VALVE_TAGS:
    DEFAULT_NOMINAL[t] = {"flow": float(np.random.uniform(5, 50)), "pressure": float(np.random.uniform(0.5, 10))}
for t in SENSOR_TAGS:
    DEFAULT_NOMINAL[t] = {"pressure": float(np.random.uniform(0.5, 10))}
for t in FLOW_TAGS:
    DEFAULT_NOMINAL[t] = {"flow": float(np.random.uniform(20, 500))}

# positions: optional mapping of tag -> (x_pct, y_pct) for overlay (0-100)
# You can fill these in manually to match the diagram. If left empty, no overlays.
DEFAULT_POSITIONS = {
    # Example positions (approx) - adjust as needed by entering correct percents
    "V-101": (12, 20),
    "V-102": (28, 20),
    "V-103": (45, 20),
    "V-104": (60, 20),
    "V-301": (12, 55),
    "V-302": (28, 55),
    "V-501": (82, 18),
    "V-601": (8, 85),
    # Add more coordinates if you want image overlay
}

# -----------------------
# Session state init
# -----------------------
if "sim_running" not in st.session_state:
    st.session_state.sim_running = False
if "time_index" not in st.session_state:
    st.session_state.time_index = 0
if "history" not in st.session_state:
    # history: DataFrame indexed by time with columns for each tag signal
    st.session_state.history = pd.DataFrame()
if "valve_states" not in st.session_state:
    # default closed
    st.session_state.valve_states = {t: False for t in VALVE_TAGS}
if "component_values" not in st.session_state:
    # current instantaneous values
    st.session_state.component_values = {}
    for t in VALVE_TAGS:
        st.session_state.component_values[f"{t}_flow"] = 0.0
        st.session_state.component_values[f"{t}_pressure"] = DEFAULT_NOMINAL[t]["pressure"]
    for t in FLOW_TAGS:
        st.session_state.component_values[f"{t}_flow"] = DEFAULT_NOMINAL[t]["flow"]
    for t in SENSOR_TAGS:
        st.session_state.component_values[f"{t}_pressure"] = DEFAULT_NOMINAL[t]["pressure"]

# -----------------------
# Load P&ID image
# -----------------------
st.sidebar.header("Diagram")
uploaded = st.sidebar.file_uploader("Upload P&ID image (optional)", type=["png","jpg","jpeg"])
if uploaded:
    try:
        img = Image.open(uploaded).convert("RGB")
    except Exception:
        st.sidebar.error("Failed to open uploaded image.")
        img = None
else:
    try:
        img = Image.open("P&ID.png").convert("RGB")
    except Exception:
        img = None

# -----------------------
# Controls panel (left)
# -----------------------
left, center, right = st.columns([1, 2, 1])

with left:
    st.header("Controls")
    st.markdown("**Valve states** (toggle to open/close). Changes take effect in the running simulation immediately.")

    # Group valves into expandable sections for readability
    val_chunks = [VALVE_TAGS[i:i+8] for i in range(0, len(VALVE_TAGS), 8)]
    for chunk in val_chunks:
        with st.expander("Valves: " + ", ".join(chunk), expanded=False):
            for tag in chunk:
                state = st.checkbox(f"{tag}", value=st.session_state.valve_states.get(tag, False), key=f"chk_{tag}")
                st.session_state.valve_states[tag] = state

    st.markdown("---")
    st.markdown("**Other controls**")
    sim_step = st.slider("Simulation step (seconds)", min_value=0.1, max_value=2.0, value=0.5, step=0.1)
    smoothing = st.slider("Dynamics smoothing (0-1, larger = slower response)", 0.0, 0.99, 0.6, 0.01)
    noise_amp = st.slider("Noise amplitude (fraction of nominal)", 0.0, 0.5, 0.05, 0.01)

    if not st.session_state.sim_running:
        if st.button("▶ Start Simulation"):
            st.session_state.sim_running = True
            st.experimental_rerun()
    else:
        if st.button("⛔ Stop Simulation"):
            st.session_state.sim_running = False
            st.experimental_rerun()

    if st.button("⏹ Reset History"):
        st.session_state.time_index = 0
        st.session_state.history = pd.DataFrame()
        # reset current component values to nominal/zero
        for t in VALVE_TAGS:
            st.session_state.component_values[f"{t}_flow"] = 0.0
            st.session_state.component_values[f"{t}_pressure"] = DEFAULT_NOMINAL[t]["pressure"]
        for t in FLOW_TAGS:
            st.session_state.component_values[f"{t}_flow"] = DEFAULT_NOMINAL[t]["flow"]
        for t in SENSOR_TAGS:
            st.session_state.component_values[f"{t}_pressure"] = DEFAULT_NOMINAL[t]["pressure"]
        st.success("History reset")

with center:
    st.header("P&ID Diagram")
    if img is not None:
        # draw overlays
        overlay = img.copy()
        draw = ImageDraw.Draw(overlay)
        w, h = overlay.size
        for tag, pos in DEFAULT_POSITIONS.items():
            x = int(pos[0] / 100.0 * w)
            y = int(pos[1] / 100.0 * h)
            is_open = st.session_state.valve_states.get(tag, False)
            color = (0,200,0) if is_open else (200,0,0)
            r = max(6, int(min(w,h)*0.02))
            draw.ellipse((x-r,y-r,x+r,y+r), fill=color)
            draw.text((x+r+2, y-r), tag, fill=(255,255,255))
        st.image(overlay, use_column_width=True)
    else:
        st.info("No P&ID image available. Upload one in the sidebar or place 'P&ID.png' in repo root.")

with right:
    st.header("Live Summary")
    # compute a few summary values
    total_flow = sum(st.session_state.component_values.get(f"{t}_flow", 0.0) for t in VALVE_TAGS)
    avg_pressure = np.mean([st.session_state.component_values.get(f"{t}_pressure", 0.0) for t in SENSOR_TAGS]) if SENSOR_TAGS else 0.0
    st.metric("Total Flow (SLPM)", f"{total_flow:.2f}")
    st.metric("Avg Sensor Pressure (bar)", f"{avg_pressure:.2f}")
    st.markdown("**Open Valves**")
    open_list = [t for t, s in st.session_state.valve_states.items() if s]
    st.write(open_list if open_list else "— none —")

# -----------------------
# Simulation update function
# -----------------------
def simulate_step(smoothing=0.6, noise_amp=0.05):
    """Perform one simulation timestep and append to history."""
    # For each valve: target flow = nominal_flow if open else 0
    for t in VALVE_TAGS:
        nominal = DEFAULT_NOMINAL.get(t, {"flow":10,"pressure":1})
        target_flow = nominal["flow"] if st.session_state.valve_states.get(t, False) else 0.0
        # simple first-order dynamics: new = old + (target - old)*(1 - smoothing)
        old = st.session_state.component_values.get(f"{t}_flow", 0.0)
        new = old + (target_flow - old) * (1.0 - smoothing)
        # add small noise
        new = new * (1.0 + np.random.uniform(-noise_amp, noise_amp))
        st.session_state.component_values[f"{t}_flow"] = max(0.0, new)

        # pressure: if valve open, pressure drops a bit relative to nominal sensor; if closed small leakage pressure
        nominal_p = nominal.get("pressure", 1.0)
        if st.session_state.valve_states.get(t, False):
            p_target = nominal_p * 0.9  # slight drop when open
        else:
            p_target = nominal_p * 1.0  # closed holds upstream pressure nominal
        oldp = st.session_state.component_values.get(f"{t}_pressure", nominal_p)
        newp = oldp + (p_target - oldp) * (1.0 - smoothing)
        newp = newp * (1.0 + np.random.uniform(-noise_amp, noise_amp))
        st.session_state.component_values[f"{t}_pressure"] = max(0.0, newp)

    # Update sensors and flow devices (simple mapping)
    for t in FLOW_TAGS:
        nominal = DEFAULT_NOMINAL.get(t, {"flow":50})
        # flow devices show the sum of nearby valve flows scaled; here we take proportional to total open valves
        scale = len([v for v in VALVE_TAGS if st.session_state.valve_states.get(v, False)]) / max(1, len(VALVE_TAGS))
        target = nominal["flow"] * (0.3 + 0.7 * scale)
        old = st.session_state.component_values.get(f"{t}_flow", nominal["flow"])
        new = old + (target - old) * (1.0 - smoothing)
        st.session_state.component_values[f"{t}_flow"] = new * (1.0 + np.random.uniform(-noise_amp, noise_amp))

    for t in SENSOR_TAGS:
        # sensors read a weighted average of nearby valve pressures — simplify as average of valve pressures
        valve_pressures = [st.session_state.component_values.get(f"{v}_pressure", DEFAULT_NOMINAL[v]["pressure"]) for v in VALVE_TAGS]
        if valve_pressures:
            avg = np.mean(valve_pressures)
        else:
            avg = DEFAULT_NOMINAL.get(t, {"pressure":1.0})["pressure"]
        old = st.session_state.component_values.get(f"{t}_pressure", avg)
        new = old + (avg - old) * (1.0 - smoothing)
        st.session_state.component_values[f"{t}_pressure"] = new * (1.0 + np.random.uniform(-noise_amp, noise_amp))

    # Record history row (time-indexed)
    row = {}
    row["time"] = st.session_state.time_index
    # total flow and average pressure convenience columns
    row["total_flow"] = sum(st.session_state.component_values.get(f"{t}_flow",0.0) for t in VALVE_TAGS) + sum(st.session_state.component_values.get(f"{t}_flow",0.0) for t in FLOW_TAGS)
    row["avg_pressure"] = np.mean([st.session_state.component_values.get(f"{t}_pressure",0.0) for t in SENSOR_TAGS]) if SENSOR_TAGS else 0.0
    # per-valve values
    for t in VALVE_TAGS:
        row[f"{t}_flow"] = st.session_state.component_values.get(f"{t}_flow", 0.0)
        row[f"{t}_pressure"] = st.session_state.component_values.get(f"{t}_pressure", DEFAULT_NOMINAL[t]["pressure"])
    for t in FLOW_TAGS:
        row[f"{t}_flow"] = st.session_state.component_values.get(f"{t}_flow", DEFAULT_NOMINAL[t]["flow"])
    for t in SENSOR_TAGS:
        row[f"{t}_pressure"] = st.session_state.component_values.get(f"{t}_pressure", DEFAULT_NOMINAL[t]["pressure"])

    # append to history
    hist = st.session_state.history
    hist = hist.append(row, ignore_index=True)
    st.session_state.history = hist
    st.session_state.time_index += 1
    return row

# -----------------------
# Run simulation loop if requested
# -----------------------
if st.session_state.sim_running:
    # Run one simulation step, update UI, then sleep & rerun (non-blocking-ish)
    row = simulate_step(smoothing=smoothing, noise_amp=noise_amp)
    # small plots and table
    st.success(f"Sim time step: {st.session_state.time_index}  — total flow {row['total_flow']:.2f} SLPM")
    # plot live series for total_flow and avg_pressure
    hist = st.session_state.history.copy()
    if not hist.empty:
        fig, ax = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
        ax[0].plot(hist["time"], hist["total_flow"], label="Total Flow (SLPM)")
        ax[0].legend()
        ax[0].grid(True)
        ax[1].plot(hist["time"], hist["avg_pressure"], label="Avg Pressure (bar)", color="orange")
        ax[1].legend()
        ax[1].grid(True)
        st.pyplot(fig)

    # show last N rows of history
    with st.expander("Recent history (last 20 rows)"):
        st.dataframe(st.session_state.history.tail(20))

    # wait then rerun to animate
    time.sleep(sim_step)
    st.experimental_rerun()
else:
    # not running: show controls and current values
    st.info("Simulation is stopped. Click ▶ Start Simulation to begin live updates.")
    # show current summary chart from history (if any)
    if not st.session_state.history.empty:
        hist = st.session_state.history.copy()
        fig, ax = plt.subplots(2, 1, figsize=(8,5), sharex=True)
        ax[0].plot(hist["time"], hist["total_flow"], label="Total Flow (SLPM)")
        ax[0].legend(); ax[0].grid(True)
        ax[1].plot(hist["time"], hist["avg_pressure"], label="Avg Pressure (bar)", color="orange")
        ax[1].legend(); ax[1].grid(True)
        st.pyplot(fig)

# -----------------------
# Bottom: export history and full table
# -----------------------
st.markdown("---")
st.header("Export & Data")
col_a, col_b = st.columns(2)
with col_a:
    if not st.session_state.history.empty:
        csv = st.session_state.history.to_csv(index=False).encode("utf-8")
        st.download_button("Download Simulation History CSV", csv, "sim_history.csv", "text/csv")
with col_b:
    st.download_button("Download Current Component Snapshot", pd.DataFrame([st.session_state.component_values]).to_csv(index=False).encode("utf-8"), "snapshot.csv", "text/csv")
