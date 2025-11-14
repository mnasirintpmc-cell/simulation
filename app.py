import streamlit as st
import json
from PIL import Image, ImageDraw, ImageFont
import os
import math
import time
import io

st.set_page_config(layout="wide")

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
PID_FILE        = "P&ID.png"
DATA_FILE       = "valves.json"
PIPES_DATA_FILE = "pipes.json"

# ----------------------------------------------------------------------
# 1. CACHED P&ID LOADER
# ----------------------------------------------------------------------
@st.cache_data
def load_pid_image():
    try:
        img = Image.open(PID_FILE).convert("RGBA")
        return img
    except Exception as e:
        st.error(f"Failed to load {PID_FILE}: {e}")
        return Image.new("RGBA", (1200, 800), (240, 240, 240, 255))

base_img = load_pid_image()
canvas   = base_img.copy()
draw     = ImageDraw.Draw(canvas)
font     = ImageFont.load_default()

# ----------------------------------------------------------------------
# 2. LOAD VALVES
# ----------------------------------------------------------------------
def load_valves():
    if not os.path.exists(DATA_FILE):
        st.error(f"Missing {DATA_FILE}")
        st.stop()
    with open(DATA_FILE) as f:
        return json.load(f)

valves = load_valves()

# ----------------------------------------------------------------------
# 3. LOAD / SCALE / SNAP PIPES
# ----------------------------------------------------------------------
def get_image_dimensions():
    return base_img.size

def scale_lines(raw, figma_w=184, figma_h=259):
    """Scale Figma coordinates → actual P&ID size."""
    if not raw:
        return []
    w, h = get_image_dimensions()
    sx = w / figma_w
    sy = h / figma_h
    return [
        {
            "x1": int(l["x1"] * sx),
            "y1": int(l["y1"] * sy),
            "x2": int(l["x2"] * sx),
            "y2": int(l["y2"] * sy),
        }
        for l in raw
    ]

def snap_to_valve(p, max_dist=80):
    x, y = p
    best = p
    dmin = float("inf")
    for tag, d in valves.items():
        vx, vy = d["x"], d["y"]
        dist = math.hypot(vx - x, vy - y)
        if dist < dmin and dist <= max_dist:
            dmin = dist
            best = (vx, vy)
    return best

def load_pipes():
    if not os.path.exists(PIPES_DATA_FILE):
        st.warning(f"Missing {PIPES_DATA_FILE}")
        return []
    with open(PIPES_DATA_FILE) as f:
        raw = json.load(f)

    # Accept both flat list and {"lines": [...]}
    raw = raw.get("lines", raw) if isinstance(raw, dict) else raw

    # 1. Scale
    scaled = scale_lines(raw)

    # 2. Optional snap (controlled by UI checkbox)
    if st.session_state.get("snap_enabled", True):
        snapped = []
        for ln in scaled:
            p1 = snap_to_valve((ln["x1"], ln["y1"]))
            p2 = snap_to_valve((ln["x2"], ln["y2"]))
            if p1 != p2:
                snapped.append({"x1": p1[0], "y1": p1[1], "x2": p2[0], "y2": p2[1]})
        scaled = snapped

    return scaled

def save_pipes(pipes):
    with open(PIPES_DATA_FILE, "w") as f:
        json.dump(pipes, f, indent=2)

# ----------------------------------------------------------------------
# 4. SESSION STATE INITIALISATION
# ----------------------------------------------------------------------
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {t: d.get("state", False) for t, d in valves.items()}

if "pipes" not in st.session_state:
    st.session_state.pipes = load_pipes()

if "selected_pipe" not in st.session_state:
    st.session_state.selected_pipe = 0 if st.session_state.pipes else None

if "snap_enabled" not in st.session_state:
    st.session_state.snap_enabled = True

# ----------------------------------------------------------------------
# 5. HELPER: Reset pipes to a visible grid
# ----------------------------------------------------------------------
def reset_all_pipes_to_visible():
    w, h = get_image_dimensions()
    cols = 4
    rows = (len(st.session_state.pipes) + cols - 1) // cols
    spacing_x = w // (cols + 1)
    spacing_y = h // (rows + 1)
    new = []
    for i in range(len(st.session_state.pipes)):
        row, col = divmod(i, cols)
        cx = spacing_x * (col + 1)
        cy = spacing_y * (row + 1)
        new.append({"x1": cx - 50, "y1": cy, "x2": cx + 50, "y2": cy})
    return new

