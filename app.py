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

def get_pipe_groups():
    """Define pipe groups based on your requirements"""
    return {
        "Group 1": [1],      # V-101 controls any group containing pipe 1
        "Group 2": [11],     # V-102 controls any group containing pipe 11
        "Group 3": [2, 3],   # Example additional group
        "Group 4": [4, 5, 6], # Example additional group
        "Group 5": [7, 8, 9, 10] # Example additional group
    }

def get_valve_control_mapping():
    """Define which valves control which pipe groups"""
    return {
        "V-101": ["Group 1"],  # V-101 controls Group 1 (contains pipe 1)
        "V-102": ["Group 2"],  # V-102 controls Group 2 (contains pipe 11)
        "V-103": ["Group 3"],  # Example additional valve
        "V-104": ["Group 4"],  # Example additional valve
        "V-105": ["Group 5"]   # Example additional valve
    }

def get_pipe_color_based_on_groups(pipe_index, valves, valve_states):
    """Determine pipe color based on group valve states"""
    pipe_number = pipe_index + 1  # Convert to 1-indexed
    
    # Get pipe groups and valve control mapping
    pipe_groups = get_pipe_groups()
    valve_control = get_valve_control_mapping()
    
    # Find which groups this pipe belongs to
    pipe_groups_containing_this_pipe = []
    for group_name, pipes_in_group in pipe_groups.items():
        if pipe_number in pipes_in_group:
            pipe_groups_containing_this_pipe.append(group_name)
    
    # Check if any valve controlling these groups is open
    for group_name in pipe_groups_containing_this_pipe:
        # Find which valves control this group
        for valve_tag, controlled_groups in valve_control.items():
            if group_name in controlled_groups and valve_tag in valve_states:
                if valve_states[valve_tag]:
                    return (0, 255, 0)  # Green if controlling valve is open
    
    return (0, 0, 255)  # Blue if no controlling valve is open

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
                    # Get pipe color based on group valve states
                    color = get_pipe_color_based_on_groups(i, valves, st.session_state.valve_states)
                    
                    # If this pipe is selected, make it purple regardless of valve state
                    if i == st.session_state.selected_pipe:
                        color = (148, 0, 211)  # Purple for selected pipe
                        width = 8
                    else:
                        width = 6
                        
                    draw.line([(pipe["x1"], pipe["y1"]), (pipe["x2"], pipe["y2"])], fill=color, width=width)
                    
                    # Draw endpoints for selected pipe
                    if i == st.session_state.selected_pipe:
                        draw.ellipse([pipe["x1"]-6, pipe["y1"]-6, pipe["x1"]+6, pipe["y1"]+6], fill=(255, 0, 0), outline="white", width=2)
                        draw.ellipse([pipe["x2"]-6, pipe["y2"]-6, pipe["x2"]+6, pipe["y2"]+6], fill=(255, 0, 0), outline="white", width=2)
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
            draw.ellipse([x-8, y-8, x+8, x+8], fill=color, outline="white", width=2)
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

if not valves:
    st.error("No valves found in valves.json. Please check your configuration.")
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
            img_width, img_height = get_image_dimensions()
            
            # Check if pipe is reasonable
            is_reasonable = (
                -1000 <= pipe["x1"] <= img_width + 1000 and
                -1000 <= pipe["x2"] <= img_width + 1000 and
                -1000 <= pipe["y1"] <= img_height + 1000 and
                -1000 <= pipe["y2"] <= img_height + 1000
            )
            
            status_icon = "🟣" if is_selected else "🔵"
            if not is_reasonable:
                status_icon = "🟡"
            
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
    if st.session_state.pipes:
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
        
        # Show valve and group information
        st.markdown("---")
        st.subheader("🔗 Valve & Group Control")
        
        # Display valve control mapping
        valve_control = get_valve_control_mapping()
        pipe_groups = get_pipe_groups()
        
        st.write("**Valve Controls:**")
        for valve_tag, controlled_groups in valve_control.items():
            group_info = []
            for group_name in controlled_groups:
                pipes_in_group = pipe_groups[group_name]
                group_info.append(f"{group_name} (Pipes: {', '.join(map(str, pipes_in_group))})")
            
            valve_state = st.session_state.valve_states.get(valve_tag, False)
            status_icon = "🟢" if valve_state else "🔴"
            st.write(f"{status_icon} **{valve_tag}**: {', '.join(group_info)}")
        
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
            
            # Show which groups and valves control this pipe
            pipe_number = st.session_state.selected_pipe + 1
            controlling_groups = []
            controlling_valves = []
            
            pipe_groups = get_pipe_groups()
            valve_control = get_valve_control_mapping()
            
            for group_name, pipes_in_group in pipe_groups.items():
                if pipe_number in pipes_in_group:
                    controlling_groups.append(group_name)
                    # Find valves that control this group
                    for valve_tag, controlled_groups in valve_control.items():
                        if group_name in controlled_groups:
                            controlling_valves.append(valve_tag)
            
            if controlling_groups:
                st.write(f"**Member of Groups:** {', '.join(controlling_groups)}")
            if controlling_valves:
                st.write(f"**Controlled by Valves:** {', '.join(controlling_valves)}")
        else:
            st.markdown("---")
            st.subheader("ℹ️ No Pipe Selected")
            st.info("Click on a pipe in the sidebar to select and inspect it")
        
        st.markdown("---")
        st.subheader("🔧 How It Works")
        st.markdown("""
        - **V-101** controls any group containing **Pipe 1**
        - **V-102** controls any group containing **Pipe 11**
        - **Open a valve** → Controlled pipe groups turn **GREEN**
        - **Close a valve** → Controlled pipe groups turn **BLUE**
        - **Click a pipe** → Highlights it in **PURPLE**
        - Pipes can belong to multiple groups
        """)

# Debug information
with st.expander("🔧 Debug Information"):
    st.write("**Image Dimensions:**", get_image_dimensions())
    
    # Show current valve states
    st.subheader("Current Valve States")
    for tag, state in st.session_state.valve_states.items():
        status = "OPEN" if state else "CLOSED"
        color = "🟢" if state else "🔴"
        st.write(f"{color} {tag}: {status}")
    
    # Show pipe groups and control mapping
    st.subheader("Pipe Groups Configuration")
    pipe_groups = get_pipe_groups()
    for group_name, pipes_in_group in pipe_groups.items():
        st.write(f"**{group_name}:** Pipes {pipes_in_group}")
    
    st.subheader("Valve Control Mapping")
    valve_control = get_valve_control_mapping()
    for valve_tag, controlled_groups in valve_control.items():
        st.write(f"**{valve_tag}:** Controls {controlled_groups}")
    
    # Show pipe colors
    st.subheader("Pipe Colors")
    for i in range(len(st.session_state.pipes)):
        color = get_pipe_color_based_on_groups(i, valves, st.session_state.valve_states)
        color_name = "GREEN" if color == (0, 255, 0) else "BLUE"
        st.write(f"Pipe {i+1}: {color_name}")
    
    if st.session_state.pipes:
        st.write("**Pipe 1 Coordinates:**", st.session_state.pipes[0] if len(st.session_state.pipes) > 0 else "Not found")
    st.write("**All Pipes:**")
    st.json(st.session_state.pipes)
