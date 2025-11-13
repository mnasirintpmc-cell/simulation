import streamlit as st
import json
from PIL import Image, ImageDraw
import os

st.set_page_config(layout="wide")

# Configuration
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"
PIPES_DATA_FILE = "pipes.json"

def load_valves():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def load_pipes():
    if os.path.exists(PIPES_DATA_FILE):
        with open(PIPES_DATA_FILE, "r") as f:
            return json.load(f)
    return []

def save_pipes(pipes_data):
    with open(PIPES_DATA_FILE, "w") as f:
        json.dump(pipes_data, f, indent=2)

def create_pid_with_valves_and_pipes():
    """Create P&ID image with valve indicators AND pipes"""
    try:
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
        
        # Draw pipes FIRST (so valves appear on top)
        if st.session_state.pipes:
            for i, pipe in enumerate(st.session_state.pipes):
                color = (148, 0, 211) if i == st.session_state.selected_pipe else (0, 0, 255)  # Purple for selected
                width = 6 if i == st.session_state.selected_pipe else 4
                draw.line([(pipe["x1"], pipe["y1"]), (pipe["x2"], pipe["y2"])], fill=color, width=width)
        
        # Draw valves on top of pipes
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
            return Image.new("RGB", (800, 600), (255, 255, 255))

# Load valve data
valves = load_valves()
pipes = load_pipes()

# Initialize session state
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}

if "selected_pipe" not in st.session_state:
    st.session_state.selected_pipe = 0 if pipes else None

if "pipes" not in st.session_state:
    st.session_state.pipes = pipes

# Main app
st.title("P&ID Interactive Simulation")

if not valves:
    st.error("No valves found in valves.json. Please check your configuration.")
    st.stop()

# Create sidebar for valve controls
with st.sidebar:
    st.header("🎯 Valve Controls")
    st.markdown("---")
    
    # Valve toggle buttons in sidebar
    for tag, data in valves.items():
        current_state = st.session_state.valve_states[tag]
        
        # Create colored button based on state
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
    
    # Pipe selection
    if st.session_state.pipes:
        st.header("📋 Pipe Selection")
        for i in range(len(st.session_state.pipes)):
            is_selected = st.session_state.selected_pipe == i
            label = f"🟣 Pipe {i+1}" if is_selected else f"Pipe {i+1}"
            
            if st.button(label, key=f"pipe_{i}", use_container_width=True):
                st.session_state.selected_pipe = i
                st.rerun()
    
    st.markdown("---")
    
    # Current status summary in sidebar
    st.subheader("📊 Current Status")
    open_valves = sum(1 for state in st.session_state.valve_states.values() if state)
    closed_valves = len(valves) - open_valves
    
    st.metric("Open Valves", open_valves)
    st.metric("Closed Valves", closed_valves)
    if st.session_state.pipes:
        st.metric("Total Pipes", len(st.session_state.pipes))
    
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

# Main content area - P&ID display
col1, col2 = st.columns([3, 1])
with col1:
    # Create and display the P&ID with valve indicators AND pipes
    composite_img = create_pid_with_valves_and_pipes()
    st.image(composite_img, use_container_width=True, caption="Interactive P&ID - 🟣 Purple pipes = Selected | 🔵 Blue pipes = Normal")

