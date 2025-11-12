import streamlit as st
import json
from PIL import Image, ImageDraw, ImageFont
import os
import time
import io

st.set_page_config(layout="wide", page_title="Animated P&ID")

# === CONFIG ===
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"
FRAME_DELAY = 0.1  # Animation speed (seconds)

# === LOAD VALVES ===
def load_valves():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

valves = load_valves()

if not valves:
    st.error("No valves found in valves.json")
    st.stop()

# === SESSION STATE ===
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}
if "animation_time" not in st.session_state:
    st.session_state.animation_time = 0

# === SIDEBAR CONTROLS ===
with st.sidebar:
    st.header("Valve Controls")
    for tag, data in valves.items():
        current = st.session_state.valve_states[tag]
        label = f"{'OPEN' if current else 'CLOSED'} {tag}"
        color = "primary" if current else "secondary"
        if st.button(label, key=tag, use_container_width=True, type=color):
            st.session_state.valve_states[tag] = not current
            st.rerun()

    st.markdown("---")
    st.metric("Open", sum(st.session_state.valve_states.values()))
    st.metric("Closed", len(valves) - sum(st.session_state.valve_states.values()))

# === MAIN ANIMATION LOOP ===
st.title("Animated P&ID Simulation")
placeholder = st.empty()

# Load base image once
try:
    base_img = Image.open(PID_FILE).convert("RGBA")
except:
    base_img = Image.new("RGBA", (1200, 800), (240, 240, 240))

# Try to load a font
try:
    font = ImageFont.truetype("arial.ttf", 16)
except:
    font = ImageFont.load_default()

# Animation loop
while True:
    frame = base_img.copy()
    draw = ImageDraw.Draw(frame)
    
    t = st.session_state.animation_time
    st.session_state.animation_time += FRAME_DELAY

    # === DRAW VALVES ===
    for tag, data in valves.items():
        x, y = data["x"], data["y"]
        state = st.session_state.valve_states[tag]
        color = (0, 255, 0, 200) if state else (255, 0, 0, 200)
        draw.ellipse([x-12, y-12, x+12, y+12], fill=color, outline="white", width=2)
        draw.text((x+15, y-15), tag, fill="white", font=font)

    # === ANIMATED FLOW (only if valve open) ===
    for tag, data in valves.items():
        if st.session_state.valve_states[tag]:
            x, y = data["x"], data["y"]
            # Flow arrow moving right from valve
            offset = (int(t * 100) % 200) - 100
            fx = x + 30 + offset
            if 0 < fx < 1000:
                draw.polygon([
                    (fx, y), (fx+20, y-8), (fx+20, y+8)
                ], fill=(0, 200, 0, 220))

    # === ANIMATED TANK LEVEL (example at fixed position) ===
    tank_x, tank_y = 300, 500
    level_height = 50 + 40 * abs((t % 2) - 1) * 100  # Oscillate 50–150
    draw.rectangle([tank_x, tank_y - level_height, tank_x+80, tank_y], fill=(0, 100, 255, 180))
    draw.rectangle([tank_x, tank_y - 160, tank_x+80, tank_y], outline="black", width=3)

    # === SPINNING PUMP (example) ===
    pump_x, pump_y = 600, 500
    angle = t * 6  # 60 RPM
    points = []
    for i in range(6):
        a = angle + i * 60
        r = 25
        px = pump_x + r * (1 if i % 2 == 0 else 0.7) * (1 if a % 180 < 90 else -1)
        py = pump_y + r * (1 if i % 2 == 0 else 0.7) * (1 if a % 180 > 90 else -1)
        points.extend([px, py])
    draw.polygon(points, fill=(0, 150, 255, 220))

    # === ALARM FLASH (if any valve open and level high) ===
    if any(st.session_state.valve_states.values()) and level_height > 120:
        alpha = 255 if int(t * 10) % 2 == 0 else 100
        draw.ellipse([900, 100, 940, 140], fill=(255, 0, 0, alpha))

    # Convert to RGB and display
    frame_rgb = frame.convert("RGB")
    buf = io.BytesIO()
    frame_rgb.save(buf, format="PNG")
    placeholder.image(buf.getvalue(), use_container_width=True)

    time.sleep(FRAME_DELAY)
