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

def reset_all_pipes_to_visible():
    """Reset ALL pipes to visible positions"""
    img_width, img_height = get_image_dimensions()
    new_pipes = []
    
    # Create a grid of positions for all pipes
    num_pipes = len(st.session_state.pipes)
    cols = 4  # 4 columns in the grid
    rows = (num_pipes + cols - 1) // cols  # Calculate rows needed
    
    pipe_width = 100  # Default pipe length
    spacing_x = img_width // (cols + 1)
    spacing_y = img_height // (rows + 1)
    
    for i in range(num_pipes):
        row = i // cols
        col = i % cols
        
        # Calculate position in grid
        center_x = spacing_x * (col + 1)
        center_y = spacing_y * (row + 1)
        
        # Create a horizontal pipe at this position
        new_pipe = {
            "x1": center_x - pipe_width // 2,
            "y1": center_y,
            "x2": center_x + pipe_width // 2,
            "y2": center_y
        }
        new_pipes.append(new_pipe)
    
    return new_pipes

def create_pid_with_valves_and_pipes():
    """Create P&ID image with valve indicators AND pipes"""
    try:
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
        img_width, img_height = pid_img.size
        
        # Draw pipes FIRST (so valves appear on top)
        if st.session_state.pipes:
            for i, pipe in enumerate(st.session_state.pipes):
                # Check if pipe is within reasonable bounds (not thousands of pixels off)
                is_reasonable = (
                    -1000 <= pipe["x1"] <= img_width + 1000 and
                    -1000 <= pipe["x2"] <= img_width + 1000 and
                    -1000 <= pipe["y1"] <= img_height + 1000 and
                    -1000 <= pipe["y2"] <= img_height + 1000
                )
                
                if is_reasonable:
                    # Don't highlight any pipe as selected - all pipes will be blue
                    color = (0, 0, 255)  # Blue for all pipes
                    width = 6  # Standard width for all pipes
                    draw.line([(pipe["x1"], pipe["y1"]), (pipe["x2"], pipe["y2"])], fill=color, width=width)
                    
                    # Don't draw endpoints since no pipe is selected
                else:
                    # Pipe is way off screen - don't draw it
                    pass
        
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
    st.session_state.selected_pipe = None  # No pipe selected by default

if "pipes" not in st.session_state:
    st.session_state.pipes = pipes

# Main app
st.title("P&ID Interactive Simulation")

# EMERGENCY RESET BUTTON
if st.session_state.pipes:
    st.error("🚨 If pipes are not visible, click the button below to RESET ALL PIPES to visible positions!")
    if st.button("🔄 RESET ALL PIPES TO VISIBLE POSITIONS", type="primary", use_container_width=True):
        st.session_state.pipes = reset_all_pipes_to_visible()
        save_pipes(st.session_state.pipes)
        st.success("✅ All pipes reset to visible positions!")
        st.rerun()

if not valves:
    st.error("No valves found in valves.json. Please check your configuration.")
    st.stop()

# Show pipe position status
if st.session_state.pipes and st.session_state.selected_pipe is not None:
    current_pipe = st.session_state.pipes[st.session_state.selected_pipe]
    img_width, img_height = get_image_dimensions()
    
    # Check if pipe coordinates are reasonable
    is_reasonable = (
        -1000 <= current_pipe["x1"] <= img_width + 1000 and
        -1000 <= current_pipe["x2"] <= img_width + 1000 and
        -1000 <= current_pipe["y1"] <= img_height + 1000 and
        -1000 <= current_pipe["y2"] <= img_height + 1000
    )
    
    if not is_reasonable:
        st.error(f"🚨 Pipe {st.session_state.selected_pipe + 1} coordinates are EXTREMELY OFF-SCREEN! Use RESET button above.")

# Create sidebar for valve controls
with st.sidebar:
    st.header("🎯 Valve Controls")
    st.markdown("---")
    
    # Valve toggle buttons in sidebar
    for tag, data in valves.items():
        current_state = st.session_state.valve_states[tag]
        
        button_label = f"🔴 {tag} - OPEN" if current_state else f"🟢 {tag} - CLOSED"
        
        if st.button(button_label, key=f"btn_{tag}", use_container_width=True):
            st.session_state.valve_states[tag] = not current_state
            st.rerun()

# Main content area - P&ID display
col1, col2 = st.columns([3, 1])
with col1:
    # Create and display the P&ID with valve indicators AND pipes
    composite_img = create_pid_with_valves_and_pipes()
    st.image(composite_img, use_container_width=True, caption="🔵 Blue = Normal Pipes")

with col2:
    # Right sidebar for detailed status
    st.header("🔍 Details")
    st.markdown("---")
    
    # Show general pipe information instead of selected pipe info
    if st.session_state.pipes:
        st.subheader("📊 Pipe System")
        st.write(f"**Total Pipes:** {len(st.session_state.pipes)}")
        st.write(f"**Total Valves:** {len(valves)}")
        
        # Show valve status summary
        open_valves = sum(1 for state in st.session_state.valve_states.values() if state)
        closed_valves = len(valves) - open_valves
        st.write(f"**Open Valves:** {open_valves}")
        st.write(f"**Closed Valves:** {closed_valves}")

# Debug information
with st.expander("🔧 Debug Information"):
    st.write("**Image Dimensions:**", get_image_dimensions())
    if st.session_state.pipes:
        st.write("**Pipe 1 Coordinates:**", st.session_state.pipes[0] if len(st.session_state.pipes) > 0 else "Not found")
    st.write("**All Pipes:**")
    st.json(st.session_state.pipes)
