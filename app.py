# app.py
import streamlit as st
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2
import io
import json
import os

st.set_page_config(page_title="P&ID Valve Auto-Detect HMI", layout="wide")
st.title("🔎 Auto-detect valves on P&ID and toggle (HMI)")

# ---------- Helper functions ----------
def load_image(path):
    return Image.open(path).convert("RGBA")

def pil_to_cv2(pil_img):
    # RGBA/PIL -> BGR CV2
    arr = np.array(pil_img)
    if arr.shape[2] == 4:
        arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

def find_template_locations(main_cv2, template_cv2, threshold=0.78, max_results=200, neighborhood=10):
    """Return list of (x_center, y_center) in pixels using non-max suppression."""
    res = cv2.matchTemplate(main_cv2, template_cv2, cv2.TM_CCOEFF_NORMED)
    locs = np.where(res >= threshold)
    points = list(zip(locs[1], locs[0], res[locs]))  # x, y, score
    # sort by score desc
    points = sorted(points, key=lambda x: x[2], reverse=True)
    picked = []
    for x, y, s in points:
        too_close = False
        for px, py in picked:
            if abs(px - x) <= neighborhood and abs(py - y) <= neighborhood:
                too_close = True
                break
        if not too_close:
            picked.append((x, y))
        if len(picked) >= max_results:
            break
    # convert top-left to center of template
    h, w = template_cv2.shape[:2]
    centers = [(int(x + w/2), int(y + h/2)) for x, y in picked]
    return centers

def draw_overlay(base_pil, detections, states):
    """Return new PIL image with colored circles and tags drawn at detections.
       detections: list of (tag, (cx,cy)) pixel positions
       states: dict tag->bool
    """
    out = base_pil.copy()
    draw = ImageDraw.Draw(out)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 14)
    except Exception:
        font = ImageFont.load_default()
    w, h = out.size
    for tag, (cx, cy) in detections:
        r = max(8, int(min(w,h) * 0.012))
        color = (0, 200, 0, 200) if states.get(tag, False) else (200, 0, 0, 200)
        draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=color, outline=(0,0,0))
        # tag label background
        tx, ty = cx + r + 4, cy - r
        draw.rectangle([tx-2, ty-2, tx + 8 + len(tag)*7, ty + 16], fill=(0,0,0,160))
        draw.text((tx, ty), tag, fill=(255,255,255), font=font)
    return out

def pixel_to_percent(cx, cy, image_w, image_h):
    return round(100.0 * cx / image_w, 3), round(100.0 * cy / image_h, 3)

# ---------- Load main images ----------
# Must exist in repo root exactly with these names
MAIN_FN = "p&id.png"
VALVE_FN = "valve_icon.png"

if not os.path.exists(MAIN_FN):
    st.error(f"Main P&ID not found: {MAIN_FN}. Upload it to the repo root with that exact name.")
    st.stop()
if not os.path.exists(VALVE_FN):
    st.error(f"Valve icon not found: {VALVE_FN}. Upload your valve snippet named exactly '{VALVE_FN}'.")
    st.stop()

main_pil = load_image(MAIN_FN)
valve_pil = load_image(VALVE_FN)

# Convert to cv2 BGR for template matching
main_cv2 = pil_to_cv2(main_pil)
template_cv2 = pil_to_cv2(valve_pil)

st.sidebar.header("Detection & Tuning")
th = st.sidebar.slider("Match threshold", 0.60, 0.98, 0.82, 0.01)
neigh = st.sidebar.slider("Non-max neighborhood (px)", 2, 60, 18, 1)
max_results = st.sidebar.number_input("Max matches", min_value=1, max_value=200, value=80, step=1)

if st.sidebar.button("Run template detection"):
    # run detection now
    centers = find_template_locations(main_cv2, template_cv2, threshold=th, max_results=max_results, neighborhood=neigh)
    # assign tags sequentially V-101, V-102 ...
    detected = []
    start_num = 101
    for i, (cx, cy) in enumerate(centers):
        tag = f"V-{start_num + i}"
        detected.append((tag, (cx, cy)))
    # store detections in session
    st.session_state.detections = detected
    # initialize states
    if "valve_states" not in st.session_state:
        st.session_state.valve_states = {}
    for tag, _ in detected:
        if tag not in st.session_state.valve_states:
            st.session_state.valve_states[tag] = False
    # store percent positions too
    pos_map = {}
    for tag, (cx, cy) in detected:
        x_pct, y_pct = pixel_to_percent(cx, cy, main_pil.width, main_pil.height)
        pos_map[tag] = {"x_pct": x_pct, "y_pct": y_pct}
    st.session_state.positions = pos_map
    st.success(f"Detected {len(detected)} valve(s). You can toggle them from the sidebar list below.")

# If detections exist in session, use them; otherwise empty
detections = st.session_state.get("detections", [])

# show preview and controls
col1, col2 = st.columns([2,1])

with col1:
    st.subheader("P&ID with valve overlays")
    # if no detection yet, still show plain image
    overlay_img = draw_overlay(main_pil, detections, st.session_state.get("valve_states", {}))
    st.image(overlay_img, use_column_width=True)

with col2:
    st.subheader("Valves (toggle)")
    if not detections:
        st.info("No detected valves yet. Click 'Run template detection' to find valves using uploaded valve_icon.")
    else:
        # list detected valves with toggles
        for tag, (cx, cy) in detections:
            state = st.checkbox(tag + (" (OPEN)" if st.session_state.valve_states.get(tag, False) else " (CLOSED)"),
                                value=st.session_state.valve_states.get(tag, False),
                                key=f"chk_{tag}")
            st.session_state.valve_states[tag] = state

    st.markdown("---")
    st.subheader("Positions & Export")
    if detections:
        dfpos = []
        for tag, (cx, cy) in detections:
            x_pct, y_pct = st.session_state.positions.get(tag, {}).get("x_pct"), st.session_state.positions.get(tag, {}).get("y_pct")
            dfpos.append({"Tag": tag, "x_pct": x_pct, "y_pct": y_pct})
        st.dataframe(dfpos)

    if st.button("Export positions JSON"):
        out = {"positions": st.session_state.get("positions", {}), "states": st.session_state.get("valve_states", {})}
        st.download_button("Download JSON", json.dumps(out, indent=2), file_name="valve_positions_states.json", mime="application/json")

# ---------- Simulate simple readings ----------
st.markdown("---")
st.header("HMI Readings (simulated)")

if not detections:
    st.write("No valves detected — run detection first.")
else:
    rows = []
    total_flow = 0.0
    for tag, (cx, cy) in detections:
        open_state = st.session_state.valve_states.get(tag, False)
        # simple simulation: open -> flow = base * random factor, pressure slightly lower when open
        base_flow = 10.0 + (int(tag.split("-")[1]) % 10) * 2.0
        flow = base_flow * (1.5 if open_state else 0.0) * (1.0 + np.random.uniform(-0.05, 0.05))
        pressure = 100.0 - (int(tag.split("-")[1]) % 30) * 0.8
        if open_state:
            pressure *= 0.95
        rows.append({"Tag": tag, "Open": open_state, "Flow_SLPM": round(flow, 2), "Pressure_bar": round(pressure,2)})
        total_flow += flow
    df = st.dataframe(rows, use_container_width=True)

    st.metric("Total simulated flow (SLPM)", f"{round(total_flow,2)}")

# ---------- live overlay update after toggles ----------
# Re-render overlay to show updated colors immediately
overlay_img2 = draw_overlay(main_pil, detections, st.session_state.get("valve_states", {}))
st.image(overlay_img2, caption="Overlay updated", use_column_width=True)
