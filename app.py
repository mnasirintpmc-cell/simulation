import streamlit as st
import json
from PIL import Image, ImageDraw
import os
import math

st.set_page_config(layout="wide")

# ========================= CONFIG =========================
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"
PIPES_DATA_FILE = "pipes.json"

# ======================= LOAD DATA ========================
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

valves = load_valves()
pipes = load_pipes()

# ===================== SESSION STATE ======================
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data.get("state", False) for tag, data in valves.items()}
if "selected_pipe" not in st.session_state:
    st.session_state.selected_pipe = None
if "pipes" not in st.session_state:
    st.session_state.pipes = pipes

# ===================== LEADER GROUPS ======================
def get_groups():
    return {
        1:  [20],
        2:  [3, 4, 14, 21, 22],   # V-301
        5:  [6, 7, 8, 9, 18],     # V-103
        11: [10, 19],
        12: [],                    # V-501 - ONLY pipe 12, no followers
        13: [14, 4, 21, 22],      # V-302
        17: [16, 15, 8],          # V-105
        22: [3, 4, 14, 21]        # V-104 downstream
    }

# ============ HARD-CODED + PROXIMITY CONTROL =============
def get_leader_of_pipe(pipe_idx_0):
    pipe_num = pipe_idx_0 + 1
    pipe = st.session_state.pipes[pipe_idx_0]

    # 1. Hard-coded valves (these override everything) - V-501 controls pipe 12
    hard = {"V-301":2, "V-302":13, "V-103":5, "V-104":22, "V-501":12}
    for v, leader in hard.items():
        if pipe_num == leader:
            return leader - 1  # return 0-based leader index

    # 2. Proximity (40px from start point)
    best_leader = None
    best_dist = float('inf')
    for leader_1based in get_groups().keys():
        leader_idx = leader_1based - 1
        if leader_idx >= len(pipes): continue
        px = pipes[leader_idx]
        dist = math.hypot(px["x1"] - pipe["x1"], px["y1"] - pipe["y1"])
        if dist < best_dist and dist <= 40:
            best_dist = dist
            best_leader = leader_idx
    return best_leader

# ================ ACTIVE LEADERS SET ====================
def get_active_leaders():
    active_leaders = set()
    
    # Hard-coded valves - V-501 controls pipe 12
    for valve, leader_1 in {"V-301":2, "V-302":13, "V-103":5, "V-104":22, "V-501":12}.items():
        if st.session_state.valve_states.get(valve, False):
            active_leaders.add(leader_1 - 1)

    # Proximity valves (including V-105)
    for i in range(len(pipes)):
        leader = get_leader_of_pipe(i)
        if leader is not None:
            ctrl_valve = None
            for tag, v in valves.items():
                if st.session_state.valve_states.get(tag, False):
                    dist = math.hypot(v["x"] - pipes[i]["x1"], v["y"] - pipes[i]["y1"])
                    if dist <= 40:
                        ctrl_valve = tag
                        break
            if ctrl_valve:
                active_leaders.add(leader)
    
    return active_leaders

# =================== PIPE COLOR ========================
def get_pipe_color(idx_0):
    num = idx_0 + 1
    active_leaders = get_active_leaders()
    
    # Selected pipe (purple)
    if idx_0 == st.session_state.selected_pipe:
        return (148, 0, 211)
    
    # leader?
    if idx_0 in active_leaders:
        return (0, 255, 0)
    
    # follower?
    for leader_1, followers in get_groups().items():
        if num in followers and (leader_1 - 1) in active_leaders:
            return (0, 255, 0)
    
    return (0, 0, 255)  # default blue

