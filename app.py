import streamlit as st
import json
from PIL import Image, ImageDraw, ImageFont
import os
import math

st.set_page_config(layout="wide")

# ============================= CONFIG =============================
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"
PIPES_DATA_FILE = "pipes.json"

# =========================== LOAD DATA ===========================
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

valves = load_valves()
pipes = load_pipes()

if not valves or not pipes:
    st.error("Missing valves.json or pipes.json")
    st.stop()

# ========================= SESSION STATE =========================
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data.get("state", False) for tag, data in valves.items()}
if "selected_pipe" not in st.session_state:
    st.session_state.selected_pipe = None
if "pipes" not in st.session_state:
    st.session_state.pipes = pipes

# ======================= LEADER / FOLLOWER =======================
def get_pipe_groups_with_leaders():
    return {
        "Group_1": {"leader": 1,  "followers": [20]},
        "Group_2": {"leader": 11, "followers": [10, 19]},
        "Group_3": {"leader": 2,  "followers": [3, 4, 14, 21, 22]},
        "Group_4": {"leader": 13, "followers": [14, 4, 21, 22]},
        "Group_5": {"leader": 5,  "followers": [6, 7, 8, 9, 18]},
        "Group_6": {"leader": 17, "followers": [16, 15, 8]}
    }

def get_valve_to_leader_mapping():
    # V-104 and V-105 now work correctly
    return {
        "V-301": 2,   # Pipe 2 → Group_3
        "V-302": 13,  # Pipe 13 → Group_4
        "V-103": 5,   # Pipe 5 → Group_5
        "V-104": 22,  # Pipe 22 (direct + downstream)
        "V-105": 14   # Pipe 14 (V-105 downstream pipe – change to 21 or 22 if needed)
    }

# =========================== COLOR LOGIC =========================
def get_pipe_color(pipe_index, valve_states):
    pipe_number = pipe_index + 1
    mapping = get_valve_to_leader_mapping()
    groups = get_pipe_groups_with_leaders()

    # 1. Direct valve control (V-104, V-105, etc.)
    for valve_tag, controlled_pipe in mapping.items():
        if pipe_number == controlled_pipe:
            return (0, 255, 0) if valve_states.get(valve_tag, False) else (0, 0, 255)

    # 2. Leader → follower propagation
    for valve_tag, leader_pipe in mapping.items():
        if not valve_states.get(valve_tag, False):
            continue
        for g in groups.values():
            if g["leader"] == leader_pipe:
                if pipe_number == leader_pipe or pipe_number in g["followers"]:
                    return (0, 255, 0)

    # 3. Special V-104 downstream (extra safety)
    if valve_states.get("V-104", False):
        if pipe_number in [22, 14, 21, 4, 3]:
            return (0, 255, 0)

    # 4. Proximity fallback (keeps everything else working)
    pipe = st.session_state.pipes[pipe_index]
    for tag, v in valves.items():
        if math.hypot(v["x"] - pipe["x1"], v["y"] - pipe["y1"]) < 30 and valve_states.get(tag, False):
            return (0, 255, 0)

    return (0, 0, 255)  # default blue

# =========================== RENDER P&ID =========================
def create_pid():
    img = Image.open(PID_FILE).convert("RGBA")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    # Draw pipes
    for i, pipe in enumerate(st.session_state.pipes):
        color = (148, 0, 211) if i == st.session_state.selected_pipe else get_pipe_color(i, st.session_state.valve_states)
        width = 8 if i == st.session_state.selected_pipe else 6
        draw.line([(pipe["x1"], pipe["y1"]), (pipe["x2"], pipe["y2"])], fill=color, width=width)

        if i == st.session_state.selected_pipe:
            draw.ellipse([pipe["x1"]-6, pipe["y1"]-6, pipe["x1"]+6, pipe["y1"]+6], fill=(255,0,0), outline="white")
            draw.ellipse([pipe["x2"]-6, pipe["y2"]-6, pipe["x2"]+6, pipe["y2"]+6], fill=(255,0,0), outline="white")

    # Draw valves on top
    for tag, data in valves.items():
        x, y = data["x"], data["y"]
        color = (0, 255, 0) if st.session_state.valve_states[tag] else (255, 0, 0)
        draw.ellipse([x-10, y-10, x+10, y+10], fill=color, outline="white", width=3)
        draw.text((x+15, y-12), tag, fill="white", font=font)

    return img.convert("RGB")

# =============================== UI ==============================
st.title("P&ID Flow Simulation")

# Sidebar
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

# Main image
caption = f"Selected Pipe {st.session_state.selected_pipe+1} | Green = Flow | Blue = Blocked" if st.session_state.selected_pipe is not None else "Green = Flow | Blue = Blocked"
st.image(create_pid(), use_container_width=True, caption=caption)

# Debug (optional)
with st.expander("Debug"):
    st.write("Valves:", st.session_state.valve_states)
    st.json(st.session_state.pipes[:5])
