import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import math
import time

st.set_page_config(layout="wide")
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"

# === LOAD VALVES ===
def load_valves():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

valves = load_valves()
if not valves:
    st.error("No valves.json")
    st.stop()

# === SESSION STATE ===
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: bool(data.get("state", False)) for tag, data in valves.items()}
if "user_lines" not in st.session_state:
    st.session_state.user_lines = []  # [{"p1":(x,y), "p2":(x,y)}]
if "drawing" not in st.session_state:
    st.session_state.drawing = False
if "start_point" not in st.session_state:
    st.session_state.start_point = None  # (x,y) after first click

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
    if st.button("Start Drawing Pipe", use_container_width=True):
        st.session_state.drawing = True
        st.session_state.start_point = None
        st.rerun()
    if st.button("Stop Drawing", use_container_width=True):
        st.session_state.drawing = False
        st.session_state.start_point = None
        st.rerun()

# === MAIN ===
st.title("P&ID – Draw Flow Path (Click to See)")

col_img, col_info = st.columns([3,1])

# === LOAD BASE IMAGE ===
try:
    base = Image.open(PID_FILE).convert("RGBA")
except:
    base = Image.new("RGBA", (1200, 800), (255,255,255,255))

# === CLICKABLE IMAGE ===
with col_img:
    if st.session_state.drawing:
        st.info("**1. Click start point** (red dot) → **2. Click end point** → Line locks & flow animates.")
    
    # Use native clickable image
    click_data = st_clickable_images(
        [base],
        img_width=base.width,
        img_height=base.height,
        key="pid_click"
    )

    # === HANDLE CLICK ===
    if click_data and st.session_state.drawing:
        x, y = click_data[0]["x"], click_data[0]["y"]
        if st.session_state.start_point is None:
            # FIRST CLICK
            st.session_state.start_point = (x, y)
            st.success(f"Start point set: ({x}, {y})")
            st.rerun()
        else:
            # SECOND CLICK
            p1 = st.session_state.start_point
            p2 = (x, y)
            st.session_state.user_lines.append({"p1": p1, "p2": p2})
            st.session_state.start_point = None
            st.success(f"Line added: {p1} → {p2}")
            st.rerun()

# === DRAW CANVAS ===
canvas = base.copy()
draw = ImageDraw.Draw(canvas)
font = ImageFont.load_default()

# Draw valves
for tag, data in valves.items():
    x, y = data["x"], data["y"]
    col = (0,255,0) if st.session_state.valve_states.get(tag, False) else (255,0,0)
    draw.ellipse([x-10, y-10, x+10, y+10], fill=col, outline="white", width=3)
    draw.text((x+15, y-15), tag, fill="white", font=font)

# Draw start point (if active)
if st.session_state.start_point:
    sx, sy = st.session_state.start_point
    draw.ellipse([sx-15, sy-15, sx+15, sy+15], fill=(255,0,0,180), outline="red", width=3)
    # Preview line to cursor (fake with last click or center)
    # Not perfect, but shows intent
    draw.line([(sx, sy), (sx + 100, sy)], fill=(100,100,100,150), width=5)

# Draw confirmed lines + flow
for line in st.session_state.user_lines:
    p1, p2 = line["p1"], line["p2"]
    up_val = nearest_valve(p1)
    down_val = nearest_valve(p2)
    flow_ok = (up_val and down_val and 
               st.session_state.valve_states.get(up_val, False) and 
               st.session_state.valve_states.get(down_val, False))
    
    line_col = (0, 255, 0, 220) if flow_ok else (255, 0, 0, 180)
    draw.line([p1, p2], fill=line_col, width=8)

    if flow_ok:
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
    st.header("Custom Lines")
    if st.session_state.user_lines:
        for i, ln in enumerate(st.session_state.user_lines):
            p1, p2 = ln["p1"], ln["p2"]
            up = nearest_valve(p1)
            down = nearest_valve(p2)
            status = "Flow" if (up and down and 
                                st.session_state.valve_states.get(up, False) and 
                                st.session_state.valve_states.get(down, False)) else "Blocked"
            st.write(f"**Line {i+1}**: {status}")
            st.caption(f"{p1} → {p2}\nUp: {up or '—'} | Down: {down or '—'}")
            if st.button("Delete", key=f"del_{i}"):
                st.session_state.user_lines.pop(i)
                st.rerun()
    else:
        st.info("No lines drawn yet.")

# === HELPER: nearest valve ===
def nearest_valve(point, max_dist=50):
    x0, y0 = point
    best = None
    best_d = float('inf')
    for tag, data in valves.items():
        d = math.hypot(data["x"] - x0, data["y"] - y0)
        if d < best_d and d <= max_dist:
            best_d = d
            best = tag
    return best

# === CLICKABLE IMAGE COMPONENT (native Streamlit) ===
def st_clickable_images(images, img_width, img_height, key):
    """Returns list of click dicts: [{'x': int, 'y': int}]"""
    import streamlit.components.v1 as components
    import base64

    html_images = []
    for img in images:
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        b64 = base64.b64encode(buffered.getvalue()).decode()
        html_images.append(f'<img src="data:image/png;base64,{b64}" width="{img_width}" height="{img_height}">')

    html = f"""
    <div style="position:relative; display:inline-block;">
        {html_images[0]}
        <div id="click-layer" style="position:absolute; top:0; left:0; width:100%; height:100%; cursor:crosshair;"
             onclick="
                const rect = this.getBoundingClientRect();
                const x = event.clientX - rect.left;
                const y = event.clientY - rect.top;
                window.parent.postMessage({{type:'streamlit:setComponentValue', value: [{{
                    x: Math.round(x * {img_width} / rect.width),
                    y: Math.round(y * {img_height} / rect.height)
                }}] }}, '*');
             "></div>
    </div>
    <script>
        window.parent.addEventListener('message', (e) => {{ if (e.data.type === 'streamlit:setComponentValue') {{ 
            const val = e.data.value; 
            window.parent.streamlit.setComponentValue(val);
        }} });
    </script>
    """
    return components.html(html, height=img_height, key=key)