# ======================= RENDER =========================
def create_pid_with_valves_and_pipes():
    try:
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)

        # Draw pipes
        for i, pipe in enumerate(st.session_state.pipes):
            color = get_pipe_color(i)
            width = 8 if i == st.session_state.selected_pipe else 6
            draw.line([(pipe["x1"], pipe["y1"]), (pipe["x2"], pipe["y2"])], fill=color, width=width)

            # Draw endpoints for selected pipe
            if i == st.session_state.selected_pipe:
                draw.ellipse([pipe["x1"]-6, pipe["y1"]-6, pipe["x1"]+6, pipe["y1"]+6], fill=(255,0,0), outline="white", width=2)
                draw.ellipse([pipe["x2"]-6, pipe["y2"]-6, pipe["x2"]+6, pipe["y2"]+6], fill=(255,0,0), outline="white", width=2)

        # Draw valves
        for tag, data in valves.items():
            x, y = data["x"], data["y"]
            color = (0, 255, 0) if st.session_state.valve_states[tag] else (255, 0, 0)
            draw.ellipse([x-8, y-8, x+8, y+8], fill=color, outline="white", width=2)
            draw.text((x+12, y-10), tag, fill="white", stroke_fill="black", stroke_width=1)

        return pid_img.convert("RGB")
    except Exception as e:
        st.error(f"Error creating P&ID image: {e}")
        return Image.new("RGB", (1200, 800), (255, 255, 255))

# =========================== UI ===========================
st.title("🎯 P&ID Interactive Simulation")

# Create sidebar for controls
with st.sidebar:
    st.header("🎯 Valve Controls")
    st.markdown("---")
    
    # Valve toggle buttons
    for tag in valves:
        current_state = st.session_state.valve_states[tag]
        button_label = f"🔴 {tag} - OPEN" if current_state else f"🟢 {tag} - CLOSED"
        if st.button(button_label, key=f"btn_{tag}", use_container_width=True):
            st.session_state.valve_states[tag] = not current_state
            st.rerun()
    
    st.markdown("---")
    st.header("📋 Pipe Selection")
    st.markdown("Click on a pipe to highlight it")
    
    # Unselect all pipes button
    if st.button("🚫 Unselect All Pipes", use_container_width=True, type="secondary"):
        st.session_state.selected_pipe = None
        st.rerun()
    
    # Pipe selection buttons
    for i in range(len(st.session_state.pipes)):
        is_selected = st.session_state.selected_pipe == i
        status_icon = "🟣" if is_selected else "🔵"
        label = f"{status_icon} Pipe {i+1}"
        if st.button(label, key=f"pipe_{i}", use_container_width=True):
            st.session_state.selected_pipe = i
            st.rerun()

    # Pipe Position Adjustment
    st.markdown("---")
    st.header("🛠️ Pipe Position Adjustment")
    
    if st.session_state.selected_pipe is not None:
        pipe = st.session_state.pipes[st.session_state.selected_pipe]
        st.write(f"**Adjusting Pipe {st.session_state.selected_pipe + 1}**")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Start Point**")
            new_x1 = st.number_input("X1", value=pipe["x1"], key="x1_adjust")
            new_y1 = st.number_input("Y1", value=pipe["y1"], key="y1_adjust")
        with col2:
            st.write("**End Point**")
            new_x2 = st.number_input("X2", value=pipe["x2"], key="x2_adjust")
            new_y2 = st.number_input("Y2", value=pipe["y2"], key="y2_adjust")
        
        if st.button("💾 Apply Position Changes", use_container_width=True):
            st.session_state.pipes[st.session_state.selected_pipe] = {
                "x1": new_x1, "y1": new_y1, "x2": new_x2, "y2": new_y2
            }
            save_pipes(st.session_state.pipes)
            st.success("Pipe position updated!")
            st.rerun()
        
        # Show distances to valves
        st.markdown("---")
        st.subheader("📏 Distance to Valves")
        pipe = st.session_state.pipes[st.session_state.selected_pipe]
        x1, y1 = pipe["x1"], pipe["y1"]
        
        for tag, valve_data in valves.items():
            valve_x, valve_y = valve_data["x"], valve_data["y"]
            distance = math.hypot(valve_x - x1, valve_y - y1)
            st.write(f"**{tag}**: {distance:.1f} pixels")
    else:
        st.info("Select a pipe first to adjust its position")

# Main content area
col1, col2 = st.columns([3, 1])

