import streamlit as st
import json
from PIL import Image, ImageDraw, ImageFont
import os
import time
import io
import math  # For arrow angles

st.set_page_config(layout="wide")
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"

# Load valves (exact from your JSON)
def load_valves():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

valves = load_valves()
if not valves:
    st.error("No valves in valves.json")
    st.stop()

# Session state
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: bool(data.get("state", False)) for tag, data in valves.items()}
if "animation_running" not in st.session_state:
    st.session_state.animation_running = False

# Define paths (from your description + image analysis)
# Each path: list of valve tags; flow if all open
PATHS = [
    # Main line: V-101 → V-301 → CV-1 → CV-2 → V-105 (horizontal y=430, with 90° at CV-1 to vertical stub)
    {
        "name": "Main Process Line",
        "valves": ["V-101", "V-301", "CV-1", "CV-2", "V-105"],
        "segments": [  # (start_x, start_y, end_x, end_y, direction)
            (150, 430, 250, 430, "horizontal"),  # V-101 to V-301
            (250, 430, 350, 430, "horizontal"),  # V-301 to CV-1
            (350, 430, 350, 350, "vertical"),    # 90° up from CV-1 to CV-2 stub
            (350, 350, 450, 350, "horizontal"),  # CV-2 to V-105 (adjusted per image)
            (450, 350, 450, 430, "vertical")     # Down to main V-105
        ]
    },
    # Barrier gas (top branch): V-601 → MPV-7 → down to CV-1
    {
        "name": "Barrier Gas Branch",
        "valves": ["V-601", "MPV-7", "CV-1"],
        "segments": [
            (300, 200, 400, 200, "horizontal"),  # Gas supply to V-601
            (400, 200, 400, 430, "vertical")     # Down to CV-1
        ]
    },
    # Buffer gas (bottom branch): V-602 → MPV-8 → up to V-105
    {
        "name": "Buffer Gas Branch",
        "valves": ["V-602", "MPV-8", "V-105"],
        "segments": [
            (700, 600, 700, 550, "vertical"),    # V-602 up
            (700, 550, 700, 430, "vertical")     # To V-105
        ]
    }
    # Add more paths if needed (e.g., drain: V-501 → PI-105)
]

# Sidebar (your original)
with st.sidebar:
    st.header("🎯 Valve Controls")
    st.markdown("---")
    for tag in valves:
        state = st.session_state.valve_states.get(tag, False)
        label = f"🔴 {tag} - {'OPEN' if state else 'CLOSED'}"
        btn_type = "primary" if state else "secondary"
        if st.button(label, key=f"btn_{tag}", type=btn_type):
            st.session_state.valve_states[tag] = not state
            st.rerun()
    st.markdown("---")
    open_count = sum(st.session_state.valve_states.values())
    st.metric("Open Valves", open_count)
    st.markdown("---")
    if st.button("🚀 Start Animation"):
        st.session_state.animation_running = True
        st.rerun()

# Main
st.title("Tandem Seal P&ID — Flow Paths Animated")
col1, col2 = st.columns([3, 1])
with col1:
    placeholder = st.empty()
    if not st.session_state.animation_running:
        st.image(PID_FILE, use_container_width=True, caption="Toggle valves → Start Animation")

with col2:
    st.header("Path Status")
    for path in PATHS:
        all_open = all(st.session_state.valve_states.get(v, False) for v in path["valves"])
        color = "🟢 Flow Active" if all_open else "🔴 Blocked"
        st.write(f"**{path['name']}**: {color}")

# Frame creator
def create_frame(t):
    img = Image.open(PID_FILE).convert("RGBA")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    # Draw valves
    for tag, data in valves.items():
        if tag in valves:  # Safety
            x, y = data["x"], data["y"]
            color = (0, 255, 0) if st.session_state.valve_states.get(tag, False) else (255, 0, 0)
            draw.ellipse((x-8, y-8, x+8, y+8), fill=color, outline="white", width=2)
            draw.text((x+12, y-10), tag, fill="white", font=font)

    # Animate paths
    for path in PATHS:
        all_open = all(st.session_state.valve_states.get(v, False) for v in path["valves"])
        line_color = (0, 255, 0, 128) if all_open else (255, 0, 0, 128)
        for seg in path["segments"]:
            sx, sy, ex, ey, dir = seg
            # Color the line
            draw.line([(sx, sy), (ex, ey)], fill=line_color, width=6)
            if all_open:
                # Animated arrows (3 per segment, moving)
                seg_len = math.sqrt((ex - sx)**2 + (ey - sy)**2)
                for i in range(3):
                    offset = (int(t * 30 + i * (seg_len / 3)) % seg_len) / seg_len
                    ax = sx + offset * (ex - sx)
                    ay = sy + offset * (ey - sy)
                    # Arrow triangle (directional)
                    if dir == "horizontal":
                        arrow_pts = [(ax, ay-5), (ax+15, ay), (ax, ay+5)]
                    elif dir == "vertical":
                        arrow_pts = [(ax-5, ay), (ax, ay+15), (ax+5, ay)] if ey > sy else [(ax+5, ay), (ax, ay-15), (ax-5, ay)]
                    draw.polygon(arrow_pts, fill=(0, 200, 0))

    return img.convert("RGB")

# Run animation (8s loop)
if st.session_state.animation_running:
    start = time.time()
    while time.time() - start < 8:
        frame = create_frame(time.time() - start)
        buf = io.BytesIO()
        frame.save(buf, "PNG")
        placeholder.image(buf.getvalue(), use_container_width=True, caption="Flow: Green lines/arrows = Active | Red = Blocked")
        time.sleep(0.2)
    st.session_state.animation_running = False
    st.rerun()

# Instructions
st.markdown("---")
st.markdown("**Paths Analyzed:** Main (V-101→V-105 w/ 90° at CV-1), Barrier Gas (top-down), Buffer Gas (bottom-up). Arrows move L→R or top→bottom.")
with st.expander("Full Path Breakdown"):
    for path in PATHS:
        st.write(f"**{path['name']}**: Valves {', '.join(path['valves'])} | Segments: {path['segments']}")

# Debug
with st.expander("🔧 Valves"):
    st.json({tag: {"pos": data["x,y"], "state": state} for tag, data in valves.items() for state in [st.session_state.valve_states.get(tag, False)]})
