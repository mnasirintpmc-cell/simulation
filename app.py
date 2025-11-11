import streamlit as st
import json
from PIL import Image, ImageDraw
import os

st.set_page_config(layout="wide")

# Configuration
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"

def initialize_valve_data():
    """Initialize with empty valve data"""
    return {}

def save_valves(valves_data):
    with open(DATA_FILE, "w") as f:
        json.dump(valves_data, f, indent=4)

def load_valves():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return initialize_valve_data()

# Load or initialize valve data
if "valves" not in st.session_state:
    st.session_state.valves = load_valves()

# Main app
st.title("P&ID Valve Extractor")
st.markdown("### Step 1: Identify Valves on Your P&ID")

# Display the P&ID
try:
    pid_img = Image.open(PID_FILE)
    st.image(pid_img, use_column_width=True, caption="Your P&ID - Identify valve tags")
except Exception as e:
    st.error(f"Could not load P&ID image: {e}")
    st.stop()

st.markdown("---")
st.markdown("### Step 2: Add Valves Found on Your P&ID")

# Valve management
col1, col2 = st.columns(2)

with col1:
    st.subheader("Add New Valve")
    
    with st.form("add_valve_form"):
        valve_tag = st.text_input("Valve Tag (e.g., V-101, V-102):")
        default_x = st.number_input("X Position", value=100)
        default_y = st.number_input("Y Position", value=100)
        initial_state = st.selectbox("Initial State", ["Closed", "Open"])
        
        if st.form_submit_button("Add Valve"):
            if valve_tag and valve_tag.strip():
                tag = valve_tag.strip()
                st.session_state.valves[tag] = {
                    "x": int(default_x),
                    "y": int(default_y), 
                    "state": (initial_state == "Open")
                }
                save_valves(st.session_state.valves)
                st.success(f"Added valve {tag}")
                st.rerun()
            else:
                st.error("Please enter a valve tag")

with col2:
    st.subheader("Current Valves")
    if st.session_state.valves:
        for tag, data in st.session_state.valves.items():
            status = "OPEN" if data["state"] else "CLOSED"
            st.write(f"**{tag}** - {status} - Position: ({data['x']}, {data['y']})")
            
            col_edit, col_del = st.columns(2)
            with col_edit:
                if st.button(f"Edit 📍", key=f"edit_{tag}"):
                    st.session_state.editing_valve = tag
            with col_del:
                if st.button(f"Delete 🗑️", key=f"del_{tag}"):
                    del st.session_state.valves[tag]
                    save_valves(st.session_state.valves)
                    st.rerun()
    else:
        st.info("No valves added yet. Use the form to add valves from your P&ID.")

st.markdown("---")
st.markdown("### Step 3: Position Valves on P&ID")

if st.session_state.valves:
    # Create image with valve markers
    try:
        pid_with_markers = pid_img.copy().convert("RGBA")
        draw = ImageDraw.Draw(pid_with_markers)
        
        for tag, data in st.session_state.valves.items():
            x, y = data["x"], data["y"]
            color = (0, 255, 0) if data["state"] else (255, 0, 0)  # Green if open, red if closed
            
            # Draw a circle marker
            draw.ellipse([x-10, y-10, x+10, y+10], fill=color, outline="white", width=2)
            # Draw valve tag text
            draw.text((x+15, y-15), tag, fill="white", stroke_fill="black", stroke_width=2)
        
        st.image(pid_with_markers, use_column_width=True, caption="P&ID with Valve Markers")
        
    except Exception as e:
        st.error(f"Error drawing valve markers: {e}")
        st.image(pid_img, use_column_width=True, caption="Original P&ID")

# Valve position adjustment
if st.session_state.valves:
    st.markdown("### Step 4: Adjust Valve Positions")
    
    selected_valve = st.selectbox("Select valve to adjust position:", list(st.session_state.valves.keys()))
    
    if selected_valve:
        data = st.session_state.valves[selected_valve]
        col_x, col_y, col_btn = st.columns([1, 1, 1])
        
        with col_x:
            new_x = st.number_input("X Position", value=data["x"], key="adj_x")
        with col_y:
            new_y = st.number_input("Y Position", value=data["y"], key="adj_y")
        with col_btn:
            if st.button("Update Position"):
                st.session_state.valves[selected_valve]["x"] = int(new_x)
                st.session_state.valves[selected_valve]["y"] = int(new_y)
                save_valves(st.session_state.valves)
                st.success(f"Updated position for {selected_valve}")
                st.rerun()

# Instructions
with st.expander("📋 Instructions"):
    st.markdown("""
    1. **Identify Valves**: Look at your P&ID above and identify all valve tags (like V-101, V-102, etc.)
    2. **Add Valves**: Use the form to add each valve with its tag and approximate position
    3. **Position Valves**: Adjust the X,Y coordinates to place markers exactly where valves are on the P&ID
    4. **Test**: Once all valves are added, you'll be able to open/close them interactively
    
    **Tips**:
    - Start by adding just 2-3 valves to test
    - Use the position adjustment to fine-tune valve locations
    - Valve positions are saved automatically
    """)

# Debug info
with st.expander("🔧 Debug Information"):
    st.write("Current valve data:", st.session_state.valves)
    st.write(f"Total valves: {len(st.session_state.valves)}")