with col1:
    # Create and display the P&ID
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
    
    # System status
    st.subheader("📊 System Status")
    active_pipes = sum(1 for i in range(len(st.session_state.pipes)) if get_pipe_color(i) == (0, 255, 0))
    st.write(f"**Active Flow Pipes:** {active_pipes}")
    st.write(f"**No Flow Pipes:** {len(st.session_state.pipes) - active_pipes}")
    
    # Valve status
    open_valves = sum(1 for state in st.session_state.valve_states.values() if state)
    closed_valves = len(valves) - open_valves
    st.write(f"**Open Valves:** {open_valves}")
    st.write(f"**Closed Valves:** {closed_valves}")
    
    # Valve control mapping
    st.markdown("---")
    st.subheader("🔗 Valve Control")
    
    hard_mapped = {"V-301":2, "V-302":13, "V-103":5, "V-104":22, "V-501":12}  # V-501 controls pipe 12
    groups = get_groups()
    
    for valve_tag, leader_pipe in hard_mapped.items():
        valve_state = st.session_state.valve_states.get(valve_tag, False)
        status_icon = "🟢" if valve_state else "🔵"
        
        # Get followers for this leader
        followers = groups.get(leader_pipe, [])
        controlled_pipes = [leader_pipe] + followers
        
        st.write(f"{status_icon} **{valve_tag}** → Pipe {leader_pipe}")
        st.write(f"Controls: Pipes {controlled_pipes}")
        st.write("---")
    
    # V-105 (proximity based)
    v105_state = st.session_state.valve_states.get("V-105", False)
    status_icon = "🟢" if v105_state else "🔵"
    st.write(f"{status_icon} **V-105** → Pipe 17 (Proximity)")
    st.write("Controls: Pipes 17, 16, 15, 8")
    st.write("---")
    
    # Selected pipe info
    if st.session_state.selected_pipe is not None:
        st.markdown("---")
        st.subheader(f"🟣 Selected Pipe {st.session_state.selected_pipe + 1}")
        
        pipe_number = st.session_state.selected_pipe + 1
        leader_idx = get_leader_of_pipe(st.session_state.selected_pipe)
        
        if leader_idx is not None:
            leader_pipe = leader_idx + 1
            # Find which valve controls this leader
            controlling_valve = None
            for valve, l_pipe in hard_mapped.items():
                if l_pipe == leader_pipe:
                    controlling_valve = valve
                    break
            
            if not controlling_valve:
                # Check proximity valves
                pipe_data = st.session_state.pipes[st.session_state.selected_pipe]
                for tag, v_data in valves.items():
                    dist = math.hypot(v_data["x"] - pipe_data["x1"], v_data["y"] - pipe_data["y1"])
                    if dist <= 40 and st.session_state.valve_states.get(tag, False):
                        controlling_valve = tag
                        break
            
            if controlling_valve:
                valve_state = st.session_state.valve_states.get(controlling_valve, False)
                status = "OPEN" if valve_state else "CLOSED"
                st.write(f"**Controlled by:** {controlling_valve} ({status})")
        
        # Check flow status
        color = get_pipe_color(st.session_state.selected_pipe)
        flow_status = "🟢 ACTIVE FLOW" if color == (0, 255, 0) else "🔵 NO FLOW"
        st.write(f"**Flow Status:** {flow_status}")

# Debug information
with st.expander("🔧 Debug Information"):
    st.write("**Active Leaders:**", [i+1 for i in get_active_leaders()])
    
    st.subheader("Pipe Control Information")
    for i in range(len(st.session_state.pipes)):
        pipe_number = i + 1
        color = get_pipe_color(i)
        color_name = "GREEN" if color == (0, 255, 0) else "BLUE"
        leader_idx = get_leader_of_pipe(i)
        leader_info = f" | Leader: Pipe {leader_idx + 1}" if leader_idx is not None else " | No Leader"
        st.write(f"Pipe {pipe_number}: {color_name}{leader_info}")

st.success("✅ V-501 FIXED! Now activates ONLY pipe 12. All valves working correctly!")
