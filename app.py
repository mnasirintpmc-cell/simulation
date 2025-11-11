# app.py
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import json
import io
import os

# ---------------- Page config ----------------
st.set_page_config(page_title="P&ID Manual Placement (Option B)", layout="wide")
st.title("📌 P&ID Manual Placement & HMI — Option B")

# ---------------- Files / tags ----------------
PID_FN = "P&ID.png"
ICON_FN = "valve_icon.png"   # the small valve symbol you uploaded

TAGS = [
    "V-101","V-102","V-103","V-104",
    "V-301","V-302","V-303",
    "V-401","V-402","V-501","V-601",
    "PCV-501","CV-1","CV-2","CV-3","CV-4",
    "MPV-1","MPV-2","MPV-7","MPV-8",
    # add/remove tags as needed
]

# ---------------- Helpers ----------------
def load_image(fn):
    if not os.path.exists(fn):
        return None
    return Image.open(fn).convert("RGBA")

def draw_overlay(base_img, positions, states, icon_img, icon_scale_pct=4):
    """
    Draw icons and labels on a copy of base_img.
    positions: dict tag -> {"x_pct":float, "y_pct":float}
    states: dict tag -> bool (True=open)
    icon_img: PIL.Image
    icon_scale_pct: average icon size as percent of image width
    """
    out = base_img.copy()
    draw = ImageDraw.Draw(out)
    w, h = out.size

    # resize icon relative to image width
    icon_w = max(16, int(w * icon_scale_pct / 100.0))
    icon_h = int(icon_w * icon_img.height / max(1, icon_img.width))
    icon_resized = icon_img.resize((icon_w, icon_h), Image.LANCZOS)

    # optional font
    try:
        from PIL import ImageFont
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

        # choose overlay color based on state
        is_open = states.get(tag, False)
        overlay_color = (0, 200, 0, 180) if is_open else (200, 0, 0, 180)

        # colorize icon: create a tint overlay
        icon = icon_resized.copy().convert("RGBA")
        tint = Image.new("RGBA", icon.size, overlay_color)
        icon = Image.alpha_composite(icon, tint)

        # paste icon centered at (cx, cy)
        top_left = (cx - icon.size[0]//2, cy - icon.size[1]//2)
        out.paste(icon, top_left, icon)

        # draw text label to the right of icon
        label_x = top_left[0] + icon.size[0] + 6
        label_y = top_left[1]
        text = tag
        # draw small background rectangle for label
        text_w, text_h = draw.textsize(text, font=font) if font else (len(text)*7, 12)
        draw.rectangle([label_x-2, label_y-2, label_x+text_w+4, label_y+text_h+2], fill=(0,0,0,160))
        draw.text((label_x, label_y), text, fill=(255,255,255,255), font=font)

    return out

# ---------------- Session state init ----------------
if "positions" not in st.session_state:
    st.session_state.positions = {}  # tag -> {"x_pct":.., "y_pct":..}
if "states" not in st.session_state:
    st.session_state.states = {t: False for t in TAGS}  # open/closed
if "icon_scale" not in st.session_state:
    st.session_state.icon_scale = 4  # percent of image width

# ---------------- Load assets ----------------
pid_img = load_image(PID_FN)
icon_img = load_image(ICON_FN)

if pid_img is None:
    st.error(f"Missing '{PID_FN}' in repo root. Upload it first.")
    st.stop()
if icon_img is None:
    st.warning(f"Valve icon '{ICON_FN}' not found. You can still place tags manually; icons will be empty.")
    # create a simple fallback icon (circle)
    fallback = Image.new("RGBA", (64,64), (0,0,0,0))
    d = ImageDraw.Draw(fallback)
    d.ellipse((8,8,56,56), fill=(180,0,0,255))
    icon_img = fallback

# ---------------- UI layout ----------------
left_col, right_col = st.columns([1,2])

with left_col:
    st.header("Manual Placement Panel (Option B)")
    st.markdown("1. Select a tag.  2. Use sliders to position it on the P&ID (percent).  3. Click **Save position**.  4. Toggle OPEN to change state color.")
    sel = st.selectbox("Select tag to place", ["<select>"] + TAGS)

    # show current saved position if exists
    if sel != "<select>":
        existing = st.session_state.positions.get(sel)
        if existing:
            st.info(f"Saved position for {sel}: X={existing['x_pct']}%, Y={existing['y_pct']}%")
            init_x = float(existing["x_pct"])
            init_y = float(existing["y_pct"])
        else:
            init_x = 10.0
            init_y = 10.0

        x_pct = st.slider("X position (%)", 0.0, 100.0, init_x, 0.1)
        y_pct = st.slider("Y position (%)", 0.0, 100.0, init_y, 0.1)

        if st.button("Save position"):
            st.session_state.positions[sel] = {"x_pct": round(x_pct,3), "y_pct": round(y_pct,3)}
            st.success(f"Saved {sel} at X={x_pct}%, Y={y_pct}%")

    st.markdown("---")
    st.subheader("Icon & state controls")

    icon_scale = st.slider("Icon size (% of image width)", 2, 12, st.session_state.icon_scale, 1)
    st.session_state.icon_scale = icon_scale

    st.markdown("Toggle valves (open = green, closed = red):")
    for t in TAGS:
        st.session_state.states[t] = st.checkbox(t + " OPEN", value=st.session_state.states.get(t, False), key=f"state_{t}")

    st.markdown("---")
    if st.button("Reset all positions"):
        st.session_state.positions = {}
        st.success("All positions cleared (you can re-place).")
    if st.button("Reset states (close all)"):
        st.session_state.states = {t: False for t in TAGS}
        st.success("All valves set to CLOSED.")

    st.markdown("---")
    # export / import positions JSON
    st.subheader("Export / Import placements")
    if st.button("Export placements & states JSON"):
        out = {"positions": st.session_state.positions, "states": st.session_state.states}
        b = io.BytesIO()
        b.write(json.dumps(out, indent=2).encode("utf-8"))
        b.seek(0)
        st.download_button("Download JSON", b, "placements_states.json", "application/json")

    uploaded_json = st.file_uploader("Import placements JSON (optional)", type=["json"])
    if uploaded_json is not None:
        try:
            raw = uploaded_json.read().decode("utf-8")
            parsed = json.loads(raw)
            if "positions" in parsed:
                st.session_state.positions.update(parsed["positions"])
            if "states" in parsed:
                st.session_state.states.update(parsed["states"])
            st.success("Imported placements/states.")
        except Exception as e:
            st.error("Failed to import JSON: " + str(e))

with right_col:
    st.header("P&ID Preview with overlays")
    overlay_img = draw_overlay(pid_img, st.session_state.positions, st.session_state.states, icon_img, icon_scale_pct=st.session_state.icon_scale)
    st.image(overlay_img, use_column_width=True)

    # quick table of placed tags
    st.subheader("Placed tags")
    if st.session_state.positions:
        rows = []
        for tag, pos in st.session_state.positions.items():
            rows.append({"Tag": tag, "X%": pos["x_pct"], "Y%": pos["y_pct"], "State": "OPEN" if st.session_state.states.get(tag, False) else "CLOSED"})
        st.table(rows)
    else:
        st.info("No tags placed yet. Select a tag on the left and Save position.")

# ---------------- Footer ----------------
st.markdown("---")
st.caption("Manual placement mode (Option B). Use sliders and Save position to set exact coordinates on the P&ID. Export JSON when done to reuse placements.")
