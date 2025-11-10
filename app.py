# app.py
import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw
from streamlit_drawable_canvas import st_canvas
import json
import io
import time

st.set_page_config(page_title="P&ID Precise Placement HMI", layout="wide")
st.title("📌 P&ID HMI — Place tags precisely, then simulate (Option A)")

# -------------------------
# Config: tag lists (edit if needed)
# -------------------------
VALVE_TAGS = [
    "V-101","V-102","V-103","V-104","V-301","V-302","V-501","V-601",
    "CV-1","CV-2","CV-3","CV-4",
    "MPV-1","MPV-6","MPV-7","MPV-8",
]
SENSOR_TAGS = ["PT-101","PT-102","PT-103","PT-104","PT-105","PT-601","PT-602"]
FLOW_TAGS = ["MFM-100","MFM-200","MFM-300","MFM-400","MFC-1/2"]

ALL_TAGS = VALVE_TAGS + SENSOR_TAGS + FLOW_TAGS

# -------------------------
# Load image
# -------------------------
try:
    bg = Image.open("P&ID.png").convert("RGBA")
except Exception as e:
    st.error("Could not load P&ID.png from repo root. Upload or place it in the same folder as app.py.")
    st.stop()

img_w, img_h = bg.size

# -------------------------
# Session state for placements & states
# -------------------------
if "positions" not in st.session_state:
    # mapping tag -> {"x_pct":..., "y_pct":...}
    st.session_state.positions = {}

if "valve_state" not in st.session_state:
    # True=open, False=closed
    st.session_state.valve_state = {t: False for t in VALVE_TAGS}

if "sensor_values" not in st.session_state:
    # store PT/PI initial values
    st.session_state.sensor_values = {t: 0.0 for t in SENSOR_TAGS + FLOW_TAGS}
    # init sensible defaults
    for s in SENSOR_TAGS:
        st.session_state.sensor_values[s] = round(np.random.uniform(1.0, 5.0), 2)
    for f in FLOW_TAGS:
        st.session_state.sensor_values[f] = round(np.random.uniform(5.0, 200.0), 2)

# -------------------------
# Left column: placement UI
# -------------------------
left, right = st.columns([1,2])

with left:
    st.header("1) Place tags exactly (click to place)")
    st.markdown("""
    * Select a tag from the dropdown, then click **on the diagram** to place it.
    * You can re-place any tag by selecting it and clicking again.
    * When finished, click **Save placements**.
    """)
    selected_tag = st.selectbox("Select tag to place", ["<select>"] + ALL_TAGS)
    place_mode = st.checkbox("Placement mode enabled (click on image to place)", value=True)

    st.markdown("**Current placements**")
    if st.session_state.positions:
        pos_df = pd.DataFrame([
            {"Tag": k, "x%": v["x_pct"], "y%": v["y_pct"]} for k, v in st.session_state.positions.items()
        ])
        st.dataframe(pos_df, use_container_width=True)
    else:
        st.info("No tags placed yet.")

    if st.button("Save placements to file"):
        # write json to download
        b = io.BytesIO()
        b.write(json.dumps(st.session_state.positions, indent=2).encode("utf-8"))
        b.seek(0)
        st.download_button("Download placements JSON", b, "placements.json", "application/json")

    st.markdown("---")
    st.header("2) Valve States & Simulation")
    for t in VALVE_TAGS:
        st.session_state.valve_state[t] = st.checkbox(f"{t} OPEN", value=st.session_state.valve_state.get(t, False), key=f"state_{t}")

    if st.button("Instant simulate (apply changes)"):
        # quick rule: open valves increase nearby flows; we'll update sensor_values simply
        open_count = sum(st.session_state.valve_state.values())
        # sensors: average valve effect
        for s in SENSOR_TAGS:
            base = st.session_state.sensor_values.get(s, 1.0)
            st.session_state.sensor_values[s] = round(max(0.1, base * (1.0 - 0.05*open_count)), 2)
        for f in FLOW_TAGS:
            base = st.session_state.sensor_values.get(f, 10.0)
            st.session_state.sensor_values[f] = round(base * (1.0 + 0.15*open_count), 2)
        st.success("Simulation applied — sensor readings updated.")

