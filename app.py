import streamlit as st
import cv2
import pytesseract
import numpy as np
from PIL import Image, ImageDraw

# ------------------ PAGE SETUP ------------------
st.set_page_config(page_title="P&ID Valve Simulator", layout="wide")
st.title("🧠 P&ID Interactive Valve Simulator (with icons)")

# ------------------ LOAD IMAGES ------------------
PID_FILE = "P&ID.png"
VALVE_ICON_FILE = "valve_icon.png"  # your valve icon file

try:
    pid_image = Image.open(PID_FILE).convert("RGBA")
except FileNotFoundError:
    st.error(f"❌ Cannot find '{PID_FILE}'. Please upload it to the repo root.")
    st.stop()

try:
    valve_icon = Image.open(VALVE_ICON_FILE).convert("RGBA")
except FileNotFoundError:
    st.error(f"❌ Cannot find '{VALVE_ICON_FILE}'. Please upload it to the repo root.")
    st.stop()

# Convert to OpenCV for OCR
img_cv = np.array(pid_image)
img_gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)

# ------------------ OCR DETECTION ------------------
st.sidebar.header("OCR Settings")
threshold = st.sidebar.slider("Detection Confidence", 0, 100, 60, 5)

st.write("🔍 Detecting valve tags...")

ocr_data = pytesseract.image_to_data(img_gray, output_type=pytesseract.Output.DICT)

# Expected valve tags
expected_tags = [
    "V-101", "V-102", "V-103", "V-104",
    "V-301", "V-302", "V-303",
    "V-401", "V-402", "V-501", "V-601",
    "PCV-501", "CV-1", "CV-2", "CV-3", "CV-4",
    "MPV-1", "MPV-2", "MPV-7", "MPV-8"
]

detected_tags = []
for i, text in enumerate(ocr_data["text"]):
    try:
        conf_str = str(ocr_data["conf"][i])
        conf = int(float(conf_str)) if conf_str not in ["", "nan"] else 0
    except Exception:
        conf = 0

    if conf < threshold:
        continue

    txt = str(text).strip().upper()
    for tag in expected_tags:
        if tag in txt:
            x, y, w, h = (
                int(ocr_data["left"][i]),
                int(ocr_data["top"][i]),
                int(ocr_data["width"][i]),
                int(ocr_data["height"][i]),
            )
            detected_tags.append((tag, x, y, w, h))
            break

if not detected_tags:
    st.warning("⚠️ No valve tags detected. Try lowering the confidence threshold.")
else:
    st.success(f"✅ Detected {len(detected_tags)} valve tag(s).")

# ------------------ DRAW VALVE ICONS ------------------
display_img = pid_image.copy()

# Scale icon smaller
icon_size = (40, 40)
valve_icon_resized = valve_icon.resize(icon_size)

# Create toggle states
st.sidebar.header("Valve Control Panel")
valve_states = {}

for tag, x, y, w, h in detected_tags:
    valve_states[tag] = st.sidebar.toggle(f"{tag}", value=False)

# Overlay valves on top of P&ID
for tag, x, y, w, h in detected_tags:
    icon_x, icon_y = x, y - 20
    state = valve_states[tag]

    # Change color dynamically (green open / red closed)
    icon = valve_icon_resized.copy()
    color_overlay = Image.new("RGBA", icon.size, (0, 255, 0, 120) if state else (255, 0, 0, 120))
    icon = Image.alpha_composite(icon, color_overlay)

    display_img.paste(icon, (icon_x, icon_y), icon)

st.image(display_img, caption="Interactive P&ID with Valve Icons", use_container_width=True)

# ------------------ DISPLAY STATES ------------------
st.subheader("🧩 Live Valve States")
st.json({tag: "OPEN" if state else "CLOSED" for tag, state in valve_states.items()})
