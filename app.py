# app.py
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import json
import os

# ───────────────────────────────────────────────
# CONFIGURATION
# ───────────────────────────────────────────────
st.set_page_config(page_title="P&ID Interactive HMI", layout="wide")
st.title("🧭 P&ID Simulation with Saved Valve Positions")

PID_FN = "P&ID.png"
ICON_FN = "valve_icon.png"
SAVE_FN = "valve_positions.json"

TAGS = [
    "V-101","V-102","V-103","V-104",
    "V-301","V-302","V-303",
    "V-401","V-402","V-501","V-601",
    "PCV-501","CV-1","CV-2","CV-3","CV-4",
    "MPV-1","MPV-2","MPV-7","MPV-8"
]

# ───────────────────────────────────────────────
# HELPERS
# ───────────────────────────────────────────────
def load_image(fn):
    if not os.path.exists(fn):
        return None
    return Image.open(fn).convert("RGBA")

def measure_text(draw, text, font):
    """Safe text sizing for Pillow ≥10."""
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        return (len(text) * 7, 12)

def autosave():
    """Save positions & states safely."""
    try:
        data = {
            "positions": st.session_state.positions,
            "states": st.session_state.states
        }
        with open(SAVE_FN, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        st.warning(f"⚠️ Could not save data: {e}")

def autoload():
    """Load previously saved valve positions and states if available."""
    if os.path.exists(SAVE_FN):
        try:
            with open(SAVE_FN, "r") as f:
                data = json.load(f)
                if "positions" in data:
                    st.session_state.positions.update(data["positions"])
                if "states" in data:
                    st.session_state.states.update(data["states"])
        except Exception as e:
            st.error(f"❌ Failed to load saved positions: {e}")

def draw_overlay(base_img, positions, states, icon_img, icon_scale_pct=4):
    out = base_img.copy()
    w, h = out.size
    icon_w = max(16, int(w * icon_scale_pct / 100.0))
    icon_h = int(icon_w * icon_img.height / max(1, icon_img.width))
    icon_resized = icon_img.resize((icon_w, icon_h), Image.LANCZOS)

    overlay = Image.new("RGBA", out.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", max(12, int(icon_w/3)))
    except Exception:
        font = ImageFont.load_default()

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

        # Color tint for icon
        icon = icon_resized.copy().convert("RGBA")
        tint = Image.new("RGBA", icon.size, overlay_color)
        icon = Image.alpha_composite(icon, tint)

        top_left = (cx - icon.size[0]//2, cy - icon.size[1]//2)
        overlay.paste(icon, top_left, icon)

        text = tag
        text_w, text_h = measure_text(draw, text, font)
        label_x = top_left[0] + icon.size[0] + 6
        label_y = top_left[1]
        draw.rectangle(
            [label_x-2, label_y-2, label_x+text_w+4, label_y+text_h+2],
            fill=(0,0,0,160)
        )
        draw.text((label_x, label_y), text, fill=(255,255,255,255), font=font)

    merged = Image.alpha_composite(out, overlay)
    display = merged.convert("RGB")
    return display

# ───────────────────────────────────────────────
# SESSION INIT
# ───────────────────────────────────────────────
if "positions" not in st.session_state:
    st.session_state.positions = {}
if "states" not in st.session_state:
    st.session_state.states = {t: False for t in TAGS}
if "icon_scale" not in st.session_state:
    st.session_state.icon_scale = 4

autoload()  # Load saved data if available

pid_img = load_image(PID_FN)
icon_img = load_image(ICON_FN)
if pid_img is None:
    st.error(f"❌ Missing '{PID_FN}' in repo root.")
    st.stop()
if icon_img is None:
    st.warning(f"⚠️ Missing '{ICON_FN}', using fallback red dot.")
    icon_img = Image.new("RGBA", (64,64), (0,0,0,0))
    d = ImageDraw.Draw(icon_img)
    d.ellipse((8,8,56,56), fill=(180,0,0,255))

# ───────────────────────────────────────────────
# LAYOUT
# ───────────────────────────────────────────────
col1, col2 = st.columns([1, 2])

with col1:
    st.header("Valve Configuration")
    sel = st.selectbox("Select valve tag", ["<select>"] + TAGS)
    if sel != "<select>":
        existing = st.session_state.positions.get(sel)
        init_x = existing["x_pct"] if existing else 10.0
        init_y = existing["y_pct"] if existing else 10.0
        x_pct = st.slider("X position (%)", 0.0, 100.0, float(init_x), 0.1)
        y_pct = st.slider("Y position (%)", 0.0, 100.0, float(init_y), 0.1)
        if st.button("💾 Save valve position"):
            st.session_state.positions[sel] = {"x_pct": round(x_pct,3), "y_pct": round(y_pct,3)}
            autosave()
            st.success(f"Saved {sel} at {x_pct}%, {y_pct}%")

    st.markdown("---")
    st.session_state.icon_scale = st.slider("Icon size (% width)", 2, 12, st.session_state.icon_scale, 1)

with col2:
    # Draw updated image
    overlay_img = draw_overlay(
        pid_img,
        st.session_state.positions,
        st.session_state.states,
        icon_img,
        icon_scale_pct=st.session_state.icon_scale
    )
    st.image(overlay_img, use_container_width=True)

# ───────────────────────────────────────────────
# DYNAMIC TOGGLES BELOW IMAGE
# ───────────────────────────────────────────────
st.markdown("### 🟢 Toggle Valves (appears next to each valve icon)")

cols = st.columns(4)
for i, tag in enumerate(TAGS):
    with cols[i % 4]:
        st.session_state.states[tag] = st.toggle(
            f"{tag} — {'OPEN' if st.session_state.states.get(tag, False) else 'CLOSED'}",
            value=st.session_state.states.get(tag, False),
            key=f"toggle_{tag}",
            on_change=autosave
        )

# Save whenever anything changes
autosave()
