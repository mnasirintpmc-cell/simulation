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
st.title("🎯 PIPE ALIGNMENT TOOL - CLICK & MOVE")

st.markdown("""
### **EASY PROCESS:**
1. **Click any pipe button** to select it (turns PURPLE 🟣)
2. **Use arrow keys or sliders** to move it  
3. **See it move in real-time**
4. **Repeat** for all pipes
""")

# Display P&ID background
st.header("📍 Your P&ID Background")
try:
    pid_img = Image.open(PID_FILE)
    st.image(pid_img, use_container_width=True, caption="Align pipes to match this P&ID")
except:
    st.error("Could not load P&ID.png")

# Clickable Pipe Selection - HORIZONTAL LAYOUT
st.header("🎯 Click to Select Pipe")
st.info("🟣 **PURPLE = Selected** | 🔵 Blue = Not selected")

if st.session_state.pipes:
    # Create clickable buttons in a horizontal layout
    cols = st.columns(len(st.session_state.pipes))
    for i, pipe in enumerate(st.session_state.pipes):
        with cols[i]:
            is_selected = st.session_state.selected_pipe == i
            button_color = "🟣" if is_selected else "🔵"
            button_text = f"{button_color} Pipe {i+1}"
            
            if st.button(button_text, key=f"select_{i}", use_container_width=True):
                st.session_state.selected_pipe = i
                st.rerun()

# Movement Controls
st.header("🔄 Move Selected Pipe")

if st.session_state.selected_pipe is not None:
    current_pipe = st.session_state.pipes[st.session_state.selected_pipe]
    st.success(f"**Selected: 🟣 Pipe {st.session_state.selected_pipe + 1}**")
    
    # Big Arrow Buttons
    st.subheader("🎮 Arrow Controls (5px moves)")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("⬅️ LEFT", use_container_width=True, type="primary"):
            current_pipe["x1"] -= 5
            current_pipe["x2"] -= 5
            save_pipes(st.session_state.pipes)
            st.rerun()
    
    with col2:
        if st.button("➡️ RIGHT", use_container_width=True, type="primary"):
            current_pipe["x1"] += 5
            current_pipe["x2"] += 5
            save_pipes(st.session_state.pipes)
            st.rerun()
    
    with col3:
        if st.button("⬆️ UP", use_container_width=True, type="primary"):
            current_pipe["y1"] -= 5
            current_pipe["y2"] -= 5
            save_pipes(st.session_state.pipes)
            st.rerun()
    
    with col4:
        if st.button("⬇️ DOWN", use_container_width=True, type="primary"):
            current_pipe["y1"] += 5
            current_pipe["y2"] += 5
            save_pipes(st.session_state.pipes)
            st.rerun()
    
    # Fine Adjustment Sliders
    st.subheader("🎛️ Fine Adjustment Sliders")
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        move_x = st.slider("Move X", -50, 50, 0, key="fine_x")
    
    with col2:
        move_y = st.slider("Move Y", -50, 50, 0, key="fine_y")
    
    with col3:
        if st.button("🚀 APPLY", use_container_width=True, type="secondary"):
            current_pipe["x1"] += move_x
            current_pipe["x2"] += move_x
            current_pipe["y1"] += move_y
            current_pipe["y2"] += move_y
            save_pipes(st.session_state.pipes)
            st.rerun()
    
    # Quick Jump to Coordinates
    st.subheader("🎯 Jump to Exact Position")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        new_x1 = st.number_input("Start X", value=current_pipe["x1"], key="jump_x1")
    with col2:
        new_y1 = st.number_input("Start Y", value=current_pipe["y1"], key="jump_y1")
    with col3:
        new_x2 = st.number_input("End X", value=current_pipe["x2"], key="jump_x2")
    with col4:
        new_y2 = st.number_input("End Y", value=current_pipe["y2"], key="jump_y2")
    
    if st.button("💫 JUMP TO POSITION", use_container_width=True):
        current_pipe["x1"] = new_x1
        current_pipe["y1"] = new_y1
        current_pipe["x2"] = new_x2
        current_pipe["y2"] = new_y2
        save_pipes(st.session_state.pipes)
        st.rerun()

# Real-time Preview
st.header("👁️ Live Preview - PURPLE = Selected")
try:
    # Create preview image
    preview_img = Image.open(PID_FILE).convert("RGBA")
    draw = ImageDraw.Draw(preview_img)
    
    # Draw all pipes
    for i, pipe in enumerate(st.session_state.pipes):
        if i == st.session_state.selected_pipe:
            # SELECTED PIPE: PURPLE and THICK
            color = (128, 0, 128)  # PURPLE
            width = 10
            # Add glowing effect
            draw.line([(pipe["x1"], pipe["y1"]), (pipe["x2"], pipe["y2"])], fill=(255, 255, 255), width=width+4)
        else:
            # Other pipes: Light blue and thin
            color = (100, 100, 255)
            width = 4
        
        draw.line([(pipe["x1"], pipe["y1"]), (pipe["x2"], pipe["y2"])], fill=color, width=width)
        
        # Add endpoints for selected pipe
        if i == st.session_state.selected_pipe:
            draw.ellipse([pipe["x1"]-8, pipe["y1"]-8, pipe["x1"]+8, pipe["y1"]+8], fill=(255, 0, 0), outline="white", width=2)
            draw.ellipse([pipe["x2"]-8, pipe["y2"]-8, pipe["x2"]+8, pipe["y2"]+8], fill=(255, 0, 0), outline="white", width=2)
    
    # Draw valves
    for tag, data in valves.items():
        x, y = data["x"], data["y"]
        state = st.session_state.valve_states[tag]
        color = (0, 255, 0) if state else (255, 0, 0)
        draw.ellipse([x-8, y-8, x+8, y+8], fill=color, outline="black", width=2)
        draw.text((x+10, y-6), tag, fill="black")
    
    st.image(preview_img, use_container_width=True, caption="🟣 PURPLE = Selected Pipe | 🔵 Blue = Other Pipes | 🔴 Red dots = Selected pipe endpoints")

except Exception as e:
    st.error(f"Preview error: {e}")

# Valve Controls in Sidebar
with st.sidebar:
    st.header("🎯 Valve Controls")
    for tag in valves:
        state = st.session_state.valve_states[tag]
        label = f"🔴 {tag}" if state else f"🟢 {tag}"
        if st.button(label, key=f"valve_{tag}", use_container_width=True):
            st.session_state.valve_states[tag] = not state
            st.rerun()
    
    st.markdown("---")
    st.header("💾 Save/Load")
    if st.button("💾 Save All Pipes", use_container_width=True, type="primary"):
        save_pipes(st.session_state.pipes)
        st.sidebar.success("Saved!")
    
    if st.button("🔄 Reset Selection", use_container_width=True):
        st.session_state.selected_pipe = 0
        st.rerun()

# Current Coordinates
st.header("📋 All Pipe Positions")
for i, pipe in enumerate(st.session_state.pipes):
    if i == st.session_state.selected_pipe:
        st.success(f"**🟣 Pipe {i+1}:** ({pipe['x1']}, {pipe['y1']}) to ({pipe['x2']}, {pipe['y2']})")
    else:
        st.write(f"Pipe {i+1}: ({pipe['x1']}, {pipe['y1']}) to ({pipe['x2']}, {pipe['y2']})")

st.success("🎉 **Click pipe buttons → Use arrows/sliders → Watch PURPLE pipe move!**")
