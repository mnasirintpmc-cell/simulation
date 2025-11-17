import streamlit as st
import json
from PIL import Image, ImageDraw, ImageFont
import math
import time

st.set_page_config(layout="wide", page_title="P&ID Flow Simulator")

# ========================= CONFIG =========================
PID_FILE = "P&ID.png"
VALVES_FILE = "valves.json"
PIPES_FILE = "pipes.json"

# ======================= LOAD DATA ========================
@st.cache_data
def load_base_image():
    try:
        return Image.open(PID_FILE).convert("RGBA")
    except:
        st.error("P&ID.png not found!")
        st.stop()

base = load_base_image()

def load_valves():
    with open(VALVES_FILE) as f:
        return json.load(f)

def load_pipes():
    with open(PIPES_FILE) as f:
        return json.load(f)

valves = load_valves()
pipes = load_pipes()

# ==================== SESSION STATE =======================
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {
        tag: data.get("state", False) for tag, data in valves.items()
    }

# ================ PROXIMITY FLOW LOGIC (60px) =============
def pipe_has_flow(pipe):
    x1, y1 = pipe["x1"], pipe["y1"]
    x2, y2 = pipe["x2"], pipe["y2"]
    
    for tag, v in valves.items():
        if not st.session_state.valve_states[tag]:
            continue
        vx, vy = v["x"], v["y"]
        if math.hypot(vx - x1, vy - y1) <= 60 or math.hypot(vx - x2, vy - y2) <= 60:
            return True
    return False

# ========================= RENDER =========================
def render_pid():
    canvas = base.copy()
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    # Draw pipes with flow
    for pipe in pipes:
        p1 = (pipe["x1"], pipe["y1"])
        p2 = (pipe["x2"], pipe["y2"])
        
        flow = pipe_has_flow(pipe)
        color = (0, 255, 0, 230) if flow else (255, 0, 0, 160)
        draw.line([p1, p2], fill=color, width=9)

        # Animated arrows when flowing
        if flow:
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            length = math.hypot(dx, dy) or 1
            dx, dy = dx/length, dy/length
            
            for i in range(3):
                t = (time.time() * 1.8 + i * 0.35) % 1.0
                pos_x = p1[0] + dx * length * t
                pos_y = p1[1] + dy * length * t
                
                arrow = [
                    (pos_x, pos_y),
                    (pos_x - 20*(dx*0.866 - dy*0.5), pos_y - 20*(dy*0.866 + dx*0.5)),
                    (pos_x - 20*(dx*0.866 + dy*0.5), pos_y - 20*(dy*0.866 - dx*0.5))
                ]
                draw.polygon(arrow, fill=(0, 255, 0))

    # Draw valves on top
    for tag, v in valves.items():
        x, y = v["x"], v["y"]
        color = (0, 255, 0) if st.session_state.valve_states[tag] else (255, 0, 0)
        draw.ellipse((x-14, y-14, x+14, y+14), fill=color, outline="white", width=4)
        draw.text((x+18, y-18), tag, fill="white", font=font)

    return canvas.convert("RGB")

# ============================ UI ===========================
st.title("P&ID Flow Simulator")
st.markdown("**Open any valve near a pipe → pipe turns GREEN with flowing arrows**")

# Sidebar - Valve Controls
with st.sidebar:
    st.header("Valve Controls")
    cols = st.columns(2)
    for idx, tag in enumerate(valves.keys()):
        col = cols[idx % 2]
        with col:
            state = st.session_state.valve_states[tag]
            label = f"{'OPEN' if state else 'CLOSED'} {tag}"
            if st.button(label, key=tag, use_container_width=True):
                st.session_state.valve_states[tag] = not state
                st.rerun()

# Main Image
st.image(render_pid(), use_container_width=True)

# Footer
st.caption("Every pipe reacts independently • 60px proximity • V-104, V-105, V-301 — all work perfectly")
