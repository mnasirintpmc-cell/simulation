def load_lines():
    if not os.path.exists(LINES_FILE):
        st.warning("Missing pipes.json")
        return []

    try:
        with open(LINES_FILE) as f:
            raw = json.load(f)
    except:
        return []

    # Get valve positions
    valve_pos = {tag: (data["x"], data["y"]) for tag, data in valves.items()}

    # Snap function
    def snap(point):
        x, y = point
        best_tag = None
        best_dist = float('inf')
        for tag, (vx, vy) in valve_pos.items():
            dist = math.hypot(vx - x, vy - y)
            if dist < best_dist and dist < 100:
                best_dist = dist
                best_tag = tag
        return (valve_pos[best_tag] if best_tag else point)

    snapped_lines = []
    for line in raw:
        p1 = snap((line["x1"], line["y1"]))
        p2 = snap((line["x2"], line["y2"]))
        if p1 != p2:
            snapped_lines.append({"x1": p1[0], "y1": p1[1], "x2": p2[0], "y2": p2[1]})
    return snapped_linesimport streamlit as st
import json
from PIL import Image, ImageDraw, ImageFont
import os
import math
import time
import io

st.set_page_config(layout="wide")

# === CONFIG ===
PID_FILE     = "P&ID.png"
VALVES_FILE  = "valves.json"
LINES_FILE   = "pipes.json"  # Your Figma export (SVG or JSON)

# === AUTO-SCALE LINES FROM FIGMA TO P&ID SIZE ===
def scale_lines(lines, figma_w=184, figma_h=259, target_w=1200, target_h=800):
    if not lines:
        return []
    scale_x = target_w / figma_w
    scale_y = target_h / figma_h
    scaled = []
    for line in lines:
        try:
            scaled.append({
                "x1": int(line["x1"] * scale_x),
                "y1": int(line["y1"] * scale_y),
                "x2": int(line["x2"] * scale_x),
                "y2": int(line["y2"] * scale_y)
            })
        except:
            # Handle SVG format
            scaled.append({
                "x1": int(float(line.get("x1", 0)) * scale_x),
                "y1": int(float(line.get("y1", 0)) * scale_y),
                "x2": int(float(line.get("x2", 0)) * scale_x),
                "y2": int(float(line.get("y2", 0)) * scale_y)
            })
    return scaled

# === LOAD VALVES ===
def load_valves():
    if not os.path.exists(VALVES_FILE):
        st.error(f"Missing {VALVES_FILE}")
        st.stop()
    try:
        with open(VALVES_FILE) as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Invalid {VALVES_FILE}: {e}")
        st.stop()

valves = load_valves()

# === LOAD LINES (SVG or JSON) + SCALE ===
def load_lines():
    if not os.path.exists(LINES_FILE):
        st.warning(f"Missing {LINES_FILE} – upload your Figma export")
        return []

    raw_lines = []

    if LINES_FILE.endswith(".svg"):
        import xml.etree.ElementTree as ET
        try:
            tree = ET.parse(LINES_FILE)
            root = tree.getroot()
            ns = {'svg': 'http://www.w3.org/2000/svg'}
            for line in root.findall('.//svg:line', ns):
                try:
                    x1 = int(float(line.get('x1', 0)))
                    y1 = int(float(line.get('y1', 0)))
                    x2 = int(float(line.get('x2', 0)))
                    y2 = int(float(line.get('y2', 0)))
                    if (x1, y1) != (x2, y2):
                        raw_lines.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2})
                except:
                    pass
        except Exception as e:
            st.error(f"SVG error: {e}")
    else:
        try:
            with open(LINES_FILE) as f:
                data = json.load(f)
            raw_lines = data.get("lines", data) if isinstance(data, dict) else data
        except Exception as e:
            st.error(f"JSON error: {e}")

    # === AUTO-SCALE TO P&ID SIZE ===
    try:
        img = Image.open(PID_FILE)
        target_w, target_h = img.size
    except:
        target_w, target_h = 1200, 800  # fallback

    return scale_lines(raw_lines, target_w=target_w, target_h=target_h)

lines = load_lines()

