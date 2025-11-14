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
                    color = (148, 0, 211) if i == st.session_state.selected_pipe else (0, 0, 255)  # Purple for selected
                    width = 8 if i == st.session_state.selected_pipe else 6
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
    st.session_state.selected_pipe = 0 if pipes else None

if "pipes" not in st.session_state:
    st.session_state.pipes = pipes

# Main app
st.title("P&ID Interactive Simulation")

# SAVE ALL PIPES BUTTON
st.info("💾 **Move pipes as needed, then click below to PERMANENTLY save positions**")
if st.button("💾 SAVE ALL PIPE POSITIONS", type="primary", use_container_width=True):
    save_pipes(st.session_state.pipes)
    st.success("✅ All pipe positions saved! They will persist after refresh.")

# EMERGENCY RESET BUTTON
if st.session_state.pipes:
    st.error("🚨 If pipes are not visible, click the button below to RESET ALL PIPES to visible positions!")
    if st.button("🔄 RESET ALL PIPES TO VISIBLE POSITIONS", type="secondary", use_container_width=True):
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
    
    st.markdown("---")
    
    # Pipe selection
    if st.session_state.pipes:
        st.header("📋 Pipe Selection")
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
    st.image(composite_img, use_container_width=True, caption="🟣 Purple = Selected | 🔵 Blue = Normal | 🟡 Yellow = Off-screen (in sidebar)")

