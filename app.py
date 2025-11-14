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
    """Load valve positions from JSON - VALVES ARE FIXED"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def load_pipes():
    """Load pipe positions from JSON file - PIPES ARE MOVABLE"""
    try:
        if os.path.exists(PIPES_DATA_FILE):
            with open(PIPES_DATA_FILE, "r") as f:
                pipes_data = json.load(f)
                if isinstance(pipes_data, list) and len(pipes_data) > 0:
                    return pipes_data
        # Return default pipes if file doesn't exist
        return create_default_pipes()
    except Exception as e:
        st.error(f"Error loading pipes: {e}")
        return create_default_pipes()

def create_default_pipes():
    """Create default pipe positions"""
    img_width, img_height = get_image_dimensions()
    default_pipes = []
    
    # Create 8 default pipes in a grid pattern
    num_pipes = 8
    cols = 4
    rows = 2
    
    pipe_length = 120
    spacing_x = img_width // (cols + 1)
    spacing_y = img_height // (rows + 1)
    
    for i in range(num_pipes):
        row = i // cols
        col = i % cols
        
        center_x = spacing_x * (col + 1)
        center_y = spacing_y * (row + 1)
        
        default_pipe = {
            "id": i,
            "x1": center_x - pipe_length // 2,
            "y1": center_y,
            "x2": center_x + pipe_length // 2,
            "y2": center_y,
            "name": f"Pipe_{i+1}"
        }
        default_pipes.append(default_pipe)
    
    # Save the default pipes
    save_pipes(default_pipes)
    return default_pipes

def save_pipes(pipes_data):
    """Save pipe positions to JSON file"""
    try:
        with open(PIPES_DATA_FILE, "w") as f:
            json.dump(pipes_data, f, indent=2)
        st.success("✅ Pipes saved successfully!")
        return True
    except Exception as e:
        st.error(f"Error saving pipes: {e}")
        return False

def get_image_dimensions():
    """Get the dimensions of the P&ID image"""
    try:
        with Image.open(PID_FILE) as img:
            return img.size
    except:
        return (1200, 800)  # Default fallback

def create_pid_with_valves_and_pipes():
    """Create P&ID image with FIXED valves and MOVABLE pipes"""
    try:
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
        img_width, img_height = pid_img.size
        
        # Draw pipes FIRST (so valves appear on top)
        if st.session_state.pipes:
            for i, pipe in enumerate(st.session_state.pipes):
                # Check if pipe is within reasonable bounds
                is_reasonable = (
                    -1000 <= pipe["x1"] <= img_width + 1000 and
                    -1000 <= pipe["x2"] <= img_width + 1000 and
                    -1000 <= pipe["y1"] <= img_height + 1000 and
                    -1000 <= pipe["y2"] <= img_height + 1000
                )
                
                if is_reasonable:
                    color = (148, 0, 211) if i == st.session_state.selected_pipe else (0, 0, 255)  # Purple for selected
                    width = 8 if i == st.session_state.selected_pipe else 6
                    draw.line([(pipe["x1"], pipe["y1"]), (pipe["x2"], pipe["y2"])], fill=color, width=width)
                    
                    # Draw endpoints for selected pipe
                    if i == st.session_state.selected_pipe:
                        draw.ellipse([pipe["x1"]-6, pipe["y1"]-6, pipe["x1"]+6, pipe["y1"]+6], fill=(255, 0, 0), outline="white", width=2)
                        draw.ellipse([pipe["x2"]-6, pipe["y2"]-6, pipe["x2"]+6, pipe["y2"]+6], fill=(255, 0, 0), outline="white", width=2)
                        
                    # Draw pipe name
                    mid_x = (pipe["x1"] + pipe["x2"]) // 2
                    mid_y = (pipe["y1"] + pipe["y2"]) // 2
                    draw.text((mid_x + 10, mid_y - 10), pipe.get("name", f"Pipe_{i+1}"), fill="white", stroke_fill="black", stroke_width=1)
        
        # Draw VALVES (FIXED POSITIONS from JSON)
        for tag, data in valves.items():
            x, y = data["x"], data["y"]  # Fixed positions from JSON
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

# Load data - VALVES ARE FIXED, PIPES ARE MOVABLE
valves = load_valves()

# Initialize session state
if "pipes" not in st.session_state:
    st.session_state.pipes = load_pipes()  # Load pipes from JSON

if "valve_states" not in st.session_state:
    # Valve states can change, but positions are fixed
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}

if "selected_pipe" not in st.session_state:
    st.session_state.selected_pipe = 0 if st.session_state.pipes else None

# Initialize coordinate state for real-time updates
if "current_coords" not in st.session_state:
    if st.session_state.pipes and st.session_state.selected_pipe is not None:
        pipe = st.session_state.pipes[st.session_state.selected_pipe]
        st.session_state.current_coords = {
            "x1": pipe["x1"],
            "y1": pipe["y1"], 
            "x2": pipe["x2"],
            "y2": pipe["y2"]
        }
    else:
        st.session_state.current_coords = {"x1": 0, "y1": 0, "x2": 0, "y2": 0}

# Update coordinates when pipe selection changes
if st.session_state.pipes and st.session_state.selected_pipe is not None:
    current_pipe = st.session_state.pipes[st.session_state.selected_pipe]
    st.session_state.current_coords = {
        "x1": current_pipe["x1"],
        "y1": current_pipe["y1"],
        "x2": current_pipe["x2"], 
        "y2": current_pipe["y2"]
    }

# Main app
st.title("P&ID Interactive Simulation")
st.markdown("**🔒 Valves are fixed | 🎯 Pipes are movable**")

# SAVE ALL PIPES BUTTON
st.info("💾 **Move pipes as needed, then click below to PERMANENTLY save positions**")
if st.button("💾 SAVE ALL PIPE POSITIONS", type="primary", use_container_width=True):
    if save_pipes(st.session_state.pipes):
        st.success("✅ All pipe positions saved! They will persist after refresh.")

# RESET PIPES BUTTON (if needed)
if st.button("🔄 RESET ALL PIPES TO DEFAULT", type="secondary", use_container_width=True):
    st.session_state.pipes = create_default_pipes()
    st.session_state.selected_pipe = 0
    st.success("✅ All pipes reset to default positions!")
    st.rerun()

if not valves:
    st.error("No valves found in valves.json. Please check your configuration.")
    st.stop()

# Create sidebar for controls
with st.sidebar:
    st.header("🎯 Valve Controls")
    st.markdown("---")
    
    # Valve toggle buttons - STATES can change, but POSITIONS are fixed
    for tag, data in valves.items():
        current_state = st.session_state.valve_states[tag]
        
        button_label = f"🔴 {tag} - OPEN" if current_state else f"🟢 {tag} - CLOSED"
        
        if st.button(button_label, key=f"btn_{tag}", use_container_width=True):
            st.session_state.valve_states[tag] = not current_state
            st.rerun()
    
    st.markdown("---")
    
    # Pipe selection
    if st.session_state.pipes:
        st.header("📋 Pipe Selection")
        for i in range(len(st.session_state.pipes)):
            is_selected = st.session_state.selected_pipe == i
            pipe = st.session_state.pipes[i]
            
            status_icon = "🟣" if is_selected else "🔵"
            
            label = f"{status_icon} {pipe.get('name', f'Pipe {i+1}')}" 
            
            if st.button(label, key=f"pipe_{i}", use_container_width=True):
                st.session_state.selected_pipe = i
                # Update coordinates when pipe selection changes
                st.session_state.current_coords = {
                    "x1": pipe["x1"],
                    "y1": pipe["y1"],
                    "x2": pipe["x2"],
                    "y2": pipe["y2"]
                }
                st.rerun()

# Main content area
col1, col2 = st.columns([3, 1])
with col1:
    # Display the P&ID
    composite_img = create_pid_with_valves_and_pipes()
    st.image(composite_img, use_container_width=True, caption="🟣 Selected Pipe | 🔵 Normal Pipe | 🔴/🟢 Valve States")

with col2:
    # Pipe controls
    st.header("🔧 Pipe Controls")
    st.markdown("---")
    
    if st.session_state.selected_pipe is not None and st.session_state.pipes:
        pipe = st.session_state.pipes[st.session_state.selected_pipe]
        
        st.subheader(f"🟣 {pipe.get('name', f'Pipe {st.session_state.selected_pipe + 1}')}")
        
        # Display current coordinates (LIVE UPDATES)
        st.write(f"**Start:** ({pipe['x1']}, {pipe['y1']})")
        st.write(f"**End:** ({pipe['x2']}, {pipe['y2']})")
        
        # Quick movement controls
        st.markdown("---")
        st.subheader("📍 Move Pipe")
        col_up, col_down, col_left, col_right = st.columns(4)
        with col_up:
            if st.button("↑", use_container_width=True):
                pipe["y1"] -= 10
                pipe["y2"] -= 10
                st.session_state.pipes[st.session_state.selected_pipe] = pipe
                # Update coordinate display immediately
                st.session_state.current_coords = {
                    "x1": pipe["x1"],
                    "y1": pipe["y1"],
                    "x2": pipe["x2"],
                    "y2": pipe["y2"]
                }
                st.rerun()
        with col_down:
            if st.button("↓", use_container_width=True):
                pipe["y1"] += 10
                pipe["y2"] += 10
                st.session_state.pipes[st.session_state.selected_pipe] = pipe
                st.session_state.current_coords = {
                    "x1": pipe["x1"],
                    "y1": pipe["y1"],
                    "x2": pipe["x2"],
                    "y2": pipe["y2"]
                }
                st.rerun()
        with col_left:
            if st.button("←", use_container_width=True):
                pipe["x1"] -= 10
                pipe["x2"] -= 10
                st.session_state.pipes[st.session_state.selected_pipe] = pipe
                st.session_state.current_coords = {
                    "x1": pipe["x1"],
                    "y1": pipe["y1"],
                    "x2": pipe["x2"],
                    "y2": pipe["y2"]
                }
                st.rerun()
        with col_right:
            if st.button("→", use_container_width=True):
                pipe["x1"] += 10
                pipe["x2"] += 10
                st.session_state.pipes[st.session_state.selected_pipe] = pipe
                st.session_state.current_coords = {
                    "x1": pipe["x1"],
                    "y1": pipe["y1"],
                    "x2": pipe["x2"],
                    "y2": pipe["y2"]
                }
                st.rerun()
        
        # Manual coordinate input - ALWAYS SHOWS CURRENT VALUES
        st.markdown("---")
        st.subheader("🎯 Set Exact Coordinates")
        
        # Use current coordinates from session state
        new_x1 = st.number_input("X1", value=st.session_state.current_coords["x1"], key="set_x1")
        new_y1 = st.number_input("Y1", value=st.session_state.current_coords["y1"], key="set_y1")
        new_x2 = st.number_input("X2", value=st.session_state.current_coords["x2"], key="set_x2") 
        new_y2 = st.number_input("Y2", value=st.session_state.current_coords["y2"], key="set_y2")
        
        if st.button("💫 APPLY COORDINATES", use_container_width=True):
            pipe["x1"] = new_x1
            pipe["y1"] = new_y1
            pipe["x2"] = new_x2
            pipe["y2"] = new_y2
            st.session_state.pipes[st.session_state.selected_pipe] = pipe
            # Update coordinate display
            st.session_state.current_coords = {
                "x1": new_x1,
                "y1": new_y1,
                "x2": new_x2,
                "y2": new_y2
            }
            st.rerun()
        
        # Save individual pipe
        st.markdown("---")
        if st.button("💾 SAVE THIS PIPE", use_container_width=True, type="primary"):
            if save_pipes(st.session_state.pipes):
                st.success("✅ Pipe position saved!")

# Debug information
with st.expander("🔧 System Info"):
    st.write("**Valves Loaded:**", len(valves))
    st.write("**Pipes Loaded:**", len(st.session_state.pipes))
    st.write("**Selected Pipe:**", st.session_state.selected_pipe)
    st.write("**Current Coordinates:**", st.session_state.current_coords)
    st.write("**Pipes File:**", PIPES_DATA_FILE)