# === SESSION STATE ===
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {
        tag: bool(data.get("state", False)) for tag, data in valves.items()
    }

# === SIDEBAR ===
with st.sidebar:
    st.header("Valve Controls")
    for tag, data in valves.items():
        state = st.session_state.valve_states[tag]
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button(
                f"{'OPEN' if state else 'CLOSED'} {tag}",
                type="primary" if state else "secondary",
                key=f"btn_{tag}",
                use_container_width=True,
            ):
                st.session_state.valve_states[tag] = not state
                st.rerun()
        with col2:
            st.write("OPEN" if state else "CLOSED")

    st.markdown("---")
    open_cnt = sum(st.session_state.valve_states.values())
    st.metric("Open", open_cnt)
    st.metric("Closed", len(valves) - open_cnt)

    st.markdown("---")
    if st.button("Open All", use_container_width=True):
        for t in valves:
            st.session_state.valve_states[t] = True
        st.rerun()
    if st.button("Close All", use_container_width=True):
        for t in valves:
            st.session_state.valve_states[t] = False
        st.rerun()

# === MAIN ===
st.title("P&ID – Figma Flow Paths (Auto-Scaled)")

col_img, col_info = st.columns([3, 1])

# === LOAD P&ID IMAGE ===
try:
    base = Image.open(PID_FILE).convert("RGBA")
except:
    st.error(f"Missing {PID_FILE}")
    base = Image.new("RGBA", (1200, 800), (240, 240, 240, 255))

canvas = base.copy()
draw = ImageDraw.Draw(canvas)
font = ImageFont.load_default()

# === DRAW VALVES ===
for tag, data in valves.items():
    x, y = data["x"], data["y"]
    col = (0, 255, 0, 255) if st.session_state.valve_states.get(tag, False) else (255, 0, 0, 255)
    draw.ellipse([x-10, y-10, x+10, y+10], fill=col, outline="white", width=3)
    draw.text((x+15, y-15), tag, fill="white", font=font)

# === HELPER: Nearest valve ===
def nearest_valve(point, max_dist=80):
    x0, y0 = point
    best = None
    best_d = float('inf')
    for tag, data in valves.items():
        d = math.hypot(data["x"] - x0, data["y"] - y0)
        if d < best_d and d <= max_dist:
            best_d = d
            best = tag
    return best

# === DRAW PIPES + FLOW ===
for line in lines:
    try:
        p1 = (line["x1"], line["y1"])
        p2 = (line["x2"], line["y2"])
    except:
        continue

    up = nearest_valve(p1)
    down = nearest_valve(p2)
    flow = up and down and st.session_state.valve_states.get(up, False) and st.session_state.valve_states.get(down, False)

    line_color = (0, 255, 0, 220) if flow else (255, 0, 0, 180)
    draw.line([p1, p2], fill=line_color, width=8)

    if flow:
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
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
                (ax - a_len * math.cos(angle + 0.5), ay - a_len * math.sin(angle + 0.5)),
            ]
            draw.polygon(pts, fill=(0, 200, 0))

# === DISPLAY IMAGE ===
with col_img:
    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, "PNG")
    st.image(buf.getvalue(), use_container_width=True)

# === RIGHT PANEL ===
with col_info:
    st.header("Pipe Status")
    if lines:
        for i, line in enumerate(lines):
            try:
                p1 = (line["x1"], line["y1"])
                p2 = (line["x2"], line["y2"])
            except:
                continue
            up = nearest_valve(p1) or "—"
            down = nearest_valve(p2) or "—"
            flow = up != "—" and down != "—" and st.session_state.valve_states.get(up, False) and st.session_state.valve_states.get(down, False)
            status = "Flow" if flow else "Blocked"
            st.write(f"**Pipe {i+1}**: {status}")
            st.caption(f"{p1} → {p2}\nUp: {up} | Down: {down}")
    else:
        st.info("No pipes loaded – check `pipes.json`")

# === DEBUG ===
with st.expander("Debug Info"):
    st.write("**P&ID Size:**", base.size)
    st.write("**Loaded Pipes:**", len(lines))
    st.json(lines[:5])  # Show first 5
    st.write("**Valves:**", list(valves.keys()))