# -------------------------
# Right column: interactive canvas
# -------------------------
with right:
    st.header("Diagram — click to set selected tag")

    # prepare canvas background as base64 data URL is handled by st_canvas automatically using background_image=bg
    drawing_mode = "point" if place_mode and selected_tag != "<select>" else None

    canvas_result = st_canvas(
        fill_color="rgba(255, 0, 0, 0.3)",
        stroke_width=2,
        background_image=bg,
        update_streamlit=True,
        height=min(900, int(img_h * (900/img_h))),
        drawing_mode=drawing_mode,
        key="pid_canvas"
    )

    # When user clicks/points, st_canvas adds a point object in canvas_result.json_data["objects"]
    if canvas_result.json_data and "objects" in canvas_result.json_data:
        # get last object
        objs = canvas_result.json_data["objects"]
        # find latest point object (mode "point" creates 'path' with single point)
        for o in objs[::-1]:
            if o.get("type") in ("path", "circle", "rect"):
                # determine center coordinates relative to image
                left = o.get("left", None)
                top = o.get("top", None)
                width = o.get("width", o.get("radius", 0))
                height = o.get("height", o.get("radius", 0))
                if left is None or top is None:
                    continue
                cx = left + width/2
                cy = top + height/2
                # convert canvas pixel coords to percent (canvas size may be scaled)
                # canvas_result.clientWidth / clientHeight not exposed, but background image is drawn full scale;
                # st_canvas returns coordinates relative to the rendered canvas size. We'll compute percent relative to canvas.
                canvas_w = canvas_result.json_data.get("background", {}).get("width", canvas_result.json_data.get("canvasWidth", bg.width))
                canvas_h = canvas_result.json_data.get("background", {}).get("height", canvas_result.json_data.get("canvasHeight", bg.height))
                # Fallback if not present:
                if not canvas_w or not canvas_h:
                    canvas_w, canvas_h = bg.size
                x_pct = round(100.0 * cx / canvas_w, 2)
                y_pct = round(100.0 * cy / canvas_h, 2)

                if selected_tag != "<select>":
                    # save position for selected tag
                    st.session_state.positions[selected_tag] = {"x_pct": x_pct, "y_pct": y_pct}
                    st.success(f"Placed {selected_tag} at {x_pct}%, {y_pct}%")
                else:
                    st.warning("Select a tag first (left dropdown) to place.")

                # clear canvas objects to avoid duplicates (workaround)
                # Note: st_canvas does not provide direct clear; we rely on user / canvas reset by re-render
                break

    # After placement: draw overlay with saved positions (visual confirmation)
    overlay = bg.copy()
    draw = ImageDraw.Draw(overlay)
    w, h = overlay.size
    for tag, pos in st.session_state.positions.items():
        x = int(pos["x_pct"] / 100.0 * w)
        y = int(pos["y_pct"] / 100.0 * h)
        # small circle and label
        r = max(8, int(min(w,h)*0.02))
        # color: valve -> green if open else red; sensors blue/yellow
        if tag in VALVE_TAGS:
            color = (0,200,0) if st.session_state.valve_state.get(tag, False) else (200,0,0)
        elif tag in SENSOR_TAGS:
            color = (255,200,0)
        else:
            color = (0,150,200)
        draw.ellipse((x-r, y-r, x+r, y+r), fill=color)
        draw.text((x+r+2, y-r), tag, fill=(255,255,255))

    st.markdown("**Overlay preview of placed tags**")
    st.image(overlay, use_column_width=True)

# -------------------------
# Bottom: HMI display of sensors and controls
# -------------------------
st.markdown("---")
st.header("HMI Readings")

cols = st.columns(3)
with cols[0]:
    st.subheader("Pressure Transducers (PT)")
    for s in SENSOR_TAGS:
        val = st.session_state.sensor_values.get(s, 0.0)
        st.metric(s, f"{val} bar")
with cols[1]:
    st.subheader("Flow Devices")
    for f in FLOW_TAGS:
        val = st.session_state.sensor_values.get(f, 0.0)
        st.metric(f, f"{val} SLPM")
with cols[2]:
    st.subheader("Valves")
    for v in VALVE_TAGS:
        st.write(f"{v}: {'OPEN' if st.session_state.valve_state.get(v, False) else 'CLOSED'}")

# -------------------------
# Export placements and states
# -------------------------
st.markdown("---")
if st.button("Export current positions + states"):
    out = {"positions": st.session_state.positions, "valve_state": st.session_state.valve_state, "sensor_values": st.session_state.sensor_values}
    st.download_button("Download JSON", json.dumps(out, indent=2), file_name="hmi_positions_states.json", mime="application/json")

st.caption("Tip: place all tags by selecting a tag and clicking the diagram; then use 'Instant simulate' to update PT/PI readings.")
