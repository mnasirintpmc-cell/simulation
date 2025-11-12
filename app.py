import streamlit as st
import json
from PIL import Image, ImageDraw, ImageFont
import os
import time
import io

# === CONFIG ===
st.set_page_config(layout="wide", page_title="Animated P&ID")

PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"
FRAME_DELAY = 0.1  # seconds per frame

# === LOAD VALVES ===
def load_valves():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

valves = load_valves()

if not valves:
    st.error("No valves found in `valves.json`. Create one with valve tags and positions.")
    st.stop()

# === SESSION STATE ===
if "valve_states" not in st.session_state:
    # Ensure all states are boolean
    st.session_state.valve_states = {
        tag: bool(data.get("state", False)) for tag, data in valves.items()
    }

if "animation_time" not in st.session_state:
    st.session_state.animation_time = 0.0

# === SIDEBAR CONTROLS ===
with st.sidebar:
    st.header("Valve Controls")
    st.markdown("---")

    for tag in valves.keys():
        current = st.session_state.valve_states[tag]
        label = f"{'OPEN' if current else 'CLOSED'} {tag}"
        btn_type = "primary" if current else "secondary"
        if st.button(label, key=f"btn_{tag}", use_container_width=True, type=btn_type):
            st.session_state.valve_states[tag] = not current
            st.rerun()

    st.markdown("---")
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

# === MAIN ANIMATION ===
st.title("Animated P&ID Simulation")
st.markdown("Click valves in sidebar • Watch flow, level, pump, alarm")

placeholder = st.empty()

# Load base image
try:
    base_img = Image.open(PID_FILE).convert("RGBA")
except Exception as e:
    st.warning(f"Could not load {PID_FILE}: {e}")
    base_img = Image.new("RGBA", (1200, 800), (240, 240, 240, 255))

# Font
try:
    font = ImageFont.truetype("arial.ttf", 18)
except:
    font = ImageFont.load_default()

# === ANIMATION LOOP ===
while True:
    t = st.session_state.animation_time
    st.session_state.animation_time += FRAME_DELAY

    frame = base_img.copy()
    draw = ImageDraw.Draw(frame)

    # === DRAW VALVES ===
    for tag, data in valves.items():
        x, y = data["x"], data["y"]
        state = st.session_state.valve_states[tag]
        color = (0, 255, 0, 220) if state else (255, 0, 0, 220)
        draw.ellipse([x-14, y-14, x+14, y+14], fill=color, outline="white", width=3)
        draw.text((x+18, y-18), tag, fill="white", font=font, stroke_fill="black", stroke_width=1)

    # === FLOW ARROWS (only on open valves) ===
    for tag, data in valves.items():
        if st.session_state.valve_states[tag]:
            x, y = data["x"], data["y"]
            offset = (int(t * 120) % 240) - 80
            fx = x + 40 + offset
            if 0 < fx < frame.width - 50:
                draw.polygon([
                    (fx, y-6), (fx+25, y), (fx, y+6)
                ], fill=(0, 200, 0, 240))

    # === TANK LEVEL (fixed position example) ===
    tank_x, tank_y = 300, 550
    level_percent = 40 + 30 * (1 + (t % 4 - 2) / 2)  # 10% to 70%
    level_h = int(160 * (level_percent / 100))
    draw.rectangle([tank_x, tank_y - level_h, tank_x+90, tank_y], fill=(0, 120, 255, 180))
    draw.rectangle([tank_x, tank_y - 160, tank_x+90, tank_y], outline="black", width=4)

    # === SPINNING PUMP ===
    pump_x, pump_y = 650, 520
    angle = t * 8
    blades = []
    for i in range(6):
        a = angle + i * 60
        r = 30
        dx = r * ((a % 180) / 90 if (a % 180) < 90 else 2 - (a % 180) / 90)
        dy = r * (1 if i % 2 == 0 else 0.7)
        blades.extend([pump_x + dx, pump_y + dy])
    draw.polygon(blades, fill=(0, 150, 255, 230))

    # === ALARM (flash if level high + flow) ===
    if level_percent > 60 and any(st.session_state.valve_states.values()):
        alpha = 255 if int(t * 8) % 2 == 0 else 80
        draw.ellipse([950, 100, 1000, 150], fill=(255, 0, 0, alpha))
        draw.text((960, 160), "HIGH!", fill="red", font=font)

    # === DISPLAY FRAME ===
    frame_rgb = frame.convert("RGB")
    buf = io.BytesIO()
    frame_rgb.save(buf, format="PNG")
    placeholder.image(buf.getvalue(), use_container_width=True)

    time.sleep(FRAME_DELAY)