with col2:
    # Right sidebar for detailed status
    st.header("🔍 Details")
    st.markdown("---")
    
    # Selected pipe info
    if st.session_state.selected_pipe is not None and st.session_state.pipes:
        pipe = st.session_state.pipes[st.session_state.selected_pipe]
        st.subheader(f"🟣 Pipe {st.session_state.selected_pipe + 1}")
        st.write(f"Start: ({pipe['x1']}, {pipe['y1']})")
        st.write(f"End: ({pipe['x2']}, {pipe['y2']})")
        
        # Calculate current length and orientation
        length = ((pipe["x2"] - pipe["x1"])**2 + (pipe["y2"] - pipe["y1"])**2)**0.5
        is_horizontal = abs(pipe["y2"] - pipe["y1"]) < abs(pipe["x2"] - pipe["x1"])
        orientation = "Horizontal" if is_horizontal else "Vertical"
        st.write(f"**Length:** {int(length)} pixels")
        st.write(f"**Orientation:** {orientation}")
        
        # Pipe movement controls
        st.markdown("---")
        st.subheader("📍 Move Pipe")
        col_up, col_down = st.columns(2)
        with col_up:
            if st.button("↑ Up", use_container_width=True):
                pipe["y1"] -= 5
                pipe["y2"] -= 5
                save_pipes(st.session_state.pipes)
                st.rerun()
        with col_down:
            if st.button("↓ Down", use_container_width=True):
                pipe["y1"] += 5
                pipe["y2"] += 5
                save_pipes(st.session_state.pipes)
                st.rerun()
        
        col_left, col_right = st.columns(2)
        with col_left:
            if st.button("← Left", use_container_width=True):
                pipe["x1"] -= 5
                pipe["x2"] -= 5
                save_pipes(st.session_state.pipes)
                st.rerun()
        with col_right:
            if st.button("→ Right", use_container_width=True):
                pipe["x1"] += 5
                pipe["x2"] += 5
                save_pipes(st.session_state.pipes)
                st.rerun()
        
        # Orientation controls
        st.markdown("---")
        st.subheader("🔄 Change Orientation")
        col_horiz, col_vert = st.columns(2)
        with col_horiz:
            if st.button("➖ Horizontal", use_container_width=True):
                # Make pipe horizontal (keep start point, adjust end point)
                pipe["y2"] = pipe["y1"]
                save_pipes(st.session_state.pipes)
                st.rerun()
        with col_vert:
            if st.button("➡️ Vertical", use_container_width=True):
                # Make pipe vertical (keep start point, adjust end point)
                pipe["x2"] = pipe["x1"]
                save_pipes(st.session_state.pipes)
                st.rerun()
        
        # Length controls
        st.markdown("---")
        st.subheader("📏 Adjust Length")
        col_longer, col_shorter = st.columns(2)
        with col_longer:
            if st.button("➕ Longer", use_container_width=True):
                # Increase length by 10 pixels
                if is_horizontal:
                    if pipe["x2"] > pipe["x1"]:
                        pipe["x2"] += 10
                    else:
                        pipe["x1"] += 10
                else:
                    if pipe["y2"] > pipe["y1"]:
                        pipe["y2"] += 10
                    else:
                        pipe["y1"] += 10
                save_pipes(st.session_state.pipes)
                st.rerun()
        with col_shorter:
            if st.button("➖ Shorter", use_container_width=True):
                # Decrease length by 10 pixels (minimum 10 pixels)
                if is_horizontal:
                    if abs(pipe["x2"] - pipe["x1"]) > 20:
                        if pipe["x2"] > pipe["x1"]:
                            pipe["x2"] -= 10
                        else:
                            pipe["x1"] -= 10
                else:
                    if abs(pipe["y2"] - pipe["y1"]) > 20:
                        if pipe["y2"] > pipe["y1"]:
                            pipe["y2"] -= 10
                        else:
                            pipe["y1"] -= 10
                save_pipes(st.session_state.pipes)
                st.rerun()
        
        # Precise length control
        st.markdown("---")
        st.subheader("🎯 Set Exact Length")
        new_length = st.number_input("Length (pixels)", value=int(length), min_value=10, max_value=500)
        if st.button("Apply Length", use_container_width=True):
            if is_horizontal:
                # Keep Y same, adjust X
                if pipe["x2"] > pipe["x1"]:
                    pipe["x2"] = pipe["x1"] + new_length
                else:
                    pipe["x1"] = pipe["x2"] + new_length
            else:
                # Keep X same, adjust Y
                if pipe["y2"] > pipe["y1"]:
                    pipe["y2"] = pipe["y1"] + new_length
                else:
                    pipe["y1"] = pipe["y2"] + new_length
            save_pipes(st.session_state.pipes)
            st.rerun()
    
    st.markdown("---")
    
    # Valve details
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
    st.markdown("**Pipe Colors:**")
    st.markdown("- 🟣 Purple = Selected Pipe")
    st.markdown("- 🔵 Blue = Normal Pipes")

with col2:
    st.markdown("**Pipe Controls:**")
    st.markdown("- **Arrows**: Move entire pipe")
    st.markdown("- **Horizontal/Vertical**: Change orientation")
    st.markdown("- **Longer/Shorter**: Adjust length")
    st.markdown("- **Length input**: Set exact length")

with col3:
    st.markdown("**Notes:**")
    st.markdown("- Valve positions are fixed")
    st.markdown("- Pipe positions can be adjusted")
    st.markdown("- Changes are saved automatically")
    st.markdown("- Minimum pipe length: 10 pixels")

# Debug information
with st.expander("🔧 Debug Information"):
    st.write("**Loaded Valves Configuration:**")
    st.json(valves)
    
    st.write("**Loaded Pipes Configuration:**")
    st.json(st.session_state.pipes)
    
    st.write("**Current Valve States:**")
    st.json(st.session_state.valve_states)
    
    st.write(f"**Total Valves:** {len(valves)}")
    st.write(f"**Total Pipes:** {len(st.session_state.pipes)}")
    st.write(f"**Selected Pipe:** {st.session_state.selected_pipe}")
