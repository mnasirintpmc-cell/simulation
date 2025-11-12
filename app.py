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
    """Load pipes with proper error handling"""
    try:
        if os.path.exists(PIPES_DATA_FILE):
            with open(PIPES_DATA_FILE, "r") as f:
                pipes_data = json.load(f)
                # Ensure it's a list and has the right structure
                if isinstance(pipes_data, list) and len(pipes_data) > 0:
                    return pipes_data
    except Exception as e:
        st.error(f"Error loading pipes: {e}")
    return []

def save_pipes(pipes_data):
    """Save pipes with proper formatting"""
    with open(PIPES_DATA_FILE, "w") as f:
        json.dump(pipes_data, f, indent=2)

def create_pid_with_pipes():
    """Create P&ID display with pipes and valves"""
    try:
        # Load the actual P&ID image
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
        
        # Load data
        valves = load_valves()
        pipes = st.session_state.pipes  # Use session state pipes
        
        # Draw pipes
        for i, pipe in enumerate(pipes):
            x1, y1, x2, y2 = pipe["x1"], pipe["y1"], pipe["x2"], pipe["y2"]
            
            # Highlight selected pipe with VIOLET
            if st.session_state.get("selected_pipe") == i:
                pipe_color = (148, 0, 211)  # VIOLET for selected pipe
                pipe_width = 12
            else:
                pipe_color = (0, 0, 255)  # Blue for normal pipes
                pipe_width = 8
            
            draw.line([(x1, y1), (x2, y2)], fill=pipe_color, width=pipe_width)
            
            # Draw endpoints
            endpoint_size = 6 if st.session_state.get("selected_pipe") == i else 4
            endpoint_color_start = (255, 0, 0)  # Red
            endpoint_color_end = (0, 255, 0) if st.session_state.get("selected_pipe") != i else (255, 0, 0)  # Green or Red
            
            draw.ellipse([x1-endpoint_size, y1-endpoint_size, x1+endpoint_size, y1+endpoint_size], 
                        fill=endpoint_color_start, outline="white", width=2)
            draw.ellipse([x2-endpoint_size, y2-endpoint_size, x2+endpoint_size, y2+endpoint_size], 
                        fill=endpoint_color_end, outline="white", width=2)
        
        # Draw valves
        for tag, data in valves.items():
            x, y = data["x"], data["y"]
            current_state = st.session_state.valve_states.get(tag, False)
            
            valve_color = (0, 255, 0) if current_state else (255, 0, 0)
            draw.ellipse([x-8, y-8, x+8, y+8], fill=valve_color, outline="black", width=2)
            draw.text((x+10, y-6), tag, fill="black")
        
        return pid_img.convert("RGB")
    
    except Exception as e:
        st.error(f"Error creating display: {e}")
        return Image.new("RGB", (1200, 800), (255, 255, 255))

# Initialize session state
if "valve_states" not in st.session_state:
    valves = load_valves()
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}

if "pipes" not in st.session_state:
    st.session_state.pipes = load_pipes()

if "selected_pipe" not in st.session_state:
    st.session_state.selected_pipe = None

# Main app
st.title("P&ID Interactive Simulation - Drag & Drop Pipes")

# Debug info
st.write(f"Loaded {len(st.session_state.pipes)} pipes")

# Pipe Movement Controls
st.header("🔧 Pipe Movement Controls")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Select Pipe")
    if st.session_state.pipes:
        pipe_options = [f"Pipe {i+1} ({st.session_state.pipes[i]['x1']},{st.session_state.pipes[i]['y1']} to {st.session_state.pipes[i]['x2']},{st.session_state.pipes[i]['y2']})" 
                       for i in range(len(st.session_state.pipes))]
        selected_pipe = st.selectbox("Choose pipe to move:", options=pipe_options, 
                                   index=st.session_state.selected_pipe or 0)
        st.session_state.selected_pipe = pipe_options.index(selected_pipe)

with col2:
    st.subheader("Drag Pipe")
    st.info("Use these controls to drag the selected pipe")
    
    drag_x = st.slider("Drag X", -50, 50, 0, key="drag_x")
    drag_y = st.slider("Drag Y", -50, 50, 0, key="drag_y")
    
    if st.button("Apply Drag", use_container_width=True):
        if st.session_state.selected_pipe is not None:
            pipe_index = st.session_state.selected_pipe
            st.session_state.pipes[pipe_index]["x1"] += drag_x
            st.session_state.pipes[pipe_index]["y1"] += drag_y
            st.session_state.pipes[pipe_index]["x2"] += drag_x
            st.session_state.pipes[pipe_index]["y2"] += drag_y
            save_pipes(st.session_state.pipes)
            st.rerun()

