import streamlit as st
import json
from PIL import Image, ImageDraw, ImageFont
import os
import math
import time
import io

st.set_page_config(layout="wide")

# === CONFIG ===
PID_FILE       = "P&ID.png"
VALVES_FILE    = "valves.json"
PIPES_FILE     = "pipes.json"

# === CACHED P&ID LOADER ===
@st.cache_data
def load_pid_image():
    try:
        return Image.open(PID_FILE).convert("RGBA")
    except Exception as e:
        st.error(f"Failed to load {PID_FILE}: {e}")
        return Image.new("RGBA", (1200, 800), (240, 240, 240, 255))

base = load_pid_image()
canvas = base.copy()
draw = ImageDraw.Draw(canvas)
font = ImageFont.load_default()

# === LOAD VALVES ===
def load_valves():
    if not os.path.exists(VALVES_FILE):
        st.error(f"Missing {VALVES_FILE}")
        st.stop()
    with open(VALVES_FILE) as f:
        return json.load(f)

valves = load_valves()

# === LOAD & AUTO-SCALE PIPES FROM pipes.json ===
def load_pipes():
    if not os.path.exists(PIPES_FILE):
        st.warning(f"Missing {PIPES_FILE} – no pipes will be shown")
        return []

    try:
        with open(PIPES_FILE) as f:
            data = json.load(f)
        raw_pipes = data.get("lines", data) if isinstance(data, dict) else data
    except Exception as e:
        st.error(f"Error reading {PIPES_FILE}: {e}")
        return []

    # GET P&ID SIZE
    try:
        pid_w, pid_h = Image.open(PID_FILE).size
    except:
        pid_w, pid_h = 1200, 800

    # ESTIMATE FIGMA CANVAS FROM MAX COORDINATE
    if raw_pipes:
        max_x = max(max(p["x1"], p["x2"]) for p in raw_pipes)
        max_y = max(max(p["y1"], p["y2"]) for p in raw_pipes)
        figma_w = max(max_x, 184)
        figma_h = max(max_y, 259)
    else:
        figma_w, figma_h = 184, 259

    # SCALE
    scale_x = pid_w / figma_w
    scale_y = pid_h / figma_h

    scaled_pipes = []
    for p in raw_pipes:
        scaled_pipes.append({
            "x1": int(p["x1"] * scale_x),
            "y1": int(p["y1"] * scale_y),
            "x2": int(p["x2"] * scale_x),
            "y2": int(p["y2"] * scale_y)
        })

    st.caption(f"Scaled pipes: {figma_w}×{figma_h} → {pid_w}×{pid_h}")
    return scaled_pipes

pipes = load_pipes()

# === SNAP PIPE ENDS TO NEAREST VALVE (optional) ===
def snap_to_valve(p, max_dist=80):
    x, y = p
    best = p
    dmin = float('inf')
    for tag, v in valves.items():
        d = math.hypot(v["x"] - x, v["y"] - y)
        if d < dmin and d <= max_dist:
            dmin = d
            best = (v["x"], v["y"])
    return best

# Optional: toggle snap in UI
snap_enabled = st.checkbox("Snap pipe ends to valves", value=True)

# Apply snap if enabled
if snap_enabled:
    snapped_pipes = []
    for p in pipes:
        p1 = snap_to_valve((p["x1"], p["y1"]))
        p2 = snap_to_valve((p["x2"], p["y2"]))
        snapped_pipes.append({"x1": p1[0], "y1": p1[1], "x2": p2[0], "y2": p2[1]})
    pipes = snapped_pipes

# === SESSION STATE ===
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {
        tag: bool(data.get("state", False)) for tag, data in valves.items()
    }

# === FIND NEAREST VALVE TO A POINT ===
def nearest_valve(point, max_dist=60):
    x0, y0 = point
    best = None
    best_d = float('inf')
    for tag, data in valves.items():
        d = math.hypot(data["x"] - x0, data["y"] - y0)
        if d < best_d and d <= max_dist:
            best_d = d
            best = tag
    return best

# === RENDER P&ID WITH FLOW ===
def render_pid():
    canvas = base.copy()
    draw = ImageDraw.Draw(canvas)

    # --- 1. DRAW PIPES + FLOW ---
    for pipe in pipes:
        p1 = (pipe["x1"], pipe["y1"])
        p2 = (pipe["x2"], pipe["y2"])

        up_val   = nearest_valve(p1)
        down_val = nearest_valve(p2)

        flow = (up_val and down_val and
                st.session_state.valve_states.get(up_val, False) and
                st.session_state.valve_states.get(down_val, False))

        color = (0, 255, 0, 220) if flow else (255, 0, 0, 180)
        draw.line([p1, p2], fill=color, width=8)

        # ANIMATED ARROWS
        if flow:
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            for i in range(3):
                t = (time.time() * 0.6 + i * 0.33) % 1
                ax = p1[0] + dx * t
                ay = p1[1] + dy * t
                angle = math.atan2(dy, dx)
                a_len = 14
                pts = [
                    (ax, ay),
                    (ax - a_len * math.cos(angle - 0.5), ay - a_len * math.sin(angle - 0.5)),
                    (ax - a_len * math.cos(angle + 0.5), ay - a_len * math.sin(angle + 0.5))
                ]
                draw.polygon(pts, fill=(0, 200, 0))

    # --- 2. DRAW VALVES ---
    for tag, data in valves.items():
        x, y = data["x"], data["y"]
        color = (0, 255, 0) if st.session_state.valve_states.get(tag, False) else (255, 0, 0)
        draw.ellipse([x-10, y-10, x+10, y+10], fill=color, outline="white", width=3)
        draw.text((x+15, y-15), tag, fill="white", font=font)

    return canvas.convert("RGB")

# === UI ===
st.title("P&ID Flow Simulation")

# Valve Controls
st.subheader("Valve Controls")
cols = st.columns(3)
for i, (tag, _) in enumerate(valves.items()):
    with cols[i % 3]:
        state = st.session_state.valve_states[tag]
        icon = "OPEN" if state else "CLOSED"
        if st.button(f"{icon} {tag}", key=f"v_{tag}", use_container_width=True):
            st.session_state.valve_states[tag] = not state
            st.rerun()

# Main Image
st.image(render_pid(), use_container_width=True,
         caption="Green = Flow (both valves OPEN) | Red = Blocked")

# Debug
with st.expander("Debug Info", expanded=False):
    st.write("P&ID Size:", base.size)
    st.write("Loaded Pipes:", len(pipes))
    st.write("Snap Enabled:", snap_enabled)
    st.write("Valve States:", st.session_state.valve_states)
    if pipes:
        st.json(pipes[:3])