# ----------------------------------------------------------------------
# 6. DRAWING ROUTINE
# ----------------------------------------------------------------------
def create_pid_with_valves_and_pipes():
    # start from the cached image
    canvas = base_img.copy()
    draw   = ImageDraw.Draw(canvas)
    w, h   = canvas.size

    # ---------- 1. PIPES ----------
    for i, pipe in enumerate(st.session_state.pipes):
        # flow detection
        up   = next((t for t, d in valves.items()
                     if math.hypot(d["x"] - pipe["x1"], d["y"] - pipe["y1"]) < 60), None)
        down = next((t for t, d in valves.items()
                     if math.hypot(d["x"] - pipe["x2"], d["y"] - pipe["y2"]) < 60), None)
        flow = (up and down and
                st.session_state.valve_states.get(up, False) and
                st.session_state.valve_states.get(down, False))

        # colour / thickness
        col   = (0, 255, 0, 220) if flow else (255, 0, 0, 180)
        width = 8 if i == st.session_state.selected_pipe else 6
        draw.line([(pipe["x1"], pipe["y1"]), (pipe["x2"], pipe["y2"])],
                  fill=col, width=width)

        # selected pipe markers
        if i == st.session_state.selected_pipe:
            draw.ellipse([pipe["x1"]-6, pipe["y1"]-6, pipe["x1"]+6, pipe["y1"]+6],
                         fill=(255, 0, 0), outline="white", width=2)
            draw.ellipse([pipe["x2"]-6, pipe["y2"]-6, pipe["x2"]+6, pipe["y2"]+6],
                         fill=(255, 0, 0), outline="white", width=2)

        # animated arrows when flow is active
        if flow:
            dx, dy = pipe["x2"] - pipe["x1"], pipe["y2"] - pipe["y1"]
            for j in range(3):
                t = (time.time() * 0.6 + j * 0.33) % 1
                ax = pipe["x1"] + dx * t
                ay = pipe["y1"] + dy * t
                ang = math.atan2(dy, dx)
                a_len = 14
                pts = [
                    (ax, ay),
                    (ax - a_len * math.cos(ang - 0.5), ay - a_len * math.sin(ang - 0.5)),
                    (ax - a_len * math.cos(ang + 0.5), ay - a_len * math.sin(ang + 0.5))
                ]
                draw.polygon(pts, fill=(0, 200, 0))

    # ---------- 2. VALVES ----------
    for tag, data in valves.items():
        x, y = data["x"], data["y"]
        col = (0, 255, 0) if st.session_state.valve_states[tag] else (255, 0, 0)
        draw.ellipse([x-8, y-8, x+8, y+8], fill=col, outline="white", width=2)
        draw.text((x+12, y-10), tag, fill="white", stroke_fill="black", stroke_width=1)

    return canvas.convert("RGB")

# ----------------------------------------------------------------------
# 7. UI
# ----------------------------------------------------------------------
st.title("P&ID Interactive Simulation")

# ---- Top bar -------------------------------------------------
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    st.info("Pipe positions **auto-save** when you move them")
with c2:
    if st.button("MANUAL SAVE", use_container_width=True, type="primary"):
        save_pipes(st.session_state.pipes)
        st.success("Saved!")
with c3:
    if st.session_state.pipes and st.button("RESET ALL", use_container_width=True, type="secondary"):
        st.session_state.pipes = reset_all_pipes_to_visible()
        save_pipes(st.session_state.pipes)
        st.rerun()

# ---- Snap toggle ------------------------------------------------
st.session_state.snap_enabled = st.checkbox(
    "Snap pipe ends to nearest valve", value=st.session_state.snap_enabled)

# ---- Main layout ------------------------------------------------
col_img, col_ctrl = st.columns([3, 1])

with col_img:
    img = create_pid_with_valves_and_pipes()
    st.image(img, use_container_width=True,
             caption="Selected Pipe | Normal Pipe | Green = Flow")

