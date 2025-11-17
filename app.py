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

def get_pipe_groups():
    """Define mechanical pipe connections - pipes that are joined together"""
    return {
        "Group_1": [1, 20],    # Pipe 1 is mechanically joined with Pipe 20
        "Group_2": [11, 19],   # Pipe 11 is mechanically joined with Pipe 19
        # Add more mechanical connections as needed
        # "Group_3": [2, 3, 4], # Example: multiple pipes connected
    }

def get_valve_control_mapping():
    """Define which valves control which pipe groups"""
    return {
        "V-101": ["Group_1"],  # V-101 controls Group 1 (pipes 1 and 20)
        "V-102": ["Group_2"],  # V-102 controls Group 2 (pipes 11 and 19)
        # Add more valve controls as needed
        # "V-103": ["Group_3"],
    }

def find_pipe_group(pipe_number, pipe_groups):
    """Find which group a pipe belongs to"""
    for group_name, pipes_in_group in pipe_groups.items():
        if pipe_number in pipes_in_group:
            return group_name
    return None

def get_pipe_color_based_on_groups(pipe_index, valves, valve_states):
    """Determine pipe color based on mechanical group valve states"""
    pipe_number = pipe_index + 1  # Convert to 1-indexed
    
    # Get pipe groups and valve control mapping
    pipe_groups = get_pipe_groups()
    valve_control = get_valve_control_mapping()
    
    # Find which group this pipe belongs to
    pipe_group = find_pipe_group(pipe_number, pipe_groups)
    
    if pipe_group:
        # Find which valves control this group
        for valve_tag, controlled_groups in valve_control.items():
            if pipe_group in controlled_groups and valve_tag in valve_states:
                if valve_states[valve_tag]:
                    return (0, 255, 0)  # Green if controlling valve is open
                else:
                    return (0, 0, 255)  # Blue if controlling valve is closed
    
    # If pipe doesn't belong to any group, check proximity to valves
    return get_pipe_color_based_on_proximity(pipe_index, valves, valve_states)

def get_pipe_color_based_on_proximity(pipe_index, valves, valve_states):
    """Fallback: determine pipe color based on valve proximity"""
    pipe_number = pipe_index + 1
    pipe = st.session_state.pipes[pipe_index]
    
    # Check if any valve is near the pipe start
    x1, y1 = pipe["x1"], pipe["y1"]  # Start point (upstream)
    valve_proximity_threshold = 20  # pixels
    
    for tag, valve_data in valves.items():
        valve_x, valve_y = valve_data["x"], valve_data["y"]
        
        # Calculate distance between pipe start and valve
        distance = ((valve_x - x1)**2 + (valve_y - y1)**2)**0.5
        
        # If valve is close to pipe start point and is open, make pipe green
        if distance <= valve_proximity_threshold and valve_states[tag]:
            return (0, 255, 0)  # Green for active flow
    
    return (0, 0, 255)  # Blue for no flow

def create_pid_with_valves_and_pipes():
    """Create P&ID image with valve indicators AND pipes - PRESERVING EXACT SCALE"""
    try:
        # Open the original P&ID image without any resizing
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
        img_width, img_height = pid_img.size
        
        # Draw pipes FIRST using exact coordinates from JSON
        if st.session_state.pipes:
            for i, pipe in enumerate(st.session_state.pipes):
                # Use exact coordinates from JSON - no scaling or modification
                x1, y1, x2, y2 = pipe["x1"], pipe["y1"], pipe["x2"], pipe["y2"]
                
                # Get pipe color based on group valve states
                color = get_pipe_color_based_on_groups(i, valves, st.session_state.valve_states)
                
                # If this pipe is selected, make it purple regardless of valve state
                if i == st.session_state.selected_pipe:
                    color = (148, 0, 211)  # Purple for selected pipe
                    width = 8
                else:
                    width = 6
                    
                # Draw the pipe with exact coordinates
                draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
                
                # Draw endpoints for selected pipe
                if i == st.session_state.selected_pipe:
                    draw.ellipse([x1-6, y1-6, x1+6, y1+6], fill=(255, 0, 0), outline="white", width=2)
                    draw.ellipse([x2-6, y2-6, x2+6, y2+6], fill=(255, 0, 0), outline="white", width=2)
        
        # Draw valves on top of pipes using exact coordinates from JSON
        for tag, data in valves.items():
            x, y = data["x"], data["y"]  # Exact coordinates from JSON
            current_state = st.session_state.valve_states[tag]
            
            # Choose color based on valve state
            color = (0, 255, 0) if current_state else (255, 0, 0)
            
            # Draw valve indicator at exact coordinates
            draw.ellipse([x-8, y-8, x+8, y+8], fill=color, outline="white", width=2)
            draw.text((x+12, y-10), tag, fill="white", stroke_fill="black", stroke_width=1)
            
        return pid_img.convert("RGB")
    except Exception as e:
        st.error(f"Error creating P&ID image: {e}")
        try:
            return Image.open(PID_FILE).convert("RGB")
        except:
            return Image.new("RGB", (1200, 800), (255, 255, 255))

