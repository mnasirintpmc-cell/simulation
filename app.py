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

def get_image_dimensions():
    """Get the dimensions of the P&ID image"""
    try:
        with Image.open(PID_FILE) as img:
            return img.size
    except:
        return (1200, 800)  # Default fallback

def is_pipe_visible(pipe, img_width=1200, img_height=800):
    """Check if pipe coordinates are within image boundaries"""
    return (0 <= pipe["x1"] <= img_width and 
            0 <= pipe["x2"] <= img_width and
            0 <= pipe["y1"] <= img_height and 
            0 <= pipe["y2"] <= img_height)

def create_pid_with_valves_and_pipes():
    """Create P&ID image with valve indicators AND pipes"""
    try:
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
        
        # Draw pipes FIRST (so valves appear on top)
        if st.session_state.pipes:
            for i, pipe in enumerate(st.session_state.pipes):
                # Check if pipe is visible
                img_width, img_height = pid_img.size
                is_visible = is_pipe_visible(pipe, img_width, img_height)
                
                if is_visible:
                    color = (148, 0, 211) if i == st.session_state.selected_pipe else (0, 0, 255)  # Purple for selected
                    width = 6 if i == st.session_state.selected_pipe else 4
                    draw.line([(pipe["x1"], pipe["y1"]), (pipe["x2"], pipe["y2"])], fill=color, width=width)
                else:
                    # Draw off-screen pipes in yellow for debugging
                    color = (255, 255, 0)  # Yellow for off-screen
                    width = 4
                    # Only draw if at least one point is near the edge
                    if (pipe["x1"] < img_width + 100 or pipe["x2"] < img_width + 100 or
                        pipe["y1"] < img_height + 100 or pipe["y2"] < img_height + 100):
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
            return Image.new("RGB", (1200, 800), (255, 255, 255))

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

# Show pipe position status
if st.session_state.pipes and st.session_state.selected_pipe is not None:
    current_pipe = st.session_state.pipes[st.session_state.selected_pipe]
    img_width, img_height = get_image_dimensions()
    is_visible = is_pipe_visible(current_pipe, img_width, img_height)
    
    if not is_visible:
        st.error(f"🚨 Pipe {st.session_state.selected_pipe + 1} is OFF-SCREEN! Use 'Fix Position' button below.")

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
            pipe = st.session_state.pipes[i]
            img_width, img_height = get_image_dimensions()
            is_visible = is_pipe_visible(pipe, img_width, img_height)
            
            status_icon = "🟣" if is_selected else ("🔵" if is_visible else "🟡")
            label = f"{status_icon} Pipe {i+1}" 
            
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
        visible_pipes = sum(1 for pipe in st.session_state.pipes if is_pipe_visible(pipe))
        st.metric("Visible Pipes", f"{visible_pipes}/{len(st.session_state.pipes)}")
    
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
    st.image(composite_img, use_container_width=True, caption="🟣 Purple = Selected | 🔵 Blue = Normal | 🟡 Yellow = Off-screen")

with col2:
    # Right sidebar for detailed status
    st.header("🔍 Details")
    st.markdown("---")
    
    # Selected pipe info
    if st.session_state.selected_pipe is not None and st.session_state.pipes:
        pipe = st.session_state.pipes[st.session_state.selected_pipe]
        img_width, img_height = get_image_dimensions()
        is_visible = is_pipe_visible(pipe, img_width, img_height)
        
        st.subheader(f"🟣 Pipe {st.session_state.selected_pipe + 1}")
        st.write(f"Start: ({pipe['x1']}, {pipe['y1']})")
        st.write(f"End: ({pipe['x2']}, {pipe['y2']})")
        
        if not is_visible:
            st.error("❌ This pipe is OFF-SCREEN!")
        
        # Calculate current length and orientation
        length = ((pipe["x2"] - pipe["x1"])**2 + (pipe["y2"] - pipe["y1"])**2)**0.5
        is_horizontal = abs(pipe["y2"] - pipe["y1"]) < abs(pipe["x2"] - pipe["x1"])
        orientation = "Horizontal" if is_horizontal else "Vertical"
        st.write(f"**Length:** {int(length)} pixels")
        st.write(f"**Orientation:** {orientation}")
        
        # FIX POSITION BUTTON - NEW FEATURE
        st.markdown("---")
        st.subheader("🎯 Fix Position")
        if st.button("🛠️ FIX PIPE POSITION", use_container_width=True, type="primary"):
            img_width, img_height = get_image_dimensions()
            
            # Move pipe to a safe visible position
            safe_x = img_width // 2
            safe_y = img_height // 2
            
            # Calculate current pipe vector
            dx = pipe["x2"] - pipe["x1"]
            dy = pipe["y2"] - pipe["y1"]
            
            # Move pipe to center while preserving its shape
            pipe["x1"] = safe_x - dx // 2
            pipe["y1"] = safe_y - dy // 2
            pipe["x2"] = safe_x + dx // 2
            pipe["y2"] = safe_y + dy // 2
            
            save_pipes(st.session_state.pipes)
            st.success(f"✅ Pipe {st.session_state.selected_pipe + 1} moved to visible area!")
            st.rerun()
        
        # Pipe movement controls
        st.markdown("---")
        st.subheader("📍 Move Pipe")
        col_up, col_down = st.columns(2)
        with col_up:
            if st.button("↑ Up", use_container_width=True):
                pipe["y1"] -= 10
                pipe["y2"] -= 10
                save_pipes(st.session_state.pipes)
                st.rerun()
        with col_down:
            if st.button("↓ Down", use_container_width=True):
                pipe["y1"] += 10
                pipe["y2"] += 10
                save_pipes(st.session_state.pipes)
                st.rerun()
        
        col_left, col_right = st.columns(2)
        with col_left:
            if st.button("← Left", use_container_width=True):
                pipe["x1"] -= 10
                pipe["x2"] -= 10
                save_pipes(st.session_state.pipes)
                st.rerun()
        with col_right:
            if st.button("→ Right", use_container_width=True):
                pipe["x1"] += 10
                pipe["x2"] += 10
                save_pipes(st.session_state.pipes)
                st.rerun()
        
        # Quick jump to coordinates
        st.markdown("---")
        st.subheader("🎯 Set Coordinates")
        col1, col2 = st.columns(2)
        with col1:
            new_x1 = st.number_input("X1", value=pipe["x1"], key="set_x1")
            new_y1 = st.number_input("Y1", value=pipe["y1"], key="set_y1")
        with col2:
            new_x2 = st.number_input("X2", value=pipe["x2"], key="set_x2")
            new_y2 = st.number_input("Y2", value=pipe["y2"], key="set_y2")
        
        if st.button("💫 JUMP TO COORDINATES", use_container_width=True):
            pipe["x1"] = new_x1
            pipe["y1"] = new_y1
            pipe["x2"] = new_x2
            pipe["y2"] = new_y2
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

# Debug information
with st.expander("🔧 Debug Information"):
    st.write("**Image Dimensions:**", get_image_dimensions())
    st.write("**Loaded Valves Configuration:**")
    st.json(valves)
    
    st.write("**Loaded Pipes Configuration:**")
    st.json(st.session_state.pipes)
    
    st.write("**Current Valve States:**")
    st.json(st.session_state.valve_states)
    
    st.write(f"**Total Valves:** {len(valves)}")
    st.write(f"**Total Pipes:** {len(st.session_state.pipes)}")
    st.write(f"**Selected Pipe:** {st.session_state.selected_pipe}")
