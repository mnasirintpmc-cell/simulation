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

def save_pipes(pipes_data):
    with open(PIPES_DATA_FILE, "w") as f:
        json.dump(pipes_data, f, indent=2)

def get_image_dimensions():
    """Get the dimensions of the P&ID image"""
    try:
        with Image.open(PID_FILE) as img:
            return img.size
    except:
        return (1200, 800)  # Default fallback

def get_pipe_groups_with_leaders():
    """Define mechanical pipe connections with leading pipes"""
    return {
        "Group_1": {
            "leader": 1,           # Pipe 1 is the leader
            "followers": [20]      # Pipe 20 follows Pipe 1
        },
        "Group_2": {
            "leader": 11,          # Pipe 11 is the leader  
            "followers": [10, 19]  # Pipe 11 leads 10 and 19
        },
        "Group_3": {
            "leader": 2,           # Pipe 2 is the leader
            "followers": [3, 4, 14, 21, 22]  # Pipe 2 leads 3,4,14,21,22
        },
        "Group_4": {
            "leader": 13,          # Pipe 13 is the leader
            "followers": [14, 4, 21, 22]  # Pipe 13 leads 14,4,21,22
        },
        "Group_5": {
            "leader": 5,           # Pipe 5 is the leader
            "followers": [6, 7, 8, 9, 18]  # Pipe 5 leads 6,7,8,9,18
        },
        "Group_6": {
            "leader": 17,          # Pipe 17 is the leader
            "followers": [16, 15, 8]  # Pipe 17 leads 16,15,8
        }
    }

def get_valve_to_leader_mapping():
    """Define which valves control which leader pipes"""
    return {
        "V-301": 2,   # V-301 controls Pipe 2 (leader)
        "V-302": 13   # V-302 controls Pipe 13 (leader)
    }

def get_leading_pipe_color(leader_pipe_index, valves, valve_states):
    """Get the color for the leading pipe based on valve control"""
    leader_pipe_number = leader_pipe_index + 1
    
    # Check if this leader pipe is controlled by a specific valve
    valve_mapping = get_valve_to_leader_mapping()
    for valve_tag, controlled_leader in valve_mapping.items():
        if leader_pipe_number == controlled_leader:
            # This leader is controlled by a specific valve
            if valve_states.get(valve_tag, False):
                return (0, 255, 0)  # Green if controlling valve is open
            else:
                return (0, 0, 255)  # Blue if controlling valve is closed
    
    # Normal proximity-based logic for other pipes
    leader_pipe = st.session_state.pipes[leader_pipe_index]
    x1, y1 = leader_pipe["x1"], leader_pipe["y1"]
    valve_proximity_threshold = 20
    
    for tag, valve_data in valves.items():
        valve_x, valve_y = valve_data["x"], valve_data["y"]
        distance = ((valve_x - x1)**2 + (valve_y - y1)**2)**0.5
        
        if distance <= valve_proximity_threshold:
            if valve_states[tag]:
                return (0, 255, 0)  # Green if valve open
            else:
                return (0, 0, 255)  # Blue if valve closed
    
    return (0, 0, 255)  # Default to blue if no valve found

def get_pipe_color_based_on_leader_system(pipe_index, valves, valve_states):
    """Determine pipe color based on leading pipe system"""
    pipe_number = pipe_index + 1
    
    # Get pipe groups with leaders
    pipe_groups = get_pipe_groups_with_leaders()
    
    # Check if this pipe is a leader in any group
    for group_name, group_data in pipe_groups.items():
        if pipe_number == group_data["leader"]:
            # This pipe is a leader - get its color from valve control
            return get_leading_pipe_color(pipe_index, valves, valve_states)
    
    # Check if this pipe is a follower in any group
    for group_name, group_data in pipe_groups.items():
        if pipe_number in group_data["followers"]:
            # This pipe is a follower - find its leader and get the leader's color
            leader_pipe_number = group_data["leader"]
            leader_pipe_index = leader_pipe_number - 1  # Convert to 0-indexed
            
            if leader_pipe_index < len(st.session_state.pipes):
                return get_leading_pipe_color(leader_pipe_index, valves, valve_states)
    
    # If pipe doesn't belong to any group, use proximity-based logic
    return get_pipe_color_based_on_proximity(pipe_index, valves, valve_states)

