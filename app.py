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

def get_pipe_color_based_on_valves(pipe_index, pipe_coords, valves, valve_states):
    """Determine pipe color based on upstream valve state AND dependencies"""
    pipe_number = pipe_index + 1  # Convert to 1-indexed for clarity
    
    # Define valve dependencies with their specific pipes
    valve_dependencies = {
        "V-301": [2, 3, 14, 22, 21],  # V-301 controls pipes 2,3,14,22,21
        "V-302": [13, 14, 22, 21]     # V-302 controls pipes 13,14,22,21
    }
    
    # Check each valve's dependencies
    for valve_tag, dependent_pipes in valve_dependencies.items():
        if valve_tag in valve_states:
            if pipe_number in dependent_pipes:
                if valve_states[valve_tag]:
                    return (0, 255, 0)  # Green if valve is open
                else:
                    return (0, 0, 255)  # Blue if valve is closed
    
    # Define pipe dependencies (pipes that follow other pipes)
    pipe_dependencies = {
        20: 1,   # Pipe 20 follows pipe 1
        19: 11   # Pipe 19 follows pipe 11
    }
    
    # Check if this pipe depends on another pipe
    if pipe_number in pipe_dependencies:
        leader_pipe_number = pipe_dependencies[pipe_number]
        leader_pipe_index = leader_pipe_number - 1  # Convert back to 0-indexed
        if leader_pipe_index < len(st.session_state.pipes):
            # Get the color from the leader pipe
            leader_color = get_pipe_color_based_on_valves(leader_pipe_index, st.session_state.pipes[leader_pipe_index], valves, valve_states)
            return leader_color
    
    # If no dependency, check valves normally (physical proximity)
    pipe = pipe_coords
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
                    # Get pipe color based on upstream valve state AND dependencies
                    color = get_pipe_color_based_on_valves(i, pipe, valves, st.session_state.valve_states)
                    
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
            color = get_pipe_color_based_on_valves(i, pipe, valves, st.session_state.valve_states)
            if color == (0, 255, 0):  # Green
                active_pipes += 1
        
        st.write(f"**Active Flow Pipes:** {active_pipes}")
        st.write(f"**No Flow Pipes:** {len(st.session_state.pipes) - active_pipes}")
        
        # Show valve status summary
        open_valves = sum(1 for state in st.session_state.valve_states.values() if state)
        closed_valves = len(valves) - open_valves
        st.write(f"**Open Valves:** {open_valves}")
        st.write(f"**Closed Valves:** {closed_valves}")
        
        # Show valve dependencies
        st.markdown("---")
        st.subheader("🔗 Valve Dependencies")
        st.markdown("""
        **V-301 Controls:**
        - Pipes 2, 3, 14, 22, 21
        
        **V-302 Controls:**
        - Pipes 13, 14, 22, 21
        
        **Pipe Dependencies:**
        - Pipe 20 follows Pipe 1
        - Pipe 19 follows Pipe 11
        """)
        
        # Show selected pipe info
        if st.session_state.selected_pipe is not None:
            st.markdown("---")
            st.subheader(f"🟣 Selected Pipe {st.session_state.selected_pipe + 1}")
            pipe = st.session_state.pipes[st.session_state.selected_pipe]
            st.write(f"Start: ({pipe['x1']}, {pipe['y1']})")
            st.write(f"End: ({pipe['x2']}, {pipe['y2']})")
            
            # Check flow status for selected pipe
            color = get_pipe_color_based_on_valves(st.session_state.selected_pipe, pipe, valves, st.session_state.valve_states)
            flow_status = "🟢 ACTIVE FLOW" if color == (0, 255, 0) else "🔵 NO FLOW"
            st.write(f"**Flow Status:** {flow_status}")
            
            # Show which valves control this pipe
            controlling_valves = []
            valve_dependencies = {
                "V-301": [2, 3, 14, 22, 21],
                "V-302": [13, 14, 22, 21]
            }
            
            for valve_tag, pipes_list in valve_dependencies.items():
                if (st.session_state.selected_pipe + 1) in pipes_list:
                    controlling_valves.append(valve_tag)
            
            if controlling_valves:
                st.write(f"**Controlled by:** {', '.join(controlling_valves)}")
        else:
            st.markdown("---")
            st.subheader("ℹ️ No Pipe Selected")
            st.info("Click on a pipe in the sidebar to select and inspect it")
        
        st.markdown("---")
        st.subheader("🔧 How It Works")
        st.markdown("""
        - **Open a valve** → Controlled pipes turn **GREEN**
        - **Close a valve** → Controlled pipes turn **BLUE**
        - **Click a pipe** → Highlights it in **PURPLE**
        - **Unselect All** → Removes purple highlighting
        - **Valve Dependencies** override physical proximity
        - Some pipes follow the color of other pipes
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
    
    # Show pipe colors
    st.subheader("Pipe Colors")
    for i in range(len(st.session_state.pipes)):
        color = get_pipe_color_based_on_valves(i, st.session_state.pipes[i], valves, st.session_state.valve_states)
        color_name = "GREEN" if color == (0, 255, 0) else "BLUE"
        st.write(f"Pipe {i+1}: {color_name}")
    
    if st.session_state.pipes:
        st.write("**Pipe 1 Coordinates:**", st.session_state.pipes[0] if len(st.session_state.pipes) > 0 else "Not found")
    st.write("**All Pipes:**")
    st.json(st.session_state.pipes)
