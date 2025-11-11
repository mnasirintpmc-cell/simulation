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
        
        # Define pipe segments - UPDATE THESE COORDINATES TO MATCH YOUR P&ID
        # You'll need to trace the actual pipe paths from your P&ID
        pipe_segments = {
            "supply_line": {
                "coords": [(50, 100, 150, 100)],  # From supply to V-101
                "connected_valves": ["V-101"],
                "requires": ["V-101"]  # Only flows if V-101 is open
            },
            "main_line_1": {
                "coords": [(150, 100, 250, 100), (250, 100, 250, 150)],  # V-101 to V-102
                "connected_valves": ["V-101", "V-102"],
                "requires": ["V-101", "V-102"]  # Both valves must be open
            },
            "main_line_2": {
                "coords": [(250, 150, 350, 150), (350, 150, 350, 200)],  # V-102 to V-103
                "connected_valves": ["V-102", "V-103"],
                "requires": ["V-101", "V-102", "V-103"]  # All valves in path must be open
            },
            "branch_line": {
                "coords": [(250, 100, 250, 50), (250, 50, 350, 50)],  # Branch from main line
                "connected_valves": ["V-104"],
                "requires": ["V-101", "V-104"]  # Supply + branch valve
            }
        }
        
        # Calculate flow for each pipe segment
        for pipe_id, pipe_data in pipe_segments.items():
            required_valves = pipe_data["requires"]
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
            draw.rectangle([x+15, y-15, x+80, y+5], fill=(0, 0, 0, 200))
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
    st.subheader("🌊 Flow Status")
    
    # Check if supply is open
    supply_open = st.session_state.valve_states.get("V-101", False)
    
    if supply_open:
        # Count how many paths have flow
        active_paths = 0
        if st.session_state.valve_states.get("V-102", False):
            active_paths += 1
        if st.session_state.valve_states.get("V-103", False):
            active_paths += 1
        if st.session_state.valve_states.get("V-104", False):
            active_paths += 1
            
        st.success(f"✅ Supply Active")
        st.metric("Active Paths", active_paths)
    else:
        st.error("❌ Supply Blocked")
        st.metric("Active Paths", 0)
    
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
    
    # Display flow status
    supply_state = st.session_state.valve_states.get("V-101", False)
    if supply_state:
        st.success("🌊 **System Status:** SUPPLY ACTIVE - Flow available")
    else:
        st.error("💧 **System Status:** SUPPLY BLOCKED - No flow possible")
    
    # Display the P&ID
    st.image(composite_img, use_container_width=True, caption="Interactive P&ID - Flow depends on V-101 (Supply Valve)")

with col2:
    # Right sidebar for detailed status
    st.header("🔍 Flow Analysis")
    st.markdown("---")
    
    # Flow path analysis
    st.subheader("Flow Paths")
    
    supply_open = st.session_state.valve_states.get("V-101", False)
    
    if supply_open:
        st.write("**Available Paths:**")
        
        if st.session_state.valve_states.get("V-102", False):
            if st.session_state.valve_states.get("V-103", False):
                st.success("✅ Main Line: V-101 → V-102 → V-103")
            else:
                st.warning("⚠️ Main Line: V-101 → V-102 (stopped at V-103)")
        else:
            st.error("❌ Main Line: Blocked at V-102")
            
        if st.session_state.valve_states.get("V-104", False):
            st.success("✅ Branch Line: V-101 → V-104")
        else:
            st.error("❌ Branch Line: Blocked at V-104")
    else:
        st.error("❌ All paths blocked - V-101 (Supply) is closed")

# Instructions with specific scenarios
st.markdown("---")
st.markdown("### 🎯 Test Scenarios")

scenario_col1, scenario_col2, scenario_col3 = st.columns(3)

with scenario_col1:
    st.markdown("**Scenario 1: Full Flow**")
    st.markdown("- Open: V-101, V-102, V-103, V-104")
    st.markdown("- Result: All pipes blue")
    if st.button("Apply Scenario 1", key="scenario1"):
        for tag in valves:
            st.session_state.valve_states[tag] = True
        st.rerun()

with scenario_col2:
    st.markdown("**Scenario 2: Supply Only**")
    st.markdown("- Open: V-101 only")
    st.markdown("- Close: V-102, V-103, V-104")
    st.markdown("- Result: Only supply pipe blue")
    if st.button("Apply Scenario 2", key="scenario2"):
        for tag in valves:
            st.session_state.valve_states[tag] = (tag == "V-101")
        st.rerun()

with scenario_col3:
    st.markdown("**Scenario 3: No Flow**")
    st.markdown("- Close: All valves")
    st.markdown("- Result: All pipes gray")
    if st.button("Apply Scenario 3", key="scenario3"):
        for tag in valves:
            st.session_state.valve_states[tag] = False
        st.rerun()
