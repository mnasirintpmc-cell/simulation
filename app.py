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

def create_pid_with_pipes():
    """Create P&ID display with pipes and valves"""
    try:
        # Load the actual P&ID image
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
        
        # Load data
        valves = load_valves()
        pipes = load_pipes()
        
        # Draw pipes with bright colors and thicker lines
        for i, pipe in enumerate(pipes):
            x1, y1, x2, y2 = pipe["x1"], pipe["y1"], pipe["x2"], pipe["y2"]
            
            # Highlight selected pipe with VIOLET and thicker line
            if st.session_state.get("selected_pipe") == i:
                pipe_color = (148, 0, 211)  # VIOLET for selected pipe
                pipe_width = 12  # Extra thick for selected pipe
            else:
                pipe_color = (0, 0, 255)  # Bright blue for normal pipes
                pipe_width = 8
            
            draw.line([(x1, y1), (x2, y2)], fill=pipe_color, width=pipe_width)
            
            # Draw pipe endpoints - RED for selected pipe, normal colors for others
            if st.session_state.get("selected_pipe") == i:
                # RED endpoints for selected pipe
                draw.ellipse([x1-6, y1-6, x1+6, y1+6], fill=(255, 0, 0), outline="white", width=2)
                draw.ellipse([x2-6, y2-6, x2+6, y2+6], fill=(255, 0, 0), outline="white", width=2)
            else:
                # Normal colors for unselected pipes
                draw.ellipse([x1-4, y1-4, x1+4, y1+4], fill=(255, 0, 0))  # Red dot start
                draw.ellipse([x2-4, y2-4, x2+4, y2+4], fill=(0, 255, 0))  # Green dot end
        
        # Draw valves with smaller sizes
        for tag, data in valves.items():
            x, y = data["x"], data["y"]
            current_state = st.session_state.valve_states.get(tag, False)
            
            # Bright colors for valves
            valve_color = (0, 255, 0) if current_state else (255, 0, 0)  # Green/Red
            
            # Smaller valve indicators
            draw.ellipse([x-8, y-8, x+8, y+8], fill=valve_color, outline="black", width=2)
            
            # Draw valve tag
            draw.text((x+10, y-6), tag, fill="black")
        
        return pid_img.convert("RGB")
    
    except Exception as e:
        st.error(f"Error creating display: {e}")
        return Image.new("RGB", (1200, 800), (255, 255, 255))

# Load data
valves = load_valves()
pipes = load_pipes()

# Initialize session state
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}

if "selected_pipe" not in st.session_state:
    st.session_state.selected_pipe = None

# Main app
st.title("P&ID Interactive Simulation - Pipe Editor")

# Pipe Movement Controls
st.header("🔧 Pipe Movement Controls")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Select Pipe")
    if pipes:
        pipe_options = [f"Pipe {i+1} ({pipes[i]['x1']},{pipes[i]['y1']} to {pipes[i]['x2']},{pipes[i]['y2']})" for i in range(len(pipes))]
        selected_pipe = st.selectbox("Choose pipe to move:", options=pipe_options, index=st.session_state.selected_pipe or 0)
        st.session_state.selected_pipe = pipe_options.index(selected_pipe)

with col2:
    st.subheader("Move Selected Pipe")
    move_x = st.number_input("Move X (pixels)", value=0, key="move_x")
    move_y = st.number_input("Move Y (pixels)", value=0, key="move_y")
    
    if st.button("Apply Movement", use_container_width=True):
        if st.session_state.selected_pipe is not None:
            pipe_index = st.session_state.selected_pipe
            pipes[pipe_index]["x1"] += move_x
            pipes[pipe_index]["y1"] += move_y
            pipes[pipe_index]["x2"] += move_x
            pipes[pipe_index]["y2"] += move_y
            save_pipes(pipes)
            st.rerun()

