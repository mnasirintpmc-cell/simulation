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
            draw.ellipse([x-8, y-8, x+8, x+8], fill=color, outline="white", width=2)
            
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

# Interactive valve controls ON THE P&ID
st.markdown("---")
st.markdown("### Quick Valve Controls")

if st.session_state.valves:
    # Create a grid of toggle buttons - 4 columns
    valve_list = list(st.session_state.valves.items())
    
    # Calculate how many rows we need
    num_columns = 4
    num_valves = len(valve_list)
    num_rows = (num_valves + num_columns - 1) // num_columns
    
    # Create toggle buttons in a grid
    for row in range(num_rows):
        cols = st.columns(num_columns)
        for col_idx in range(num_columns):
            valve_index = row * num_columns + col_idx
            if valve_index < num_valves:
                tag, data = valve_list[valve_index]
                with cols[col_idx]:
                    status = "OPEN" if data["state"] else "CLOSED"
                    button_text = f"🔴 Close {tag}" if data["state"] else f"🟢 Open {tag}"
                    
                    if st.button(button_text, key=f"quick_toggle_{tag}", use_container_width=True):
                        st.session_state.valves[tag]["state"] = not st.session_state.valves[tag]["state"]
                        save_valves(st.session_state.valves)
                        st.rerun()
                    
                    # Show current position
                    st.caption(f"Position: ({data['x']}, {data['y']})")
else:
    st.info("No valves configured. Use the section below to add valves.")

# Individual valve control cards
if st.session_state.valves:
    st.markdown("---")
    st.markdown("### Individual Valve Control Panels")
    
    # Create columns for valve cards
    num_valves = len(st.session_state.valves)
    num_columns = min(3, num_valves)  # Max 3 columns for better layout
    
    if num_columns > 0:
        valve_columns = st.columns(num_columns)
        
        for i, (tag, data) in enumerate(st.session_state.valves.items()):
            col_idx = i % num_columns
            with valve_columns[col_idx]:
                # Create a card-like container
                with st.container():
                    status = "OPEN" if data["state"] else "CLOSED"
                    emoji = "🟢" if data["state"] else "🔴"
                    button_color = "secondary" if data["state"] else "primary"
                    
                    st.markdown(f"#### {tag}")
                    st.markdown(f"**Status:** {emoji} {status}")
                    st.markdown(f"**Position:** ({data['x']}, {data['y']})")
                    
                    # Toggle button with different styles
                    col_on, col_off = st.columns(2)
                    with col_on:
                        if st.button(f"🟢 Open", key=f"open_{tag}", use_container_width=True, 
                                   disabled=data["state"]):
                            st.session_state.valves[tag]["state"] = True
                            save_valves(st.session_state.valves)
                            st.rerun()
                    
                    with col_off:
                        if st.button(f"🔴 Close", key=f"close_{tag}", use_container_width=True,
                                   disabled=not data["state"]):
                            st.session_state.valves[tag]["state"] = False
                            save_valves(st.session_state.valves)
                            st.rerun()
                    
                    # Single toggle button alternative
                    if st.button(f"🔄 Toggle {tag}", key=f"toggle_{tag}", use_container_width=True):
                        st.session_state.valves[tag]["state"] = not st.session_state.valves[tag]["state"]
                        save_valves(st.session_state.valves)
                        st.rerun()
                    
                    st.markdown("---")

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
    # Summary table
    st.subheader("Valve Status Summary")
    summary_data = []
    for tag, data in st.session_state.valves.items():
        summary_data.append({
            "Valve Tag": tag,
            "Status": "OPEN" if data["state"] else "CLOSED",
            "Position": f"({data['x']}, {data['y']})"
        })
    
    st.table(summary_data)
    
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
    **Valve Control Options:**
    
    1. **Quick Toggle Grid**: Use the grid of colored buttons for fast operation
    2. **Individual Control Panels**: Each valve has its own control card with Open/Close buttons
    3. **Visual Feedback**: Valves show as 🟢 Green (OPEN) or 🔴 Red (CLOSED) on the P&ID
    
    **Setup Phase (Positions Unlocked):**
    - Add and position valves using the management section
    - Lock positions when ready for simulation
    
    **Simulation Phase (Positions Locked):**
    - Use any of the toggle buttons to control valves
    - Watch the P&ID update in real-time
    - All changes are automatically saved
    """)
