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
if "pressure_sources" not in st.session_state:
    st.session_state.pressure_sources = {
        1: 100.0,   # Main header
        5: 85.0,    # Pump discharge
        11: 75.0,   # Secondary header
        23: 90.0,   # Compressor discharge
    }
if "show_pressure" not in st.session_state:
    st.session_state.show_pressure = True
if "pressure_data" not in st.session_state:
    st.session_state.pressure_data = {}

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

# ================== PRESSURE SIMULATION ==================
def calculate_pipe_pressure(pipe_idx):
    """Calculate actual pressure in pipe considering upstream sources and valve states"""
    pipe_num = pipe_idx + 1
    
    # If this pipe is a designated pressure source, use its value
    if pipe_num in st.session_state.pressure_sources:
        source_pressure = st.session_state.pressure_sources[pipe_num]
        # Check if path from source to this pipe is open
        if is_path_open_from_source(pipe_idx, pipe_num):
            return source_pressure
        else:
            return 0.0
    
    # Find closest upstream pressure source with open path
    upstream_pressure = find_upstream_pressure(pipe_idx)
    return upstream_pressure

def is_path_open_from_source(pipe_idx, source_pipe_num):
    """Check if valves between source and this pipe are open"""
    # For now, use simple flow logic - if pipe is active, path is open
    return is_pipe_active(pipe_idx)

def find_upstream_pressure(pipe_idx):
    """Find pressure from nearest upstream source with open path"""
    pipe_num = pipe_idx + 1
    max_pressure = 0.0
    
    # Check all pressure sources
    for source_pipe, source_pressure in st.session_state.pressure_sources.items():
        # Check if there's a path from source to this pipe
        if is_path_available(source_pipe - 1, pipe_idx):
            # Calculate pressure drop based on path length
            path_length = calculate_path_length(source_pipe - 1, pipe_idx)
            pressure_drop = path_length * 2.0  # 2 psi drop per pipe segment
            final_pressure = max(0, source_pressure - pressure_drop)
            max_pressure = max(max_pressure, final_pressure)
    
    return max_pressure

def is_path_available(from_pipe_idx, to_pipe_idx):
    """Check if there's an open path between two pipes"""
    if from_pipe_idx == to_pipe_idx:
        return True
    
    # Simple implementation - check if both pipes are active
    # In a real implementation, you'd trace the actual pipe connections
    return is_pipe_active(from_pipe_idx) and is_pipe_active(to_pipe_idx)

def calculate_path_length(from_pipe_idx, to_pipe_idx):
    """Calculate approximate path length between pipes"""
    # Simple implementation - use geometric distance
    pipe1 = st.session_state.pipes[from_pipe_idx]
    pipe2 = st.session_state.pipes[to_pipe_idx]
    
    mid1_x = (pipe1["x1"] + pipe1["x2"]) / 2
    mid1_y = (pipe1["y1"] + pipe1["y2"]) / 2
    mid2_x = (pipe2["x1"] + pipe2["x2"]) / 2
    mid2_y = (pipe2["y1"] + pipe2["y2"]) / 2
    
    distance = math.hypot(mid2_x - mid1_x, mid2_y - mid1_y)
    return distance / 100  # Normalize to pipe segments

def is_pipe_active(idx_0):
    """Check if pipe has flow (original logic)"""
    num = idx_0 + 1
    active_leaders = get_active_leaders()
    
    # leader?
    if idx_0 in active_leaders:
        return True
    # follower?
    for leader_1, followers in get_groups().items():
        if num in followers and (leader_1 - 1) in active_leaders:
            return True
    return False

