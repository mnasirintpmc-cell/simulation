import streamlit as st
import json
from PIL import Image, ImageDraw
import os

st.set_page_config(layout="wide")

# Configuration
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"

def load_valves():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def create_pid_with_valves_and_buttons():
    """Create P&ID image with valve indicators and button positions"""
    try:
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
        
        button_positions = {}
        
        for tag, data in valves.items():
            x, y = data["x"], data["y"]
            current_state = st.session_state.valve_states[tag]
            
            # Choose color based on valve state
            color = (0, 255, 0) if current_state else (255, 0, 0)
            
            # Draw valve indicator
            draw.ellipse([x-8, y-8, x+8, y+8], fill=color, outline="white", width=2)
            draw.text((x+12, y-10), tag, fill="white", stroke_fill="black", stroke_width=1)
            
            # Store button position (shifted above the valve)
            button_positions[tag] = (x, y - 40)
            
        return pid_img.convert("RGB"), button_positions
    except Exception as e:
        st.error(f"Error creating P&ID image: {e}")
        try:
            return Image.open(PID_FILE).convert("RGB"), {}
        except:
            return Image.new("RGB", (800, 600), (255, 255, 255)), {}

# Load valve data
valves = load_valves()

# Initialize session state for current states
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}

# Main app
st.title("P&ID Interactive Simulation")

if not valves:
    st.error("No valves found in valves.json. Please check your configuration.")
    st.stop()

# Create the P&ID with valve indicators
composite_img, button_positions = create_pid_with_valves_and_buttons()

# Display the P&ID
st.image(composite_img, use_container_width=True, caption="Interactive P&ID")

# Create valve controls in a grid below the image
st.markdown("---")
st.markdown("### Valve Controls")

# Create columns for the valve buttons
num_columns = min(4, len(valves))
columns = st.columns(num_columns)

# Display toggle buttons in a grid
for i, (tag, data) in enumerate(valves.items()):
    col_idx = i % num_columns
    with columns[col_idx]:
        current_state = st.session_state.valve_states[tag]
        
        # Create colored button based on state
        if current_state:
            button_label = f"🔴 {tag} - OPEN"
            button_type = "primary"
        else:
            button_label = f"🟢 {tag} - CLOSED" 
            button_type = "secondary"
        
        if st.button(button_label, key=f"btn_{tag}", use_container_width=True, type=button_type):
            st.session_state.valve_states[tag] = not current_state
            st.rerun()
        
        # Show position info
        st.caption(f"Position: ({data['x']}, {data['y']})")

# Current status display
st.markdown("---")
st.markdown("### Current Valve Status")

# Create a nice status table
status_data = []
for tag, data in valves.items():
    current_state = st.session_state.valve_states[tag]
    status_data.append({
        "Valve": tag,
        "Status": "🟢 OPEN" if current_state else "🔴 CLOSED",
        "Position": f"({data['x']}, {data['y']})"
    })

# Display as columns for better layout
if status_data:
    num_cols = min(3, len(status_data))
    status_cols = st.columns(num_cols)
    
    for i, status in enumerate(status_data):
        col_idx = i % num_cols
        with status_cols[col_idx]:
            st.metric(
                label=status["Valve"],
                value=status["Status"],
                delta=status["Position"]
            )

# Instructions
st.markdown("---")
st.markdown("### Instructions")
st.markdown("""
- **Green circles** on the P&ID indicate OPEN valves
- **Red circles** on the P&ID indicate CLOSED valves
- Click the buttons above to toggle valve states
- Valve positions are fixed from your JSON configuration
- All changes are temporary (not saved to file)
""")

# Debug information
with st.expander("🔧 Configuration Details"):
    st.write("**Loaded Valves:**", valves)
    st.write("**Current States:**", st.session_state.valve_states)
    st.write("**Button Positions:**", button_positions)
