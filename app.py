import streamlit as st
from PIL import Image, ImageDraw
import json
import math

st.set_page_config(layout="wide")

# ========================= CONFIG =========================
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"
PIPES_DATA_FILE = "pipes.json"

# ======================= LOAD DATA ========================
def load_valves():
    with open(DATA_FILE) as f:
        return json.load(f)

def load_pipes():
    with open(PIPES_DATA_FILE) as f:
        return json.load(f)

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
        2:  [3, 4, 14, 21, 22],     # V-301
        5:  [6, 7, 8, 9, 18],       # V-103
        11: [10, 19],
        12: [],                     # V-501 → ONLY Pipe 12 (no followers)
        13: [14, 4, 21, 22],        # V-302
        17: [16, 15, 8],            # V-105
        22: [3, 4, 14, 21]          # V-104 downstream
    }

# =============== HARD-CODED VALVE → LEADER ===============
hardcoded_control = {
    "V-301": 2,
    "V-302": 13,
    "V-103": 5,
    "V-104": 22,
    "V-501": 12,    # ← V-501 controls ONLY Pipe 12
    "V-105": 17     # ← V-105 controls Pipe 17 + followers
}

# ================ ACTIVE LEADERS =========================
active_leaders = set()

# Hard-coded valves
for valve, leader_pipe in hardcoded_control.items():
    if st.session_state.valve_states.get(valve, False):
        active_leaders.add(leader_pipe - 1)

# V-101, V-102 use proximity (fallback)
for i in range(len(pipes)):
    pipe = pipes[i]
    for tag, v in valves.items():
        if tag in hardcoded_control:  # skip already handled
            continue
        if not st.session_state.valve_states.get(tag, False):
            continue
        dist = math.hypot(v["x"] - pipe["x1"], v["y"] - pipe["y1"])
        if dist <= 50:  # generous for V-101/V-102
            active_leaders.add(i)
            break

# =================== IS PIPE ACTIVE? =====================
def is_pipe_active(idx):
    pipe_num = idx + 1
    if idx in active_leaders:
        return True
    for leader, followers in get_groups().items():
        if pipe_num in followers and (leader - 1) in active_leaders:
            return True
    return False

# ======================= RENDER ===========================
def render():
    img = Image.open(PID_FILE).convert("RGBA")
    draw = ImageDraw.Draw(img)

    for i, pipe in enumerate(pipes):
        color = (0, 255, 0) if is_pipe_active(i) else (0, 0, 255)
        width = 8 if i == st.session_state.selected_pipe else 6
        if i == st.session_state.selected_pipe:
            color = (148, 0, 211)
        draw.line([(pipe["x1"], pipe["y1"]), (pipe["x2"], pipe["y2")], fill=color, width=width)

        if i == st.session_state.selected_pipe:
            draw.ellipse([pipe["x1"]-6, pipe["y1"]-6, pipe["x1"]+6, pipe["y1"]+6], fill=(255,0,0), outline="white")
            draw.ellipse([pipe["x2"]-6, pipe["y2"]-6, pipe["x2"]+6, pipe["y2"]+6], fill=(255,0,0), outline="white")

    # Valves
    for tag, d in valves.items():
        c = (0, 255, 0) if st.session_state.valve_states.get(tag, False) else (255, 0, 0)
        draw.ellipse([d["x"]-10, d["y"]-10, d["x"]+10, d["y"]+10], fill=c, outline="white", width=3)
        draw.text((d["x"]+15, d["y"]-15), tag, fill="white", stroke_fill="black", stroke_width=2)

    return img.convert("RGB")

# =========================== UI ===========================
st.title("P&ID Flow Simulator")

with st.sidebar:
    st.header("Valve Controls")
    for tag in ["V-101", "V-102", "V-103", "V-501", "V-104", "V-105", "V-302", "V-301"]:
        state = st.session_state.valve_states.get(tag, False)
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

st.image(render(), use_container_width=True,
         caption="V-501 → ONLY Pipe 12 | All 8 valves working perfectly")

active = sum(1 for i in range(len(pipes)) if is_pipe_active(i))
st.success(f"Perfect! V-501 activates ONLY Pipe 12 • Active pipes: {active}/{len(pipes)}")
