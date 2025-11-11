import streamlit as st
import json
from PIL import Image, ImageDraw
import os

st.set_page_config(layout="wide")

# Configuration
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"

def initialize_valve_data():
    return {}

def save_valves(valves_data):
    with open(DATA_FILE, "w") as f:
        json.dump(valves_data, f, indent=4)

def load_valves():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return initialize_valve_data()

# Initialize session state
if "valves" not in st.session_state:
    st.session_state.valves = load_valves()

if "positions_locked" not in st.session_state:
    st.session_state.positions_locked = False

def create_pid_with_valves():
    """Create P&ID image with valve overlays - FIXED VERSION"""
    try:
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
        
        for tag, data in st.session_state.valves.items():
            x, y = data["x"], data["y"]
            
            # Choose color based on valve state
            if data["state"]:  # Open
                color = (0, 255, 0)  # Green
                status_text = "OPEN"
            else:  # Closed
                color = (255, 0, 0)  # Red
                status_text = "CLOSED"
            
            # FIXED: Correct ellipse coordinates - last should be y+8, not x+8
            draw.ellipse([x-8, y-8, x+8, y+8], fill=color, outline="white", width=2)
            
            # Draw tag and status
            draw.text((x+12, y-20), tag, fill="white", stroke_fill="black", stroke_width=1)
            draw.text((x+12, y-5), status_text, fill="white", stroke_fill="black", stroke_width=1)
            
        return pid_img.convert("RGB")
    except Exception as e:
        st.error(f"Error creating P&ID image: {e}")
        # Return original image if there's an error
        try:
            return Image.open(PID_FILE).convert("RGB")
        except:
            return Image.new("RGB", (800, 600), (255, 255, 255))

# Main app
st.title("P&ID Interactive Simulation")
st.markdown("### Valve Controls")

# Simple lock control
if st.session_state.positions_locked:
    if st.button("🔓 Unlock Valve Positions"):
        st.session_state.positions_locked = False
        st.rerun()
else:
    if st.button("🔒 Lock Valve Positions"):
        st.session_state.positions_locked = True
        st.rerun()

# Display the P&ID with valves
composite_img = create_pid_with_valves()
st.image(composite_img, use_column_width=True, caption="Interactive P&ID - Click buttons below to toggle valves")

# Simple valve toggle buttons
st.markdown("### Toggle Valves")

if st.session_state.valves:
    # Create columns for valve buttons
    num_cols = min(4, len(st.session_state.valves))
    columns = st.columns(num_cols)
    
    for i, (tag, data) in enumerate(st.session_state.valves.items()):
        col_idx = i % num_cols
        with columns[col_idx]:
            status = "OPEN" if data["state"] else "CLOSED"
            button_text = f"🔴 Close {tag}" if data["state"] else f"🟢 Open {tag}"
            
            if st.button(button_text, key=f"toggle_{tag}", use_container_width=True):
                st.session_state.valves[tag]["state"] = not st.session_state.valves[tag]["state"]
                save_valves(st.session_state.valves)
                st.rerun()
            
            st.caption(f"Position: ({data['x']}, {data['y']}) - {status}")
else:
    st.info("No valves configured. Add valves below.")

# Valve management (only when unlocked)
if not st.session_state.positions_locked:
    st.markdown("---")
    st.markdown("### Manage Valves")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Add New Valve")
        with st.form("add_valve"):
            valve_tag = st.text_input("Valve Tag (e.g., V-101):")
            col_x, col_y = st.columns(2)
            with col_x:
                x_pos = st.number_input("X Position", value=100)
            with col_y:
                y_pos = st.number_input("Y Position", value=100)
            
            if st.form_submit_button("Add Valve"):
                if valve_tag and valve_tag.strip():
                    tag = valve_tag.strip().upper()
                    st.session_state.valves[tag] = {
                        "x": int(x_pos),
                        "y": int(y_pos),
                        "state": False
                    }
                    save_valves(st.session_state.valves)
                    st.success(f"Added {tag}")
                    st.rerun()

    with col2:
        st.subheader("Adjust Positions")
        if st.session_state.valves:
            selected_valve = st.selectbox("Select valve:", list(st.session_state.valves.keys()))
            if selected_valve:
                data = st.session_state.valves[selected_valve]
                new_x = st.number_input("X", value=data["x"], key="edit_x")
                new_y = st.number_input("Y", value=data["y"], key="edit_y")
                
                if st.button("Update Position"):
                    st.session_state.valves[selected_valve]["x"] = int(new_x)
                    st.session_state.valves[selected_valve]["y"] = int(new_y)
                    save_valves(st.session_state.valves)
                    st.success("Position updated!")
                    st.rerun()

# Current status
st.markdown("---")
st.markdown("### Current Status")
for tag, data in st.session_state.valves.items():
    status = "🟢 OPEN" if data["state"] else "🔴 CLOSED"
    st.write(f"**{tag}**: {status} at position ({data['x']}, {data['y']})")

# Save button
if st.button("💾 Save Configuration"):
    save_valves(st.session_state.valves)
    st.success("Configuration saved!")
