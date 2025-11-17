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

# ==================== LEADER GROUPS ======================
def get_pipe_groups_with_leaders():
    return {
        "Group_1": {"leader": 1,  "followers": [20]},
        "Group_2": {"leader": 11, "followers": [10, 19]},
        "Group_3": {"leader": 2,  "followers": [3, 4, 14, 21, 22]},
        "Group_4": {"leader": 13, "followers": [14, 4, 21, 22]},
        "Group_5": {"leader": 5,  "followers": [6, 7, 8, 9, 18]},
        "Group_6": {"leader": 17, "followers": [16, 15, 8]}
    }

# ================== HARD-CODED VALVE → LEADER =============
def get_hardcoded_valve_control():
    # This is the ONLY thing that was missing/broken
    return {
        "V-103": 5,   # V-103 controls leader pipe 5 → all of Group_5
        "V-104": 22,  # V-104 controls pipe 22 → activates Group_3 & Group_4 followers
        "V-301": 2,   # already working
        "V-302": 13,  # already working
        # add more if needed
    }

# ============== PROXIMITY + HARDCODED CONTROL =============
def get_controlling_valve(pipe_index):
    pipe_num = pipe_index + 1
    pipe = st.session_state.pipes[pipe_index]
    x1, y1 = pipe["x1"], pipe["y1"]

    # 1. Hard-coded valves (V-103, V-104, etc.)
    hardcoded = get_hardcoded_valve_control()
    for valve_tag, controlled_pipe in hardcoded.items():
        if pipe_num == controlled_pipe:
            return valve_tag

    # 2. Normal proximity fallback (20px)
    closest = None
    min_dist = float('inf')
    for tag, v in valves.items():
        dist = math.hypot(v["x"] - x1, v["y"] - y1)
        if dist < min_dist and dist <= 20:
            min_dist = dist
            closest = tag
    return closest

# =================== IS LEADER ACTIVE? ===================
def is_leader_active(leader_idx_0based):
    valve = get_controlling_valve(leader_idx_0based)
    if valve and st.session_state.valve_states.get(valve, False):
        return True
    return False

# =================== PIPE COLOR LOGIC ====================
def get_pipe_color(pipe_index):
    pipe_num = pipe_index + 1
    groups = get_pipe_groups_with_leaders()

    # Check if this pipe is a leader and active
    for g in groups.values():
        if g["leader"] == pipe_num:
            return (0, 255, 0) if is_leader_active(pipe_index) else (0, 0, 255)

    # Check if it's a follower of an active leader
    for g in groups.values():
        if pipe_num in g["followers"]:
            leader_idx = g["leader"] - 1
            if leader_idx < len(pipes) and is_leader_active(leader_idx):
                return (0, 255, 0)

    # Standalone pipe with proximity valve
    valve = get_controlling_valve(pipe_index)
    if valve and st.session_state.valve_states.get(valve, False):
        return (0, 255, 0)
    return (0, 0, 255)

# ======================= RENDER ==========================
def create_pid_with_valves_and_pipes():
    pid_img = Image.open(PID_FILE).convert("RGBA")
    draw = ImageDraw.Draw(pid_img)

    # Draw pipes
    for i, pipe in enumerate(st.session_state.pipes):
        x1, y1, x2, y2 = pipe["x1"], pipe["y1"], pipe["x2"], pipe["y2"]
        color = get_pipe_color(i)
        if i == st.session_state.selected_pipe:
            color = (148, 0, 211)
            width = 8
        else:
            width = 6
        draw.line([(x1, y1), (x2, y2)], fill=color, width=width)

        if i == st.session_state.selected_pipe:
            draw.ellipse([x1-6, y1-6, x1+6, y1+6], fill=(255,0,0), outline="white", width=2)
            draw.ellipse([x2-6, y2-6, x2+6, y2+6], fill=(255,0,0), outline="white", width=2)

    # Draw valves
    for tag, data in valves.items():
        x, y = data["x"], data["y"]
        color = (0, 255, 0) if st.session_state.valve_states[tag] else (255, 0, 0)
        draw.ellipse([x-8, y-8, x+8, y+8], fill=color, outline="white", width=2)
        draw.text((x+12, y-10), tag, fill="white", stroke_fill="black", stroke_width=1)

    return pid_img.convert("RGB")

# =========================== UI ===========================
st.title("P&ID Interactive Simulation")

with st.sidebar:
    st.header("Valve Controls")
    for tag in valves:
        state = st.session_state.valve_states[tag]
        label = f"{'OPEN' if state else 'CLOSED'} {tag}"
        if st.button(label, key=tag, use_container_width=True):
            st.session_state.valve_states[tag] = not state
            st.rerun()

    st.markdown("---")
    st.header("Pipe Selection")
    if st.button("Unselect All", use_container_width=True):
        st.session_state.selected_pipe = None
        st.rerun()
    for i in range(len(pipes)):
        icon = "Selected" if i == st.session_state.selected_pipe else "Pipe"
        if st.button(f"{icon} {i+1}", key=f"p{i}", use_container_width=True):
            st.session_state.selected_pipe = i
            st.rerun()

# Main display
col1, col2 = st.columns([3, 1])
with col1:
    st.image(create_pid_with_valves_and_pipes(), use_container_width=True,
             caption="V-103 → Group 5 | V-104 → Pipe 22 + downstream | Green = Flow")

with col2:
    st.header("Flow Status")
    active = sum(1 for i in range(len(pipes)) if get_pipe_color(i) == (0,255,0))
    st.write(f"**Active pipes:** {active}/{len(pipes)}")

# Debug (optional)
with st.expander("Debug"):
    st.json(get_hardcoded_valve_control())
    for i in range(len(pipes)):
        valve = get_controlling_valve(i)
        st.write(f"Pipe {i+1} → controlled by → {valve}")