# ------------------------------------------------------------------
# CONTROLS (right column)
# ------------------------------------------------------------------
with col_ctrl:
    st.header("Controls")

    # ---- Pipe selection -------------------------------------------------
    if st.session_state.pipes:
        st.subheader("Select Pipe")
        cols = st.columns(4)
        for i, _ in enumerate(st.session_state.pipes):
            with cols[i % 4]:
                ico = "Selected" if i == st.session_state.selected_pipe else "Normal"
                if st.button(f"{ico} {i+1}", key=f"sel_{i}", use_container_width=True):
                    st.session_state.selected_pipe = i
                    st.rerun()

    # ---- Selected pipe editor -------------------------------------------
    if st.session_state.selected_pipe is not None:
        pipe = st.session_state.pipes[st.session_state.selected_pipe]

        st.subheader(f"Pipe {st.session_state.selected_pipe + 1}")
        st.caption(f"({pipe['x1']},{pipe['y1']}) → ({pipe['x2']},{pipe['y2']})")

        # quick actions
        a1, a2, a3 = st.columns(3)
        with a1:
            if st.button("H", help="Horizontal", use_container_width=True):
                cx = (pipe["x1"] + pipe["x2"]) // 2
                cy = (pipe["y1"] + pipe["y2"]) // 2
                pipe.update({"x1": cx-50, "y1": cy, "x2": cx+50, "y2": cy})
                save_pipes(st.session_state.pipes); st.rerun()
        with a2:
            if st.button("V", help="Vertical", use_container_width=True):
                cx = (pipe["x1"] + pipe["x2"]) // 2
                cy = (pipe["y1"] + pipe["y2"]) // 2
                pipe.update({"x1": cx, "y1": cy-50, "x2": cx, "y2": cy+50})
                save_pipes(st.session_state.pipes); st.rerun()
        with a3:
            if st.button("C", help="Center", use_container_width=True):
                w, h = get_image_dimensions()
                pipe.update({"x1": w//2-50, "y1": h//2, "x2": w//2+50, "y2": h//2})
                save_pipes(st.session_state.pipes); st.rerun()

        # movement arrows
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            if st.button("Up", use_container_width=True):
                pipe["y1"] -= 10; pipe["y2"] -= 10
                save_pipes(st.session_state.pipes); st.rerun()
        with m2:
            if st.button("Down", use_container_width=True):
                pipe["y1"] += 10; pipe["y2"] += 10
                save_pipes(st.session_state.pipes); st.rerun()
        with m3:
            if st.button("Left", use_container_width=True):
                pipe["x1"] -= 10; pipe["x2"] -= 10
                save_pipes(st.session_state.pipes); st.rerun()
        with m4:
            if st.button("Right", use_container_width=True):
                pipe["x1"] += 10; pipe["x2"] += 10
                save_pipes(st.session_state.pipes); st.rerun()

        # exact coordinates
        c1, c2 = st.columns(2)
        with c1:
            nx1 = st.number_input("X1", value=pipe["x1"], key="nx1")
            ny1 = st.number_input("Y1", value=pipe["y1"], key="ny1")
        with c2:
            nx2 = st.number_input("X2", value=pipe["x2"], key="nx2")
            ny2 = st.number_input("Y2", value=pipe["y2"], key="ny2")
        if st.button("APPLY COORDINATES", use_container_width=True, type="primary"):
            pipe.update({"x1": nx1, "y1": ny1, "x2": nx2, "y2": ny2})
            save_pipes(st.session_state.pipes)
            st.rerun()

    # ---- Valve toggles --------------------------------------------------
    st.markdown("---")
    st.subheader("Valves")
    vcols = st.columns(3)
    for i, (tag, _) in enumerate(valves.items()):
        with vcols[i % 3]:
            state = st.session_state.valve_states[tag]
            ico = "Open" if state else "Closed"
            if st.button(f"{ico} {tag}", key=f"v_{tag}", use_container_width=True):
                st.session_state.valve_states[tag] = not state
                st.rerun()

# ----------------------------------------------------------------------
# DEBUG (collapsed)
# ----------------------------------------------------------------------
with st.expander("Debug", expanded=False):
    st.write("P&ID size:", get_image_dimensions())
    st.write("Pipes:", len(st.session_state.pipes))
    st.write("Snap enabled:", st.session_state.snap_enabled)
    if st.session_state.selected_pipe is not None:
        st.json(st.session_state.pipes[st.session_state.selected_pipe])
