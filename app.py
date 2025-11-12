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
st.title("P&ID – Drag to Draw (No Packages)")

col_canvas, col_info = st.columns([3,1])

# === LOAD BASE IMAGE ===
try:
    base = Image.open(PID_FILE).convert("RGBA")
except:
    st.error(f"Missing {PID_FILE}")
    base = Image.new("RGBA", (1200, 800), (240,240,240,255))

# === DRAW FINAL IMAGE (for display below) ===
def draw_final_image():
    canvas = base.copy()
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    # Draw valves
    for tag, data in valves.items():
        x, y = data["x"], data["y"]
        col = (0,255,0,255) if st.session_state.valve_states.get(tag, False) else (255,0,0,255)
        draw.ellipse([x-10, y-10, x+10, y+10], fill=col, outline="white", width=3)
        draw.text((x+15, y-15),	tag, fill="white", font=font)

    # Draw user lines
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

    return canvas

# === DRAG-TO-DRAW HTML/JS COMPONENT ===
def drag_to_draw_component():
    buffered = io.BytesIO()
    base.save(buffered, format="PNG")
    b64 = buffered.getvalue().hex()

    html = f"""
    <div style="position:relative; border:2px solid #333; width:100%; height:{base.height}px; overflow:hidden;">
        <img src="data:image/png;base64,{b64}" id="bg-img" style="width:100%; height:100%; object-fit:contain;">
        <canvas id="draw-canvas" style="position:absolute; top:0; left:0; width:100%; height:100%; cursor:crosshair;"></canvas>
    </div>
    <script>
        const canvas = document.getElementById('draw-canvas');
        const ctx = canvas.getContext('2d');
        const img = document.getElementById('bg-img');
        let drawing = false;
        let startX, startY;

        function resize() {{
            canvas.width = img.clientWidth;
            canvas.height = img.clientHeight;
        }}
        resize();
        window.addEventListener('resize', resize);

        canvas.addEventListener('mousedown', (e) => {{
            if (!{str(st.session_state.drawing).lower()}) return;
            const rect = canvas.getBoundingClientRect();
            startX = e.clientX - rect.left;
            startY = e.clientY - rect.top;
            drawing = true;
            ctx.beginPath();
            ctx.moveTo(startX, startY);
        }});

        canvas.addEventListener('mousemove', (e) => {{
            if (!drawing) return;
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.strokeStyle = '#6464ff';
            ctx.lineWidth = 8;
            ctx.beginPath();
            ctx.moveTo(startX, startY);
            ctx.lineTo(x, y);
            ctx.stroke();
        }});

        canvas.addEventListener('mouseup', (e) => {{
            if (!drawing) return;
            drawing = false;
            const rect = canvas.getBoundingClientRect();
            const endX = e.clientX - rect.left;
            const endY = e.clientY - rect.top;

            const scaleX = img.naturalWidth / img.clientWidth;
            const scaleY = img.naturalHeight / img.clientHeight;

            const p1x = Math.round(startX * scaleX);
            const p1y = Math.round(startY * scaleY);
            const p2x = Math.round(endX * scaleX);
            const p2y = Math.round(endY * scaleY);

            window.parent.postMessage({{
                type: 'streamlit:setComponentValue',
                value: {{p1: {{x: p1x, y: p1y}}, p2: {{x: p2x, y: p2y}}}}
            }}, '*');

            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }});
    </script>
    """
    return st.components.v1.html(html, height=base.height + 50, key="drag_canvas")

# === DRAWING MODE ===
with col_canvas:
    if st.session_state.drawing:
        result = drag_to_draw_component()
        if result is not None and hasattr(result, "value"):
            line = result.value
            p1 = (line["p1"]["x"], line["p1"]["y"])
            p2 = (line["p2"]["x"], line["p2"]["y"])
            if not any(l["p1"] == p1 and l["p2"] == p2 for l in st.session_state.user_lines):
                st.session_state.user_lines.append({"p1": p1, "p2": p2})
                st.success(f"Line: {p1} to {p2}")
                st.rerun()

    # Show final image
    final_img = draw_final_image()
    buf = io.BytesIO()
    final_img.convert("RGB").save(buf, "PNG")
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
