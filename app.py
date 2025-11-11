# app.py
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import json
import io
import os

st.set_page_config(page_title="P&ID Manual Placement (Option B)", layout="wide")
st.title("📌 P&ID Manual Placement & HMI — Option B (Fixed Overlay)")

PID_FN = "P&ID.png"
ICON_FN = "valve_icon.png"

TAGS = [
    "V-101","V-102","V-103","V-104",
    "V-301","V-302","V-303",
    "V-401","V-402","V-501","V-601",
    "PCV-501","CV-1","CV-2","CV-3","CV-4",
    "MPV-1","MPV-2","MPV-7","MPV-8"
]

def load_image(fn):
    if not os.path.exists(fn):
        return None
    return Image.open(fn).convert("RGBA")

def draw_overlay(base_img, positions, states, icon_img, icon_scale_pct=4):
    out = base_img.copy()
    w, h = out.size

    icon_w = max(16, int(w * icon_scale_pct / 100.0))
    icon_h = int(icon_w * icon_img.height / max(1, icon_img.width))
    icon_resized = icon_img.resize((icon_w, icon_h), Image.LANCZOS)

    # base overlay to paste all icons into
    overlay = Image.new("RGBA", out.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", max(12, int(icon_w/3)))
    except Exception:
        font = None

    for tag, pos in positions.items():
        try:
            x_pct = float(pos["x_pct"])
            y_pct = float(pos["y_pct"])
        except Exception:
            continue
        cx = int(w * x_pct / 100.0)
        cy = int(h * y_pct / 100.0)
        is_open = states.get(tag, False)
        overlay_color = (0, 200, 0, 180) if is_open else (200, 0, 0, 180)

        icon = icon_resized.copy().convert("RGBA")
        tint = Image.new("RGBA", icon.size, overlay_color)
        icon = Image.alpha_composite(icon, tint)

        top_left = (cx - icon.size[0]//2, cy - icon.size[1]//2)
        overlay.paste(icon, top_left, icon)

        text = tag
        text_w, text_h = draw.textsize(text, font=font) if font else (len(text)*7, 12)
        label_x = top_left[0] + icon.size[0] + 6
        label_y = top_left[1]
        draw.rectangle([label_x-2, label_y-2, label_x+text_w+4, label_y+text_h+2], fill=(0,0,0,160))
        draw.text((label_x, label_y), text, fill=(255,255,255,255), font=font)

    # merge overlays
    merged = Image.alpha_composite(out, overlay)
    # flatten transparency for Streamlit display
    display = merged.convert("RGB")
    return display

# session state
if "positions" not in st.session_state:
    st.session_state.positions = {}
if "states" not in st.session_state:
    st.session_state.states = {t: False for t in TAGS}
if "icon_scale" not in st.session_state:
    st.session_state.icon_scale = 4

pid_img = load_image(PID_FN)
icon_img = load_image(ICON_FN)
if pid_img is None:
    st.error(f"Missing '{PID_FN}' in repo root.")
    st.stop()
if icon_img is None:
    st.warning(f"Missing '{ICON_FN}', using fallback red dot.")
    icon_img = Image.new("RGBA", (64,64), (0,0,0,0))
    d = ImageDraw.Draw(icon_img)
    d.ellipse((8,8,56,56), fill=(180,0,0,255))

left, right = st.columns([1,2])

with left:
    st.header("Placement Panel")
    sel = st.selectbox("Select tag", ["<select>"] + TAGS)
    if sel != "<select>":
        existing = st.session_state.positions.get(sel)
        init_x = existing["x_pct"] if existing else 10.0
        init_y = existing["y_pct"] if existing else 10.0
        x_pct = st.slider("X position (%)", 0.0, 100.0, float(init_x), 0.1)
        y_pct = st.slider("Y position (%)", 0.0, 100.0, float(init_y), 0.1)
        if st.button("Save position"):
            st.session_state.positions[sel] = {"x_pct": round(x_pct,3), "y_pct": round(y_pct,3)}
            st.success(f"Saved {sel} at {x_pct}%, {y_pct}%")

    st.markdown("---")
    icon_scale = st.slider("Icon size (% width)", 2, 12, st.session_state.icon_scale, 1)
    st.session_state.icon_scale = icon_scale

    st.markdown("Toggle valves (green=open, red=closed)")
    for t in TAGS:
        st.session_state.states[t] = st.checkbox(
            t + " OPEN",
            value=st.session_state.states.get(t, False),
            key=f"state_{t}"
        )

with right:
    overlay_img = draw_overlay(pid_img, st.session_state.positions, st.session_state.states, icon_img, icon_scale_pct=st.session_state.icon_scale)
    st.image(overlay_img, use_container_width=True)
    if not st.session_state.positions:
        st.info("No valves placed yet — select a tag and save position on the left.")
