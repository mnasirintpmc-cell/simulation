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
if "pending_line" not in st.session_state:
    st.session_state.pending_line = None

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
        st.rerun()
    if st.button("Stop Drawing", use_container_width=True):
        st.session_state.drawing = False
        st.rerun()

# === MAIN ===
st.title("P&ID – Drag to Draw (FINAL)")

col_canvas, col_info = st.columns([3,1])

# === LOAD BASE IMAGE ===
try:
    base = Image.open(PID_FILE).convert("RGBA")
except:
    st.error(f"Missing {PID_FILE}")
    base = Image.new("RGBA", (1200, 800), (240,240,240,255))

# === DRAW FINAL IMAGE ===
def draw_final():
    canvas = base.copy()
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    # Valves
    for tag, data in valves.items():
        x, y = data["x"], data["y"]
        col = (0,255,0,255) if st.session_state.valve_states.get(tag, False) else (255,0,0,255)
        draw.ellipse([x-10, y-10, x+10, y+10], fill=col, outline="white", width=3)
        draw.text((x+15, y-15), tag, fill="white", font=font)

    # User lines
    for line in st.session_state.user_lines:
        p1, p2 = line["p1"], line["p2"]
        up = nearest_valve(p1)
        down = nearest_valve(p2)
        flow = up and down and st.session_state.valve_states.get(up, False) and st.session_state.valve_states.get(down, False)
        col = (0, 255, 0, 220) if flow else (255, 0, 0, 180)
        draw.line([p1, p2], fill=col, width=8)
        if flow:
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            for i in range(3):
                t = (time.time() * 0.6 + i * 0.33) % 1
                ax = p1[0] + dx * t
                ay = p1[1] + dy * t
                angle = math.atan2(dy, dx)
                a_len = 14
                pts = [
                    (ax, ay),
                    (ax - a_len * math.cos(angle - 0.5), ay - a_len * math.sin(angle - 0.5)),
                    (ax - a_len * math.cos(angle + 0.5), ay - a_len * math.sin(angle + 0.5))
                ]
                draw.polygon(pts, fill=(0, 200, 0))
    return canvas

# === DRAG COMPONENT (NO RETURN) ===
def drag_component():
    if not st.session_state.drawing:
        return
    buf = io.BytesIO()
    base.save(buf, "PNG")
    b64 = buf.getvalue().hex()

    html = f"""
    <div style="position:relative; width:100%; height:{base.height}px;">
        <img src="data:image/png;base64,{b64}" id="bg" style="width:100%; height:100%; object-fit:contain;">
        <canvas id="draw" style="position:absolute; top:0; left:0; width:100%; height:100%; cursor:crosshair;"></canvas>
    </div>
    <script>
        const canvas = document.getElementById('draw');
        const ctx = canvas.getContext('2d');
        const img = document.getElementById('bg');
        let drawing = false;
        let sx, sy;

        function resize() {{
            canvas.width = img.clientWidth;
            canvas.height = img.clientHeight;
        }}
        resize();
        window.addEventListener('resize', resize);

        canvas.addEventListener('mousedown', e => {{
            const r = canvas.getBoundingClientRect();
            sx = e.clientX - r.left;
            sy = e.clientY - r.top;
            drawing = true;
            ctx.beginPath();
            ctx.moveTo(sx, sy);
        }});

        canvas.addEventListener('mousemove', e => {{
            if (!drawing) return;
            const r = canvas.getBoundingClientRect();
            const x = e.clientX - r.left;
            const y = e.clientY - r.top;
            ctx.clearRect(0,0,canvas.width,canvas.height);
            ctx.strokeStyle = '#6464ff';
            ctx.lineWidth = 8;
            ctx.beginPath();
            ctx.moveTo(sx, sy);
            ctx.lineTo(x, y);
            ctx.stroke();
        }});

        canvas.addEventListener('mouseup', e => {{
            if (!drawing) return;
            drawing = false;
            const r = canvas.getBoundingClientRect();
            const ex = e.clientX - r.left;
            const ey = e.clientY - r.top;

            const scaleX = img.naturalWidth / img.clientWidth;
            const scaleY = img.naturalHeight / img.clientHeight;

            const p1 = {{x: Math.round(sx * scaleX), y: Math.round(sy * scaleY)}};
            const p2 = {{x: Math.round(ex * scaleX), y: Math.round(ey * scaleY)}};

            window.parent.postMessage({{
                type: 'streamlit:setComponentValue',
                value: {{p1, p2}}
            }}, '*');

            ctx.clearRect(0,0,canvas.width,canvas.height);
        }});
    </script>
    """
    st.components.v1.html(html, height=base.height + 50, key="drag")

# === CALL COMPONENT (NO ASSIGNMENT) ===
with col_canvas:
    drag_component()

    # === GET LINE FROM postMessage ===
    try:
        msg = st._get_message()
        if msg and msg.get("type") == "streamlit:setComponentValue":
            data = msg["value"]
            p1 = (data["p1"]["x"], data["p1"]["y"])
            p2 = (data["p2"]["x"], data["p2"]["y"])
            if not any(l["p1"] == p1 and l["p2"] == p2 for l in st.session_state.user_lines):
                st.session_state.user_lines.append({"p1": p1, "p2": p2})
                st.success(f"Line: {p1} to {p2}")
                st.rerun()
    except:
        pass

    # === SHOW FINAL IMAGE ===
    final = draw_final()
    buf = io.BytesIO()
    final.convert("RGB").save(buf, "PNG")
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
        st.info("Click **Start Drawing** and **drag** on image.")

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
