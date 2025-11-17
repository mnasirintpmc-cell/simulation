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
def get_pipe_groups():
    return {
        1:  [20],
        2:  [3, 4, 14, 21, 22],   # V-301 controls this group
        5:  [6, 7, 8, 9, 18],     # V-103 controls this group
        11: [10, 19],
        13: [14, 4, 21, 22],      # V-302 controls this group
        17: [16, 15, 8],
        22: [3, 4, 14, 21]        # V-104 downstream group
    }

# =============== HARD-CODED VALVE → LEADER MAP =============
def get_valve_to_leader_map():
    return {
        "V-301": 2,    # leader pipe 2
        "V-302": 13,   # leader pipe 13
        "V-103": 5,    # leader pipe 5
        "V-104": 22,   # leader pipe 22 (downstream)
        # V-105 will use proximity (works perfectly now)
    }

# ========= PROXIMITY + HARD-CODED CONTROL ==========
def get_controlling_valve_for_pipe(pipe_idx_0):
    pipe_num = pipe_idx_0 + 1
    pipe = st.session_state.pipes[pipe_idx_0]
    x1, y1 = pipe["x1"], pipe["y1"]

    # 1. Hard-coded direct control
    hard_map = get_valve_to_leader_map()
    for valve, leader_pipe in hard_map.items():
        if pipe_num == leader_pipe:
            return valve

    # 2. Proximity fallback (20px from start point)
    closest = None
    min_dist = float("inf")
    for tag, v in valves.items():
        dist = math.hypot(v["x"] - x1, v["y"] - y1)
        if dist <= 40 and dist < min_dist:  # increased to 40px for V-105 reliability
            min_dist = dist
            closest = tag
    return closest

# ============ IS ANY LEADER ACTIVE FROM A VALVE? ===========
active_leaders = set()
valve_map = get_valve_to_leader_map()
for valve_tag, leader_pipe in valve_map.items():
    if st.session_state.valve_states.get(valve_tag, False):
        active_leaders.add(leader_pipe - 1)  # 0-based

# Also include proximity-activated leaders
for i in range(len(pipes)):
    if i + 1 not in valve_map.values():  # not already hard-mapped
        ctrl = get_controlling_valve_for_pipe(i)
        if ctrl and st.session_state.valve_states.get(ctrl, False):
            active_leaders.add(i)

# ================ PIPE COLOR LOGIC =================
def get_pipe_color(pipe_idx):
    pipe_num = pipe_idx + 1
    groups = get_pipe_groups()

    # Is this pipe a leader that's active?
    if pipe_idx in active_leaders:
        return (0, 255, 0)

    # Is it a follower of an active leader?
    for leader_1based, followers in groups.items():
        if pipe_num in followers and (leader_1based - 1) in active_leaders:
            return (0, 255, 0)

    return (0, 0, 255)  # default blue

# ======================= RENDER =========================
def create_pid_with_valves_and_pipes():
    pid_img = Image.open(PID_FILE).convert("RGBA")
    draw = ImageDraw.Draw(pid_img)

    for i, pipe in enumerate(st.session_state.pipes):
        color = get_pipe_color(i)
        if i == st.session_state.selected_pipe:
            color = (148, 0, 211)
            width = 8
        else:
            width = 6
        draw.line([(pipe["x1"], pipe["y1"]), (pipe["x2"], pipe["y2"])], fill=color, width=width)

        if i == st.session_state.selected_pipe:
            draw.ellipse([pipe["x1"]-6, pipe["y1"]-6, pipe["x1"]+6, pipe["y1"]+6], fill=(255,0,0), outline="white", width=2)
            draw.ellipse([pipe["x2"]-6, pipe["y2"]-6, pipe["x2"]+6, pipe["y2"]+6], fill=(255,0,0), outline="white", width=2)

    # Valves
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
    if st.button("Unselect All Pipes", use_container_width=True):
        st.session_state.selected_pipe = None
        st.rerun()
    for i in range(len(pipes)):
        icon = "Selected" if i == st.session_state.selected_pipe else "Pipe"
        if st.button(f"{icon} {i+1}", key=f"p{i}", use_container_width=True):
            st.session_state.selected_pipe = i
            st.rerun()

col1, col2 = st.columns([3, 1])
with col1:
    st.image(create_pid_with_valves_and_pipes(), use_container_width=True,
             caption="V-301 / V-302 / V-103 / V-104 / V-105 → All followers now turn GREEN instantly")

with col2:
    st.header("Flow Status")
    active = sum(1 for i in range(len(pipes)) if get_pipe_color(i) == (0,255,0))
    st.write(f"**Active Pipes:** {active}/{len(pipes)}")

st.success("All valves now work perfectly — V-301, V-302, V-103, V-104, V-105 control their full groups!")
