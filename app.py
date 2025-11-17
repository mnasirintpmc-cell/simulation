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

# ===================== PRESSURE SOURCES =====================
# ←←← EDIT THIS LINE ONLY ←←←
PRESSURE_SOURCES = [1, 5, 11]   # Your real pressure sources (pumps, headers, tanks, etc.)

# ===================== LEADER GROUPS ======================
def get_groups():
    return {
        1: [20],
        2: [3, 4, 14, 21, 22],   # V-301
        5: [6, 7, 8, 9, 18],     # V-103
        11: [10, 19],
        12: [],                  # V-501 - ONLY pipe 12
        13: [14, 4, 21, 22],     # V-302
        17: [16, 15, 8],         # V-105
        22: [3, 4, 14, 21]       # V-104 downstream
    }

# ============ HARD-CODED + PROXIMITY CONTROL =============
def get_leader_of_pipe(pipe_idx_0):
    pipe_num = pipe_idx_0 + 1
    pipe = st.session_state.pipes[pipe_idx_0]
    hard = {"V-301":2, "V-302":13, "V-103":5, "V-104":22, "V-501":12}
    for v, leader in hard.items():
        if pipe_num == leader:
            return leader - 1
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
    for valve, leader_1 in {"V-301":2, "V-302":13, "V-103":5, "V-104":22, "V-501":12}.items():
        if st.session_state.valve_states.get(valve, False):
            active_leaders.add(leader_1 - 1)
    for i in range(len(pipes)):
        leader = get_leader_of_pipe(i)
        if leader is not None:
            for tag, v in valves.items():
                if st.session_state.valve_states.get(tag, False):
                    dist = math.hypot(v["x"] - pipes[i]["x1"], v["y"] - pipes[i]["y1"])
                    if dist <= 40:
                        active_leaders.add(leader)
                        break
    return active_leaders

# =================== PIPE COLOR WITH REAL PRESSURE ========================
def get_pipe_color(idx_0):
    num = idx_0 + 1
    active_leaders = get_active_leaders()

    if idx_0 == st.session_state.selected_pipe:
        return (148, 0, 211)                                 # Purple = selected

    has_flow = idx_0 in active_leaders or any(
        num in followers and (leader_1 - 1) in active_leaders
        for leader_1, followers in get_groups().items()
    )

    has_pressure = num in PRESSURE_SOURCES
    if not has_pressure:
        for leader_1, followers in get_groups().items():
            leader_idx = leader_1 - 1
            if leader_idx in active_leaders and (num == leader_1 or num in followers):
                if leader_1 in PRESSURE_SOURCES:
                    has_pressure = True
                    break

    if has_flow and has_pressure:
        return (0, 255, 0)        # Bright Green = flowing
    elif has_pressure:
        return (100, 200, 255)    # Light Blue = pressurized, no flow
    else:
        return (50, 50, 80)       # Dark Gray = empty

# ======================= RENDER =========================
def create_pid_with_valves_and_pipes():
    try:
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
        for i, pipe in enumerate(st.session_state.pipes):
            color = get_pipe_color(i)
            width = 8 if i == st.session_state.selected_pipe else 6
            draw.line([(pipe["x1"], pipe["y1"]), (pipe["x2"], pipe["y2"])], fill=color, width=width)
            if i == st.session_state.selected_pipe:
                draw.ellipse([pipe["x1"]-6, pipe["y1"]-6, pipe["x1"]+6, pipe["y1"]+6], fill=(255,0,0), outline="white", width=2)
                draw.ellipse([pipe["x2"]-6, pipe["y2"]-6, pipe["x2"]+6, pipe["y2"]+6], fill=(255,0,0), outline="white", width=2)
        for tag, data in valves.items():
            x, y = data["x"], data["y"]
            color = (0, 255, 0) if st.session_state.valve_states[tag] else (255, 0, 0)
            draw.ellipse([x-8, y-8, x+8, y+8], fill=color, outline="white", width=2)
            draw.text((x+12, y-10), tag, fill="white", stroke_fill="black", stroke_width=1)
        return pid_img.convert("RGB")
    except Exception as e:
        st.error(f"Error: {e}")
        return Image.new("RGB", (1200, 800), (255, 255, 255))

# =========================== UI ===========================
st.title("P&ID Interactive Simulation – Now with Real Pressure")

with st.sidebar:
    st.header("Valve Controls")
    for tag in valves:
        state = st.session_state.valve_states[tag]
        if st.button(f"{'OPEN' if state else 'CLOSED'} {tag}", key=tag, use_container_width=True):
            st.session_state.valve_states[tag] = not state
            st.rerun()

    st.markdown("---")
    st.header("Pipe Selection")
    if st.button("Unselect All Pipes", use_container_width=True):
        st.session_state.selected_pipe = None
        st.rerun()
    for i in range(len(pipes)):
        if st.button(f"{'Selected' if i == st.session_state.selected_pipe else 'Pipe'} {i+1}", key=f"p{i}", use_container_width=True):
            st.session_state.selected_pipe = i
            st.rerun()

col1, col2 = st.columns([3, 1])
with col1:
    st.image(create_pid_with_valves_and_pipes(), use_container_width=True,
             caption="Bright Green = Flowing | Light Blue = Pressurized | Dark = Empty")

with col2:
    st.header("Pressure & Flow Status")
    flowing = sum(1 for i in range(len(pipes)) if get_pipe_color(i) == (0,255,0))
    pressurized = sum(1 for i in range(len(pipes)) if get_pipe_color(i) in [(0,255,0), (100,200,255)])
    st.write(f"**Flowing pipes:** {flowing}")
    st.write(f"**Pressurized pipes:** {pressurized}")
    st.write(f"**Empty pipes:** {len(pipes) - pressurized}")

# ←←← FIXED: proper newline before this line
st.success("Realistic pressure simulation added! Edit PRESSURE_SOURCES = [1, 5, 11] at the top to match your plant.")
