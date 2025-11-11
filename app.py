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

def create_pid_with_flow():
    """Create P&ID image with valve indicators and flow animation"""
    try:
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
        
        # =====================================================
        # UPDATE THIS SECTION WITH YOUR ACTUAL PIPE COORDINATES
        # =====================================================
        pipe_segments = {
            # Section 1: V-101 to V-301
            "section_1": {
                "coords": [
                    (100, 200, 200, 200),  # Horizontal pipe from V-101 to midpoint
                    (200, 200, 200, 300)   # Vertical pipe down to V-301
                ],
                "flow_logic": ["V-101"]  # Only needs V-101 open to be active
            },
            # Section 2: V-301 to V-105
            "section_2": {
                "coords": [
                    (200, 300, 300, 300),  # Horizontal pipe from V-301 to V-105
                ],
                "flow_logic": ["V-101", "V-301"]  # Needs both V-101 AND V-301 open
            },
            # Section 3: V-105 to destination
            "section_3": {
                "coords": [
                    (300, 300, 400, 300),  # Horizontal pipe from V-105 onward
                ],
                "flow_logic": ["V-101", "V-301", "V-105"]  # Needs all three valves open
            },
            # Add more sections as needed...
        }
        
        # Calculate flow for each pipe segment based on your logic
        for pipe_id, pipe_data in pipe_segments.items():
            required_valves = pipe_data["flow_logic"]
            has_flow = True
            
            # Check if ALL required valves are open
            for valve_tag in required_valves:
                if valve_tag in st.session_state.valve_states:
                    if not st.session_state.valve_states[valve_tag]:
                        has_flow = False
                        break
                else:
                    has_flow = False  # Valve not found
            
            # Draw pipe segment with appropriate color
            if has_flow:
                pipe_color = (0, 100, 255)  # Bright blue for active flow
                pipe_width = 8
            else:
                pipe_color = (100, 100, 100)  # Gray for no flow
                pipe_width = 6
            
            for coord in pipe_data["coords"]:
                draw.line(coord, fill=pipe_color, width=pipe_width)
        
        # Draw valves on top of pipes
        for tag, data in valves.items():
            x, y = data["x"], data["y"]
            current_state = st.session_state.valve_states[tag]
            
            # Choose color based on valve state
            valve_color = (0, 255, 0) if current_state else (255, 0, 0)  # Green open, red closed
            
            # Draw valve indicator
            draw.ellipse([x-12, y-12, x+12, y+12], fill=valve_color, outline="white", width=3)
            
            # Draw valve tag with background for readability
            bbox = draw.textbbox((x+15, y-12), tag)
            text_width = bbox[2] - bbox[0] + 10
            draw.rectangle([x+15, y-15, x+15+text_width, y+3], fill=(0, 0, 0, 200))
            draw.text((x+18, y-12), tag, fill="white")
            
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
st.title("P&ID Interactive Simulation with Flow Animation")

if not valves:
    st.error("No valves found in valves.json. Please check your configuration.")
    st.stop()

