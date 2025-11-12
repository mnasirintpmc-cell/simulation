import streamlit as st
import json
from PIL import Image, ImageDraw, ImageFont
import os
import io
import time
import math

# --------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------
st.set_page_config(layout="wide")
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"

# --------------------------------------------------------------
# LOAD VALVES (force boolean state)
# --------------------------------------------------------------
def load_valves():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"valves.json error: {e}")
    return {}

valves = load_valves()
if not valves:
    st.error("No valves in valves.json – add at least two valves.")
    st.stop()

if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: bool(data.get("state", False)) for tag, data in valves.items()}

# --------------------------------------------------------------
# USER-DRAWN PIPE STATE
# --------------------------------------------------------------
if "user_lines" not in st.session_state:
    st.session_state.user_lines = []          # list of dicts: {"p1":(x,y), "p2":(x,y), "confirmed":True}
if "temp_line" not in st.session_state:
    st.session_state.temp_line = None         # None or (x1,y1,x2,y2) while drawing
if "drawing" not in st.session_state:
    st.session_state.drawing = False

# --------------------------------------------------------------
# SIDEBAR – VALVE CONTROLS (your original)
# --------------------------------------------------------------
with st.sidebar:
    st.header("Valve Controls")
    for tag, data in valves.items():
        state = st.session_state.valve_states[tag]
        label = f"{'OPEN' if state else 'CLOSED'} {tag}"
        btn_type = "primary" if state else "secondary"
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button(label, key=f"btn_{tag}", type=btn_type, use_container_width=True):
                st.session_state.valve_states[tag] = not state
                st.rerun()
        with col2:
            st.write("OPEN" if state else "CLOSED")

    st.markdown("---")
    open_cnt = sum(1 for v in st.session_state.valve_states.values() if v)
    st.metric("Open Valves", open_cnt)
    st.metric("Closed Valves", len(valves) - open_cnt)

    st.markdown("---")
    colA, colB = st.columns(2)
    with colA:
        if st.button("Open All", use_container_width=True):
            for t in valves: st.session_state.valve_states[t] = True
            st.rerun()
    with colB:
        if st.button("Close All", use_container_width=True):
            for t in valves: st.session_state.valve_states[t] = False
            st.rerun()

    st.markdown("---")
    if st.button("Start / Stop Drawing", use_container_width=True):
        st.session_state.drawing = not st.session_state.drawing
        st.session_state.temp_line = None
        st.rerun()

# --------------------------------------------------------------
# MAIN UI
# --------------------------------------------------------------
st.title("P&ID – Draw Your Own Flow Path")
col_img, col_info = st.columns([3, 1])

# --------------------------------------------------------------
# IMAGE WITH CLICK HANDLER (Streamlit native)
# --------------------------------------------------------------
with col_img:
    # Load base image once
    try:
        base = Image.open(PID_FILE).convert("RGBA")
    except Exception:
        base = Image.new("RGBA", (1200, 800), (255, 255, 255, 255))

    # --------------------------------------------------
    # 1. USER CLICK → build temp line
    # --------------------------------------------------
    if st.session_state.drawing:
        st.info("Click **two points** on the diagram to draw a pipe segment. "
                "After the second click the line is locked until you **Confirm** or **Delete**.")
        # Streamlit click detection (returns dict with x,y in *pixels* of the image)
        click = st.experimental_get_query_params().get("click", [None])[0]
        if click:
            try:
                cx, cy = map(int, click.split(","))
            except Exception:
                cx, cy = None, None
        else:
            cx, cy = None, None

        if cx is not None:
            if st.session_state.temp_line is None:
                # first point
                st.session_state.temp_line = (cx, cy, cx, cy)
            else:
                # second point → lock it
                x1, y1, _, _ = st.session_state.temp_line
                st.session_state.temp_line = (x1, y1, cx, cy)
                # auto-confirm for demo (you can keep manual confirm)
                st.session_state.user_lines.append({
                    "p1": (x1, y1),
                    "p2": (cx, cy),
                    "confirmed": True
                })
                st.session_state.temp_line = None
                st.rerun()

    # --------------------------------------------------
    # 2. DRAW EVERYTHING (valves + user lines + flow colour)
    # --------------------------------------------------
    canvas = base.copy()
    draw = ImageDraw.Draw(canvas)

    # ---- draw valves (same as your original) ----
    for tag, data in valves.items():
        x, y = data["x"], data["y"]
        col = (0, 255, 0, 255) if st.session_state.valve_states[tag] else (255, 0, 0, 255)
        draw.ellipse([x-8, y-8, x+8, y+8], fill=col, outline="white", width=2)
        draw.text((x+12, y-10), tag, fill="white")

    # ---- draw temporary line (while drawing) ----
    if st.session_state.temp_line:
        x1, y1, x2, y2 = st.session_state.temp_line
        draw.line([(x1, y1), (x2, y2)], fill=(100, 100, 100, 180), width=6)

    # ---- draw confirmed user lines + flow logic ----
    for line in st.session_state.user_lines:
        p1, p2 = line["p1"], line["p2"]
        # find nearest valves to each end
        up_val = nearest_valve(p1)
        down_val = nearest_valve(p2)

        # flow = green only when BOTH valves are open
        flow_ok = (up_val and st.session_state.valve_states.get(up_val, False) and
                   down_val and st.session_state.valve_states.get(down_val, False))

        line_col = (0, 255, 0, 200) if flow_ok else (255, 0, 0, 150)
        draw.line([p1, p2], fill=line_col, width=7)

        # simple moving arrow (3 arrows per segment)
        if flow_ok:
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            length = math.hypot(dx, dy) or 1
            for i in range(3):
                ratio = (time.time() * 0.5 + i * 0.33) % 1
                ax = p1[0] + dx * ratio
                ay = p1[1] + dy * ratio
                angle = math.atan2(dy, dx)
                a_len = 12
                pts = [
                    (ax, ay),
                    (ax - a_len * math.cos(angle - 0.5), ay - a_len * math.sin(angle - 0.5)),
                    (ax - a_len * math.cos(angle + 0.5), ay - a_len * math.sin(angle + 0.5))
                ]
                draw.polygon(pts, fill=(0, 180, 0))

    # --------------------------------------------------
    # 3. DISPLAY IMAGE
    # --------------------------------------------------
    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, "PNG")
    st.image(buf.getvalue(), use_container_width=True)

