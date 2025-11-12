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
        st.markdown("*Animation running: Process flow L→R, gas bubbles upward.*")
    else:
        # Static display
        try:
            static_img = Image.open(PID_FILE).convert("RGB")
            st.image(static_img, use_container_width=True, caption="Static P&ID - Click 'Start Animation' to see flow")
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

# Animation function (tailored to tandem seal: horizontal process flow, vertical gas)
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
    
    # Main process flow: Horizontal dashes along y=350 (your pipe centerline), only past open valves
    pipe_y = 350
    flow_speed = 30  # Slower for realism
    for tag, data in valves.items():
        if st.session_state.valve_states[tag]:  # Only if this valve open
            vx, vy = data["x"], data["y"]
            # Start flow after valve; multiple particles for continuous look
            for i in range(4):  # 4 particles per valve
                offset = (int(t * flow_speed + i * 60) % 500)  # Cycle length 500px
                fx = vx + offset
                if vx < fx < 1200:  # Flow right, within bounds
                    # Green dash (pipe flow style)
                    draw.rectangle([fx, pipe_y-3, fx+20, pipe_y+3], fill=(0, 200, 0, 200))
                    # Small arrowhead
                    draw.polygon([(fx+20, pipe_y-2), (fx+25, pipe_y), (fx+20, pipe_y+2)], fill=(0, 150, 0, 220))
    
    # Barrier gas: Upward bubbles from gas supply valves (V-601/V-602 at bottom, but rise up; y<400 for top lines)
    bubble_speed = 20
    for tag, data in valves.items():
        if st.session_state.valve_states[tag] and data["y"] > 400:  # Bottom gas valves (V-601 etc.)
            vx, vy = data["x"], data["y"]
            for i in range(2):  # 2 bubbles per valve
                bubble_offset = (int(t * bubble_speed + i * 40) % 200)
                by = vy - bubble_offset  # Rise upward
                if by > 100:  # Within diagram
                    # Light blue bubble
                    draw.ellipse([vx-4, by-4, vx+4, by+4], fill=(173, 216, 230, 180))
                    draw.ellipse([vx-2, by-2, vx+2, by+2], fill=(135, 206, 250, 220))  # Inner glow
    
    return pid_img.convert("RGB")

# Run animation if toggled (8s demo loop for Cloud)
if st.session_state.animation_running:
    start_time = time.time()
    anim_placeholder = st.empty()
    
    while time.time() - start_time < 8:
        t = time.time() % 8  # Cycle time
        frame = create_animated_frame(t)
        
        buf = io.BytesIO()
        frame.save(buf, format="PNG")
        anim_placeholder.image(buf.getvalue(), use_container_width=True, caption=f"Tandem Seal Flow | t={t:.1f}s")
        
        time.sleep(0.2)  # 5 FPS for smooth, non-CPU-heavy
    
    st.session_state.animation_running = False
    st.success("Animation demo complete! Toggle valves and restart to see changes.")
    st.rerun()

# Instructions (updated for tandem seal)
st.markdown("---")
st.markdown("### 📋 Instructions")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**Valve Colors:**")
    st.markdown("- 🟢 Green = Valve OPEN")
    st.markdown("- 🔴 Red = Valve CLOSED")
with col2:
    st.markdown("**Flow Animation:**")
    st.markdown("- Green dashes/arrows: Process fluid L→R")
    st.markdown("- Blue bubbles: Barrier gas upward")
    st.markdown("- Only through open valves")
with col3:
    st.markdown("**Controls:**")
    st.markdown("- Sidebar toggles update live")
    st.markdown("- 'Start Animation' for 8s demo")
    st.markdown("- Restart after changes")

# Debug
with st.expander("🔧 Debug Information"):
    st.write("**Loaded Valves:**")
    st.json(valves)
    st.write("**Current States:**")
    st.json(st.session_state.valve_states)
    st.write(f"**Total Valves:** {len(valves)}")

# Footer note
st.markdown("---")
st.caption("Tandem Seal Simulation: Buffer gas flow through primary/secondary seals.")