with col3:
    st.subheader("Quick Movements")
    if st.button("← Move Left 10px", use_container_width=True):
        if st.session_state.selected_pipe is not None:
            pipe_index = st.session_state.selected_pipe
            pipes[pipe_index]["x1"] -= 10
            pipes[pipe_index]["x2"] -= 10
            save_pipes(pipes)
            st.rerun()
    
    if st.button("→ Move Right 10px", use_container_width=True):
        if st.session_state.selected_pipe is not None:
            pipe_index = st.session_state.selected_pipe
            pipes[pipe_index]["x1"] += 10
            pipes[pipe_index]["x2"] += 10
            save_pipes(pipes)
            st.rerun()
    
    if st.button("↑ Move Up 10px", use_container_width=True):
        if st.session_state.selected_pipe is not None:
            pipe_index = st.session_state.selected_pipe
            pipes[pipe_index]["y1"] -= 10
            pipes[pipe_index]["y2"] -= 10
            save_pipes(pipes)
            st.rerun()
    
    if st.button("↓ Move Down 10px", use_container_width=True):
        if st.session_state.selected_pipe is not None:
            pipe_index = st.session_state.selected_pipe
            pipes[pipe_index]["y1"] += 10
            pipes[pipe_index]["y2"] += 10
            save_pipes(pipes)
            st.rerun()

# Manual Pipe Editing
st.header("✏️ Manual Pipe Editing")
if st.session_state.selected_pipe is not None:
    pipe_index = st.session_state.selected_pipe
    with st.form(f"edit_pipe_{pipe_index}"):
        st.subheader(f"Edit Pipe {pipe_index + 1}")
        st.info("🔮 **VIOLET pipe with RED endpoints = Currently Selected**")
        col1, col2 = st.columns(2)
        
        with col1:
            new_x1 = st.number_input("Start X", value=pipes[pipe_index]["x1"], key="edit_x1")
            new_y1 = st.number_input("Start Y", value=pipes[pipe_index]["y1"], key="edit_y1")
        
        with col2:
            new_x2 = st.number_input("End X", value=pipes[pipe_index]["x2"], key="edit_x2")
            new_y2 = st.number_input("End Y", value=pipes[pipe_index]["y2"], key="edit_y2")
        
        if st.form_submit_button("Update Pipe Coordinates"):
            pipes[pipe_index]["x1"] = new_x1
            pipes[pipe_index]["y1"] = new_y1
            pipes[pipe_index]["x2"] = new_x2
            pipes[pipe_index]["y2"] = new_y2
            save_pipes(pipes)
            st.rerun()

# Display the P&ID with pipes
st.header("🎯 P&ID Display")
composite_img = create_pid_with_pipes()
st.image(composite_img, use_container_width=True, caption="🔮 VIOLET pipe with RED endpoints = Selected | Blue pipes = Normal | Red/Green dots = Pipe endpoints")

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
    st.header("📊 Pipe Info")
    if st.session_state.selected_pipe is not None:
        pipe = pipes[st.session_state.selected_pipe]
        st.success(f"**Selected Pipe {st.session_state.selected_pipe + 1}:**")
        st.write(f"Start: ({pipe['x1']}, {pipe['y1']})")
        st.write(f"End: ({pipe['x2']}, {pipe['y2']})")
        st.write("🔮 **VIOLET with RED endpoints**")
    else:
        st.write("No pipe selected")

# Quick actions
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    if st.button("Open All Valves"):
        for tag in valves:
            st.session_state.valve_states[tag] = True
        st.rerun()
with col2:
    if st.button("Close All Valves"):
        for tag in valves:
            st.session_state.valve_states[tag] = False
        st.rerun()

# Reset functionality
if st.button("Reset Pipe Selection"):
    st.session_state.selected_pipe = None
    st.rerun()

# Debug information
with st.expander("🔧 Debug Information"):
    st.write("**Valves:**", valves)
    st.write("**Pipes:**", pipes)
    st.write("**Selected Pipe:**", st.session_state.selected_pipe)
