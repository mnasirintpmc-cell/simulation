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
        st.rerun()

# Main app
st.title("Tandem Seal P&ID Interactive Simulation")
col1, col2 = st.columns([3, 1])
with col1:
    # Create and display the P&ID with valve indicators
    composite_img = create_pid_with_valves()
    st.image(composite_img, use_container_width=True, caption="Interactive P&ID - Valves update in real-time")
with col2:
    # Right sidebar for detailed status
    st.header("🔍 Valve Details")
    st.markdown("---")
   
    for tag, data in valves.items():
        current_state = st.session_state.valve_states[tag]
        status = "🟢 OPEN" if current_state else "🔴 CLOSED"
       
        with st.expander(f"{tag} - {status}", expanded=False):
            st.write(f"**Position:** ({data['x']}, {data['y']})")
            st.write(f"**Current State:** {status}")
           
            # Mini toggle inside expander
            if st.button(f"Toggle {tag}", key=f"mini_{tag}", use_container_width=True):
                st.session_state.valve_states[tag] = not current_state
                st.rerun()

# Bottom section for additional info
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
    st.markdown("- Click valve details for more info")
    st.markdown("- Use quick actions for bulk operations")
with col3:
    st.markdown("**Notes:**")
    st.markdown("- Valve positions are fixed")
    st.markdown("- Changes are temporary")
    st.markdown("- No file modifications")
# Debug information
with st.expander("🔧 Debug Information"):
    st.write("**Loaded Valves Configuration:**")
    st.json(valves)
   
    st.write("**Current Valve States:**")
    st.json(st.session_state.valve_states)
   
    st.write(f"**Total Valves:** {len(valves)}")

# Animation loop if running
if st.session_state.animation_running:
    start_time = time.time()
    anim_placeholder = st.empty()
    
    while time.time() - start_time < 8:  # 8s loop
        t = time.time() - start_time
        frame = create_animated_frame(t)
        
        buf = io.BytesIO()
        frame.save(buf, format="PNG")
        anim_placeholder.image(buf.getvalue(), use_container_width=True, caption="Flow animation - Arrows move along paths")
        
        time.sleep(0.2)  # 5 FPS
    
    st.session_state.animation_running = False
    st.success("Animation complete! Restart for changes.")
    st.rerun()

# Function to create base image with valve indicators (your original)
def create_pid_with_valves():
    try:
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
       
        for tag, data in valves.items():
            x, y = data["x"], data["y"]
            current_state = st.session_state.valve_states[tag]
           
            # Choose color based on valve state
            color = (0, 255, 0) if current_state else (255, 0, 0)
           
            # Draw valve indicator
            draw.ellipse([x-8, y-8, x+8, y+8], fill=color, outline="white", width=2)
            draw.text((x+12, y-10), tag, fill="white", stroke_fill="black", stroke_width=1)
           
        return pid_img.convert("RGB")
    except Exception as e:
        st.error(f"Error creating P&ID image: {e}")
        try:
            return Image.open(PID_FILE).convert("RGB")
        except:
            return Image.new("RGB", (800, 500), (255, 255, 255))

