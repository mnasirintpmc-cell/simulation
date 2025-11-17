import streamlit as st
import json
from PIL import Image, ImageDraw
import os

st.set_page_config(layout="wide")

# Configuration
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"
PIPES_DATA_FILE = "pipes.json"
PROCESS_RULES_FILE = "process_rules.json"

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

def load_process_rules():
    """Load process rules that define pipe colors based on valve combinations"""
    default_rules = {
        "processes": {
            "process_1": {
                "name": "Main Flow Process",
                "description": "Flow through V-301 and V-302 system",
                "valve_conditions": {
                    "V-301": "OPEN",
                    "V-302": "OPEN"
                },
                "pipe_colors": {
                    2: "GREEN", 3: "GREEN", 4: "GREEN", 13: "GREEN", 14: "GREEN", 21: "GREEN", 22: "GREEN"
                }
            },
            "process_2": {
                "name": "V-103 System",
                "description": "Flow through V-103 system",
                "valve_conditions": {
                    "V-103": "OPEN"
                },
                "pipe_colors": {
                    8: "GREEN", 15: "GREEN", 16: "GREEN", 17: "GREEN"
                }
            },
            "process_3": {
                "name": "V-301 Only",
                "description": "Flow only through V-301",
                "valve_conditions": {
                    "V-301": "OPEN",
                    "V-302": "CLOSED"
                },
                "pipe_colors": {
                    2: "GREEN", 3: "GREEN", 4: "GREEN", 14: "GREEN", 21: "GREEN", 22: "GREEN"
                }
            },
            "process_4": {
                "name": "V-302 Only", 
                "description": "Flow only through V-302",
                "valve_conditions": {
                    "V-301": "CLOSED",
                    "V-302": "OPEN"
                },
                "pipe_colors": {
                    4: "GREEN", 13: "GREEN", 14: "GREEN", 21: "GREEN", 22: "GREEN"
                }
            }
        },
        "pipe_dependencies": {
            20: 1,   # Pipe 20 follows pipe 1
            19: 11   # Pipe 19 follows pipe 11
        }
    }
    
    if os.path.exists(PROCESS_RULES_FILE):
        try:
            with open(PROCESS_RULES_FILE, "r") as f:
                user_rules = json.load(f)
                # Merge with default rules
                default_rules.update(user_rules)
        except:
            st.warning("Error loading process_rules.json, using default rules")
    
    return default_rules

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

def check_process_conditions(valve_states, process_conditions):
    """Check if all valve conditions for a process are met"""
    for valve, required_state in process_conditions.items():
        if valve not in valve_states:
            return False
        actual_state = "OPEN" if valve_states[valve] else "CLOSED"
        if actual_state != required_state:
            return False
    return True

def get_pipe_color_based_on_process(pipe_index, pipe_coords, valves, valve_states, process_rules):
    """Determine pipe color based on active processes and process rules"""
    pipe_number = pipe_index + 1  # Convert to 1-indexed for clarity
    
    # First, check if any process rules apply to this pipe
    active_processes = []
    
    for process_id, process_data in process_rules["processes"].items():
        if check_process_conditions(valve_states, process_data["valve_conditions"]):
            active_processes.append(process_data["name"])
            # If this pipe is defined in the process, use that color
            if pipe_number in process_data["pipe_colors"]:
                color_rule = process_data["pipe_colors"][pipe_number]
                if color_rule == "GREEN":
                    return (0, 255, 0)  # Green
                elif color_rule == "BLUE":
                    return (0, 0, 255)  # Blue
    
    # Check pipe dependencies
    if "pipe_dependencies" in process_rules:
        pipe_dependencies = process_rules["pipe_dependencies"]
        if pipe_number in pipe_dependencies:
            leader_pipe_number = pipe_dependencies[pipe_number]
            leader_pipe_index = leader_pipe_number - 1  # Convert back to 0-indexed
            if leader_pipe_index < len(st.session_state.pipes):
                # Get the color from the leader pipe
                leader_color = get_pipe_color_based_on_process(leader_pipe_index, st.session_state.pipes[leader_pipe_index], valves, valve_states, process_rules)
                return leader_color
    
    # If no process rule applies, check physical proximity to valves
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
                    # Get pipe color based on process rules
                    color = get_pipe_color_based_on_process(i, pipe, valves, st.session_state.valve_states, st.session_state.process_rules)
                    
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
process_rules = load_process_rules()