with col2:
    # Right sidebar for detailed status
    st.header("🔧 Pipe Controls")
    st.markdown("---")
    
    # Selected pipe info
    if st.session_state.selected_pipe is not None and st.session_state.pipes:
        pipe = st.session_state.pipes[st.session_state.selected_pipe]
        img_width, img_height = get_image_dimensions()
        
        st.subheader(f"🟣 Pipe {st.session_state.selected_pipe + 1}")
        
        # Display current coordinates (LIVE UPDATES)
        st.write(f"**Start:** ({pipe['x1']}, {pipe['y1']})")
        st.write(f"**End:** ({pipe['x2']}, {pipe['y2']})")
        
        # Check if coordinates are reasonable
        is_reasonable = (
            -1000 <= pipe["x1"] <= img_width + 1000 and
            -1000 <= pipe["x2"] <= img_width + 1000 and
            -1000 <= pipe["y1"] <= img_height + 1000 and
            -1000 <= pipe["y2"] <= img_height + 1000
        )
        
        if not is_reasonable:
            st.error("❌ Coordinates are EXTREMELY off-screen!")
            st.info("Use the RESET button at the top to fix this pipe.")
        else:
            # Calculate current length and orientation
            length = ((pipe["x2"] - pipe["x1"])**2 + (pipe["y2"] - pipe["y1"])**2)**0.5
            is_horizontal = abs(pipe["y2"] - pipe["y1"]) < abs(pipe["x2"] - pipe["x1"])
            orientation = "Horizontal" if is_horizontal else "Vertical"
            st.write(f"**Length:** {int(length)} pixels")
            st.write(f"**Orientation:** {orientation}")
            
            # PIPE ORIENTATION CONTROLS
            st.markdown("---")
            st.subheader("📐 Set Pipe Orientation")
            col_horiz, col_vert = st.columns(2)
            with col_horiz:
                if st.button("➖ Horizontal", use_container_width=True):
                    # Make pipe horizontal (keep center position)
                    center_x = (pipe["x1"] + pipe["x2"]) // 2
                    center_y = (pipe["y1"] + pipe["y2"]) // 2
                    length = 100
                    
                    pipe["x1"] = center_x - length // 2
                    pipe["y1"] = center_y
                    pipe["x2"] = center_x + length // 2
                    pipe["y2"] = center_y
                    
                    save_pipes(st.session_state.pipes)
                    st.rerun()
            
            with col_vert:
                if st.button("➡️ Vertical", use_container_width=True):
                    # Make pipe vertical (keep center position)
                    center_x = (pipe["x1"] + pipe["x2"]) // 2
                    center_y = (pipe["y1"] + pipe["y2"]) // 2
                    length = 100
                    
                    pipe["x1"] = center_x
                    pipe["y1"] = center_y - length // 2
                    pipe["x2"] = center_x
                    pipe["y2"] = center_y + length // 2
                    
                    save_pipes(st.session_state.pipes)
                    st.rerun()
            
            # QUICK RESET THIS PIPE
            st.markdown("---")
            st.subheader("🛠️ Quick Fix")
            if st.button("🔄 RESET THIS PIPE", use_container_width=True, type="secondary"):
                img_width, img_height = get_image_dimensions()
                
                # Move to center with reasonable length
                center_x = img_width // 2
                center_y = img_height // 2
                length = 100
                
                pipe["x1"] = center_x - length // 2
                pipe["y1"] = center_y
                pipe["x2"] = center_x + length // 2
                pipe["y2"] = center_y
                
                save_pipes(st.session_state.pipes)
                st.success("✅ Pipe reset to center!")
                st.rerun()
            
            # Pipe movement controls - APPROXIMATE MOVEMENT
            st.markdown("---")
            st.subheader("📍 Move Pipe")
            st.info("Use arrows for positioning")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button("↑", use_container_width=True):
                    pipe["y1"] -= 10
                    pipe["y2"] -= 10
                    save_pipes(st.session_state.pipes)
                    st.rerun()
            with col2:
                if st.button("↓", use_container_width=True):
                    pipe["y1"] += 10
                    pipe["y2"] += 10
                    save_pipes(st.session_state.pipes)
                    st.rerun()
            with col3:
                if st.button("←", use_container_width=True):
                    pipe["x1"] -= 10
                    pipe["x2"] -= 10
                    save_pipes(st.session_state.pipes)
                    st.rerun()
            with col4:
                if st.button("→", use_container_width=True):
                    pipe["x1"] += 10
                    pipe["x2"] += 10
                    save_pipes(st.session_state.pipes)
                    st.rerun()
            
            # Manual coordinate input - ALWAYS SHOWS CURRENT PIPE COORDINATES
            st.markdown("---")
            st.subheader("🎯 Current Coordinates")
            st.info("These fields ALWAYS show the current pipe position")
            
            # Create a display that shows current coordinates (read-only style)
            coord_col1, coord_col2 = st.columns(2)
            with coord_col1:
                st.text_input("X1", value=str(pipe["x1"]), key="display_x1", disabled=True)
                st.text_input("Y1", value=str(pipe["y1"]), key="display_y1", disabled=True)
            with coord_col2:
                st.text_input("X2", value=str(pipe["x2"]), key="display_x2", disabled=True) 
                st.text_input("Y2", value=str(pipe["y2"]), key="display_y2", disabled=True)
            
            # Manual coordinate input for when you want to type exact values
            st.markdown("---")
            st.subheader("✏️ Set Exact Coordinates")
            st.info("Type new coordinates below and click APPLY")
            
            # Use unique keys based on pipe selection to avoid conflicts
            pipe_key = f"manual_{st.session_state.selected_pipe}"
            new_x1 = st.number_input("New X1", value=pipe["x1"], key=f"new_x1_{pipe_key}")
            new_y1 = st.number_input("New Y1", value=pipe["y1"], key=f"new_y1_{pipe_key}")
            new_x2 = st.number_input("New X2", value=pipe["x2"], key=f"new_x2_{pipe_key}") 
            new_y2 = st.number_input("New Y2", value=pipe["y2"], key=f"new_y2_{pipe_key}")
            
            # Apply coordinates button - only needed if you manually type new numbers
            if st.button("💫 APPLY NEW COORDINATES", use_container_width=True, type="primary"):
                pipe["x1"] = new_x1
                pipe["y1"] = new_y1
                pipe["x2"] = new_x2
                pipe["y2"] = new_y2
                save_pipes(st.session_state.pipes)
                st.rerun()

# Debug information
with st.expander("🔧 Debug Information"):
    st.write("**Image Dimensions:**", get_image_dimensions())
    if st.session_state.pipes:
        st.write("**Pipe 5 Coordinates:**", st.session_state.pipes[4] if len(st.session_state.pipes) > 4 else "Not found")
    st.write("**All Pipes:**")
    st.json(st.session_state.pipes)