# Function to add animation (lines color change + arrows)
def create_animated_frame(t):
    pid_img = Image.open(PID_FILE).convert("RGBA")
    draw = ImageDraw.Draw(pid_img)
    font = ImageFont.load_default()

    # Draw valve indicators (same as static)
    for tag, data in valves.items():
        x, y = data["x"], data["y"]
        state = st.session_state.valve_states[tag]
        color = (0, 255, 0) if state else (255, 0, 0)
        draw.ellipse([x-8, y-8, x+8, y+8], fill=color, outline="white", width=2)
        draw.text((x+12, y-10), tag, fill="white", font=font)

    # Path 1: V-101 → V-301 → 90° from CV-1 → CV-2 → V-105 (y=320 main, vertical down from CV-1)
    path1_valves = ['V-101', 'V-301', 'CV-1', 'CV-2', 'V-105']
    all_open1 = all(st.session_state.valve_states.get(v, False) for v in path1_valves)
    line_color1 = (0, 255, 0) if all_open1 else (255, 0, 0)
    segments1 = [
        (120, 320, 220, 320),  # V-101 to V-301 horizontal
        (220, 320, 320, 320),  # V-301 to CV-1 horizontal
        (320, 320, 320, 420),  # 90° down from CV-1 to CV-2 vertical
        (320, 420, 420, 420),  # CV-2 to V-105 horizontal
    ]
    for sx, sy, ex, ey in segments1:
        draw.line([(sx, sy), (ex, ey)], fill=line_color1, width=5)
        if all_open1:
            # Arrows moving along segment
            dx, dy = ex - sx, ey - sy
            len_seg = math.sqrt(dx**2 + dy**2)
            for i in range(5):
                offset = (t * 30 + i * (len_seg / 5)) % len_seg
                ax = sx + (dx / len_seg) * offset
                ay = sy + (dy / len_seg) * offset
                angle = math.atan2(dy, dx)
                arrow_len = 10
                arrow1x = ax - arrow_len * math.sin(angle - math.pi/6)
                arrow1y = ay + arrow_len * math.cos(angle - math.pi/6)
                arrow2x = ax - arrow_len * math.sin(angle + math.pi/6)
                arrow2y = ay + arrow_len * math.cos(angle + math.pi/6)
                draw.polygon([(ax, ay), (arrow1x, arrow1y), (arrow2x, arrow2y)], fill=(0, 200, 0))

    # Path 2: Barrier Gas (top, down from V-601)
    path2_valves = ['V-601', 'MPV-7', 'CV-1']
    all_open2 = all(st.session_state.valve_states.get(v, False) for v in path2_valves)
    line_color2 = (0, 255, 0) if all_open2 else (255, 0, 0)
    segments2 = [
        (200, 200, 200, 320)  # V-601 down to CV-1 vertical
    ]
    for sx, sy, ex, ey in segments2:
        draw.line([(sx, sy), (ex, ey)], fill=line_color2, width=5)
        if all_open2:
            # Down arrows
            dx, dy = ex - sx, ey - sy
            len_seg = math.sqrt(dx**2 + dy**2)
            for i in range(5):
                offset = (t * 30 + i * (len_seg / 5)) % len_seg
                ax = sx + (dx / len_seg) * offset
                ay = sy + (dy / len_seg) * offset
                angle = math.atan2(dy, dx)
                arrow_len = 10
                arrow1x = ax - arrow_len * math.sin(angle - math.pi/6)
                arrow1y = ay + arrow_len * math.cos(angle - math.pi/6)
                arrow2x = ax - arrow_len * math.sin(angle + math.pi/6)
                arrow2y = ay + arrow_len * math.cos(angle + math.pi/6)
                draw.polygon([(ax, ay), (arrow1x, arrow1y), (arrow2x, arrow2y)], fill=(0, 200, 0))

    # Path 3: Buffer Gas (bottom, up from V-602)
    path3_valves = ['V-602', 'MPV-8', 'V-104']
    all_open3 = all(st.session_state.valve_states.get(v, False) for v in path3_valves)
    line_color3 = (0, 255, 0) if all_open3 else (255, 0, 0)
    segments3 = [
        (350, 450, 350, 320)  # V-602 up to V-104 vertical
    ]
    for sx, sy, ex, ey in segments3:
        draw.line([(sx, sy), (ex, ey)], fill=line_color3, width=5)
        if all_open3:
            # Up arrows (reverse direction for up)
            dx, dy = ex - sx, ey - sy
            len_seg = math.sqrt(dx**2 + dy**2)
            for i in range(5):
                offset = (t * 30 + i * (len_seg / 5)) % len_seg
                ax = sx + (dx / len_seg) * offset
                ay = sy + (dy / len_seg) * offset
                angle = math.atan2(dy, dx) + math.pi  # Reverse for up
                arrow_len = 10
                arrow1x = ax - arrow_len * math.sin(angle - math.pi/6)
                arrow1y = ay + arrow_len * math.cos(angle - math.pi/6)
                arrow2x = ax - arrow_len * math.sin(angle + math.pi/6)
                arrow2y = ay + arrow_len * math.cos(angle + math.pi/6)
                draw.polygon([(ax, ay), (arrow1x, arrow1y), (arrow2x, arrow2y)], fill=(0, 200, 0))

    # Add more paths if needed (e.g., drain V-501 horizontal)
    path4_valves = ['V-501']
    all_open4 = all(st.session_state.valve_states.get(v, False) for v in path4_valves)
    line_color4 = (0, 255, 0) if all_open4 else (255, 0, 0)
    segments4 = [
        (400, 480, 500, 480)  # V-501 to PI-105 horizontal
    ]
    for sx, sy, ex, ey in segments4:
        draw.line([(sx, sy), (ex, ey)], fill=line_color4, width=5)
        if all_open4:
            dx, dy = ex - sx, ey - sy
            len_seg = math.sqrt(dx**2 + dy**2)
            for i in range(5):
                offset = (t * 30 + i * (len_seg / 5)) % len_seg
                ax = sx + (dx / len_seg) * offset
                ay = sy + (dy / len_seg) * offset
                angle = math.atan2(dy, dx)
                arrow_len = 10
                arrow1x = ax - arrow_len * math.sin(angle - math.pi/6)
                arrow1y = ay + arrow_len * math.cos(angle - math.pi/6)
                arrow2x = ax - arrow_len * math.sin(angle + math.pi/6)
                arrow2y = ay + arrow_len * math.cos(angle + math.pi/6)
                draw.polygon([(ax, ay), (arrow1x, arrow1y), (arrow2x, arrow2y)], fill=(0, 200, 0))

    return pid_img