# Create sidebar for valve controls
with st.sidebar:
    st.header("🎯 Valve Controls")
    st.markdown("---")
    
    # Valve toggle buttons in sidebar
    for tag, data in valves.items():
        current_state = st.session_state.valve_states[tag]
        
        # Create colored button based on state
        if current_state:
            button_label = f"🔴 {tag} - OPEN"
            button_type = "primary"
        else:
            button_label = f"🟢 {tag} - CLOSED" 
            button_type = "secondary"
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button(button_label, key=f"btn_{tag}", use_container_width=True, type=button_type):
                st.session_state.valve_states[tag] = not current_state
                st.rerun()
        with col2:
            status = "🟢" if current_state else "🔴"
            st.write(status)
    
    st.markdown("---")
    
    # Flow status summary
    st.subheader("🌊 Flow Analysis")
    
    # Check flow in each section based on your logic
    section_1_flow = st.session_state.valve_states.get("V-101", False)
    section_2_flow = section_1_flow and st.session_state.valve_states.get("V-301", False)
    section_3_flow = section_2_flow and st.session_state.valve_states.get("V-105", False)
    
    st.write("**Section Flow:**")
    st.write(f"{'✅' if section_1_flow else '❌'} Section 1 (V-101 to V-301)")
    st.write(f"{'✅' if section_2_flow else '❌'} Section 2 (V-301 to V-105)")
    st.write(f"{'✅' if section_3_flow else '❌'} Section 3 (V-105 onward)")
    
    st.markdown("---")
    
    # Quick actions
    st.subheader("⚡ Quick Actions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Open All", use_container_width=True):
            for tag in valves:
                st.session_state.valve_states[tag] = True
            st.rerun()
    with col2:
        if st.button("Close All", use_container_width=True):
            for tag in valves:
                st.session_state.valve_states[tag] = False
            st.rerun()

# Main content area - P&ID display with flow
col1, col2 = st.columns([3, 1])

with col1:
    # Create and display the P&ID with flow animation
    composite_img = create_pid_with_flow()
    
    # Display current flow state
    st.subheader("🌊 Current Flow State")
    
    if st.session_state.valve_states.get("V-101", False):
        st.success("✅ **Supply Active** - V-101 is OPEN")
        if st.session_state.valve_states.get("V-301", False):
            st.success("✅ **Section 1-2 Active** - Flow reaching V-105")
            if st.session_state.valve_states.get("V-105", False):
                st.success("✅ **Full Flow** - All sections active")
            else:
                st.warning("⚠️ **Flow Stopped** - V-105 is CLOSED")
        else:
            st.warning("⚠️ **Flow Limited** - V-301 is CLOSED, flow stops at Section 1")
    else:
        st.error("❌ **No Supply** - V-101 is CLOSED, no flow anywhere")
    
    # Display the P&ID
    st.image(composite_img, use_container_width=True, caption="Interactive P&ID - Flow follows your specific logic")

with col2:
    # Right sidebar for system info
    st.header("🔧 System Info")
    st.markdown("---")
    
    st.subheader("Flow Logic")
    st.markdown("""
    **Your Current Logic:**
    - Section 1: V-101 only
    - Section 2: V-101 + V-301  
    - Section 3: V-101 + V-301 + V-105
    """)
    
    st.markdown("---")
    st.subheader("Need Help?")
    st.markdown("""
    To make this work:
    1. Update pipe coordinates in code
    2. Adjust flow_logic for each section
    3. Add more sections as needed
    """)

# Configuration section for updating pipe coordinates
st.markdown("---")
st.markdown("### 🔧 Pipe Configuration Helper")

with st.expander("Click here to see your current valve positions and help configure pipes"):
    st.write("**Your Current Valve Positions from JSON:**")
    for tag, data in valves.items():
        st.write(f"- {tag}: Position ({data['x']}, {data['y']})")
    
    st.markdown("---")
    st.markdown("**To configure pipes, I need:**")
    st.markdown("1. **Pipe coordinates** for each section")
    st.markdown("2. **Flow logic** for each section (which valves control flow)")
    st.markdown("3. **Valve connections** (which valves connect to which pipes)")
    
    st.markdown("**Example format:**")
    st.code("""
    pipe_segments = {
        "section_1": {
            "coords": [(x1,y1,x2,y2), (x2,y2,x3,y3)],  # Pipe line coordinates
            "flow_logic": ["V-101"]  # Valves needed for flow
        },
        "section_2": {
            "coords": [(x3,y3,x4,y4)],
            "flow_logic": ["V-101", "V-301"]
        }
    }
    """)

# Tell me your actual flow scenarios!
st.markdown("---")
st.markdown("### 📝 Please Provide Your Flow Scenarios")

st.markdown("""
**Copy-paste this template and fill in your actual flow logic:**
