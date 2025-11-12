import streamlit as st
from streamlit_canvas import st_canvas
import json
from PIL import Image, ImageDraw, ImageFont
import os
import io
import math
import time

st.set_page_config(layout="wide")
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"

# === LOAD VALVES ===
def load_valves():
    if not os.path.exists(DATA_FILE):
        st.error(f"Missing {DATA_FILE}")
        st.stop()
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Invalid {DATA_FILE}: {e}")
        st.stop()

valves = load_valves()

# === SESSION STATE ===
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: bool(data.get("state", False)) for tag, data in valves.items()}
if "user_lines" not in st.session_state:
    st.session_state.user_lines = []
if "drawing" not in st.session_state:
    st.session_state.drawing = False

# === SIDEBAR ===
with st.sidebar:
    st.header("Valve Controls")
    for tag, data in valves.items():
        state = st.session_state.valve_states[tag]
        col1, col2 = st.columns([3,1])
        with col1:
            if st.button(f"{'OPEN' if state else 'CLOSED'} {tag}",
                        type="primary" if state else "secondary",
                        key=f"btn_{tag}", use_container_width=True):
                st.session_state.valve_states[tag] = not state
                st.rerun()
        with col2:
            st.write("OPEN" if state else "CLOSED")

    st.markdown("---")
    open_cnt = sum(1 for v in st.session_state.valve_states.values() if v)
    st.metric("Open", open_cnt)
    st.metric("Closed", len(valves) - open_cnt)

    st.markdown("---")
    if st.button("Start Drawing", use_container_width=True):
        st.session_state.drawing = True
        st.rerun()
    if st.button("Stop Drawing", use_container_width=True):
        st.session_state.drawing = False
        st.rerun()

# === MAIN ===
st.title("P&ID – Drag to Draw Flow (Instant)")

col_canvas, col_info = st.columns([3,1])

# === LOAD BASE IMAGE ===
try:
    base = Image.open(PID_FILE).convert("RGBA")
except:
    st.error(f"Missing {PID_FILE}")
    base = Image.new("RGBA", (1200, 800), (240,240,240,255))

# === CANVAS ===
with col_canvas:
    if st.session_state.drawing:
        st.info("**Drag** from start to end to draw a pipe.")
        
        canvas_result = st_canvas(
            fill_color="rgba(255, 0, 0, 0.3)",
            stroke_width=8,
            stroke_color="rgba(100, 100, 255, 1)",
            background_image=base,
            height=base.height,
            width=base.width,
            drawing_mode="line",
            key="canvas"
        )

        # === NEW LINE FROM CANVAS ===
        if canvas_result.json_data is not None:
            objects = canvas_result.json_data["objects"]
            for obj in objects:
                if obj["type"] == "path":
                    path = obj["path"]
                    if len(path) >= 2:
                        x1, y1 = path[0][1], path[0][2]
                        x2, y2 = path[-1][1], path[-1][2]
                        # Avoid duplicates
                        if not any(l["p1"] == (x1,y1) and l["p2"] == (x2,y2) for l in st.session_state.user_lines):
                            st.session_state.user_lines.append({"p1": (x1,y1), "p2": (x2,y2)})
                            st.success(f"Line added: ({x1},{y1}) to ({x2},{y2})")
                            st.rerun()

# === DRAW FINAL IMAGE ===
canvas = base.copy()
draw = ImageDraw.Draw(canvas)
font = ImageFont.load_default()

# Draw valves
for tag, data in valves.items():
    x, y = data["x"], data["y"]
    col = (0,255,0,255) if st.session_state.valve_states.get(tag, False) else (255,0,0,255)
    draw.ellipse([x-10, y-10, x+10, y+10], fill=col, outline="white", width=3)
    draw.text((x+15, y-15), tag, fill="white", font=font)

# Draw user lines + flow
for line in st.session_state.user_lines:
    p1, p2 = line["p1"], line["p2"]
    up = nearest_valve(p1)
    down = nearest_valve(p2)
    flow = (up and down and 
            st.session_state.valve_states.get(up, False) and 
            st.session_state.valve_states.get(down, False))
    
    line_col = (0, 255, 0, 220) if flow else (255, 0, 0, 180)
    draw.line([p1, p2], fill=line_col, width=8)

    if flow:
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        length = math.hypot(dx, dy) or 1
        for i in range(3):
            ratio = (time.time() * 0.6 + i * 0.33) % 1
            ax = p1[0] + dx * ratio
            ay = p1[1] + dy * ratio
            angle = math.atan2(dy, dx)
            a_len = 14
            pts = [
                (ax, ay),
                (ax - a_len * math.cos(angle - 0.5), ay - a_len * math.sin(angle - 0.5)),
                (ax - a_len * math.cos(angle + 0.5), ay - a_len * math.sin(angle + 0.5))
            ]
            draw.polygon(pts, fill=(0, 200, 0))

# === DISPLAY FINAL IMAGE ===
buf = io.BytesIO()
canvas.convert("RGB").save(buf, "PNG")
st.image(buf.getvalue(), use_container_width=True)

# === RIGHT PANEL ===
with col_info:
    st.header("Drawn Lines")
    if st.session_state.user_lines:
        for i, ln in enumerate(st.session_state.user_lines):
            p1, p2 = ln["p1"], ln["p2"]
            up = nearest_valve(p1)
            down = nearest_valve(p2)
            status = "Flow" if (up and down and 
                                st.session_state.valve_states.get(up, False) and 
                                st.session_state.valve_states.get(down, False)) else "Blocked"
            st.write(f"**Line {i+1}**: {status}")
            st.caption(f"{p1} to {p2}\nUp: {up or '—'} | Down: {down or '—'}")
            if st.button("Delete", key=f"del_{i}"):
                st.session_state.user_lines.pop(i)
                st.rerun()
    else:
        st.info("Click **Start Drawing** and **drag** on the image.")

# === HELPER ===
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
