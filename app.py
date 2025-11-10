# app.py
import streamlit as st
import cv2
import pytesseract
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pandas as pd

# -------------------- PAGE SETUP --------------------
st.set_page_config(page_title="P&ID Valve HMI Simulator", layout="wide")
st.title("🧠 P&ID Interactive Valve Simulator")

# -------------------- LOAD IMAGE --------------------
PID_FILE = "P&ID.png"

try:
    pid_image = Image.open(PID_FILE).convert("RGB")
except FileNotFoundError:
    st.error(f"❌ Cannot find '{PID_FILE}'. Please upload it to the repo root.")
    st.stop()

# Convert for OpenCV
img_cv = np.array(pid_image)
img_gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)

# -------------------- OCR DETECTION --------------------
st.sidebar.header("OCR Settings")
threshold = st.sidebar.slider("Detection Confidence", 0, 100, 60, 5)

st.write("🔍 Detecting valve tags using OCR... (this may take a few seconds)")

# Extract text data
ocr_data = pytesseract.image_to_data(img_gray, output_type=pytesseract.Output.DICT)

# Define expected tags
expected_tags = [
    "V-101", "V-102", "V-103", "V-104",
    "V-301", "V-302", "V-303",
    "V-401", "V-402", "V-501", "V-601",
    "PCV-501", "CV-1", "CV-2", "CV-3", "CV-4",
    "MPV-1", "MPV-2", "MPV-7", "MPV-8"
]

detected_tags = []
for i, text in enumerate(ocr_data['text']):
    conf = int(ocr_data['conf'][i]) if ocr_data['conf'][i].isdigit() else 0
    if conf < threshold:
        continue
    txt = text.strip().upper()
    for tag in expected_tags:
        if tag in txt:
            x, y, w, h = (ocr_data['left'][i], ocr_data['top'][i],
                          ocr_data['width'][i], ocr_data['height'][i])
            detected_tags.append((tag, x, y, w, h))
            break

if not detected_tags:
    st.warning("⚠️ No valve tags detected. Try lowering the confidence threshold.")
else:
    st.success(f"✅ Detected {len(detected_tags)} valve tag(s).")

# -------------------- DRAW ON IMAGE --------------------
display_img = pid_image.copy()
draw = ImageDraw.Draw(display_img)
try:
    font = ImageFont.truetype("DejaVuSans.ttf", 16)
except:
    font = ImageFont.load_default()

for tag, x, y, w, h in detected_tags:
    draw.rectangle([x, y, x + w, y + h], outline="lime", width=2)
    draw.text((x, y - 12), tag, fill="yellow", font=font)

st.image(display_img, caption="Detected Valve Tags", use_container_width=True)

# -------------------- INTERACTIVE CONTROL --------------------
st.sidebar.header("Valve Control Panel")

valve_states = {}
for tag, *_ in detected_tags:
    state = st.sidebar.toggle(f"{tag}", value=False)
    valve_states[tag] = "OPEN" if state else "CLOSED"

# -------------------- HMI SIMULATION TABLE --------------------
if detected_tags:
    st.subheader("🧩 Live HMI Readings")

    data = []
    np.random.seed(42)

    for tag, *_ in detected_tags:
        open_state = valve_states[tag] == "OPEN"
        flow = np.random.uniform(10, 30) if open_state else 0
        pressure = np.random.uniform(3, 8) if open_state else np.random.uniform(8, 10)
        data.append({
            "Tag": tag,
            "State": valve_states[tag],
            "Flow (SLPM)": round(flow, 2),
            "Pressure (bar)": round(pressure, 2)
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
else:
    st.info("Run OCR detection to see live valve readings.")
