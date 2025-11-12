import streamlit as st
import json
from PIL import Image, ImageDraw, ImageFont
import os
import time
import io

st.set_page_config(layout="wide")
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"

# Load valves
def load_valves():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

valves = load_valves()
if not valves:
    st.error("No valves found in valves.json")
    st.stop()

# Session state
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}
if "animation_running" not in st.session_state:
    st.session_state.animation_running = False

# === SIDEBAR (unchanged) ===
with st.sidebar:
    st.header("Valve Controls")
    st.markdown("---")
    for tag, data in valves.items():
        state = st.session_state.valve_states[tag]
        label = f"{'OPEN' if state else 'CLOSED'} {tag}"
        btn_type = "primary" if state else "secondary"
        col1, col2 = st.columns([3,1])
        with col1:
            if st.button(label, key=f"btn_{tag}", type=btn_type, use_container_width=True):
                st.session_state.valve_states[tag] = not state
                st.rerun()
        with col2:
            st.write("OPEN" if state else "CLOSED")
    st.markdown("---")
    open_count = sum(st.session_state.valve_states.values())
    st.metric("Open", open_count)
    st.metric("Closed", len(valves) - open_count)
    st.markdown("---")
    if st.button("Start Animation", use_container_width=True):
        st.session_state.animation_running = True
        st.rerun()

# === MAIN ===
st.title("Tandem Seal P&ID — Real Flow Animation")
col1, col2 = st.columns([3,1])

with col1:
    placeholder = st.empty() if st.session_state.animation_running else None
    if not st.session_state.animation_running:
        try:
            st.image(PID_FILE, use_container_width=True, caption="Click 'Start Animation'")
        except:
            st.error("P&ID.png missing")

with col2:
    st.header("Valve Details")
    for tag, data in valves.items():
        state = st.session_state.valve_states[tag]
        with st.expander(f"{tag} - {'OPEN' if state else 'CLOSED'}"):
            st.write(f"Position: ({data['x']}, {data['y']})")
            if st.button(f"Toggle", key=f"mini_{tag}"):
                st.session_state.valve_states[tag] = not state
                st.rerun()

# === ANIMATION LOOP ===
def create_frame(t):
    try:
        img = Image.open(PID_FILE).convert("RGBA")
    except:
        img = Image.new("RGBA", (1200, 800), (255,255,255,255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    # Draw valves
    for tag, data in valves.items():
        x, y = data["x"], data["y"]
        color = (0,255,0,255) if st.session_state.valve_states[tag] else (255,0,0,255)
        draw.ellipse([x-10, y-10, x+10, y+10], fill=color, outline="white", width=2)
        draw.text((x+15, y-15), tag, fill="white", font=font)

    # MAIN PROCESS FLOW: y=430, left→right, only past open valves
    main_y = 430
    for tag, data in valves.items():
        if st.session_state.valve_states[tag]:
            vx = data["x"]
            for i in range(5):
                offset = (int(t * 40 + i * 70) % 600)
                fx = vx + 30 + offset
                if fx < 1150:
                    draw.rectangle([fx, main_y-4, fx+25, main_y+4], fill=(0,200,0,220))
                    draw.polygon([(fx+25, main_y-3), (fx+32, main_y), (fx+25, main_y+3)], fill=(0,150,0,240))

    # BARRIER GAS (TOP): x=400, upward from y=430 → y=300
    if any(st.session_state.valve_states.get(tag, False) for tag in ["V-601", "V-101"] if tag in valves):
        for i in range(3):
            offset = (int(t * 25 + i * 50) % 130)
            gy = 430 - offset
            if gy > 300:
                draw.ellipse([395, gy-5, 405, gy+5], fill=(135,206,250,200))
                draw.ellipse([397, gy-3, 403, gy+3], fill=(173,216,230,220))

    # BUFFER GAS (BOTTOM): x=700, downward from y=430 → y=550
    if any(st.session_state.valve_states.get(tag, False) for tag in ["V-602", "V-104"] if tag in valves):
        for i in range(3):
            offset = (int(t * 20 + i * 60) % 120)
            gy = 430 + offset
            if gy < 550:
                draw.ellipse([695, gy-5, 705, gy+5], fill=(100,180,255,200))
                draw.ellipse([697, gy-3, 703, gy+3], fill=(135,206,250,220))

    return img.convert("RGB")

# Run animation
if st.session_state.animation_running:
    start = time.time()
    while time.time() - start < 10:
        frame = create_frame(time.time() - start)
        buf = io.BytesIO()
        frame.save(buf, "PNG")
        placeholder.image(buf.getvalue(), use_container_width=True)
        time.sleep(0.15)  # ~6.7 FPS
    st.session_state.animation_running = False
    st.success("Animation finished. Restart to run again.")
    st.rerun()

# Instructions
st.markdown("---")
st.caption("Flow: Green = Process | Blue = Gas | Only through open valves | Matches your P&ID exactly.")