def get_pipe_color_based_on_proximity(pipe_index, valves, valve_states):
    """Determine pipe color based on valve proximity"""
    pipe = st.session_state.pipes[pipe_index]
    
    # Check if any valve is near the pipe start
    x1, y1 = pipe["x1"], pipe["y1"]
    valve_proximity_threshold = 20
    
    for tag, valve_data in valves.items():
        valve_x, valve_y = valve_data["x"], valve_data["y"]
        distance = ((valve_x - x1)**2 + (valve_y - y1)**2)**0.5
        
        if distance <= valve_proximity_threshold and valve_states[tag]:
            return (0, 255, 0)  # Green for active flow
    
    return (0, 0, 255)  # Blue for no flow

def create_pid_with_valves_and_pipes():
    """Create P&ID image with valve indicators AND pipes - PRESERVING EXACT SCALE"""
    try:
        # Open the original P&ID image without any resizing
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
        
        # Draw pipes FIRST using exact coordinates from JSON
        if st.session_state.pipes:
            for i, pipe in enumerate(st.session_state.pipes):
                # Use exact coordinates from JSON - no scaling or modification
                x1, y1, x2, y2 = pipe["x1"], pipe["y1"], pipe["x2"], pipe["y2"]
                
                # Get pipe color based on leader system
                color = get_pipe_color_based_on_leader_system(i, valves, st.session_state.valve_states)
                
                # If this pipe is selected, make it purple regardless of valve state
                if i == st.session_state.selected_pipe:
                    color = (148, 0, 211)  # Purple for selected pipe
                    width = 8
                else:
                    width = 6
                    
                # Draw the pipe with exact coordinates
                draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
                
                # Draw endpoints for selected pipe
                if i == st.session_state.selected_pipe:
                    draw.ellipse([x1-6, y1-6, x1+6, y1+6], fill=(255, 0, 0), outline="white", width=2)
                    draw.ellipse([x2-6, y2-6, x2+6, y2+6], fill=(255, 0, 0), outline="white", width=2)
        
        # Draw valves on top of pipes using exact coordinates from JSON
        for tag, data in valves.items():
            x, y = data["x"], data["y"]
            current_state = st.session_state.valve_states[tag]
            
            # Choose color based on valve state
            color = (0, 255, 0) if current_state else (255, 0, 0)
            
            # Draw valve indicator at exact coordinates
            draw.ellipse([x-8, y-8, x+8, y+8], fill=color, outline="white", width=2)
            draw.text((x+12, y-10), tag, fill="white", stroke_fill="black", stroke_width=1)
            
        return pid_img.convert("RGB")
    except Exception as e:
        st.error(f"Error creating P&ID image: {e}")
        try:
            return Image.open(PID_FILE).convert("RGB")
        except:
            return Image.new("RGB", (1200, 800), (255, 255, 255))

# Load valve data from JSON
valves = load_valves()
pipes = load_pipes()

# Initialize session state
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}

if "selected_pipe" not in st.session_state:
    st.session_state.selected_pipe = None

if "pipes" not in st.session_state:
    st.session_state.pipes = pipes

# Main app
st.title("P&ID Interactive Simulation")

if not valves:
    st.error("No valves found in valves.json. Please check your configuration.")
    st.stop()

if not pipes:
    st.error("No pipes found in pipes.json. Please check your configuration.")
    st.stop()

# Create sidebar for valve controls AND pipe selection
with st.sidebar:
    st.header("🎯 Valve Controls")
    st.markdown("---")
    
    # Valve toggle buttons in sidebar
    for tag, data in valves.items():
        current_state = st.session_state.valve_states[tag]
        
        button_label = f"🔴 {tag} - OPEN" if current_state else f"🟢 {tag} - CLOSED"
        
        if st.button(button_label, key=f"btn_{tag}", use_container_width=True):
            st.session_state.valve_states[tag] = not current_state
            st.rerun()
    
    st.markdown("---")
    st.header("📋 Pipe Selection")
    st.markdown("Click on a pipe to highlight it")
    
    # UNSELECT ALL PIPES BUTTON
    if st.button("🚫 Unselect All Pipes", use_container_width=True, type="secondary"):
        st.session_state.selected_pipe = None
        st.rerun()
    
    # Pipe selection buttons
    if st.session_state.pipes:
        for i in range(len(st.session_state.pipes)):
            is_selected = st.session_state.selected_pipe == i
            pipe = st.session_state.pipes[i]
            
            status_icon = "🟣" if is_selected else "🔵"
            label = f"{status_icon} Pipe {i+1}" 
            
            if st.button(label, key=f"pipe_{i}", use_container_width=True):
                st.session_state.selected_pipe = i
                st.rerun()

