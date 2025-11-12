import streamlit as st
import json
from PIL import Image, ImageDraw, ImageFont
import os
import io
import math
import time

st.set_page_config(layout="wide")
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"

# === LOAD VALVES ===
def load_valves():
    if not os.path.exists(DATA_FILE):
        st.error(f"Missing {DATA_FILE}")
        st.stop()
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Invalid {DATA_FILE}: {e}")
        st.stop()

valves = load_valves()

# === SESSION STATE ===
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: bool(data.get("state", False)) for tag, data in valves.items()}
if "user_lines" not in st.session_state:
    st.session_state.user_lines = []
if "drawing" not in st.session_state:
    st.session_state.drawing = False
if "start_point" not in st.session_state:
    st.session_state.start_point = None

# === SIDEBAR ===
with st.sidebar:
    st.header("Valve Controls")
    for tag, data in valves.items():
        state = st.session_state.valve_states[tag]
        col1, col2 = st.columns([3,1])
        with col1:
            if st.button(f"{'OPEN' if state else 'CLOSED'} {tag}",
                        type="primary" if state else "secondary",
                        key=f"btn_{tag}", use_container_width=True):
                st.session_state.valve_states[tag] = not state
                st.rerun()
        with col2:
            st.write("OPEN" if state else "CLOSED")

    st.markdown("---")
    open_cnt = sum(1 for v in st.session_state.valve_states.values() if v)
    st.metric("Open", open_cnt)
    st.metric("Closed", len(valves) - open_cnt)

    st.markdown("---")
    if st.button("Start Drawing", use_container_width=True):
        st.session_state.drawing = True
        st.session_state.start_point = None
        st.rerun()
    if st.button("Stop Drawing", use_container_width=True):
        st.session_state.drawing = False
        st.session_state.start_point = None
        st.rerun()

# === MAIN ===
st.title("P&ID – Click to Draw Flow Path")

col_img, col_info = st.columns([3,1])

# === LOAD BASE IMAGE ===
try:
    base = Image.open(PID_FILE).convert("RGBA")
except:
    st.error(f"Missing {PID_FILE}")
    base = Image.new("RGBA", (1200, 800), (240,240,240,255))

# === CLICKABLE IMAGE (ROBUST) ===
def clickable_image():
    buffered = io.BytesIO()
    base.save(buffered, format="PNG")
    b64 = buffered.getvalue().hex()

    html = f"""
    <div id="clickable-container" style="position:relative; display:inline-block;">
        <img src="data:image/png;base64,{b64}" id="pid-img" style="max-width:100%;">
        <canvas id="overlay" style="position:absolute; top:0; left:0; width:100%; height:100%; cursor:crosshair;"></canvas>
    </div>
    <script>
        const img = document.getElementById('pid-img');
        const canvas = document.getElementById('overlay');
        const ctx = canvas.getContext('2d');
        
        function resize() {{
            canvas.width = img.clientWidth;
            canvas.height = img.clientHeight;
        }}
        resize();
        window.addEventListener('resize', resize);

        function getScaled(x, y) {{
            const rect = canvas.getBoundingClientRect();
            const scaleX = img.naturalWidth / rect.width;
            const scaleY = img.naturalHeight / rect.height;
            return {{x: Math.round(x * scaleX), y: Math.round(y * scaleY)}};
        }}

        canvas.addEventListener('click', (e) => {{
            const rect = canvas.getBoundingClientRect();
            const px = e.clientX - rect.left;
            const py = e.clientY - rect.top;
            const scaled = getScaled(px, py);
            window.parent.postMessage({{type: 'streamlit:setComponentValue', value: [scaled]}}, '*');
        }});

        canvas.addEventListener('mousemove', (e) => {{
            const rect = canvas.getBoundingClientRect();
            const px = e.clientX - rect.left;
            const py = e.clientY - rect.top;
            const scaled = getScaled(px, py);
            window.parent.postMessage({{type: 'streamlit:mouse', value: scaled}}, '*');
        }});
    </script>
    """
    return st.components.v1.html(html, height=base.height + 50, key="clickable_img")

# === CAPTURE CLICK & MOUSE ===
click_data = None
mouse_pos = None

if st.session_state.drawing:
    result = clickable_image()
    # result is None, but messages come via postMessage
    # We use a workaround with st.session_state
    pass  # click handled below

