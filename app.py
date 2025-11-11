import streamlit as st
import json
from PIL import Image, ImageDraw
import os

st.set_page_config(layout="wide")

# Configuration
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"

def save_valves(valves_data):
    with open(DATA_FILE, "w") as f:
        json.dump(valves_data, f, indent=4)

def load_valves():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

# Load valve data
if "valves" not in st.session_state:
    st.session_state.valves = load_valves()

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
        try:
            return Image.open(PID_FILE).convert("RGB")
        except:
            return Image.new("RGB", (800, 600), (255, 255, 255))

# Main app
st.title("P&ID Interactive Simulation")
st.markdown("### Valve Controls")

# Display the P&ID with valves
composite_img = create_pid_with_valves()
st.image(composite_img, use_column_width=True, caption="Interactive P&ID - Click buttons below to toggle valves")

# Valve toggle buttons
st.markdown("### Toggle Valves")

if st.session_state.valves:
    # Create columns for valve buttons
    valves_list = list(st.session_state.valves.items())
    num_cols = min(4, len(valves_list))
    columns = st.columns(num_cols)
    
    for i, (tag, data) in enumerate(valves_list):
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
    st.info("No valves configured in valves.json")

# Current status display
st.markdown("---")
st.markdown("### Current Valve Status")
for tag, data in st.session_state.valves.items():
    status = "🟢 OPEN" if data["state"] else "🔴 CLOSED"
    st.write(f"**{tag}**: {status} at position ({data['x']}, {data['y']})")

# Save button
if st.button("💾 Save Configuration"):
    save_valves(st.session_state.valves)
    st.success("Configuration saved!")
