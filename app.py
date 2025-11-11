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

# Initialize locked state
if "positions_locked" not in st.session_state:
    st.session_state.positions_locked = False

def create_pid_with_valves():
    """Create P&ID image with valve overlays"""
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
            
            # Draw valve marker
            draw.ellipse([x-8, y-8, x+8, y+8], fill=color, outline="white", width=2)
            
            # Draw tag and status
            draw.text((x+12, y-20), tag, fill="white", stroke_fill="black", stroke_width=1)
            draw.text((x+12, y-5), status_text, fill="white", stroke_fill="black", stroke_width=1)
            
        return pid_img.convert("RGB")
    except Exception as e:
        st.error(f"Error creating P&ID image: {e}")
        return Image.new("RGB", (800, 600), (255, 255, 255))

# Main app
st.title("P&ID Interactive Simulation")
st.markdown("### Valve Configuration Manager")

# Locking controls
col_lock, col_export, col_import = st.columns(3)

with col_lock:
    if st.session_state.positions_locked:
        if st.button("🔓 Unlock Valve Positions"):
            st.session_state.positions_locked = False
            st.rerun()
    else:
        if st.button("🔒 Lock Valve Positions"):
            st.session_state.positions_locked = True
            st.rerun()

with col_export:
    if st.button("💾 Export Configuration"):
        save_valves(st.session_state.valves)
        st.success("Configuration saved successfully!")

with col_import:
    st.info(f"Data file: {DATA_FILE}")

# Display status
if st.session_state.positions_locked:
    st.success("✅ Valve positions are LOCKED - Ready for simulation")
else:
    st.warning("⚠️ Valve positions are UNLOCKED - You can adjust positions")

# Display the P&ID with valves
st.markdown("---")
st.markdown("### P&ID with Valves")

composite_img = create_pid_with_valves()
st.image(composite_img, use_column_width=True, caption="Interactive P&ID with Valve Status")

# Interactive valve controls
st.markdown("---")
st.markdown("### Valve Controls")

if st.session_state.valves:
    # Create columns for valve controls
    num_valves = len(st.session_state.valves)
    num_columns = min(4, num_valves)
    
    if num_columns > 0:
        valve_columns = st.columns(num_columns)
        
        for i, (tag, data) in enumerate(st.session_state.valves.items()):
            col_idx = i % num_columns
            with valve_columns[col_idx]:
                status = "OPEN" if data["state"] else "CLOSED"
                emoji = "🟢" if data["state"] else "🔴"
                
                st.write(f"**{tag}**")
                st.write(f"Status: {emoji} {status}")
                st.write(f"Position: ({data['x']}, {data['y']})")
                
                # Toggle button
                if st.button(f"Toggle {tag}", key=f"toggle_{tag}"):
                    st.session_state.valves[tag]["state"] = not st.session_state.valves[tag]["state"]
                    save_valves(st.session_state.valves)
                    st.rerun()
else:
    st.info("No valves configured. Use the section below to add valves.")

# Valve management section (only show when unlocked)
if not st.session_state.positions_locked:
    st.markdown("---")
    st.markdown("### Valve Management")
    
    col_add, col_edit = st.columns(2)
    
    with col_add:
        st.subheader("Add New Valve")
        with st.form("add_valve_form"):
            valve_tag = st.text_input("Valve Tag (e.g., V-101):")
            col_x, col_y = st.columns(2)
            with col_x:
                default_x = st.number_input("X Position", value=100, key="add_x")
            with col_y:
                default_y = st.number_input("Y Position", value=100, key="add_y")
            initial_state = st.selectbox("Initial State", ["Closed", "Open"])
            
            if st.form_submit_button("Add Valve"):
                if valve_tag and valve_tag.strip():
                    tag = valve_tag.strip().upper()
                    if tag in st.session_state.valves:
                        st.error(f"Valve {tag} already exists!")
                    else:
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
    
    with col_edit:
        st.subheader("Adjust Valve Positions")
        if st.session_state.valves:
            selected_valve = st.selectbox("Select valve:", list(st.session_state.valves.keys()))
            
            if selected_valve:
                data = st.session_state.valves[selected_valve]
                col_x, col_y = st.columns(2)
                
                with col_x:
                    new_x = st.number_input("X Position", value=data["x"], key="edit_x")
                with col_y:
                    new_y = st.number_input("Y Position", value=data["y"], key="edit_y")
                
                col_upd, col_del = st.columns(2)
                with col_upd:
                    if st.button("Update Position"):
                        st.session_state.valves[selected_valve]["x"] = int(new_x)
                        st.session_state.valves[selected_valve]["y"] = int(new_y)
                        save_valves(st.session_state.valves)
                        st.success(f"Updated position for {selected_valve}")
                        st.rerun()
                with col_del:
                    if st.button("Delete Valve"):
                        del st.session_state.valves[selected_valve]
                        save_valves(st.session_state.valves)
                        st.success(f"Deleted valve {selected_valve}")
                        st.rerun()
        else:
            st.info("No valves to edit")

# Current configuration display
st.markdown("---")
st.markdown("### Current Configuration")

if st.session_state.valves:
    st.json(st.session_state.valves)
    
    # Export configuration as file
    config_str = json.dumps(st.session_state.valves, indent=2)
    st.download_button(
        label="📥 Download Configuration",
        data=config_str,
        file_name="valve_configuration.json",
        mime="application/json"
    )
else:
    st.info("No valves configured")

# Instructions
with st.expander("📋 How to Use"):
    st.markdown("""
    **Setup Phase (Positions Unlocked):**
    1. Add valves using the tag names from your P&ID (e.g., V-101, V-201)
    2. Adjust X,Y positions to place valves accurately on the P&ID
    3. Set initial states (Open/Closed)
    4. Click **🔒 Lock Valve Positions** when done
    
    **Simulation Phase (Positions Locked):**
    1. Use toggle buttons to open/close valves
    2. Watch the P&ID update in real-time
    3. Valve positions are fixed - focus on process simulation
    
    **Data Management:**
    - Configuration is automatically saved to `valves.json`
    - Use **💾 Export Configuration** to force save
    - Download backup configuration file for safekeeping
    """)
