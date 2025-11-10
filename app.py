# ==========================================================
# Dry Gas Simulation & P&ID Valve OCR Tool (Streamlit)
# ==========================================================

import streamlit as st
import pandas as pd
import numpy as np

from PIL import Image
import pytesseract

# ----------------------------------------------------------
# Page setup
# ----------------------------------------------------------
st.set_page_config(page_title="Dry Gas Simulation", layout="wide")
st.title("🧪 Dry Gas Test Simulation & P&ID Viewer")

# ----------------------------------------------------------
# Sidebar navigation
# ----------------------------------------------------------
menu = st.sidebar.radio("Navigation", ["P&ID Simulation", "Trend Viewer"])

# ----------------------------------------------------------
# 1️⃣ P&ID Simulation Screen
# ----------------------------------------------------------
if menu == "P&ID Simulation":
    st.header("📘 P&ID Simulation")
    st.write("Upload a P&ID diagram, detect valve tags, and simulate opening/closing.")

    # Load P&ID image (default or uploaded)
    uploaded_image = st.file_uploader("Upload P&ID Image (PNG/JPG)", type=["png", "jpg", "jpeg"])
    if uploaded_image is not None:
        image = Image.open(uploaded_image)
    else:
        try:
            image = Image.open("P&ID.png")
        except Exception as e:
            st.error("❌ Could not load 'P&ID.png'. Please make sure it’s in the same folder as app.py.")
            st.stop()

    st.image(image, caption="P&ID Diagram", use_container_width=True)

    # OCR detection (detect valve tags)
    st.subheader("🔍 Detecting valve tags via OCR...")
    try:
        text = pytesseract.image_to_string(image)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        tags = [line for line in lines if any(tag in line.upper() for tag in ["V", "VALVE", "FV", "PV", "XV"])]

        if tags:
            st.success(f"✅ Detected {len(tags)} possible valve tags:")
            for t in tags:
                st.write(f"- {t}")
        else:
            st.warning("⚠️ No clear valve tags detected. Check image clarity or text visibility.")
    except Exception as e:
        st.error("⚠️ OCR failed. Make sure 'tesseract-ocr' is installed and image has readable text.")
        st.stop()

    # Simple simulation controls
    st.subheader("⚙️ Valve Simulation Control")
    if tags:
        selected_valve = st.selectbox("Select Valve to Simulate", tags)
        action = st.radio("Action", ["Open", "Close"])
        if st.button("Simulate"):
            if action == "Open":
                st.success(f"✅ Valve {selected_valve} opened successfully.")
            else:
                st.warning(f"🚧 Valve {selected_valve} closed successfully.")
    else:
        st.info("Upload a valid image or ensure tags are visible for valve control.")

# ----------------------------------------------------------
# 2️⃣ Trend Viewer
# ----------------------------------------------------------
elif menu == "Trend Viewer":
    st.header("📊 Trend Viewer")
    st.write("Visualize and highlight trends from CSV data (Flow, Pressure, Temperature).")

    uploaded_csv = st.file_uploader("Upload CSV data", type=["csv"])
    if uploaded_csv is not None:
        try:
            df = pd.read_csv(uploaded_csv)
            st.success("✅ CSV loaded successfully.")
        except Exception as e:
            st.error(f"❌ Failed to read CSV: {e}")
            st.stop()
    else:
        try:
            df = pd.read_csv("TestData53684.csv")
            st.info("Using default CSV file: TestData53684.csv")
        except Exception as e:
            st.error("❌ No CSV uploaded and default file not found.")
            st.stop()

    # Preview editable data
    st.subheader("🧾 Data Table (Editable)")
    edited_df = st.data_editor(df.head(12), use_container_width=True, num_rows="dynamic")

    # Trend plotting
    numeric_cols = [c for c in edited_df.columns if edited_df[c].dtype != "object"]
    if not numeric_cols:
        st.warning("No numeric columns found for trend plotting.")
        st.stop()

    st.subheader("📈 Select Parameters to Plot")
    selected_cols = st.multiselect("Select columns to visualize", numeric_cols, default=numeric_cols[:3])

    if selected_cols:
        fig = px.line(edited_df, y=selected_cols, title="Trend Plot", markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Select at least one column to plot.")

st.markdown("---")
st.caption("Developed by M. Nasir — Simulation & Data Visualization Tool")
