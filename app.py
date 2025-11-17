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
pipes   = load_pipes()

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
        12: [16, 15, 8],            # V-501 → Pipe 12 + followers
        13: [14, 4, 21, 22],        # V-302
        22: [3, 4, 14, 21]          # V-104 downstream
    }

# ============ ALL 8 VALVES HARD-CODED (V-501 → PIPE 12) ============
def get_hardcoded_valve_control():
    return {
        "V-101": 1,     # change if needed
        "V-102": 11,    # change if needed
        "V-103": 5,     # Pipe 5 + followers
        "V-501": 12,    # ← V-501 NOW ACTIVATES PIPE 12 + ALL ITS FOLLOWERS
        "V-104": 22,    # Pipe 22 + downstream
        "V-105": 14,    # change if needed (14, 21, or 22)
        "V-302": 13,    # Pipe 13 + followers
        "V-301": 2      # Pipe 2 + followers
    }

# ================ ACTIVE LEADERS =========================
active_leaders = set()
for valve_tag, leader_pipe_1based in get_hardcoded_valve_control().items():
    if st.session_state.valve_states.get(valve_tag, False):
        leader_idx = leader_pipe_1based - 1
        if 0 <= leader_idx < len(pipes):
            active_leaders.add(leader_idx)

# =================== IS PIPE ACTIVE? =====================
def is_pipe_active(idx_0):
    pipe_num = idx_0 + 1
    if idx_0 in active_leaders:
        return True
    for leader_1, followers in get_groups().items():
        if pipe_num in followers and (leader_1 - 1) in active_leaders:
            return True
    return False

# ======================= RENDER ===========================
def create_pid():
    img = Image.open(PID_FILE).convert("RGBA")
    draw = ImageDraw.Draw(img)

    for i, pipe in enumerate(st.session_state.pipes):
        color = (0, 255, 0) if is_pipe_active(i) else (0, 0, 255)
        width = 8 if i == st.session_state.selected_pipe else 6
        if i == st.session_state.selected_pipe:
            color = (148, 0, 211)  # purple when selected
        draw.line([(pipe["x1"], pipe["y1"]), (pipe["x2"], pipe["y2"])], fill=color, width=width)
        
        if i == st.session_state.selected_pipe:
            draw.ellipse([pipe["x1"]-6, pipe["y1"]-6, pipe["x1"]+6, pipe["y1"]+6], fill=(255,0,0), outline="white", width=2)
            draw.ellipse([pipe["x2"]-6, pipe["y2"]-6, pipe["x2"]+6, pipe["y2"]+6], fill=(255,0,0), outline="white", width=2)

    # Draw valves
    for tag, d in valves.items():
        c = (0, 255, 0) if st.session_state.valve_states.get(tag, False) else (255, 0, 0)
        draw.ellipse([d["x"]-8, d["y"]-8, d["x"]+8, d["y"]+8], fill=c, outline="white", width=2)
        draw.text((d["x"]+12, d["y"]-10), tag, fill="white", stroke_fill="black", stroke_width=1)

    return img.convert("RGB")

# =========================== UI ===========================
st.title("P&ID Interactive Simulation")

with st.sidebar:
    st.header("Valve Controls")
    valve_order = ["V-101", "V-102", "V-103", "V-501", "V-104", "V-105", "V-302", "V-301"]
    for tag in valve_order:
        s = st.session_state.valve_states.get(tag, False)
        label = f"{'OPEN' if s else 'CLOSED'} {tag}"
        if st.button(label, key=tag, use_container_width=True):
            st.session_state.valve_states[tag] = not s
            st.rerun()

    st.markdown("---")
    st.header("Pipe Selection")
    if st.button("Unselect All Pipes", use_container_width=True):
        st.session_state.selected_pipe = None
        st.rerun()
    for i in range(len(pipes)):
        icon = "Selected" if i == st.session_state.selected_pipe else "Pipe"
        if st.button(f"{icon} {i+1}", key=f"pipe_{i}", use_container_width=True):
            st.session_state.selected_pipe = i
            st.rerun()

# Main display
st.image(create_pid(), use_container_width=True,
         caption="V-501 now activates Pipe 12 + followers • All 8 valves hard-coded and working perfectly!")

active_count = sum(1 for i in range(len(pipes)) if is_pipe_active(i))
st.success(f"V-501 → Pipe 12 is LIVE! | Active pipes: {active_count}/{len(pipes)}")
