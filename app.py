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

def create_pid_with_valves():
    """Create P&ID image with valve indicators"""
    try:
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
        
        for tag, data in valves.items():
            x, y = data["x"], data["y"]
            current_state = st.session_state.valve_states[tag]
            
            # Choose color based on valve state
            color = (0, 255, 0) if current_state else (255, 0, 0)
            
            # Draw valve indicator
            draw.ellipse([x-8, y-8, x+8, y+8], fill=color, outline="white", width=2)
            draw.text((x+12, y-10), tag, fill="white", stroke_fill="black", stroke_width=1)
            
        return pid_img.convert("RGB")
    except Exception as e:
        st.error(f"Error creating P&ID image: {e}")
        try:
            return Image.open(PID_FILE).convert("RGB")
        except:
            return Image.new("RGB", (800, 600), (255, 255, 255))

# Load valve data
valves = load_valves()

# Initialize session state for current states
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}

# Main app
st.title("P&ID Interactive Simulation")

if valves:
    # Create CSS for absolute positioning of toggle buttons
    css_styles = ""
    for tag, data in valves.items():
        x, y = data["x"], data["y"]
        # Position buttons 70px above the valve indicators
        button_y = y - 70
        css_styles += f"""
        div[data-testid="column"]:has(button[key="{tag}"]) {{
            position: absolute !important;
            left: {x}px !important;
            top: {button_y}px !important;
            transform: translateX(-50%) !important;
            z-index: 1000 !important;
            width: auto !important;
        }}
        """
    
    st.markdown(f"""
    <style>
    .stApp {{
        position: relative;
    }}
    {css_styles}
    </style>
    """, unsafe_allow_html=True)
    
    # Display the P&ID with valve indicators
    composite_img = create_pid_with_valves()
    st.image(composite_img, use_column_width=True, caption="Interactive P&ID - Click buttons above valves to toggle")
    
    # Create toggle buttons at shifted positions
    for tag, data in valves.items():
        current_state = st.session_state.valve_states[tag]
        button_text = f"🔴 {tag} (OPEN)" if current_state else f"🟢 {tag} (CLOSED)"
        
        # Create columns to hold the buttons (positioned via CSS)
        col = st.columns(1)[0]
        with col:
            if st.button(button_text, key=tag, use_container_width=True):
                st.session_state.valve_states[tag] = not current_state
                st.rerun()

else:
    st.error("No valves found in valves.json")

# Show current status
st.markdown("---")
st.markdown("### Current Valve Status:")
if valves:
    cols = st.columns(3)
    for i, (tag, data) in enumerate(valves.items()):
        col_idx = i % 3
        with cols[col_idx]:
            current_state = st.session_state.valve_states[tag]
            status = "🟢 OPEN" if current_state else "🔴 CLOSED"
            st.write(f"**{tag}**: {status}")
            st.write(f"Position: ({data['x']}, {data['y']})")

# Instructions
st.markdown("---")
st.markdown("### Instructions:")
st.markdown("""
- **Green circle** = Valve is OPEN
- **Red circle** = Valve is CLOSED  
- Click the toggle buttons **above each valve** to change its state
- Valve positions are fixed from your JSON file
- Changes are temporary (not saved to JSON file)
""")

# Debug info
with st.expander("Debug Information"):
    st.write("Valves data:", valves)
    st.write("Current states:", st.session_state.valve_states)
