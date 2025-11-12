import streamlit as st
import json
from PIL import Image, ImageDraw, ImageFont
import os
import math
import time
import io

st.set_page_config(layout="wide")

# === CONFIG ===
PID_FILE     = "P&ID.png"
VALVES_FILE  = "valves.json"
LINES_FILE   = "pipes.json"

# === CACHED P&ID LOADER ===
@st.cache_data
def load_pid_image():
    try:
        img = Image.open(PID_FILE).convert("RGBA")
        return img
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
    try:
        with open(VALVES_FILE) as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Invalid {VALVES_FILE}: {e}")
        st.stop()

valves = load_valves()

# === LOAD & SCALE + SNAP LINES ===
def scale_lines(lines, target_w, target_h, figma_w=184, figma_h=259):
    if not lines:
        return []
    sx = target_w / figma_w
    sy = target_h / figma_h
    return [
        {
            "x1": int(l["x1"] * sx),
            "y1": int(l["y1"] * sy),
            "x2": int(l["x2"] * sx),
            "y2": int(l["y2"] * sy)
        }
        for l in lines
    ]

def snap_to_valve(point, valves, max_dist=100):
    x, y = point
    best = point
    min_d = float('inf')
    for tag, data in valves.items():
        vx, vy = data["x"], data["y"]
        d = math.hypot(vx - x, vy - y)
        if d < min_d and d <= max_dist:
            min_d = d
            best = (vx, vy)
    return best

def load_lines():
    if not os.path.exists(LINES_FILE):
        st.warning(f"Missing {LINES_FILE}")
        return []

    try:
        with open(LINES_FILE) as f:
            data = json.load(f)
        raw = data.get("lines", data) if isinstance(data, dict) else data
    except Exception as e:
        st.error(f"Error reading {LINES_FILE}: {e}")
        return []

    w, h = base.size
    scaled = scale_lines(raw, w, h)

    # Optional: Snap to valves
    snapped = []
    for line in scaled:
        p1 = snap_to_valve((line["x1"], line["y1"]), valves)
        p2 = snap_to_valve((line["x2"], line["y2"]), valves)
        if p1 != p2:
            snapped.append({"x1": p1[0], "y1": p1[1], "x2": p2[0], "y2": p2[1]})
    return snapped

lines = load_lines()

# === SESSION STATE ===
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {
        tag: bool(data.get("state", False)) for tag, data in valves.items()
    }

# === SIDEBAR ===
with st.sidebar:
    st.header("Valve Controls")
    for tag, data in valves.items():
        state = st.session_state.valve_states[tag]
        if st.button(
            f"{'OPEN' if state else 'CLOSED'} {tag}",
            type="primary" if state else "secondary",
            key=f"btn_{tag}",
            use_container_width=True,
        ):
            st.session_state.valve_states[tag] = not state
            st.rerun()
    st.markdown("---")
    st.metric("Open", sum(st.session_state.valve_states.values()))
    st.metric("Closed", len(valves) - sum(st.session_state.valve_states.values()))

# === DRAW VALVES ===
for tag, data in valves.items():
    x, y = data["x"], data["y"]
    col = (0,255,0,255) if st.session_state.valve_states.get(tag, False) else (255,0,0,255)
    draw.ellipse([x-10, y-10, x+10, y+10], fill=col, outline="white", width=3)
    draw.text((x+15, y-15), tag, fill="white", font=font)

# === DRAW PIPES + FLOW ===
for line in lines:
    p1 = (line["x1"], line["y1"])
    p2 = (line["x2"], line["y2"])

    # Find nearest valves
    up = next((t for t, d in valves.items() if math.hypot(d["x"]-p1[0], d["y"]-p1[1]) < 60), None)
    down = next((t for t, d in valves.items() if math.hypot(d["x"]-p2[0], d["y"]-p2[1]) < 60), None)
    flow = up and down and st.session_state.valve_states.get(up, False) and st.session_state.valve_states.get(down, False)

    draw.line([p1, p2], fill=(0,255,0,220) if flow else (255,0,0,180), width=8)

    if flow:
        dx, dy = p2[0]-p1[0], p2[1]-p1[1]
        length = math.hypot(dx, dy) or 1
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
            draw.polygon(pts, fill=(0,200,0))

# === DISPLAY ===
buf = io.BytesIO()
canvas.convert("RGB").save(buf, "PNG")
st.image(buf.getvalue(), use_container_width=True)

# === DEBUG (Optional) ===
with st.expander("Debug"):
    st.write("P&ID Size:", base.size)
    st.write("Loaded Pipes:", len(lines))
    st.json(lines[:3])
