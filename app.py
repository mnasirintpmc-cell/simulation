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

def create_pid_with_pipes():
    """Create P&ID display with pipes and valves - NO SCALING"""
    try:
        # Load the actual P&ID image
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
        
        # Load data
        valves = load_valves()
        pipes = load_pipes()
        
        # Draw pipes EXACTLY as they are in pipes.json - NO SCALING
        for i, pipe in enumerate(pipes):
            x1, y1, x2, y2 = pipe["x1"], pipe["y1"], pipe["x2"], pipe["y2"]
            
            # Highlight selected pipe with VIOLET
            if st.session_state.get("selected_pipe") == i:
                pipe_color = (148, 0, 211)  # VIOLET for selected pipe
                pipe_width = 6
            else:
                pipe_color = (0, 0, 255)  # Blue for normal pipes
                pipe_width = 4
            
            draw.line([(x1, y1), (x2, y2)], fill=pipe_color, width=pipe_width)
        
        # Draw valves with original smaller sizes
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

# Load data
valves = load_valves()
pipes = load_pipes()

# Initialize session state
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}

if "selected_pipe" not in st.session_state:
    st.session_state.selected_pipe = None

# Main app
st.title("P&ID Interactive Simulation")

# Sidebar with clickable pipe selection
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
    st.header("📋 Pipe Selection")
    st.info("Click any pipe to highlight it")
    
    # Clickable pipe buttons
    if pipes:
        for i, pipe in enumerate(pipes):
            is_selected = st.session_state.selected_pipe == i
            button_label = f"🔮 Pipe {i+1}" if is_selected else f"Pipe {i+1}"
            
            if st.button(button_label, key=f"pipe_btn_{i}", use_container_width=True):
                st.session_state.selected_pipe = i
                st.rerun()
        
        # Show selected pipe info
        if st.session_state.selected_pipe is not None:
            pipe = pipes[st.session_state.selected_pipe]
            st.markdown("---")
            st.subheader("📊 Selected Pipe Info")
            st.write(f"**Pipe {st.session_state.selected_pipe + 1}**")
            st.write(f"Start: `({pipe['x1']}, {pipe['y1']})`")
            st.write(f"End: `({pipe['x2']}, {pipe['y2']})`")
            st.success("🔮 Violet highlight = Selected pipe")
    
    st.markdown("---")
    st.header("⚡ Quick Actions")
    if st.button("Open All Valves", use_container_width=True):
        for tag in valves:
            st.session_state.valve_states[tag] = True
        st.rerun()
    if st.button("Close All Valves", use_container_width=True):
        for tag in valves:
            st.session_state.valve_states[tag] = False
        st.rerun()

# Main display area
st.header("🎯 P&ID Display")
composite_img = create_pid_with_pipes()
st.image(composite_img, use_container_width=True, caption="🔮 Violet pipes = Selected | Your pipes are displayed EXACTLY as positioned")

# Current coordinates display
st.markdown("---")
st.header("📋 Current Pipe Coordinates")
st.info("These are the EXACT coordinates from your pipes.json file - no scaling applied")
st.json(pipes)

st.success("✅ Your pipes are displayed exactly as you positioned them - no scaling applied!")import streamlit as st
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

def create_pid_with_pipes():
    """Create P&ID display with pipes and valves"""
    try:
        # Try to load the actual P&ID image first
        try:
            pid_img = Image.open(PID_FILE).convert("RGBA")
        except:
            # If no P&ID image, create a white background
            pid_img = Image.new("RGBA", (1200, 800), (255, 255, 255, 255))
        
        draw = ImageDraw.Draw(pid_img)
        
        # Load data
        valves = load_valves()
        pipes = load_pipes()
        
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
        
        # Draw valves with original smaller sizes
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

# Load data
valves = load_valves()
pipes = load_pipes()

# Initialize session state
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}

if "selected_pipe" not in st.session_state:
    st.session_state.selected_pipe = None

# Main app
st.title("P&ID Interactive Simulation")

# Sidebar with clickable pipe selection
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
    st.header("📋 Pipe Selection")
    st.info("Click any pipe to highlight it")
    
    # Clickable pipe buttons
    if pipes:
        for i, pipe in enumerate(pipes):
            is_selected = st.session_state.selected_pipe == i
            button_label = f"🔮 Pipe {i+1}" if is_selected else f"Pipe {i+1}"
            
            if st.button(button_label, key=f"pipe_btn_{i}", use_container_width=True):
                st.session_state.selected_pipe = i
                st.rerun()
        
        # Show selected pipe info
        if st.session_state.selected_pipe is not None:
            pipe = pipes[st.session_state.selected_pipe]
            st.markdown("---")
            st.subheader("📊 Selected Pipe Info")
            st.write(f"**Pipe {st.session_state.selected_pipe + 1}**")
            st.write(f"Start: `({pipe['x1']}, {pipe['y1']})`")
            st.write(f"End: `({pipe['x2']}, {pipe['y2']})`")
            st.success("🔮 Violet highlight = Selected pipe")
    
    st.markdown("---")
    st.header("⚡ Quick Actions")
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

# Main display area
col1, col2 = st.columns([3, 1])

with col1:
    st.header("🎯 P&ID Display")
    composite_img = create_pid_with_pipes()
    st.image(composite_img, use_container_width=True, caption="🔮 Violet pipes = Selected | Blue pipes = Normal")

with col2:
    st.header("📝 System Info")
    st.write(f"**Valves:** {len(valves)}")
    st.write(f"**Pipes:** {len(pipes)}")
    
    if st.session_state.selected_pipe is not None:
        st.success(f"**Selected:** Pipe {st.session_state.selected_pipe + 1}")
    else:
        st.info("No pipe selected")
    
    # Export functionality
    st.markdown("---")
    st.subheader("📤 Export Data")
    pipes_json = json.dumps(pipes, indent=2)
    st.download_button(
        label="📥 Download pipes.json",
        data=pipes_json,
        file_name="pipes.json",
        mime="application/json"
    )

# Final coordinates display
st.markdown("---")
st.header("📋 Final Pipe Coordinates")
st.json(pipes)

st.success("✅ Pipe coordinates are locked and saved. Use the sidebar to select and highlight pipes!")
