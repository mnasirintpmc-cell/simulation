import streamlit as st
import json
from PIL import Image, ImageDraw
import os
import time

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
        
        # Define pipe segments (you'll need to adjust these coordinates based on your P&ID)
        # Format: {pipe_id: [(x1,y1,x2,y2), ...], connected_valves: [valve1, valve2]}
        pipe_segments = {
            "main_line_1": {
                "coords": [(50, 100, 200, 100), (200, 100, 200, 150), (200, 150, 300, 150)],
                "connected_valves": ["V-101", "V-102"]
            },
            "main_line_2": {
                "coords": [(300, 150, 400, 150), (400, 150, 400, 200), (400, 200, 500, 200)],
                "connected_valves": ["V-102", "V-103"]
            },
            "branch_line_1": {
                "coords": [(200, 100, 200, 50), (200, 50, 300, 50)],
                "connected_valves": ["V-104"]
            }
        }
        
        # Calculate flow for each pipe segment
        for pipe_id, pipe_data in pipe_segments.items():
            connected_valves = pipe_data["connected_valves"]
            has_flow = True
            
            # Check if all connected valves are open for flow to pass
            for valve_tag in connected_valves:
                if valve_tag in st.session_state.valve_states:
                    if not st.session_state.valve_states[valve_tag]:
                        has_flow = False
                        break
            
            # Draw pipe segment with appropriate color
            pipe_color = (0, 100, 255, 200) if has_flow else (100, 100, 100, 150)  # Blue for flow, gray for no flow
            pipe_width = 6 if has_flow else 4
            
            for coord in pipe_data["coords"]:
                draw.line(coord, fill=pipe_color, width=pipe_width)
        
        # Draw valves on top of pipes
        for tag, data in valves.items():
            x, y = data["x"], data["y"]
            current_state = st.session_state.valve_states[tag]
            
            # Choose color based on valve state
            valve_color = (0, 255, 0, 255) if current_state else (255, 0, 0, 255)  # Green open, red closed
            
            # Draw valve indicator
            draw.ellipse([x-10, y-10, x+10, y+10], fill=valve_color, outline="white", width=3)
            draw.text((x+12, y-8), tag, fill="white", stroke_fill="black", stroke_width=2)
            
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

# Initialize animation state
if "animation_frame" not in st.session_state:
    st.session_state.animation_frame = 0

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
                st.session_state.animation_frame = (st.session_state.animation_frame + 1) % 10
                st.rerun()
        with col2:
            status = "🟢" if current_state else "🔴"
            st.write(status)
    
    st.markdown("---")
    
    # Flow status summary
    st.subheader("🌊 Flow Status")
    flowing_pipes = 0
    total_pipes = 3  # Adjust based on your pipe segments
    
    # Calculate flow status (simplified)
    open_valves = sum(1 for state in st.session_state.valve_states.values() if state)
    if open_valves >= 2:  # Simple logic - adjust based on your P&ID
        flowing_pipes = 2
    elif open_valves >= 1:
        flowing_pipes = 1
    
    st.metric("Flowing Pipes", f"{flowing_pipes}/{total_pipes}")
    st.progress(flowing_pipes / total_pipes)
    
    st.markdown("---")
    
    # Quick actions
    st.subheader("⚡ Quick Actions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Open All", use_container_width=True):
            for tag in valves:
                st.session_state.valve_states[tag] = True
            st.session_state.animation_frame = (st.session_state.animation_frame + 1) % 10
            st.rerun()
    with col2:
        if st.button("Close All", use_container_width=True):
            for tag in valves:
                st.session_state.valve_states[tag] = False
            st.session_state.animation_frame = (st.session_state.animation_frame + 1) % 10
            st.rerun()

# Main content area - P&ID display with flow
col1, col2 = st.columns([3, 1])

with col1:
    # Create and display the P&ID with flow animation
    composite_img = create_pid_with_flow()
    
    # Add animation indicator
    st.markdown(f"**Flow Status:** {'🌊 Flow Active' if any(st.session_state.valve_states.values()) else '💧 No Flow'}")
    
    # Display the animated P&ID
    st.image(composite_img, use_container_width=True, caption="Interactive P&ID - Blue pipes show active flow")
    
    # Auto-refresh for animation (optional)
    if st.checkbox("Auto-refresh flow display", value=True):
        time.sleep(0.5)
        st.session_state.animation_frame = (st.session_state.animation_frame + 1) % 10
        st.rerun()

with col2:
    # Right sidebar for detailed status
    st.header("🔍 System Status")
    st.markdown("---")
    
    # Flow direction indicators
    st.subheader("Flow Directions")
    if st.session_state.valve_states.get("V-101", False) and st.session_state.valve_states.get("V-102", False):
        st.success("✅ Main Line Flow")
    else:
        st.error("❌ Main Line Blocked")
        
    if st.session_state.valve_states.get("V-103", False):
        st.success("✅ Branch Line Flow")
    else:
        st.error("❌ Branch Line Blocked")
    
    st.markdown("---")
    
    # Valve details
    st.subheader("Valve Details")
    for tag, data in valves.items():
        current_state = st.session_state.valve_states[tag]
        status = "🟢 OPEN" if current_state else "🔴 CLOSED"
        
        with st.expander(f"{tag} - {status}", expanded=False):
            st.write(f"**Position:** ({data['x']}, {data['y']})")
            st.write(f"**Impact:** {'Allows flow' if current_state else 'Blocks flow'}")
            
            # Mini toggle inside expander
            if st.button(f"Toggle {tag}", key=f"mini_{tag}", use_container_width=True):
                st.session_state.valve_states[tag] = not current_state
                st.session_state.animation_frame = (st.session_state.animation_frame + 1) % 10
                st.rerun()

# Bottom section for flow legend and instructions
st.markdown("---")
st.markdown("### 🌊 Flow Legend & Instructions")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Pipe Colors:**")
    st.markdown("- 🔵 **Blue** = Active Flow")
    st.markdown("- ⚫ **Gray** = No Flow")
    st.markdown("- 🟢 **Green Circle** = Valve OPEN")
    st.markdown("- 🔴 **Red Circle** = Valve CLOSED")

with col2:
    st.markdown("**Flow Logic:**")
    st.markdown("- Flow requires OPEN valves")
    st.markdown("- Closed valves block flow")
    st.markdown("- Multiple valves control complex paths")
    st.markdown("- Real-time visual feedback")

with col3:
    st.markdown("**Try These:**")
    st.markdown("- Open V-101 & V-102 for main flow")
    st.markdown("- Close V-102 to see flow stop")
    st.markdown("- Experiment with different combinations")

# Debug information
with st.expander("🔧 System Configuration"):
    st.write("**Valve States:**")
    for tag, state in st.session_state.valve_states.items():
        st.write(f"- {tag}: {'OPEN' if state else 'CLOSED'}")
    
    st.write("**Animation Frame:**", st.session_state.animation_frame)
