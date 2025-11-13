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

# Load data
valves = load_valves()
pipes = load_pipes()

# Initialize session state
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}

if "selected_pipe" not in st.session_state:
    st.session_state.selected_pipe = 0 if pipes else None

if "pipes" not in st.session_state:
    st.session_state.pipes = pipes

def create_pid_display():
    """Create P&ID display with pipes and valves"""
    try:
        # Load the P&ID image
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
        
        # Draw pipes
        for i, pipe in enumerate(st.session_state.pipes):
            color = (148, 0, 211) if i == st.session_state.selected_pipe else (0, 0, 255)  # Purple for selected
            width = 8 if i == st.session_state.selected_pipe else 4
            draw.line([(pipe["x1"], pipe["y1"]), (pipe["x2"], pipe["y2"])], fill=color, width=width)
        
        # Draw valves
        for tag, data in valves.items():
            x, y = data["x"], data["y"]
            state = st.session_state.valve_states[tag]
            color = (0, 255, 0) if state else (255, 0, 0)
            draw.ellipse([x-8, y-8, x+8, y+8], fill=color, outline="black", width=2)
            draw.text((x+10, y-6), tag, fill="black")
        
        return pid_img.convert("RGB")
    
    except Exception as e:
        st.error(f"Error: {e}")
        return Image.new("RGB", (1200, 800), (255, 255, 255))

# Main app
st.title("P&ID Pipe Position Adjuster")

# Display the P&ID
st.image(create_pid_display(), use_container_width=True, caption="🟣 Purple = Selected Pipe | 🔵 Blue = Other Pipes")

# Pipe selection in sidebar - JUST LIKE VALVES
with st.sidebar:
    st.header("🎯 Select Pipe to Adjust")
    
    if st.session_state.pipes:
        for i in range(len(st.session_state.pipes)):
            is_selected = st.session_state.selected_pipe == i
            label = f"🟣 Pipe {i+1}" if is_selected else f"Pipe {i+1}"
            
            if st.button(label, key=f"pipe_select_{i}", use_container_width=True):
                st.session_state.selected_pipe = i
                st.rerun()
    
    st.markdown("---")
    st.header("🎯 Valve Controls")
    for tag in valves:
        state = st.session_state.valve_states[tag]
        label = f"🔴 {tag}" if state else f"🟢 {tag}"
        if st.button(label, key=f"valve_{tag}", use_container_width=True):
            st.session_state.valve_states[tag] = not state
            st.rerun()

# Pipe position adjustment - SIMPLE NUMBER INPUTS LIKE VALVES
if st.session_state.selected_pipe is not None:
    st.header(f"✏️ Adjust Pipe {st.session_state.selected_pipe + 1} Position")
    
    current_pipe = st.session_state.pipes[st.session_state.selected_pipe]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Start Point")
        new_x1 = st.number_input("X1", value=current_pipe["x1"], key="x1_input")
        new_y1 = st.number_input("Y1", value=current_pipe["y1"], key="y1_input")
    
    with col2:
        st.subheader("End Point")  
        new_x2 = st.number_input("X2", value=current_pipe["x2"], key="x2_input")
        new_y2 = st.number_input("Y2", value=current_pipe["y2"], key="y2_input")
    
    if st.button("💾 Save Pipe Position", type="primary"):
        st.session_state.pipes[st.session_state.selected_pipe]["x1"] = new_x1
        st.session_state.pipes[st.session_state.selected_pipe]["y1"] = new_y1
        st.session_state.pipes[st.session_state.selected_pipe]["x2"] = new_x2
        st.session_state.pipes[st.session_state.selected_pipe]["y2"] = new_y2
        save_pipes(st.session_state.pipes)
        st.success("Pipe position saved!")
        st.rerun()

# Quick movement buttons
if st.session_state.selected_pipe is not None:
    st.header("🔄 Quick Adjustments")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("← Move Left 5px"):
            pipe = st.session_state.pipes[st.session_state.selected_pipe]
            pipe["x1"] -= 5
            pipe["x2"] -= 5
            save_pipes(st.session_state.pipes)
            st.rerun()
    
    with col2:
        if st.button("→ Move Right 5px"):
            pipe = st.session_state.pipes[st.session_state.selected_pipe]
            pipe["x1"] += 5
            pipe["x2"] += 5
            save_pipes(st.session_state.pipes)
            st.rerun()
    
    with col3:
        if st.button("↑ Move Up 5px"):
            pipe = st.session_state.pipes[st.session_state.selected_pipe]
            pipe["y1"] -= 5
            pipe["y2"] -= 5
            save_pipes(st.session_state.pipes)
            st.rerun()
    
    with col4:
        if st.button("↓ Move Down 5px"):
            pipe = st.session_state.pipes[st.session_state.selected_pipe]
            pipe["y1"] += 5
            pipe["y2"] += 5
            save_pipes(st.session_state.pipes)
            st.rerun()

# Current coordinates display
st.header("📋 Current Pipe Positions")
for i, pipe in enumerate(st.session_state.pipes):
    if i == st.session_state.selected_pipe:
        st.success(f"**🟣 Pipe {i+1}:** ({pipe['x1']}, {pipe['y1']}) to ({pipe['x2']}, {pipe['y2']})")
    else:
        st.write(f"Pipe {i+1}: ({pipe['x1']}, {pipe['y1']}) to ({pipe['x2']}, {pipe['y2']})")

st.info("💡 **Just like valves:** Select pipe → Adjust numbers → Click save!")
