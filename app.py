import streamlit as st
import json
from PIL import Image, ImageDraw, ImageFont
import os
import math
import time

st.set_page_config(layout="wide")

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
PID_FILE       = "P&ID.png"
VALVES_FILE    = "valves.json"
PIPES_FILE     = "pipes.json"

# ----------------------------------------------------------------------
# 1. CACHED P&ID LOADER
# ----------------------------------------------------------------------
@st.cache_data
def load_pid_image():
    try:
        return Image.open(PID_FILE).convert("RGBA")
    except Exception as e:
        st.error(f"Failed to load {PID_FILE}: {e}")
        return Image.new("RGBA", (1200, 800), (240, 240, 240, 255))

base = load_pid_image()

# ----------------------------------------------------------------------
# 2. LOAD VALVES
# ----------------------------------------------------------------------
def load_valves():
    if not os.path.exists(VALVES_FILE):
        st.error(f"Missing {VALVES_FILE}")
        st.stop()
    with open(VALVES_FILE) as f:
        return json.load(f)

valves = load_valves()

# ----------------------------------------------------------------------
# 3. LOAD & AUTO-SCALE PIPES
# ----------------------------------------------------------------------
def load_pipes():
    if not os.path.exists(PIPES_FILE):
        st.warning(f"Missing {PIPES_FILE} – no pipes will be shown")
        return []

    with open(PIPES_FILE) as f:
        raw = json.load(f)

    raw = raw.get("lines", raw) if isinstance(raw, dict) else raw

    # ---- get real P&ID size ----
    try:
        pid_w, pid_h = Image.open(PID_FILE).size
    except:
        pid_w, pid_h = 1200, 800

    # ---- estimate Figma canvas from max coordinate ----
    if raw:
        max_x = max(max(p["x1"], p["x2"]) for p in raw)
        max_y = max(max(p["y1"], p["y2"]) for p in raw)
        figma_w = max(max_x, 184)
        figma_h = max(max_y, 259)
    else:
        figma_w, figma_h = 184, 259

    sx = pid_w / figma_w
    sy = pid_h / figma_h

    scaled = []
    for p in raw:
        scaled.append({
            "x1": int(p["x1"] * sx),
            "y1": int(p["y1"] * sy),
            "x2": int(p["x2"] * sx),
            "y2": int(p["y2"] * sy)
        })
    return scaled

pipes = load_pipes()

# ----------------------------------------------------------------------
# 4. OPTIONAL SNAP TO VALVES
# ----------------------------------------------------------------------
snap_enabled = st.checkbox("Snap pipe ends to nearest valve", value=True)

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

if snap_enabled:
    snapped = []
    for p in pipes:
        p1 = snap_to_valve((p["x1"], p["y1"]))
        p2 = snap_to_valve((p["x2"], p["y2"]))
        snapped.append({"x1": p1[0], "y1": p1[1], "x2": p2[0], "y2": p2[1]})
    pipes = snapped

# ----------------------------------------------------------------------
# 5. SESSION STATE (valves only)
# ----------------------------------------------------------------------
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {
        tag: bool(data.get("state", False)) for tag, data in valves.items()
    }

# ----------------------------------------------------------------------
# 6. NEAREST VALVE HELPER
# ----------------------------------------------------------------------
def nearest_valve(point, max_dist=60):
    x0, y0 = point
    best = None
    dmin = float('inf')
    for tag, data in valves.items():
        d = math.hypot(data["x"] - x0, data["y"] - y0)
        if d < dmin and d <= max_dist:
            dmin = d
            best = tag
    return best

# ----------------------------------------------------------------------
# 7. RENDER P&ID WITH FLOW
# ----------------------------------------------------------------------
def render():
    canvas = base.copy()
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    # ---- PIPES + FLOW ----
    for pipe in pipes:
        p1 = (pipe["x1"], pipe["y1"])
        p2 = (pipe["x2"], pipe["y2"])

        up   = nearest_valve(p1)
        down = nearest_valve(p2)
        flow = up and down and st.session_state.valve_states.get(up, False) and st.session_state.valve_states.get(down, False)

        color = (0, 255, 0, 220) if flow else (255, 0, 0, 180)
        draw.line([p1, p2], fill=color, width=8)

        if flow:
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            for i in range(3):
                t = (time.time() * 0.6 + i * 0.33) % 1
                ax = p1[0] + dx * t
                ay = p1[1] + dy * t
                ang = math.atan2(dy, dx)
                a_len = 14
                pts = [
                    (ax, ay),
                    (ax - a_len * math.cos(ang - 0.5), ay - a_len * math.sin(ang - 0.5)),
                    (ax - a_len * math.cos(ang + 0.5), ay - a_len * math.sin(ang + 0.5))
                ]
                draw.polygon(pts, fill=(0, 200, 0))

    # ---- VALVES ----
    for tag, data in valves.items():
        x, y = data["x"], data["y"]
        col = (0, 255, 0) if st.session_state.valve_states.get(tag, False) else (255, 0, 0)
        draw.ellipse([x-10, y-10, x+10, y+10], fill=col, outline="white", width=3)
        draw.text((x+15, y-15), tag, fill="white", font=font)

    return canvas.convert("RGB")

# ----------------------------------------------------------------------
# 8. UI
# ----------------------------------------------------------------------
st.title("P&ID Flow Simulation")

# ---- Valve controls (sidebar) ----
with st.sidebar:
    st.header("Valve Controls")
    cols = st.columns(3)
    for i, (tag, _) in enumerate(valves.items()):
        with cols[i % 3]:
            state = st.session_state.valve_states[tag]
            icon = "OPEN" if state else "CLOSED"
            if st.button(f"{icon} {tag}", key=f"v_{tag}", use_container_width=True):
                st.session_state.valve_states[tag] = not state
                st.rerun()

# ---- Main image ----
st.image(render(), use_container_width=True,
         caption="Green = Flow (both valves OPEN) | Red = Blocked")

# ---- Debug (collapsed) ----
with st.expander("Debug", expanded=False):
    st.write("P&ID size:", base.size)
    st.write("Pipes loaded:", len(pipes))
    st.write("Snap enabled:", snap_enabled)
    st.write("Valve states:", st.session_state.valve_states)
    if pipes:
        st.json(pipes[:3])