# Main content area - P&ID display
col1, col2 = st.columns([3, 1])
with col1:
    # Create and display the P&ID with valve indicators AND pipes
    composite_img = create_pid_with_valves_and_pipes()
    
    # Show selection status
    if st.session_state.selected_pipe is not None:
        caption = f"🟣 Pipe {st.session_state.selected_pipe + 1} Selected | 🟢 Green = Flow Active | 🔵 Blue = No Flow"
    else:
        caption = "🟢 Green = Flow Active | 🔵 Blue = No Flow (No pipe selected)"
    
    st.image(composite_img, use_container_width=True, caption=caption)

with col2:
    # Right sidebar for detailed status
    st.header("🔍 Flow Status")
    st.markdown("---")
    
    # Show valve status and pipe flow information
    st.subheader("📊 System Status")
    
    # Count pipes with active flow
    active_pipes = 0
    for i, pipe in enumerate(st.session_state.pipes):
        color = get_pipe_color_based_on_leader_system(i, valves, st.session_state.valve_states)
        if color == (0, 255, 0):
            active_pipes += 1
    
    st.write(f"**Active Flow Pipes:** {active_pipes}")
    st.write(f"**No Flow Pipes:** {len(st.session_state.pipes) - active_pipes}")
    
    # Show valve status summary
    open_valves = sum(1 for state in st.session_state.valve_states.values() if state)
    closed_valves = len(valves) - open_valves
    st.write(f"**Open Valves:** {open_valves}")
    st.write(f"**Closed Valves:** {closed_valves}")
    
    # Show pipe groups with leaders
    st.markdown("---")
    st.subheader("👑 Leader-Follower System")
    
    pipe_groups = get_pipe_groups_with_leaders()
    for group_name, group_data in pipe_groups.items():
        leader_pipe = group_data["leader"]
        followers = group_data["followers"]
        
        # Get leader pipe color
        leader_color = get_pipe_color_based_on_leader_system(leader_pipe-1, valves, st.session_state.valve_states)
        leader_status = "🟢 ACTIVE" if leader_color == (0, 255, 0) else "🔵 INACTIVE"
        
        st.write(f"**{group_name}:**")
        st.write(f"👑 Leader: Pipe {leader_pipe} ({leader_status})")
        st.write(f"📋 Followers: Pipes {followers}")
        st.write("---")
    
    # Show valve control mapping
    st.markdown("---")
    st.subheader("🔗 Valve Control Mapping")
    
    valve_mapping = get_valve_to_leader_mapping()
    for valve_tag, controlled_leader in valve_mapping.items():
        valve_state = st.session_state.valve_states.get(valve_tag, False)
        
        status_icon = "🟢" if valve_state else "🔵"
        status_text = "ACTIVE" if valve_state else "INACTIVE"
        
        # Get the followers of this leader
        followers = []
        pipe_groups = get_pipe_groups_with_leaders()
        for group_name, group_data in pipe_groups.items():
            if group_data["leader"] == controlled_leader:
                followers = group_data["followers"]
                break
        
        st.write(f"{status_icon} **{valve_tag}** → **Pipe {controlled_leader}**")
        st.write(f"Controls: Pipes {[controlled_leader] + followers}")
        st.write(f"Status: {status_text}")
        st.write("---")
    
    # Show selected pipe info
    if st.session_state.selected_pipe is not None:
        st.markdown("---")
        st.subheader(f"🟣 Selected Pipe {st.session_state.selected_pipe + 1}")
        pipe = st.session_state.pipes[st.session_state.selected_pipe]
        
        # Check if this pipe is a leader or follower
        pipe_number = st.session_state.selected_pipe + 1
        pipe_groups = get_pipe_groups_with_leaders()
        
        is_leader = False
        is_follower = False
        leader_of_group = None
        follower_in_group = None
        
        for group_name, group_data in pipe_groups.items():
            if pipe_number == group_data["leader"]:
                is_leader = True
                leader_of_group = group_name
            elif pipe_number in group_data["followers"]:
                is_follower = True
                follower_in_group = group_name
        
        if is_leader:
            st.write(f"**Role:** 👑 LEADER of {leader_of_group}")
            st.write(f"**Controls:** Pipes {pipe_groups[leader_of_group]['followers']}")
            
            # Check if this leader is controlled by a specific valve
            valve_mapping = get_valve_to_leader_mapping()
            for valve_tag, controlled_leader in valve_mapping.items():
                if pipe_number == controlled_leader:
                    valve_state = st.session_state.valve_states.get(valve_tag, False)
                    status = "OPEN" if valve_state else "CLOSED"
                    st.write(f"**Controlled by:** {valve_tag} ({status})")
                    
        elif is_follower:
            st.write(f"**Role:** 📋 FOLLOWER in {follower_in_group}")
            leader_pipe = pipe_groups[follower_in_group]["leader"]
            st.write(f"**Follows:** Pipe {leader_pipe}")
        else:
            st.write(f"**Role:** 🚀 Standalone Pipe")
        
        # Check flow status
        color = get_pipe_color_based_on_leader_system(st.session_state.selected_pipe, valves, st.session_state.valve_states)
        flow_status = "🟢 ACTIVE FLOW" if color == (0, 255, 0) else "🔵 NO FLOW"
        st.write(f"**Flow Status:** {flow_status}")
        
    else:
        st.markdown("---")
        st.subheader("ℹ️ No Pipe Selected")
        st.info("Click on a pipe in the sidebar to select and inspect it")
    
    st.markdown("---")
    st.subheader("🔧 How It Works")
    st.markdown("""
    **Leader-Follower Rules:**
    - **Pipe 1** → **Pipe 20**
    - **Pipe 11** → **Pipes 10, 19**
    - **Pipe 2** → **Pipes 3,4,14,21,22** (controlled by V-301)
    - **Pipe 13** → **Pipes 14,4,21,22** (controlled by V-302)
    - **Pipe 5** → **Pipes 6,7,8,9,18**
    - **Pipe 17** → **Pipes 16,15,8**
    
    **Valve Control:**
    - **V-301** → **Pipe 2** → Activates Pipes 3,4,14,21,22
    - **V-302** → **Pipe 13** → Activates Pipes 14,4,21,22
    
    **Color Coding:**
    - 🟢 **GREEN** = Active Flow
    - 🔵 **BLUE** = No Flow
    - 🟣 **PURPLE** = Selected Pipe
    - 🔴 **RED** = Closed Valve
    - 🟢 **GREEN** = Open Valve
    """)

