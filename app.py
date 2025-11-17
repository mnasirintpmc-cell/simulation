import streamlit as st
import json
from PIL import Image, ImageDraw
import os

st.set_page_config(layout="wide")

# Configuration
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"
PIPES_DATA_FILE = "pipes.json"
PIPE_GROUPS_FILE = "pipe_groups.json"

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

def load_pipe_groups():
    """Load pipe groups based on mechanical construction"""
    default_groups = {
        "pipe_groups": {
            "main_flow_line": {
                "name": "Main Flow Line",
                "description": "Primary flow path through the system",
                "pipes": [1, 2, 3, 4, 5, 6, 7],
                "valves": ["V-101", "V-102", "V-103"]
            },
            "secondary_flow_line": {
                "name": "Secondary Flow Line", 
                "description": "Secondary flow path",
                "pipes": [8, 9, 10, 11, 12, 13],
                "valves": ["V-201", "V-202"]
            },
            "bypass_line": {
                "name": "Bypass Line",
                "description": "Bypass flow path",
                "pipes": [14, 15, 16, 17],
                "valves": ["V-301", "V-302"]
            },
            "utility_line": {
                "name": "Utility Line",
                "description": "Utility service line",
                "pipes": [18, 19, 20, 21, 22],
                "valves": ["V-401", "V-402"]
            }
        },
        "valve_control": {
            "V-101": ["main_flow_line"],
            "V-102": ["main_flow_line"], 
            "V-103": ["main_flow_line"],
            "V-201": ["secondary_flow_line"],
            "V-202": ["secondary_flow_line"],
            "V-301": ["bypass_line"],
            "V-302": ["bypass_line"],
            "V-401": ["utility_line"],
            "V-402": ["utility_line"]
        }
    }
    
    if os.path.exists(PIPE_GROUPS_FILE):
        try:
            with open(PIPE_GROUPS_FILE, "r") as f:
                user_groups = json.load(f)
                # Merge with default groups
                default_groups.update(user_groups)
        except:
            st.warning("Error loading pipe_groups.json, using default groups")
    
    return default_groups

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

def get_pipe_color_based_on_groups(pipe_index, pipe_coords, valves, valve_states, pipe_groups):
    """Determine pipe color based on pipe groups and valve control"""
    pipe_number = pipe_index + 1  # Convert to 1-indexed for clarity
    
    # Find which groups this pipe belongs to
    pipe_groups_list = []
    for group_id, group_data in pipe_groups["pipe_groups"].items():
        if pipe_number in group_data["pipes"]:
            pipe_groups_list.append(group_id)
    
    # If pipe belongs to any groups, check if any controlling valves are open
    if pipe_groups_list:
        # Check all valves that control these groups
        for group_id in pipe_groups_list:
            # Find valves that control this group
            for valve_tag, controlled_groups in pipe_groups["valve_control"].items():
                if group_id in controlled_groups and valve_tag in valve_states:
                    if valve_states[valve_tag]:
                        return (0, 255, 0)  # Green - at least one controlling valve is open
        
        # If we get here, all controlling valves for all groups are closed
        return (0, 0, 255)  # Blue - all controlling valves are closed
    
    # If pipe doesn't belong to any group, check physical proximity
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
                    # Get pipe color based on pipe groups
                    color = get_pipe_color_based_on_groups(i, pipe, valves, st.session_state.valve_states, st.session_state.pipe_groups)
                    
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

# Load data
valves = load_valves()
pipes = load_pipes()
pipe_groups = load_pipe_groups()

# Initialize session state
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}

if "selected_pipe" not in st.session_state:
    st.session_state.selected_pipe = None

if "pipes" not in st.session_state:
    st.session_state.pipes = pipes

if "pipe_groups" not in st.session_state:
    st.session_state.pipe_groups = pipe_groups

if "show_group_editor" not in st.session_state:
    st.session_state.show_group_editor = False

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
    
    # GROUP EDITOR TOGGLE
    if st.button("🏗️ Show/Hide Pipe Group Editor", use_container_width=True):
        st.session_state.show_group_editor = not st.session_state.show_group_editor
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

