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

# Load valves safely
def load_valves():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading valves.json: {e}")
            return {}
    return {}

valves = load_valves()
if not valves:
    st.error("No valves found in valves.json")
    st.stop()

# Session state (force booleans)
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: bool(data.get("state", False)) for tag, data in valves.items()}

if "animation_running" not in st.session_state:
    st.session_state.animation_running = False

# Sidebar (your original, fixed sum)
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
    
    # Fixed: sum with count
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
        placeholder = st.empty()
        st.markdown("*Animation running: Lines color + arrows along pipes.*")
    else:
        # Static display
        try:
            static_img = Image.open(PID_FILE).convert("RGB")
            st.image(static_img, use_container_width=True, caption="Static P&ID - Toggle valves & start animation")
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

# Paths (pixel-accurate from your P&ID image)
PATHS = [
    # Main line with 90°: V-101 → V-301 → CV-1 → CV-2 → V-105
    {
        "name": "Main Process Line",
        "valves": ["V-101", "V-301", "CV-1", "CV-2", "V-105"],
        "segments": [
            (150, 420, 250, 420),  # V-101 to V-301 horizontal
            (250, 420, 450, 420),  # V-301 to CV-1 horizontal
            (450, 420, 450, 520),  # 90° down from CV-1 to CV-2 vertical
            (450, 520, 600, 520)   # CV-2 to V-105 horizontal
        ]
    },
    # Barrier gas (top down)
    {
        "name": "Barrier Gas",
        "valves": ["V-601"],
        "segments": [
            (300, 250, 300, 420)  # V-601 down to junction
        ]
    },
    # Buffer gas (bottom up)
    {
        "name": "Buffer Gas",
        "valves": ["V-602"],
        "segments": [
            (550, 600, 550, 420)  # V-602 up to junction
        ]
    },
    # Drain
    {
        "name": "Drain Line",
        "valves": ["V-501"],
        "segments": [
            (700, 580, 850, 580)  # V-501 horizontal
        ]
    }
]

# Animation frame function
def create_animated_frame(t):
    try:
        pid_img = Image.open(PID_FILE).convert("RGBA")
    except:
        pid_img = Image.new("RGBA", (1200, 800), (255, 255, 255))
    
    draw = ImageDraw.Draw(pid_img)
    
    # Font
    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except:
        font = ImageFont.load_default()
    
    # Draw valves
    for tag, data in valves.items():
        x, y = data["x"], data["y"]
        current_state = st.session_state.valve_states[tag]
        color = (0, 255, 0, 255) if current_state else (255, 0, 0, 255)
        
        # Valve circle
        draw.ellipse([x-8, y-8, x+8, y+8], fill=color, outline="white", width=2)
        draw.text((x+12, y-10), tag, fill="white", font=font)
    
    # Animate paths (red/green lines + arrows)
    for path in PATHS:
        all_open = all(st.session_state.valve_states.get(v, False) for v in path["valves"])
        line_color = (0, 255, 0, 180) if all_open else (255, 0, 0, 180)
        
        for seg in path["segments"]:
            sx, sy, ex, ey = seg
            # Color the line
            draw.line([(sx, sy), (ex, ey)], fill=line_color, width=8)
            
            if all_open:
                # Moving arrows (3 per segment, direction-aware)
                dx, dy = ex - sx, ey - sy
                seg_len = math.sqrt(dx**2 + dy**2)
                for i in range(3):
                    offset = (int(t * 40 + i * (seg_len / 3)) % int(seg_len))
                    fx = sx + (dx / seg_len) * offset if seg_len > 0 else sx
                    fy = sy + (dy / seg_len) * offset if seg_len > 0 else sy
                    
                    # Arrow triangle (points forward)
                    arrow_size = 12
                    if abs(dx) > abs(dy):  # Horizontal
                        dir_pts = [(fx, fy-6), (fx+arrow_size, fy), (fx, fy+6)] if dx > 0 else [(fx, fy+6), (fx-arrow_size, fy), (fx, fy-6)]
                    else:  # Vertical
                        dir_pts = [(fx-6, fy), (fx, fy+arrow_size), (fx+6, fy)] if dy > 0 else [(fx+6, fy), (fx, fy-arrow_size), (fx-6, fy)]
                    
                    draw.polygon(dir_pts, fill=(0, 200, 0, 255))
    
    return pid_img.convert("RGB")

# Run animation
if st.session_state.animation_running:
    start_time = time.time()
    anim_placeholder = st.empty()
    
    while time.time() - start_time < 8:  # 8s loop
        t = time.time() - start_time
        frame = create_animated_frame(t)
        
        buf = io.BytesIO()
        frame.save(buf, format="PNG")
        anim_placeholder.image(buf.getvalue(), use_container_width=True, caption=f"Flow Lines: Green/Red + Arrows | t={t:.1f}s")
        
        time.sleep(0.2)  # 5 FPS
    
    st.session_state.animation_running = False
    st.success("Animation complete! Toggle valves and restart.")
    st.rerun()

# Instructions
st.markdown("---")
st.markdown("### 📋 Instructions")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**Line Colors:**")
    st.markdown("- 🟢 Green = Flow Active")
    st.markdown("- 🔴 Red = Blocked")
with col2:
    st.markdown("**Arrows:**")
    st.markdown("- Move along pipes")
    st.markdown("- Direction: L→R main, top→bottom gas")
with col3:
    st.markdown("**Controls:**")
    st.markdown("- Sidebar toggles")
    st.markdown("- Start animation to see")

# Debug
with st.expander("🔧 Debug Information"):
    st.write("**Loaded Valves:**")
    st.json(valves)
    st.write("**Current States:**")
    st.json(st.session_state.valve_states)
    st.write(f"**Total Valves:** {len(valves)}")

# Footer
st.markdown("---")
st.caption("P&ID lines now aligned with your diagram pipes.")