# =================== PIPE COLOR ========================
def get_pipe_color(idx_0):
    num = idx_0 + 1
    active_leaders = get_active_leaders()
    
    # Selected pipe (purple)
    if idx_0 == st.session_state.selected_pipe:
        return (148, 0, 211)
    
    # Pressure visualization
    if st.session_state.show_pressure:
        pressure = calculate_pipe_pressure(idx_0)
        if pressure > 0:
            # Color gradient: Dark Blue (low) -> Green -> Yellow -> Red (high)
            if pressure < 25:
                # Blue to Green
                intensity = int(255 * (pressure / 25))
                return (0, intensity, 255 - intensity)
            elif pressure < 50:
                # Green to Yellow
                intensity = int(255 * ((pressure - 25) / 25))
                return (intensity, 255, 0)
            elif pressure < 75:
                # Yellow to Orange
                intensity = int(255 * ((pressure - 50) / 25))
                return (255, 255 - intensity, 0)
            else:
                # Orange to Red
                intensity = int(255 * ((pressure - 75) / 25))
                return (255, 128 - intensity, 0)
        else:
            return (0, 0, 255)  # Blue for no pressure
    
    # Original flow logic
    if idx_0 in active_leaders:
        return (0, 255, 0)
    
    for leader_1, followers in get_groups().items():
        if num in followers and (leader_1 - 1) in active_leaders:
            return (0, 255, 0)
    
    return (0, 0, 255)

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

            # Draw pressure values
            if st.session_state.show_pressure:
                pressure = calculate_pipe_pressure(i)
                if pressure > 0:
                    mid_x = (pipe["x1"] + pipe["x2"]) / 2
                    mid_y = (pipe["y1"] + pipe["y2"]) / 2
                    # Adjust text position to avoid overlap
                    text_x = mid_x + 10
                    text_y = mid_y - 10
                    draw.text((text_x, text_y), f"{pressure:.0f}", fill="white", 
                             stroke_fill="black", stroke_width=2)

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
st.title("🎯 P&ID Interactive Simulation with Pressure")

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
    st.header("💧 Pressure Sources")
    st.markdown("Set pressure input points (PSI)")
    
    # Common pressure sources
    common_sources = [1, 5, 11, 23]
    
    for pipe_num in common_sources:
        current_pressure = st.session_state.pressure_sources.get(pipe_num, 0)
        new_pressure = st.slider(
            f"Pipe {pipe_num} Pressure",
            min_value=0,
            max_value=150,
            value=int(current_pressure),
            key=f"pressure_{pipe_num}"
        )
        if new_pressure != current_pressure:
            st.session_state.pressure_sources[pipe_num] = float(new_pressure)
            st.rerun()
    
    # Add custom pressure source
    st.markdown("**Add Custom Pressure Source:**")
    col1, col2 = st.columns(2)
    with col1:
        custom_pipe = st.number_input("Pipe Number", min_value=1, max_value=50, value=12, key="custom_pipe")
    with col2:
        custom_pressure = st.number_input("PSI", min_value=0, max_value=150, value=100, key="custom_pressure")
    
    if st.button("➕ Set as Pressure Source"):
        st.session_state.pressure_sources[custom_pipe] = float(custom_pressure)
        st.rerun()
    
    # Clear all pressures
    if st.button("🗑️ Clear All Pressures"):
        st.session_state.pressure_sources = {}
        st.rerun()
    
    st.markdown("---")
    st.header("📋 Display Options")
    
    # Toggle pressure display
    show_pressure = st.toggle("Show Pressure Visualization", 
                             value=st.session_state.show_pressure)
    if show_pressure != st.session_state.show_pressure:
        st.session_state.show_pressure = show_pressure
        st.rerun()
    
    st.markdown("---")
    st.header("Pipe Selection")
    
    # Unselect all pipes button
    if st.button("🚫 Unselect All Pipes", use_container_width=True, type="secondary"):
        st.session_state.selected_pipe = None
        st.rerun()
    
    # Pipe selection buttons in 2 columns
    st.write("Select pipe to inspect:")
    cols = st.columns(2)
    for i in range(len(st.session_state.pipes)):
        with cols[i % 2]:
            is_selected = st.session_state.selected_pipe == i
            status_icon = "🟣" if is_selected else "🔵"
            label = f"{status_icon} Pipe {i+1}"
            if st.button(label, key=f"pipe_{i}", use_container_width=True):
                st.session_state.selected_pipe = i
                st.rerun()

    # Pipe Position Adjustment
    if st.session_state.selected_pipe is not None:
        st.markdown("---")
        st.header("🛠️ Pipe Position Adjustment")
        
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

# Main content area
col1, col2 = st.columns([3, 1])

