# ==========================================================
# Streamlit App - OCR Valve Simulation Fix
# ==========================================================

import os
import sys
import subprocess

# --- Ensure pytesseract is installed (fix for Streamlit Cloud) ---
try:
    import pytesseract
except ModuleNotFoundError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pytesseract"])
    import pytesseract

# --- Now import all other dependencies ---
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from PIL import Image

# Continue with your existing code below ↓↓↓
# ------------------------------------------------------------