with col3:
    st.subheader("Quick Drag")
    col_up, col_down = st.columns(2)
    with col_up:
        if st.button("↑", use_container_width=True):
            if st.session_state.selected_pipe is not None:
                pipe_index = st.session_state.selected_pipe
                st.session_state.pipes[pipe_index]["y1"] -= 10
                st.session_state.pipes[pipe_index]["y2"] -= 10
                save_pipes(st.session_state.pipes)
                st.rerun()
    
    col_left, col_right = st.columns(2)
    with col_left:
        if st.button("←", use_container_width=True):
            if st.session_state.selected_pipe is not None:
                pipe_index = st.session_state.selected_pipe
                st.session_state.pipes[pipe_index]["x1"] -= 10
                st.session_state.pipes[pipe_index]["x2"] -= 10
                save_pipes(st.session_state.pipes)
                st.rerun()
    with col_right:
        if st.button("→", use_container_width=True):
            if st.session_state.selected_pipe is not None:
                pipe_index = st.session_state.selected_pipe
                st.session_state.pipes[pipe_index]["x1"] += 10
                st.session_state.pipes[pipe_index]["x2"] += 10
                save_pipes(st.session_state.pipes)
                st.rerun()
    
    with col_down:
        if st.button("↓", use_container_width=True):
            if st.session_state.selected_pipe is not None:
                pipe_index = st.session_state.selected_pipe
                st.session_state.pipes[pipe_index]["y1"] += 10
                st.session_state.pipes[pipe_index]["y2"] += 10
                save_pipes(st.session_state.pipes)
                st.rerun()

# Manual Coordinate Editing
st.header("✏️ Manual Coordinate Editing")
if st.session_state.selected_pipe is not None:
    pipe_index = st.session_state.selected_pipe
    pipe = st.session_state.pipes[pipe_index]
    
    with st.form(f"edit_pipe_{pipe_index}"):
        st.subheader(f"Edit Pipe {pipe_index + 1} Coordinates")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Start Point**")
            new_x1 = st.number_input("X1", value=pipe["x1"], key="edit_x1")
            new_y1 = st.number_input("Y1", value=pipe["y1"], key="edit_y1")
        
        with col2:
            st.write("**End Point**")
            new_x2 = st.number_input("X2", value=pipe["x2"], key="edit_x2")
            new_y2 = st.number_input("Y2", value=pipe["y2"], key="edit_y2")
        
        if st.form_submit_button("💾 Save Coordinates"):
            st.session_state.pipes[pipe_index]["x1"] = new_x1
            st.session_state.pipes[pipe_index]["y1"] = new_y1
            st.session_state.pipes[pipe_index]["x2"] = new_x2
            st.session_state.pipes[pipe_index]["y2"] = new_y2
            save_pipes(st.session_state.pipes)
            st.success("Coordinates saved!")
            st.rerun()

# Display the P&ID
st.header("🎯 P&ID Display")
composite_img = create_pid_with_pipes()
st.image(composite_img, use_container_width=True, 
         caption="🔮 VIOLET = Selected pipe | Use drag controls above to move pipes")

# Valve controls in sidebar
with st.sidebar:
    st.header("🎯 Valve Controls")
    st.markdown("---")
    
    for tag, data in valves.items():
        current_state = st.session_state.valve_states[tag]
        button_label = f"🔴 {tag} - OPEN" if current_state else f"🟢 {tag} - CLOSED"
        
        if st.button(button_label, key=f"btn_{tag}", use_container_width=True):
            st.session_state.valve_states[tag] = not current_state
            st.rerun()

    st.markdown("---")
    st.header("📊 Selected Pipe Info")
    if st.session_state.selected_pipe is not None:
        pipe = st.session_state.pipes[st.session_state.selected_pipe]
        st.success(f"**Pipe {st.session_state.selected_pipe + 1}**")
        st.write(f"Start: ({pipe['x1']}, {pipe['y1']})")
        st.write(f"End: ({pipe['x2']}, {pipe['y2']})")
        st.info("🔮 Violet with red endpoints")
    else:
        st.write("No pipe selected")
    
    st.markdown("---")
    st.header("💾 Save/Load")
    if st.button("💾 Save All Pipes", use_container_width=True):
        save_pipes(st.session_state.pipes)
        st.success("All pipes saved!")
    
    if st.button("🔄 Reload Pipes", use_container_width=True):
        st.session_state.pipes = load_pipes()
        st.rerun()

# Quick actions
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    if st.button("Open All Valves"):
        for tag in st.session_state.valve_states:
            st.session_state.valve_states[tag] = True
        st.rerun()
with col2:
    if st.button("Close All Valves"):
        for tag in st.session_state.valve_states:
            st.session_state.valve_states[tag] = False
        st.rerun()

# Current coordinates
st.markdown("---")
st.header("📋 Current Pipe Coordinates")
st.json(st.session_state.pipes)
