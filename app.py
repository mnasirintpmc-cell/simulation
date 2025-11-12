import streamlit as st
import json
from PIL import Image, ImageDraw, ImageFont
import os
import time
import io
import math

st.set_page_config(layout="wide")
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"

# === LOAD VALVES SAFELY ===
def load_valves():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading valves.json: {e}")
    return {}

valves = load_valves()
if not valves:
    st.error("No valves found in valves.json")
    st.stop()

# === INITIALIZE SESSION STATE SAFELY ===
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {}
    for tag, data in valves.items():
        # Force boolean from JSON (could be null, string, etc.)
        st.session_state.valve_states[tag] = bool(data.get("state", False))

if "animation_running" not in st.session_state:
    st.session_state.animation_running = False

# === SIDEBAR CONTROLS ===
with st.sidebar:
    st.header("Valve Controls")
    st.markdown("---")
    
    for tag, data in valves.items():
        state = st.session_state.valve_states[tag]
        label = f"{'OPEN' if state else 'CLOSED'} {tag}"
        btn_type = "primary" if state else "secondary"
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button(label, key=f"btn_{tag}", type=btn_type, use_container_width=True):
                st.session_state.valve_states[tag] = not state
                st.rerun()
        with col2:
            st.write("OPEN" if state else "CLOSED")
    
    st.markdown("---")
    
    # FIXED: sum only booleans
    open_count = sum(1 for v in st.session_state.valve_states.values() if v)
    closed_count = len(valves) - open_count
    
    st.metric("Open Valves", open_count)
    st.metric("Closed Valves", closed_count)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Open All", use_container_width=True):
            for tag in valves:
                st.session_state.valve_states[tag] = True
            st.rerun()
    with col2:
        if st.button("Close All", use_container_width=True):
            for tag in valves:
                st.session_state.valve_states[tag] = False
            st.rerun()
    
    if st.button("Start Animation", use_container_width=True):
        st.session_state.animation_running = True
        st.rerun()

# === MAIN TITLE ===
st.title("Tandem Seal P&ID — Animated Flow")

# === PATHS FROM YOUR P&ID (PIXEL-ACCURATE) ===
PATHS = [
    {
        "name": "Main Line: V-101 → V-301 → CV-1 → CV-2 → V-105",
        "valves": ["V-101", "V-301", "CV-1", "CV-2", "V-105"],
        "segments": [
            (120, 320, 220, 320),   # V-101 → V-301
            (220, 320, 320, 320),   # V-301 → CV-1
            (320, 320, 320, 420),   # 90° down to CV-2
            (320, 420, 420, 420),   # CV-2 → V-105
        ]
    },
    {
        "name": "Barrier Gas (Top → Down)",
        "valves": ["V-601", "MPV-7"],
        "segments": [(200, 200, 200, 320)]
    },
    {
        "name": "Buffer Gas (Bottom → Up)",
        "valves": ["V-602", "MPV-8"],
        "segments": [(350, 450, 350, 320)]
    },
    {
        "name": "Drain Line",
        "valves": ["V-501"],
        "segments": [(400, 480, 500, 480)]
    }
]

# === DISPLAY STATIC OR ANIMATED ===
col1, col2 = st.columns([3, 1])
with col1:
    placeholder = st.empty()

with col2:
    st.header("Path Status")
    for path in PATHS:
        active = all(st.session_state.valve_states.get(v, False) for v in path["valves"])
        st.write(f"**{path['name']}**: {'Active' if active else 'Blocked'}")

# === ANIMATION FRAME ===
def create_frame(t):
    try:
        img = Image.open(PID_FILE).convert("RGBA")
    except:
        img = Image.new("RGBA", (800, 600), (255, 255, 255, 255))
    
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    # Draw valves
    for tag, data in valves.items():
        x, y = data["x"], data["y"]
        color = (0, 255, 0) if st.session_state.valve_states.get(tag, False) else (255, 0, 0)
        draw.ellipse([x-8, y-8, x+8, y+8], fill=color, outline="white", width=2)
        draw.text((x+12, y-10), tag, fill="white", font=font)

    # Draw paths
    for path in PATHS:
        active = all(st.session_state.valve_states.get(v, False) for v in path["valves"])
        line_color = (0, 255, 0, 180) if active else (255, 0, 0, 100)
        
        for sx, sy, ex, ey in path["segments"]:
            draw.line([(sx, sy), (ex, ey)], fill=line_color, width=6)
            
            if active:
                dx, dy = ex - sx, ey - sy
                length = math.hypot(dx, dy) or 1
                for i in range(5):
                    ratio = (t * 0.3 + i * 0.2) % 1
                    ax = sx + dx * ratio
                    ay = sy + dy * ratio
                    angle = math.atan2(dy, dx)
                    # Arrowhead
                    arrow_len = 12
                    p1 = (ax - arrow_len * math.cos(angle - 0.5), ay - arrow_len * math.sin(angle - 0.5))
                    p2 = (ax - arrow_len * math.cos(angle + 0.5), ay - arrow_len * math.sin(angle + 0.5))
                    draw.polygon([(ax, ay), p1, p2], fill=(0, 200, 0))

    return img.convert("RGB")

# === RUN ANIMATION ===
if st.session_state.animation_running:
    start = time.time()
    while time.time() - start < 8:
        frame = create_frame(time.time() - start)
        buf = io.BytesIO()
        frame.save(buf, "PNG")
        placeholder.image(buf.getvalue(), use_container_width=True)
        time.sleep(0.2)
    st.session_state.animation_running = False
    st.rerun()
else:
    # Static view
    static = create_frame(0)
    buf = io.BytesIO()
    static.save(buf, "PNG")
    placeholder.image(buf.getvalue(), use_container_width=True)

# === INSTRUCTIONS ===
st.markdown("---")
st.caption("Green = Flow Active | Red = Blocked | Arrows show direction (left→right, top→bottom)")