# === READ MESSAGES (Streamlit hack) ===
if st.session_state.drawing:
    try:
        msg = st._get_message()
        if msg and msg.get("type") == "streamlit:setComponentValue":
            click_data = msg["value"]
        elif msg and msg.get("type") == "streamlit:mouse":
            mouse_pos = msg["value"]
    except:
        pass

# === PROCESS CLICK ===
if click_data and st.session_state.drawing:
    x, y = click_data[0]["x"], click_data[0]["y"]
    if st.session_state.start_point is None:
        st.session_state.start_point = (x, y)
        st.success(f"Start: ({x}, {y})")
        st.rerun()
    else:
        p1 = st.session_state.start_point
        p2 = (x, y)
        st.session_state.user_lines.append({"p1": p1, "p2": p2})
        st.session_state.start_point = None
        st.success(f"Line: {p1} to {p2}")
        st.rerun()

# === DRAW CANVAS ===
canvas = base.copy()
draw = ImageDraw.Draw(canvas)
font = ImageFont.load_default()

# Draw valves
for tag, data in valves.items():
    x, y = data["x"], data["y"]
    col = (0,255,0,255) if st.session_state.valve_states.get(tag, False) else (255,0,0,255)
    draw.ellipse([x-10, y-10, x+10, y+10], fill=col, outline="white", width=3)
    draw.text((x+15, y-15), tag, fill="white", font=font)

# Draw start point
if st.session_state.start_point:
    sx, sy = st.session_state.start_point
    draw.ellipse([sx-16, sy-16, sx+16, sy+16], fill=(255,0,0,200), outline="red", width=4)

    # Preview line
    if mouse_pos:
        mx, my = mouse_pos["x"], mouse_pos["y"]
        draw.line([(sx, sy), (mx, my)], fill=(100,100,255,180), width=6)
    else:
        cx, cy = base.width // 2, base.height // 2
        draw.line([(sx, sy), (cx, cy)], fill=(100,100,255,180), width=6)

# Draw user lines + flow
for line in st.session_state.user_lines:
    p1, p2 = line["p1"], line["p2"]
    up = nearest_valve(p1)
    down = nearest_valve(p2)
    flow = (up and down and 
            st.session_state.valve_states.get(up, False) and 
            st.session_state.valve_states.get(down, False))
    
    line_col = (0, 255, 0, 220) if flow else (255, 0, 0, 180)
    draw.line([p1, p2], fill=line_col, width=8)

    if flow:
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        length = math.hypot(dx, dy) or 1
        for i in range(3):
            ratio = (time.time() * 0.6 + i * 0.33) % 1
            ax = p1[0] + dx * ratio
            ay = p1[1] + dy * ratio
            angle = math.atan2(dy, dx)
            a_len = 14
            pts = [
                (ax, ay),
                (ax - a_len * math.cos(angle - 0.5), ay - a_len * math.sin(angle - 0.5)),
                (ax - a_len * math.cos(angle + 0.5), ay - a_len * math.sin(angle + 0.5))
            ]
            draw.polygon(pts, fill=(0, 200, 0))

# === DISPLAY ===
buf = io.BytesIO()
canvas.convert("RGB").save(buf, "PNG")
st.image(buf.getvalue(), use_container_width=True)

# === RIGHT PANEL ===
with col_info:
    st.header("Lines")
    if st.session_state.user_lines:
        for i, ln in enumerate(st.session_state.user_lines):
            p1, p2 = ln["p1"], ln["p2"]
            up = nearest_valve(p1)
            down = nearest_valve(p2)
            status = "Flow" if (up and down and 
                                st.session_state.valve_states.get(up, False) and 
                                st.session_state.valve_states.get(down, False)) else "Blocked"
            st.write(f"**Line {i+1}**: {status}")
            st.caption(f"{p1} to {p2}\nUp: {up or '—'} | Down: {down or '—'}")
            if st.button("Delete", key=f"del_{i}"):
                st.session_state.user_lines.pop(i)
                st.rerun()
    else:
        st.info("Click **Start Drawing** and click two points.")

# === HELPER ===
def nearest_valve(point, max_dist=60):
    x0, y0 = point
    best = None
    best_d = float('inf')
    for tag, data in valves.items():
        d = math.hypot(data["x"] - x0, data["y"] - y0)
        if d < best_d and d <= max_dist:
            best_d = d
            best = tag
    return best