# Load valve data from JSON - THIS PRESERVES YOUR EXACT CONFIGURATION
valves = load_valves()
pipes = load_pipes()

# Initialize session state
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}

if "selected_pipe" not in st.session_state:
    st.session_state.selected_pipe = None

if "pipes" not in st.session_state:
    st.session_state.pipes = pipes

# Main app
st.title("P&ID Interactive Simulation")

if not valves:
    st.error("No valves found in valves.json. Please check your configuration.")
    st.stop()

if not pipes:
    st.error("No pipes found in pipes.json. Please check your configuration.")
    st.stop()

# Create sidebar for valve controls AND pipe selection
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
    
    st.markdown("---")
    st.header("📋 Pipe Selection")
    st.markdown("Click on a pipe to highlight it")
    
    # UNSELECT ALL PIPES BUTTON
    if st.button("🚫 Unselect All Pipes", use_container_width=True, type="secondary"):
        st.session_state.selected_pipe = None
        st.rerun()
    
    # Pipe selection buttons
    if st.session_state.pipes:
        for i in range(len(st.session_state.pipes)):
            is_selected = st.session_state.selected_pipe == i
            pipe = st.session_state.pipes[i]
            
            status_icon = "🟣" if is_selected else "🔵"
            label = f"{status_icon} Pipe {i+1}" 
            
            if st.button(label, key=f"pipe_{i}", use_container_width=True):
                st.session_state.selected_pipe = i
                st.rerun()

# Main content area - P&ID display
col1, col2 = st.columns([3, 1])
with col1:
    # Create and display the P&ID with valve indicators AND pipes
    composite_img = create_pid_with_valves_and_pipes()
    
    # Show selection status
    if st.session_state.selected_pipe is not None:
        caption = f"🟣 Pipe {st.session_state.selected_pipe + 1} Selected | 🟢 Green = Flow Active | 🔵 Blue = No Flow"
    else:
        caption = "🟢 Green = Flow Active | 🔵 Blue = No Flow (No pipe selected)"
    
    st.image(composite_img, use_container_width=True, caption=caption)

