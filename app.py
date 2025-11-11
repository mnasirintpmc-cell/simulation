import streamlit as st
import json
from PIL import Image, ImageDraw
import os
import io

PID_FILE = "P&ID.png"
VALVE_FILE = "valve_icon.png"
DATA_FILE = "valves.json"

st.set_page_config(layout="wide")

# Load/save valve data
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        valves = json.load(f)
else:
    valves = {
        "valve_2": {"x": 220, "y": 150, "state": False},
        "valve_3": {"x": 300, "y": 200, "state": False},
        "valve_4": {"x": 400, "y": 250, "state": False},
        "valve_5": {"x": 500, "y": 300, "state": False},
        "valve_6": {"x": 600, "y": 350, "state": False},
    }

# Initialize session state
if "valves" not in st.session_state:
    st.session_state.valves = valves

def save_valves():
    with open(DATA_FILE, "w") as f:
        json.dump(st.session_state.valves, f, indent=4)

def create_pid_with_valves():
    """Create P&ID image with valve overlays"""
    # Load base P&ID
    pid_img = Image.open(PID_FILE).convert("RGBA")
    
    # Load valve icon
    try:
        valve_icon = Image.open(VALVE_FILE).convert("RGBA")
    except:
        # Create a simple valve icon if file not found
        valve_icon = Image.new("RGBA", (30, 30), (255, 255, 255, 0))
        draw = ImageDraw.Draw(valve_icon)
        draw.rectangle([5, 5, 25, 25], fill=(255, 0, 0, 255))
    
    # Create a copy to draw on
    composite = pid_img.copy()
    
    # Overlay valves
    for name, data in st.session_state.valves.items():
        # Resize valve icon
        valve_resized = valve_icon.resize((25, 25))
        
        # Change color based on state
        if data["state"]:  # Open - green
            valve_colored = Image.new("RGBA", valve_resized.size, (0, 255, 0, 255))
        else:  # Closed - red
            valve_colored = Image.new("RGBA", valve_resized.size, (255, 0, 0, 255))
        
        # Paste valve onto composite
        composite.paste(valve_colored, (data["x"], data["y"]), valve_resized)
    
    return composite

# Create and display the P&ID with valves
composite_img = create_pid_with_valves()

# Convert to RGB for display
composite_rgb = composite_img.convert("RGB")

# Display the composite image
st.image(composite_rgb, use_column_width=True, caption="Interactive P&ID")

# Valve controls
st.subheader("Valve Controls")
col1, col2, col3, col4, col5 = st.columns(5)

valve_columns = [col1, col2, col3, col4, col5]
valve_names = list(st.session_state.valves.keys())

for i, name in enumerate(valve_names):
    with valve_columns[i]:
        data = st.session_state.valves[name]
        status = "OPEN" if data["state"] else "CLOSED"
        color = "🟢" if data["state"] else "🔴"
        
        st.write(f"**{name}**")
        st.write(f"Status: {color} {status}")
        
        if st.button(f"Toggle {name}", key=f"btn_{name}"):
            st.session_state.valves[name]["state"] = not st.session_state.valves[name]["state"]
            save_valves()
            st.rerun()

# Sidebar for position adjustment
st.sidebar.header("Valve Position Adjustment")
selected_valve = st.sidebar.selectbox("Select Valve", list(st.session_state.valves.keys()))

if selected_valve:
    current_data = st.session_state.valves[selected_valve]
    col_x, col_y = st.sidebar.columns(2)
    
    with col_x:
        new_x = st.number_input("X Position", value=current_data["x"], key="x_pos")
    with col_y:
        new_y = st.number_input("Y Position", value=current_data["y"], key="y_pos")
    
    if st.sidebar.button("💾 Save Position"):
        st.session_state.valves[selected_valve]["x"] = int(new_x)
        st.session_state.valves[selected_valve]["y"] = int(new_y)
        save_valves()
        st.sidebar.success(f"Position saved for {selected_valve}!")
        st.rerun()

# Display current valve states
st.sidebar.header("Current Valve States")
for name, data in st.session_state.valves.items():
    status = "OPEN" if data["state"] else "CLOSED"
    color = "🟢" if data["state"] else "🔴"
    st.sidebar.write(f"{color} {name}: {status} (X:{data['x']}, Y:{data['y']})")
