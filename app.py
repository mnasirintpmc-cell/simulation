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
            
            # Store button position (shifted to the left of the valve)
            button_positions[tag] = (x - 80, y)
            
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

# Alternative: Left-aligned controls for each valve
st.markdown("---")
st.markdown("### Quick Valve Toggles")

# Create a more compact layout with valves grouped by rows
valve_list = list(valves.items())
num_per_row = 5  # Adjust based on how many valves you have

for i in range(0, len(valve_list), num_per_row):
    row_valves = valve_list[i:i + num_per_row]
    cols = st.columns(len(row_valves))
    
    for col_idx, (tag, data) in enumerate(row_valves):
        with cols[col_idx]:
            current_state = st.session_state.valve_states[tag]
            
            # More compact button design
            if current_state:
                compact_label = f"🔴 {tag}"
                button_help = f"Click to close {tag}"
            else:
                compact_label = f"🟢 {tag}"
                button_help = f"Click to open {tag}"
            
            if st.button(compact_label, key=f"compact_{tag}", help=button_help, use_container_width=True):
                st.session_state.valve_states[tag] = not current_state
                st.rerun()

# Current status display
st.markdown("---")
st.markdown("### Current Valve Status")

# Display status in a clean table format
for i in range(0, len(valves), 3):
    cols = st.columns(3)
    valve_items = list(valves.items())[i:i + 3]
    
    for col_idx, (tag, data) in enumerate(valve_items):
        with cols[col_idx]:
            current_state = st.session_state.valve_states[tag]
            status = "🟢 OPEN" if current_state else "🔴 CLOSED"
            
            st.write(f"**{tag}**")
            st.write(f"Status: {status}")
            st.write(f"Position: ({data['x']}, {data['y']})")
            st.progress(100 if current_state else 0)

# Instructions
st.markdown("---")
st.markdown("### Instructions")
st.markdown("""
- **Green circles** on the P&ID indicate OPEN valves
- **Red circles** on the P&ID indicate CLOSED valves  
- Click any valve button above to toggle its state
- Valve positions are fixed from your JSON configuration
- All changes are temporary (not saved to file)
""")

# Debug information
with st.expander("🔧 Configuration Details"):
    st.write("**Loaded Valves:**", valves)
    st.write("**Current States:**", st.session_state.valve_states)
    st.write("**Total Valves:**", len(valves))
    
    # Show valve positions
    st.write("**Valve Positions:**")
    for tag, data in valves.items():
        st.write(f"- {tag}: ({data['x']}, {data['y']}) - {'OPEN' if st.session_state.valve_states[tag] else 'CLOSED'}")
