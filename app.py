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
    return {}

def get_pid_dimensions():
    """Get the actual dimensions of the P&ID image in your repo"""
    try:
        with Image.open(PID_FILE) as img:
            return img.size  # (width, height)
    except:
        return (442, 973)  # Fallback to Figma dimensions

def scale_figma_to_actual(figma_coords):
    """Scale Figma coordinates (442x973) to actual P&ID dimensions"""
    # Figma canvas dimensions
    FIGMA_WIDTH = 442
    FIGMA_HEIGHT = 973
    
    # Get actual P&ID dimensions
    actual_width, actual_height = get_pid_dimensions()
    
    # Calculate scaling factors
    scale_x = actual_width / FIGMA_WIDTH
    scale_y = actual_height / FIGMA_HEIGHT
    
    # Scale all coordinates
    scaled_coords = []
    for i in range(0, len(figma_coords), 2):
        if i + 1 < len(figma_coords):
            x = figma_coords[i] * scale_x
            y = figma_coords[i + 1] * scale_y
            scaled_coords.extend([int(x), int(y)])
    
    return scaled_coords

def create_pid_with_scaled_pipes():
    """Create P&ID image with properly scaled pipes and valves"""
    try:
        # Load the actual P&ID image
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
        
        # Load pipes data from Figma
        pipes_data = load_pipes()
        valves_data = load_valves()
        
        # Draw scaled pipes
        for pipe_id, pipe_data in pipes_data.items():
            figma_coords = pipe_data.get("coords", [])
            
            if figma_coords:
                # Scale coordinates from Figma to actual P&ID
                scaled_coords = scale_figma_to_actual(figma_coords)
                
                # Draw the pipe segments
                for i in range(0, len(scaled_coords) - 2, 2):
                    if i + 3 < len(scaled_coords):
                        x1, y1 = scaled_coords[i], scaled_coords[i + 1]
                        x2, y2 = scaled_coords[i + 2], scaled_coords[i + 3]
                        
                        # Determine pipe color based on flow logic
                        has_flow = check_pipe_flow(pipe_data, valves_data)
                        pipe_color = (0, 100, 255) if has_flow else (100, 100, 100)
                        pipe_width = 8 if has_flow else 6
                        
                        draw.line([(x1, y1), (x2, y2)], fill=pipe_color, width=pipe_width)
        
        # Draw valves on top
        for tag, data in valves_data.items():
            x, y = data["x"], data["y"]
            current_state = st.session_state.valve_states.get(tag, False)
            
            # Scale valve positions if they're from Figma
            # (Assuming valve positions are already in correct coordinates)
            valve_color = (0, 255, 0) if current_state else (255, 0, 0)
            
            draw.ellipse([x-10, y-10, x+10, y+10], fill=valve_color, outline="white", width=3)
            draw.text((x+12, y-8), tag, fill="white", stroke_fill="black", stroke_width=1)
        
        return pid_img.convert("RGB")
    
    except Exception as e:
        st.error(f"Error creating P&ID: {e}")
        try:
            return Image.open(PID_FILE).convert("RGB")
        except:
            return Image.new("RGB", (800, 600), (255, 255, 255))

def check_pipe_flow(pipe_data, valves_data):
    """Check if a pipe should have flow based on valve states"""
    required_valves = pipe_data.get("flow_logic", [])
    
    for valve_tag in required_valves:
        if valve_tag in st.session_state.valve_states:
            if not st.session_state.valve_states[valve_tag]:
                return False
        else:
            return False  # Valve not found
    
    return True

# Load data
valves = load_valves()
pipes = load_pipes()

# Initialize session state
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}

# Main app
st.title("P&ID Interactive Simulation - Scaled Pipes")

# Display scaling info
pid_width, pid_height = get_pid_dimensions()
st.write(f"**P&ID Dimensions:** {pid_width} × {pid_height} pixels")
st.write(f"**Figma Dimensions:** 442 × 973 pixels")
st.write(f"**Scaling Factors:** X: {pid_width/442:.2f}, Y: {pid_height/973:.2f}")

# Display the scaled P&ID
composite_img = create_pid_with_scaled_pipes()
st.image(composite_img, use_container_width=True, caption="P&ID with Scaled Pipes from Figma")

# Valve controls in sidebar
with st.sidebar:
    st.header("🎯 Valve Controls")
    st.markdown("---")
    
    for tag, data in valves.items():
        current_state = st.session_state.valve_states[tag]
        button_label = f"🔴 {tag} - OPEN" if current_state else f"🟢 {tag} - CLOSED"
        button_type = "primary" if current_state else "secondary"
        
        if st.button(button_label, key=f"btn_{tag}", use_container_width=True, type=button_type):
            st.session_state.valve_states[tag] = not current_state
            st.rerun()

# Debug information
with st.expander("🔧 Scaling Debug Info"):
    st.write("**Valves:**", valves)
    st.write("**Pipes (Figma coordinates):**", pipes)
    
    # Show scaled coordinates for first pipe
    if pipes:
        first_pipe = list(pipes.values())[0]
        figma_coords = first_pipe.get("coords", [])
        scaled_coords = scale_figma_to_actual(figma_coords)
        st.write("**First pipe scaling example:**")
        st.write(f"Figma: {figma_coords}")
        st.write(f"Scaled: {scaled_coords}")

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
