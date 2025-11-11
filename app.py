import streamlit as st
import json
from PIL import Image, ImageDraw
import os
import base64

st.set_page_config(layout="wide")

# Configuration
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"

def load_valves():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def create_pid_with_buttons():
    """Create P&ID image with valve status indicators"""
    try:
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
        
        for tag, data in valves.items():
            x, y = data["x"], data["y"]
            current_state = st.session_state.valve_states[tag]
            
            # Choose color based on valve state
            color = (0, 255, 0) if current_state else (255, 0, 0)  # Green if open, red if closed
            
            # Draw valve marker
            draw.ellipse([x-10, y-10, x+10, y+10], fill=color, outline="white", width=3)
            
        return pid_img.convert("RGB")
    except Exception as e:
        st.error(f"Error creating P&ID image: {e}")
        return None

# Load valve data
valves = load_valves()

# Initialize session state
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}

# Main app
st.title("P&ID Interactive Simulation")

if valves:
    # Create interactive P&ID
    st.markdown("### Click on valve areas to toggle:")
    
    # Create the P&ID with valve indicators
    pid_img = create_pid_with_buttons()
    if pid_img:
        # Display the image
        st.image(pid_img, use_column_width=True)
        
        # Create invisible buttons over valve positions using columns
        st.markdown("### Valve Controls (click to toggle):")
        
        # Create a grid of buttons positioned relative to valves
        cols = st.columns(4)
        valve_list = list(valves.items())
        
        for i, (tag, data) in enumerate(valve_list):
            col_idx = i % 4
            with cols[col_idx]:
                current_state = st.session_state.valve_states[tag]
                button_text = f"🔴 {tag} (OPEN)" if current_state else f"🟢 {tag} (CLOSED)"
                
                if st.button(button_text, key=f"control_{tag}", use_container_width=True):
                    st.session_state.valve_states[tag] = not current_state
                    st.rerun()
        
        # Show current status
        st.markdown("---")
        st.markdown("### Current Status:")
        status_cols = st.columns(3)
        for i, (tag, data) in enumerate(valve_list):
            col_idx = i % 3
            with status_cols[col_idx]:
                current_state = st.session_state.valve_states[tag]
                status = "🟢 OPEN" if current_state else "🔴 CLOSED"
                st.write(f"**{tag}**: {status}")

else:
    st.error("No valves found in valves.json")

st.markdown("---")
st.markdown("**Note**: Valve positions are fixed from your JSON file. Changes are temporary.")
