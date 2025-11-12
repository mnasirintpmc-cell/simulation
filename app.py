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

def create_pid_with_pipes():
    """Create P&ID display with pipes and valves"""
    try:
        # Try to load the actual P&ID image first
        try:
            pid_img = Image.open(PID_FILE).convert("RGBA")
        except:
            # If no P&ID image, create a white background
            pid_img = Image.new("RGBA", (1200, 800), (255, 255, 255, 255))
        
        draw = ImageDraw.Draw(pid_img)
        
        # Load data
        valves = load_valves()
        pipes = load_pipes()
        
        # Draw pipes with bright colors and thicker lines
        for pipe in pipes:
            x1, y1, x2, y2 = pipe["x1"], pipe["y1"], pipe["x2"], pipe["y2"]
            
            # Make pipes more visible - bright blue with thick lines
            pipe_color = (0, 0, 255)  # Bright blue
            pipe_width = 8  # Thicker lines
            
            draw.line([(x1, y1), (x2, y2)], fill=pipe_color, width=pipe_width)
        
        # Draw valves with bright colors
        for tag, data in valves.items():
            x, y = data["x"], data["y"]
            current_state = st.session_state.valve_states.get(tag, False)
            
            # Bright colors for valves
            valve_color = (0, 255, 0) if current_state else (255, 0, 0)  # Green/Red
            
            # Draw larger valve indicators
            draw.ellipse([x-15, y-15, x+15, y+15], fill=valve_color, outline="black", width=3)
            
            # Draw valve tag with background
            draw.text((x+18, y-12), tag, fill="black")
        
        return pid_img.convert("RGB")
    
    except Exception as e:
        st.error(f"Error creating display: {e}")
        return Image.new("RGB", (1200, 800), (255, 255, 255))

# Load valve data
valves = load_valves()
pipes = load_pipes()

# Initialize session state
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}

# Main app
st.title("P&ID Interactive Simulation")

# Debug info
st.write(f"**Loaded valves:** {len(valves)}")
st.write(f"**Loaded pipes:** {len(pipes)}")

if pipes:
    st.write("**First pipe coordinates:**", pipes[0])

# Display the P&ID with pipes
composite_img = create_pid_with_pipes()
st.image(composite_img, use_container_width=True, caption="P&ID with Pipes and Valves")

# Valve controls in sidebar
with st.sidebar:
    st.header("🎯 Valve Controls")
    st.markdown("---")
    
    for tag, data in valves.items():
        current_state = st.session_state.valve_states[tag]
        button_label = f"🔴 {tag} - OPEN" if current_state else f"🟢 {tag} - CLOSED"
        
        if st.button(button_label, key=f"btn_{tag}", use_container_width=True):
            st.session_state.valve_states[tag] = not current_state
            st.rerun()

# Quick actions
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    if st.button("Open All Valves"):
        for tag in valves:
            st.session_state.valve_states[tag] = True
        st.rerun()
with col2:
    if st.button("Close All Valves"):
        for tag in valves:
            st.session_state.valve_states[tag] = False
        st.rerun()

# Debug information
with st.expander("🔧 Debug Information"):
    st.write("**Valves:**", valves)
    st.write("**Pipes:**", pipes)
    st.write("**Valve States:**", st.session_state.valve_states)