# Pipe Group Editor
if st.session_state.show_group_editor:
    st.header("🏗️ Pipe Group Editor")
    st.markdown("Group pipes based on mechanical construction and assign controlling valves")
    
    with st.expander("📝 Edit Pipe Groups", expanded=True):
        st.json(st.session_state.pipe_groups)
        
        if st.button("💾 Save Pipe Groups"):
            try:
                with open(PIPE_GROUPS_FILE, "w") as f:
                    json.dump(st.session_state.pipe_groups, f, indent=2)
                st.success("Pipe groups saved!")
            except Exception as e:
                st.error(f"Error saving pipe groups: {e}")

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
    st.header("🔍 Pipe Group Status")
    st.markdown("---")
    
    # Show active pipe groups
    st.subheader("🏗️ Active Pipe Groups")
    active_groups = []
    
    for group_id, group_data in st.session_state.pipe_groups["pipe_groups"].items():
        # Check if any controlling valve for this group is open
        group_valves = []
        for valve_tag, controlled_groups in st.session_state.pipe_groups["valve_control"].items():
            if group_id in controlled_groups:
                group_valves.append(valve_tag)
        
        # Check if any of these valves are open
        has_open_valve = any(st.session_state.valve_states.get(valve, False) for valve in group_valves)
        
        if has_open_valve:
            active_groups.append(group_data["name"])
    
    if active_groups:
        for group in active_groups:
            st.success(f"✅ {group}")
    else:
        st.info("ℹ️ No active pipe groups")
    
    # Show valve status summary
    st.markdown("---")
    st.subheader("🎯 Valve States")
    open_valves = sum(1 for state in st.session_state.valve_states.values() if state)
    closed_valves = len(valves) - open_valves
    st.write(f"**Open Valves:** {open_valves}")
    st.write(f"**Closed Valves:** {closed_valves}")
    
    # Show selected pipe info
    if st.session_state.selected_pipe is not None:
        st.markdown("---")
        st.subheader(f"🟣 Selected Pipe {st.session_state.selected_pipe + 1}")
        pipe = st.session_state.pipes[st.session_state.selected_pipe]
        st.write(f"Start: ({pipe['x1']}, {pipe['y1']})")
        st.write(f"End: ({pipe['x2']}, {pipe['y2']})")
        
        # Check flow status for selected pipe
        color = get_pipe_color_based_on_groups(st.session_state.selected_pipe, pipe, valves, st.session_state.valve_states, st.session_state.pipe_groups)
        flow_status = "🟢 ACTIVE FLOW" if color == (0, 255, 0) else "🔵 NO FLOW"
        st.write(f"**Flow Status:** {flow_status}")
        
        # Show which groups this pipe belongs to
        pipe_groups_list = []
        for group_id, group_data in st.session_state.pipe_groups["pipe_groups"].items():
            if (st.session_state.selected_pipe + 1) in group_data["pipes"]:
                pipe_groups_list.append(group_data["name"])
        
        if pipe_groups_list:
            st.write(f"**Pipe Groups:** {', '.join(pipe_groups_list)}")
            
            # Show controlling valves for these groups
            controlling_valves = []
            for group_id, group_data in st.session_state.pipe_groups["pipe_groups"].items():
                if (st.session_state.selected_pipe + 1) in group_data["pipes"]:
                    for valve_tag, controlled_groups in st.session_state.pipe_groups["valve_control"].items():
                        if group_id in controlled_groups:
                            controlling_valves.append(valve_tag)
            
            if controlling_valves:
                st.write(f"**Controlled by:** {', '.join(set(controlling_valves))}")
    else:
        st.markdown("---")
        st.subheader("ℹ️ No Pipe Selected")
        st.info("Click on a pipe in the sidebar to select and inspect it")
    
    st.markdown("---")
    st.subheader("🔧 How It Works")
    st.markdown("""
    - **Pipe Groups** are based on mechanical construction
    - **Valves control entire groups** of pipes
    - **Open a valve** → All pipes in controlled groups turn GREEN
    - **Close all valves** for a group → All pipes in group turn BLUE
    - **Edit pipe groups** in the Group Editor
    """)

# Debug information
with st.expander("🔧 Debug Information"):
    st.write("**Image Dimensions:**", get_image_dimensions())
    
    # Show pipe group analysis
    st.subheader("Pipe Group Analysis")
    for group_id, group_data in st.session_state.pipe_groups["pipe_groups"].items():
        group_valves = []
        for valve_tag, controlled_groups in st.session_state.pipe_groups["valve_control"].items():
            if group_id in controlled_groups:
                group_valves.append(valve_tag)
        
        has_open_valve = any(st.session_state.valve_states.get(valve, False) for valve in group_valves)
        status = "🟢 ACTIVE" if has_open_valve else "🔵 INACTIVE"
        st.write(f"{status} **{group_data['name']}**")
        st.write(f"  Pipes: {group_data['pipes']}")
        st.write(f"  Controlling Valves: {group_valves}")
    
    # Show pipe colors
    st.subheader("Pipe Colors")
    for i in range(len(st.session_state.pipes)):
        color = get_pipe_color_based_on_groups(i, st.session_state.pipes[i], valves, st.session_state.valve_states, st.session_state.pipe_groups)
        color_name = "GREEN" if color == (0, 255, 0) else "BLUE"
        st.write(f"Pipe {i+1}: {color_name}")
