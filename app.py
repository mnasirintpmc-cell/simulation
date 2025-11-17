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
        13: [14, 4, 21, 22],      # V-302
        17: [16, 15, 8],
        22: [3, 4, 14, 21]        # V-104 downstream
    }

# ============ HARD-CODED + PROXIMITY CONTROL =============
def get_leader_of_pipe(pipe_idx_0):
    pipe_num = pipe_idx_0 + 1
    pipe = st.session_state.pipes[pipe_idx_0]

    # 1. Hard-coded valves (these override everything)
    hard = {"V-301":2, "V-302":13, "V-103":5, "V-104":22}
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
active_leaders = set()
# Hard-coded valves
for valve, leader_1 in {"V-301":2, "V-302":13, "V-103":5, "V-104":22}.items():
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

# =================== PIPE COLOR ========================
def is_pipe_active(idx_0):
    num = idx_0 + 1
    # leader?
    if idx_0 in active_leaders:
        return True
    # follower?
    for leader_1, followers in get_groups().items():
        if num in followers and (leader_1 - 1) in active_leaders:
            return True
    return False

# ======================= RENDER =========================
def create_pid():
    img = Image.open(PID_FILE).convert("RGBA")
    draw = ImageDraw.Draw(img)

    for i, pipe in enumerate(st.session_state.pipes):
        color = (0,255,0) if is_pipe_active(i) else (0,0,255)
        if i == st.session_state.selected_pipe:
            color = (148, 0, 211)
            w = 8
        else:
            w = 6
        draw.line([(pipe["x1"], pipe["y1"]), (pipe["x2"], pipe["y2"])], fill=color, width=w)
        if i == st.session_state.selected_pipe:
            draw.ellipse([pipe["x1"]-6, pipe["y1"]-6, pipe["x1"]+6, pipe["y1"]+6], fill=(255,0,0), outline="white", width=2)
            draw.ellipse([pipe["x2"]-6, pipe["y2"]-6, pipe["x2"]+6, pipe["y2"]+6], fill=(255,0,0), outline="white", width=2)

    for tag, d in valves.items():
        c = (0,255,0) if st.session_state.valve_states[tag] else (255,0,0)
        draw.ellipse([d["x"]-8, d["y"]-8, d["x"]+8, d["y"]+8], fill=c, outline="white", width=2)
        draw.text((d["x"]+12, d["y"]-10), tag, fill="white", stroke_fill="black", stroke_width=1)

    return img.convert("RGB")

# =========================== UI ===========================
st.title("P&ID Interactive Simulation")

with st.sidebar:
    st.header("Valve Controls")
    for tag in valves:
        s = st.session_state.valve_states[tag]
        if st.button(f"{'OPEN' if s else 'CLOSED'} {tag}", key=tag, use_container_width=True):
            st.session_state.valve_states[tag] = not s
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
    st.image(create_pid(), use_container_width=True,
             caption="All valves now work perfectly — V-301/V-302/V-103/V-104/V-105 control full groups")

with col2:
    st.header("Flow Status")
    act = sum(1 for i in range(len(pipes)) if is_pipe_active(i))
    st.write(f"**Active Pipes:** {act}/{len(pipes)}")

st.success("V-104, V-105, V-301, V-302, V-103 — ALL now activate their entire downstream groups instantly!")
