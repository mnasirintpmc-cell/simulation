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
    st.error("No valves found in valves.json. Please check your configuration.")
    st.stop()

# Initialize session state
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}

if "animation_running" not in st.session_state:
    st.session_state.animation_running = False

# Sidebar (your original, unchanged)
with st.sidebar:
    st.header("🎯 Valve Controls")
    st.markdown("---")
    
    for tag, data in valves.items():
        current_state = st.session_state.valve_states[tag]
        
        if current_state:
            button_label = f"🔴 {tag} - OPEN"
            button_type = "primary"
        else:
            button_label = f"🟢 {tag} - CLOSED"
            button_type = "secondary"
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button(button_label, key=f"btn_{tag}", use_container_width=True, type=button_type):
                st.session_state.valve_states[tag] = not current_state
                st.rerun()
        with col2:
            status = "🟢" if current_state else "🔴"
            st.write(status)
    
    st.markdown("---")
    
    # Current status summary
    st.subheader("📊 Current Status")
    open_valves = sum(1 for state in st.session_state.valve_states.values() if state)
    closed_valves = len(valves) - open_valves
    
    st.metric("Open Valves", open_valves)
    st.metric("Closed Valves", closed_valves)
    
    st.markdown("---")
    
    # Quick actions
    st.subheader("⚡ Quick Actions")
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

    # Animation toggle
    if st.button("🚀 Start/Stop Animation", use_container_width=True):
        st.session_state.animation_running = not st.session_state.animation_running
        if st.session_state.animation_running:
            st.rerun()

# Main app
st.title("Tandem Seal P&ID Interactive Simulation")
col1, col2 = st.columns([3, 1])

with col1:
    if st.session_state.animation_running:
        # Animation placeholder
        placeholder = st.empty()
        st.markdown("*Animation running: Flow along pipes, buffer flicker, gas bubbles.*")
    else:
        # Static display
        try:
            static_img = Image.open(PID_FILE).convert("RGB")
            st.image(static_img, use_container_width=True, caption="Static P&ID - Click 'Start Animation' to animate")
        except:
            st.error("P&ID.png not found")

with col2:
    st.header("🔍 Valve Details")
    st.markdown("---")
    
    for tag, data in valves.items():
        current_state = st.session_state.valve_states[tag]
        status = "🟢 OPEN" if current_state else "🔴 CLOSED"
        
        with st.expander(f"{tag} - {status}", expanded=False):
            st.write(f"**Position:** ({data['x']}, {data['y']})")
            st.write(f"**Current State:** {status}")
            
            if st.button(f"Toggle {tag}", key=f"mini_{tag}", use_container_width=True):
                st.session_state.valve_states[tag] = not current_state
                st.rerun()

# Animation function (PIL-based, pipe-aware)
def create_animated_frame(t):
    try:
        pid_img = Image.open(PID_FILE).convert("RGBA")
    except:
        pid_img = Image.new("RGBA", (1200, 800), (255, 255, 255))
    
    draw = ImageDraw.Draw(pid_img)
    
    # Try font
    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except:
        font = ImageFont.load_default()
    
    # Draw valves (your coords)
    for tag, data in valves.items():
        x, y = data["x"], data["y"]
        current_state = st.session_state.valve_states[tag]
        color = (0, 255, 0, 255) if current_state else (255, 0, 0, 255)
        
        # Valve circle
        draw.ellipse([x-8, y-8, x+8, y+8], fill=color, outline="white", width=2)
        draw.text((x+12, y-10), tag, fill="white", font=font)
    
    # Pipe flow (horizontal along main line y=350, only through open valves)
    pipe_y = 350  # Your PNG's main pipe centerline
    for tag, data in valves.items():
        if st.session_state.valve_states[tag]:
            vx, vy = data["x"], data["y"]
            # Flow particles: 3 dashes moving right from valve
            for i in range(3):
                offset = (int(t * 50 + i * 80) % 400)  # Speed + spacing
                fx = vx + offset
                if 0 < fx < 1200:  # Within image bounds
                    # Green flow dash (pipe-style)
                    draw.rectangle([fx, pipe_y-2, fx+30, pipe_y+2], fill=(0, 200, 0, 200))
    
    # Buffer pot flicker (small level at ~400,250 per your PNG)
    buffer_x, buffer_y = 400, 250
    flicker = int(20 + 10 * (t % 2))  # Subtle 20-30px height pulse
    draw.rectangle([buffer_x, buffer_y - flicker, buffer_x+40, buffer_y], fill=(135, 206, 250, 180))
    draw.rectangle([buffer_x, buffer_y - 50, buffer_x+40, buffer_y], outline="blue", width=2)
    
    # Barrier gas bubbles (upward from top valves, e.g., V-103/V-104 ~ y=200)
    for tag, data in valves.items():
        if st.session_state.valve_states[tag] and data["y"] < 300:  # Top line valves
            vx, vy = data["x"], data["y"]
            bubble_offset = int(t * 30) % 100
            by = vy - 20 - bubble_offset
            if by > 0:
                draw.ellipse([vx-5, by-5, vx+5, by+5], fill=(173, 216, 230, 150))
    
    return pid_img.convert("RGB")

# Run animation if toggled
if st.session_state.animation_running:
    start_time = time.time()
    anim_placeholder = st.empty()
    
    while time.time() - start_time < 10:  # 10s loop, then stop (Cloud-friendly)
        t = time.time() % 10  # Cycle time
        frame = create_animated_frame(t)
        
        buf = io.BytesIO()
        frame.save(buf, format="PNG")
        anim_placeholder.image(buf.getvalue(), use_container_width=True, caption=f"Frame t={t:.1f}s")
        
        time.sleep(0.1)  # 10 FPS
    
    st.session_state.animation_running = False
    st.success("Animation complete! Toggle valves and restart for changes.")
    st.rerun()

# Instructions (your original)
st.markdown("---")
st.markdown("### 📋 Instructions")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**Valve Colors:**")
    st.markdown("- 🟢 Green = Valve OPEN")
    st.markdown("- 🔴 Red = Valve CLOSED")
with col2:
    st.markdown("**Controls:**")
    st.markdown("- Use left sidebar to toggle valves")
    st.markdown("- Click 'Start Animation' to see flow")
    st.markdown("- Changes update on rerun")
with col3:
    st.markdown("**Notes:**")
    st.markdown("- Flow follows main pipe (left→right)")
    st.markdown("- Buffer flickers on any open valve")
    st.markdown("- Gas bubbles from top barriers")

# Debug
with st.expander("🔧 Debug Information"):
    st.write("**Loaded Valves:**")
    st.json(valves)
    st.write("**Current States:**")
    st.json(st.session_state.valve_states)
    st.write(f"**Total Valves:** {len(valves)}")