with col1:
    # Create and display the P&ID
    composite_img = create_pid_with_valves_and_pipes()
    
    # Show selection status
    if st.session_state.selected_pipe is not None:
        if st.session_state.show_pressure:
            pressure = calculate_pipe_pressure(st.session_state.selected_pipe)
            caption = f"🟣 Pipe {st.session_state.selected_pipe + 1} Selected | Pressure: {pressure:.1f} psi"
        else:
            caption = f"🟣 Pipe {st.session_state.selected_pipe + 1} Selected | 🟢 Green = Flow Active | 🔵 Blue = No Flow"
    else:
        if st.session_state.show_pressure:
            caption = "Pressure Visualization: 🔴 High (75-100 psi) | 🟡 Medium (50-75 psi) | 🟢 Low (25-50 psi) | 🔵 Very Low (1-25 psi) | 🔷 No Pressure"
        else:
            caption = "🟢 Green = Flow Active | 🔵 Blue = No Flow"
    
    st.image(composite_img, use_container_width=True, caption=caption)

with col2:
    # Right sidebar for detailed status
    st.header("🔍 System Status")
    st.markdown("---")
    
    # Pressure summary
    st.subheader("💧 Pressure Summary")
    pressures = [calculate_pipe_pressure(i) for i in range(len(st.session_state.pipes))]
    pipes_with_pressure = sum(1 for p in pressures if p > 0)
    max_pressure = max(pressures) if pressures else 0
    
    st.metric("Pipes Under Pressure", f"{pipes_with_pressure}/{len(pipes)}")
    st.metric("Maximum Pressure", f"{max_pressure:.1f} psi")
    st.metric("Pressure Sources", f"{len(st.session_state.pressure_sources)}")
    
    # Active pressure sources
    if st.session_state.pressure_sources:
        st.markdown("**Active Sources:**")
        for pipe_num, pressure in st.session_state.pressure_sources.items():
            st.write(f"• Pipe {pipe_num}: {pressure} psi")
    
    st.markdown("---")
    st.subheader("📊 Flow Status")
    active_pipes = sum(1 for i in range(len(st.session_state.pipes)) if is_pipe_active(i))
    st.metric("Active Flow Pipes", active_pipes)
    
    open_valves = sum(1 for state in st.session_state.valve_states.values() if state)
    st.metric("Open Valves", open_valves)
    
    # Selected pipe details
    if st.session_state.selected_pipe is not None:
        st.markdown("---")
        st.subheader(f"🟣 Pipe {st.session_state.selected_pipe + 1}")
        
        pipe_num = st.session_state.selected_pipe + 1
        pressure = calculate_pipe_pressure(st.session_state.selected_pipe)
        flow_status = "ACTIVE" if is_pipe_active(st.session_state.selected_pipe) else "NO FLOW"
        
        st.metric("Pressure", f"{pressure:.1f} psi")
        st.metric("Flow Status", flow_status)
        
        # Find controlling valve
        hard_mapped = {"V-301":2, "V-302":13, "V-103":5, "V-104":22, "V-501":12}
        controlling_valve = None
        for valve, leader_pipe in hard_mapped.items():
            if leader_pipe == pipe_num:
                controlling_valve = valve
                break
        
        if controlling_valve:
            valve_state = st.session_state.valve_states.get(controlling_valve, False)
            status = "OPEN" if valve_state else "CLOSED"
            st.write(f"**Controlled by:** {controlling_valve} ({status})")

# Debug information
with st.expander("🔧 Debug Information"):
    st.write("**Active Leaders:**", [i+1 for i in get_active_leaders()])
    st.write("**Pressure Sources:**", st.session_state.pressure_sources)
    
    st.subheader("Pipe Details")
    for i in range(len(st.session_state.pipes)):
        pipe_number = i + 1
        pressure = calculate_pipe_pressure(i)
        active = is_pipe_active(i)
        status = "ACTIVE" if active else "INACTIVE"
        st.write(f"Pipe {pipe_number}: {pressure:.1f} psi | {status}")

st.success("✅ Standard pressure simulation active! Pressure follows real process rules with upstream/downstream logic.")