# Debug information
with st.expander("🔧 Debug Information"):
    st.write("**Image Dimensions:**", get_image_dimensions())
    
    # Show current valve states
    st.subheader("Current Valve States")
    for tag, state in st.session_state.valve_states.items():
        status = "OPEN" if state else "CLOSED"
        color = "🟢" if state else "🔴"
        st.write(f"{color} {tag}: {status}")
    
    # Show pipe information with roles
    st.subheader("Pipe Roles & Colors")
    pipe_groups = get_pipe_groups_with_leaders()
    valve_mapping = get_valve_to_leader_mapping()
    
    for i in range(len(st.session_state.pipes)):
        pipe_number = i + 1
        color = get_pipe_color_based_on_leader_system(i, valves, st.session_state.valve_states)
        color_name = "GREEN" if color == (0, 255, 0) else "BLUE"
        
        # Determine role
        role = "Standalone"
        for group_name, group_data in pipe_groups.items():
            if pipe_number == group_data["leader"]:
                role = f"Leader of {group_name}"
                # Check if controlled by valve
                for valve_tag, controlled_leader in valve_mapping.items():
                    if pipe_number == controlled_leader:
                        role += f" (controlled by {valve_tag})"
                break
            elif pipe_number in group_data["followers"]:
                role = f"Follower in {group_name}"
                break
        
        st.write(f"Pipe {pipe_number}: {color_name} | {role}")
    
    st.write("**All Valves Data:**")
    st.json(valves)
    st.write("**All Pipes Data:**")
    st.json(st.session_state.pipes)