with col2:
    # Right sidebar for detailed status
    st.header("🔍 Flow Status")
    st.markdown("---")
    
    # Show valve status and pipe flow information
    st.subheader("📊 System Status")
    
    # Count pipes with active flow
    active_pipes = 0
    for i, pipe in enumerate(st.session_state.pipes):
        color = get_pipe_color_based_on_groups(i, valves, st.session_state.valve_states)
        if color == (0, 255, 0):  # Green
            active_pipes += 1
    
    st.write(f"**Active Flow Pipes:** {active_pipes}")
    st.write(f"**No Flow Pipes:** {len(st.session_state.pipes) - active_pipes}")
    
    # Show valve status summary
    open_valves = sum(1 for state in st.session_state.valve_states.values() if state)
    closed_valves = len(valves) - open_valves
    st.write(f"**Open Valves:** {open_valves}")
    st.write(f"**Closed Valves:** {closed_valves}")
    
    # Show mechanical groups information
    st.markdown("---")
    st.subheader("🔗 Mechanical Connections")
    
    pipe_groups = get_pipe_groups()
    valve_control = get_valve_control_mapping()
    
    for group_name, pipes_in_group in pipe_groups.items():
        # Find which valve controls this group
        controlling_valve = None
        for valve_tag, controlled_groups in valve_control.items():
            if group_name in controlled_groups:
                controlling_valve = valve_tag
                break
        
        if controlling_valve:
            valve_state = st.session_state.valve_states.get(controlling_valve, False)
            status_icon = "🟢" if valve_state else "🔴"
            st.write(f"{status_icon} **{controlling_valve}** controls: Pipes {pipes_in_group}")
    
    # Show selected pipe info
    if st.session_state.selected_pipe is not None:
        st.markdown("---")
        st.subheader(f"🟣 Selected Pipe {st.session_state.selected_pipe + 1}")
        pipe = st.session_state.pipes[st.session_state.selected_pipe]
        st.write(f"Start: ({pipe['x1']}, {pipe['y1']})")
        st.write(f"End: ({pipe['x2']}, {pipe['y2']})")
        
        # Check flow status for selected pipe
        color = get_pipe_color_based_on_groups(st.session_state.selected_pipe, valves, st.session_state.valve_states)
        flow_status = "🟢 ACTIVE FLOW" if color == (0, 255, 0) else "🔵 NO FLOW"
        st.write(f"**Flow Status:** {flow_status}")
        
        # Show which mechanical group this pipe belongs to
        pipe_number = st.session_state.selected_pipe + 1
        pipe_group = find_pipe_group(pipe_number, pipe_groups)
        
        if pipe_group:
            st.write(f"**Mechanical Group:** {pipe_group}")
            st.write(f"**Connected Pipes:** {pipe_groups[pipe_group]}")
            
            # Show which valve controls this group
            for valve_tag, controlled_groups in valve_control.items():
                if pipe_group in controlled_groups:
                    valve_state = st.session_state.valve_states.get(valve_tag, False)
                    status = "OPEN" if valve_state else "CLOSED"
                    st.write(f"**Controlled by:** {valve_tag} ({status})")
        else:
            st.write("**Mechanical Group:** None (Standalone pipe)")
    else:
        st.markdown("---")
        st.subheader("ℹ️ No Pipe Selected")
        st.info("Click on a pipe in the sidebar to select and inspect it")
    
    st.markdown("---")
    st.subheader("🔧 How It Works")
    st.markdown("""
    **Mechanical Connection Rules:**
    - **Pipe 1** ↔ **Pipe 20** are connected (Group 1)
    - **Pipe 11** ↔ **Pipe 19** are connected (Group 2)
    - **V-101** controls **Group 1** (Pipes 1 & 20)
    - **V-102** controls **Group 2** (Pipes 11 & 19)
    
    **Valve Logic:**
    - Open valve → All pipes in group turn **GREEN**
    - Close valve → All pipes in group turn **BLUE**
    - Connected pipes always have the same color
    """)

# Debug information
with st.expander("🔧 Debug Information"):
    st.write("**Image Dimensions:**", get_image_dimensions())
    
    # Show current valve states
    st.subheader("Current Valve States")
    for tag, state in st.session_state.valve_states.items():
        status = "OPEN" if state else "CLOSED"
        color = "🟢" if state else "🔴"
        st.write(f"{color} {tag}: {status} (Position: {valves[tag]['x']}, {valves[tag]['y']})")
    
    # Show mechanical groups
    st.subheader("Mechanical Pipe Groups")
    pipe_groups = get_pipe_groups()
    valve_control = get_valve_control_mapping()
    
    for group_name, pipes_in_group in pipe_groups.items():
        controlling_valve = None
        for valve_tag, controlled_groups in valve_control.items():
            if group_name in controlled_groups:
                controlling_valve = valve_tag
                break
        
        st.write(f"**{group_name}:** Pipes {pipes_in_group} | Controlled by: {controlling_valve}")
    
    # Show pipe information
    st.subheader("Pipe Information")
    for i, pipe in enumerate(st.session_state.pipes):
        color = get_pipe_color_based_on_groups(i, valves, st.session_state.valve_states)
        color_name = "GREEN" if color == (0, 255, 0) else "BLUE"
        pipe_group = find_pipe_group(i+1, pipe_groups)
        group_info = f" | Group: {pipe_group}" if pipe_group else " | Group: None"
        st.write(f"Pipe {i+1}: {color_name}{group_info}")
    
    st.write("**All Valves Data:**")
    st.json(valves)
    st.write("**All Pipes Data:**")
    st.json(st.session_state.pipes)
