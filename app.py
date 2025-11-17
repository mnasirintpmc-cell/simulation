import streamlit as st
import json
from PIL import Image, ImageDraw, ImageFont
import os
import math
import time

st.set_page_config(layout="wide")

# === CONFIG ===
PID_FILE        = "P&ID.png"
VALVES_FILE     = "valves.json"
PIPES_FILE      = "pipes.json"

# === CACHED P&ID LOADER ===
@st.cache_data
def load_pid():
    try:
        return Image.open(PID_FILE).convert("RGBA")
    except Exception as e:
        st.error(f"Failed to load {PID_FILE}: {e}")
        return Image.new("RGBA", (1200, 800), (240, 240, 240, 255))

base = load_pid()

# === LOAD VALVES & PIPES ===
def load_valves():
    if not os.path.exists(VALVES_FILE):
        st.error(f"Missing {VALVES_FILE}")
        st.stop()
    with open(VALVES_FILE) as f:
        return json.load(f)

def load_pipes():
    if not os.path.exists(PIPES_FILE):
        st.error(f"Missing {PIPES_FILE}")
        st.stop()
    with open(PIPES_FILE) as f:
        data = json.load(f)
        return data.get("lines", data) if isinstance(data, dict) else data

valves = load_valves()
pipes = load_pipes()

# === SESSION STATE ===
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {
        tag: bool(data.get("state", False)) for tag, data in valves.items()
    }
if "selected_pipe" not in st.session_state:
    st.session_state.selected_pipe = None

# === LEADER-FOLLOWER & VALVE MAPPING ===
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
    return {
        "V-301": 2,
        "V-302": 13,
        "V-103": 5,
        "V-104": 22
    }

def nearest_valve(point, max_dist=60):
    x0, y0 = point
    best = None
    dmin = float('inf')
    for tag, data in valves.items():
        d = math.hypot(data["x"] - x0, data["y"] - y0)
        if d < dmin and d <= max_dist:
            dmin = d
            best = tag
    return best

def get_pipe_color(pipe_index):
    pipe_number = pipe_index + 1
    valve_mapping = get_valve_to_leader_mapping()
    pipe_groups = get_pipe_groups_with_leaders()

    # Direct valve control
    for valve_tag, controlled_pipe in valve_mapping.items():
        if pipe_number == controlled_pipe:
            return (0, 255, 0) if st.session_state.valve_states.get(valve_tag, False) else (0, 0, 255)

    # Leader pipe
    for group in pipe_groups.values():
        if pipe_number == group["leader"]:
            for valve_tag, controlled_leader in valve_mapping.items():
                if group["leader"] == controlled_leader:
                    return (0, 255, 0) if st.session_state.valve_states.get(valve_tag, False) else (0, 0, 255)
            # Fallback to proximity
            p1 = (pipes[pipe_index]["x1"], pipes[pipe_index]["y1"])
            near_valve = nearest_valve(p1)
            if near_valve and st.session_state.valve_states.get(near_valve, False):
                return (0, 255, 0)
            return (0, 0, 255)

    # Follower pipe
    for group in pipe_groups.values():
        if pipe_number in group["followers"]:
            leader_index = group["leader"] - 1
            return get_pipe_color(leader_index)

    # Standalone pipe (proximity)
    p1 = (pipes[pipe_index]["x1"], pipes[pipe_index]["y1"])
    near_valve = nearest_valve(p1)
    if near_valve and st.session_state.valve_states.get(near_valve, False):
        return (0, 255, 0)
    return (0, 0, 255)

# === RENDER P&ID ===
def render():
    canvas = base.copy()
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    # Draw pipes
    for i, pipe in enumerate(pipes):
        color = get_pipe_color(i)
        width = 8 if i == st.session_state.selected_pipe else 6
        draw.line([(pipe["x1"], pipe["y1"]), (pipe["x2"], pipe["y2"])], fill=color, width=width)

        if i == st.session_state.selected_pipe:
            draw.ellipse([pipe["x1"]-6, pipe["y1"]-6, pipe["x1"]+6, pipe["y1"]+6], fill=(255,0,0))
            draw.ellipse([pipe["x2"]-6, pipe["y2"]-6, pipe["x2"]+6, pipe["y2"]+6], fill=(255,0,0))

        if color == (0, 255, 0, 220):  # Flow active → animate arrows
            dx = pipe["x2"] - pipe["x1"]
            dy = pipe["y2"] - pipe["y1"]
            for j in range(3):
                t = (time.time() * 0.6 + j * 0.33) % 1
                ax = pipe["x1"] + dx * t
                ay = pipe["y1"] + dy * t
                ang = math.atan2(dy, dx)
                pts = [
                    (ax, ay),
                    (ax - 14*math.cos(ang-0.5), ay - 14*math.sin(ang-0.5)),
                    (ax - 14*math.cos(ang+0.5), ay - 14*math.sin(ang+0.5))
                ]
                draw.polygon(pts, fill=(0,200,0))

    # Draw valves
    for tag, data in valves.items():
        x, y = data["x"], data["y"]
        col = (0,255,0) if st.session_state.valve_states.get(tag, False) else (255,0,0)
        draw.ellipse([x-10, y-10, x+10, y+10], fill=col, outline="white", width=3)
        draw.text((x+15, y-15), tag, fill="white", font=font)

    return canvas.convert("RGB")

# === UI ===
st.title("P&ID Interactive Simulation")

# Valve controls
with st.sidebar:
    st.header("Valve Controls")
    cols = st.columns(3)
    for i, (tag, _) in enumerate(valves.items()):
        with cols[i % 3]:
            state = st.session_state.valve_states[tag]
            if st.button(f"{'OPEN' if state else 'CLOSED'} {tag}", key=tag):
                st.session_state.valve_states[tag] = not state
                st.rerun()

    st.markdown("---")
    st.subheader("Pipe Selection")
    if pipes:
        cols = st.columns(4)
        for i in range(len(pipes)):
            with cols[i % 4]:
                ico = "Selected" if i == st.session_state.selected_pipe else "Normal"
                if st.button(f"{ico} {i+1}", key=f"p_{i}"):
                    st.session_state.selected_pipe = i
                    st.rerun()

st.image(render(), use_container_width=True,
         caption="Green = Flow Active | Blue = No Flow | Purple = Selected Pipe")

# Debug
with st.expander("Debug"):
    st.write("Pipes loaded:", len(pipes))
    st.write("Valve states:", st.session_state.valve_states)
    if pipes and st.session_state.selected_pipe is not None:
        st.json(pipes[st.session_state.selected_pipe])