# --------------------------------------------------------------
# RIGHT PANEL – LINE MANAGEMENT
# --------------------------------------------------------------
with col_info:
    st.header("User Lines")
    if st.session_state.user_lines:
        for idx, ln in enumerate(st.session_state.user_lines):
            p1, p2 = ln["p1"], ln["p2"]
            up = nearest_valve(p1)
            down = nearest_valve(p2)
            status = "Flow" if (up and down and
                                st.session_state.valve_states.get(up, False) and
                                st.session_state.valve_states.get(down, False)) else "Blocked"
            st.write(f"**Line {idx+1}** – {status}")
            st.caption(f"({p1[0]},{p1[1]}) → ({p2[0]},{p2[1]})  "
                       f"Upstream: {up or '-'} | Downstream: {down or '-'}")
            col_del, _ = st.columns([1, 3])
            with col_del:
                if st.button("Delete", key=f"del_{idx}"):
                    st.session_state.user_lines.pop(idx)
                    st.rerun()
    else:
        st.info("No custom lines yet. Click **Start / Stop Drawing** and click two points.")

    st.markdown("---")
    st.write("**How it works**")
    st.markdown("- Click **Start / Stop Drawing** → click **two points** on the P&ID.")
    st.markdown("- The line is **locked** after the second click.")
    st.markdown("- It turns **green** **only** when **both nearest valves are open**.")
    st.markdown("- Delete any line with the **Delete** button.")

# --------------------------------------------------------------
# HELPER: nearest valve to a point (within 40 px)
# --------------------------------------------------------------
def nearest_valve(point, max_dist=40):
    x0, y0 = point
    best = None
    best_d = float('inf')
    for tag, data in valves.items():
        vx, vy = data["x"], data["y"]
        d = math.hypot(vx - x0, vy - y0)
        if d < best_d and d <= max_dist:
            best_d = d
            best = tag
    return best

# --------------------------------------------------------------
# CLICK → query param (Streamlit hack)
# --------------------------------------------------------------
# This tiny script runs only when the image is clicked.
# It adds ?click=x,y to the URL, which we read above.
js = """
<script>
const img = document.querySelector('img[src*="data:image/png"]');
if (img) {
    img.style.cursor = 'crosshair';
    img.onclick = function(e) {
        const rect = img.getBoundingClientRect();
        const x = Math.round(e.clientX - rect.left);
        const y = Math.round(e.clientY - rect.top);
        const params = new URLSearchParams(window.location.search);
        params.set('click', x + ',' + y);
        window.history.replaceState({}, '', `${window.location.pathname}?${params}`);
    };
}
</script>
"""
if st.session_state.drawing:
    st.markdown(js, unsafe_allow_html=True)
