import streamlit as st
import json
from PIL import Image, ImageDraw
import os

st.set_page_config(layout="wide")

# Configuration
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"
PIPES_DATA_FILE = "pipes.json"

def load_valves():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def load_pipes():
    if os.path.exists(PIPES_DATA_FILE):
        with open(PIPES_DATA_FILE, "r") as f:
            return json.load(f)
    return []

def save_pipes(pipes_data):
    with open(PIPES_DATA_FILE, "w") as f:
        json.dump(pipes_data, f, indent=2)

# Load data
valves = load_valves()
pipes = load_pipes()

# Initialize session state
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}

if "selected_pipe" not in st.session_state:
    st.session_state.selected_pipe = 0 if pipes else None

if "pipes" not in st.session_state:
    st.session_state.pipes = pipes

# Main app
st.title("🎯 PIPE ALIGNMENT TOOL - DRAG & DROP")

st.markdown("""
### **EASY 3-STEP PROCESS:**
1. **Select a pipe** from dropdown
2. **Use arrow keys** to move it visually  
3. **Repeat** for all pipes until aligned
""")

# Display P&ID background
st.header("📍 Step 1: View Your P&ID")
try:
    pid_img = Image.open(PID_FILE)
    st.image(pid_img, use_container_width=True, caption="Your P&ID - Align pipes to this")
except:
    st.error("Could not load P&ID.png")

# Pipe Selection
st.header("🎯 Step 2: Select Pipe to Move")
if st.session_state.pipes:
    pipe_options = [f"Pipe {i+1}" for i in range(len(st.session_state.pipes))]
    selected_index = st.selectbox("Choose pipe:", options=pipe_options, index=st.session_state.selected_pipe or 0)
    st.session_state.selected_pipe = pipe_options.index(selected_index)
    
    current_pipe = st.session_state.pipes[st.session_state.selected_pipe]
    st.info(f"**Selected:** Pipe {st.session_state.selected_pipe + 1} | Position: ({current_pipe['x1']}, {current_pipe['y1']}) to ({current_pipe['x2']}, {current_pipe['y2']})")

# Movement Controls
st.header("🔄 Step 3: Move Selected Pipe")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    if st.button("⬅️ LEFT", use_container_width=True):
        pipe = st.session_state.pipes[st.session_state.selected_pipe]
        pipe["x1"] -= 5
        pipe["x2"] -= 5
        save_pipes(st.session_state.pipes)

with col2:
    if st.button("➡️ RIGHT", use_container_width=True):
        pipe = st.session_state.pipes[st.session_state.selected_pipe]
        pipe["x1"] += 5
        pipe["x2"] += 5
        save_pipes(st.session_state.pipes)

with col3:
    if st.button("⬆️ UP", use_container_width=True):
        pipe = st.session_state.pipes[st.session_state.selected_pipe]
        pipe["y1"] -= 5
        pipe["y2"] -= 5
        save_pipes(st.session_state.pipes)

with col4:
    if st.button("⬇️ DOWN", use_container_width=True):
        pipe = st.session_state.pipes[st.session_state.selected_pipe]
        pipe["y1"] += 5
        pipe["y2"] += 5
        save_pipes(st.session_state.pipes)

with col5:
    if st.button("💾 SAVE", use_container_width=True):
        save_pipes(st.session_state.pipes)
        st.success("Saved!")

# Fine Adjustment
st.subheader("🎛️ Fine Adjustment")
col1, col2 = st.columns(2)

with col1:
    move_x = st.slider("Move X", -20, 20, 0, key="fine_x")
    if st.button("Apply X Move"):
        pipe = st.session_state.pipes[st.session_state.selected_pipe]
        pipe["x1"] += move_x
        pipe["x2"] += move_x
        save_pipes(st.session_state.pipes)

with col2:
    move_y = st.slider("Move Y", -20, 20, 0, key="fine_y")
    if st.button("Apply Y Move"):
        pipe = st.session_state.pipes[st.session_state.selected_pipe]
        pipe["y1"] += move_y
        pipe["y2"] += move_y
        save_pipes(st.session_state.pipes)

# Real-time Preview
st.header("👁️ Live Preview")
try:
    # Create preview image
    preview_img = Image.open(PID_FILE).convert("RGBA")
    draw = ImageDraw.Draw(preview_img)
    
    # Draw all pipes
    for i, pipe in enumerate(st.session_state.pipes):
        color = (255, 0, 0) if i == st.session_state.selected_pipe else (0, 0, 255)  # Red for selected, blue for others
        width = 6 if i == st.session_state.selected_pipe else 4
        draw.line([(pipe["x1"], pipe["y1"]), (pipe["x2"], pipe["y2"])], fill=color, width=width)
    
    # Draw valves
    for tag, data in valves.items():
        x, y = data["x"], data["y"]
        state = st.session_state.valve_states[tag]
        color = (0, 255, 0) if state else (255, 0, 0)
        draw.ellipse([x-8, y-8, x+8, y+8], fill=color, outline="black", width=2)
        draw.text((x+10, y-6), tag, fill="black")
    
    st.image(preview_img, use_container_width=True, caption="🔴 RED = Selected Pipe | 🔵 BLUE = Other Pipes")

except Exception as e:
    st.error(f"Preview error: {e}")

# Valve Controls
with st.sidebar:
    st.header("🎯 Valve Controls")
    for tag in valves:
        state = st.session_state.valve_states[tag]
        label = f"🔴 {tag}" if state else f"🟢 {tag}"
        if st.button(label, key=f"valve_{tag}", use_container_width=True):
            st.session_state.valve_states[tag] = not state
            st.rerun()

# Current Coordinates
st.header("📋 Current Pipe Positions")
for i, pipe in enumerate(st.session_state.pipes):
    st.write(f"**Pipe {i+1}:** ({pipe['x1']}, {pipe['y1']}) to ({pipe['x2']}, {pipe['y2']})")

st.success("🎉 **ALIGNMENT COMPLETE WHEN PIPES MATCH YOUR P&ID!**")