# Initialize session state
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}

if "selected_pipe" not in st.session_state:
    st.session_state.selected_pipe = None

if "pipes" not in st.session_state:
    st.session_state.pipes = pipes

if "process_rules" not in st.session_state:
    st.session_state.process_rules = process_rules

if "show_process_editor" not in st.session_state:
    st.session_state.show_process_editor = False

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
    
    # PROCESS EDITOR TOGGLE
    if st.button("⚙️ Show/Hide Process Editor", use_container_width=True):
        st.session_state.show_process_editor = not st.session_state.show_process_editor
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

# Process Editor
if st.session_state.show_process_editor:
    st.header("⚙️ Process Rules Editor")
    st.markdown("Define process logic that controls pipe colors based on valve combinations")
    
    with st.expander("📝 Edit Process Rules", expanded=True):
        st.json(st.session_state.process_rules)
        
        if st.button("💾 Save Process Rules"):
            try:
                with open(PROCESS_RULES_FILE, "w") as f:
                    json.dump(st.session_state.process_rules, f, indent=2)
                st.success("Process rules saved!")
            except Exception as e:
                st.error(f"Error saving process rules: {e}")

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
    st.header("🔍 Process Status")
    st.markdown("---")
    
    # Show active processes
    st.subheader("📊 Active Processes")
    active_processes = []
    for process_id, process_data in st.session_state.process_rules["processes"].items():
        if check_process_conditions(st.session_state.valve_states, process_data["valve_conditions"]):
            active_processes.append(process_data["name"])
    
    if active_processes:
        for process in active_processes:
            st.success(f"✅ {process}")
    else:
        st.info("ℹ️ No active processes")
    
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
        color = get_pipe_color_based_on_process(st.session_state.selected_pipe, pipe, valves, st.session_state.valve_states, st.session_state.process_rules)
        flow_status = "🟢 ACTIVE FLOW" if color == (0, 255, 0) else "🔵 NO FLOW"
        st.write(f"**Flow Status:** {flow_status}")
    else:
        st.markdown("---")
        st.subheader("ℹ️ No Pipe Selected")
        st.info("Click on a pipe in the sidebar to select and inspect it")
    
    st.markdown("---")
    st.subheader("🔧 How It Works")
    st.markdown("""
    - **Process-based logic** controls pipe colors
    - **Valve combinations** define active processes
    - **Process rules** determine which pipes turn green
    - **Edit process rules** in the Process Editor
    - Some pipes follow the color of other pipes
    """)

# Debug information
with st.expander("🔧 Debug Information"):
    st.write("**Image Dimensions:**", get_image_dimensions())
    
    # Show current process analysis
    st.subheader("Process Analysis")
    for process_id, process_data in st.session_state.process_rules["processes"].items():
        is_active = check_process_conditions(st.session_state.valve_states, process_data["valve_conditions"])
        status = "🟢 ACTIVE" if is_active else "🔵 INACTIVE"
        st.write(f"{status} **{process_data['name']}**")
        st.write(f"  Conditions: {process_data['valve_conditions']}")
    
    # Show pipe colors
    st.subheader("Pipe Colors")
    for i in range(len(st.session_state.pipes)):
        color = get_pipe_color_based_on_process(i, st.session_state.pipes[i], valves, st.session_state.valve_states, st.session_state.process_rules)
        color_name = "GREEN" if color == (0, 255, 0) else "BLUE"
        st.write(f"Pipe {i+1}: {color_name}")
