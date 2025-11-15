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

def get_image_dimensions():
    """Get the dimensions of the P&ID image"""
    try:
        with Image.open(PID_FILE) as img:
            return img.size
    except:
        return (1200, 800)  # Default fallback

def create_pid_with_valves_and_pipes():
    """Create P&ID image with valve indicators AND pipes"""
    try:
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
        img_width, img_height = pid_img.size
        
        # Draw pipes FIRST (so valves appear on top)
        if st.session_state.pipes:
            for i, pipe in enumerate(st.session_state.pipes):
                is_reasonable = (
                    -1000 <= pipe["x1"] <= img_width + 1000 and
                    -1000 <= pipe["x2"] <= img_width + 1000 and
                    -1000 <= pipe["y1"] <= img_height + 1000 and
                    -1000 <= pipe["y2"] <= img_height + 1000
                )
                
                if is_reasonable:
                    color = (148, 0, 211) if i == st.session_state.selected_pipe else (0, 0, 255)
                    width = 8 if i == st.session_state.selected_pipe else 6
                    draw.line([(pipe["x1"], pipe["y1"]), (pipe["x2"], pipe["y2"])], fill=color, width=width)
                    
                    if i == st.session_state.selected_pipe:
                        draw.ellipse([pipe["x1"]-6, pipe["y1"]-6, pipe["x1"]+6, pipe["y1"]+6], fill=(255, 0, 0), outline="white", width=2)
                        draw.ellipse([pipe["x2"]-6, pipe["y2"]-6, pipe["x2"]+6, pipe["y2"]+6], fill=(255, 0, 0), outline="white", width=2)
        
        # Draw valves on top of pipes
        for tag, data in valves.items():
            x, y = data["x"], data["y"]
            current_state = st.session_state.valve_states[tag]
            
            color = (0, 255, 0) if current_state else (255, 0, 0)
            draw.ellipse([x-8, y-8, x+8, y+8], fill=color, outline="white", width=2)
            draw.text((x+12, y-10), tag, fill="white", stroke_fill="black", stroke_width=1)
            
        return pid_img.convert("RGB")
    except Exception as e:
        st.error(f"Error creating P&ID image: {e}")
        try:
            return Image.open(PID_FILE).convert("RGB")
        except:
            return Image.new("RGB", (1200, 800), (255, 255, 255))

# Load valve data
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
st.title("P&ID Interactive Simulation")

# FIX PIPE COORDINATES SECTION
st.error("🚨 PROBLEM: Your pipe coordinates are too small to be visible!")
st.info("Your current pipes.json has very small coordinates (mostly 0-20 pixels). Click below to FIX this:")

col_fix1, col_fix2 = st.columns(2)
with col_fix1:
    if st.button("🛠️ FIX PIPE COORDINATES (Scale 15x)", type="primary", use_container_width=True):
        # Scale up all coordinates by 15x to make them visible
        scaled_pipes = []
        for pipe in st.session_state.pipes:
            scaled_pipe = {
                "x1": pipe["x1"] * 15,
                "y1": pipe["y1"] * 15, 
                "x2": pipe["x2"] * 15,
                "y2": pipe["y2"] * 15
            }
            scaled_pipes.append(scaled_pipe)
        
        # UPDATE THE ACTUAL JSON FILE
        st.session_state.pipes = scaled_pipes
        save_pipes(scaled_pipes)
        st.success("✅ pipes.json UPDATED! Coordinates scaled 15x for visibility!")
        st.rerun()

with col_fix2:
    if st.button("📊 Show Current JSON", use_container_width=True):
        st.subheader("Current pipes.json content:")
        st.json(st.session_state.pipes)

# Regular controls
col_top1, col_top2 = st.columns([3, 1])
with col_top1:
    st.info("💾 Pipe positions auto-save when moved")
with col_top2:
    if st.button("💾 MANUAL SAVE", use_container_width=True, type="secondary"):
        save_pipes(st.session_state.pipes)
        st.success("✅ Saved!")

if not valves:
    st.error("No valves found in valves.json. Please check your configuration.")
    st.stop()

# Main content area
col1, col2 = st.columns([3, 1])
with col1:
    composite_img = create_pid_with_valves_and_pipes()
    st.image(composite_img, use_container_width=True, caption="🟣 Selected Pipe | 🔵 Normal Pipe")

with col2:
    # COMPACT CONTROLS
    st.header("🔧 Controls")
    
    if st.session_state.selected_pipe is not None and st.session_state.pipes:
        pipe = st.session_state.pipes[st.session_state.selected_pipe]
        
        # Current pipe info
        st.subheader(f"🟣 Pipe {st.session_state.selected_pipe + 1}")
        st.caption(f"📍 ({pipe['x1']}, {pipe['y1']}) → ({pipe['x2']}, {pipe['y2']})")
        
        # Quick actions
        st.subheader("🎯 Quick Actions")
        action_col1, action_col2, action_col3 = st.columns(3)
        with action_col1:
            if st.button("➖ H", help="Make Horizontal", use_container_width=True):
                center_x, center_y = (pipe["x1"] + pipe["x2"]) // 2, (pipe["y1"] + pipe["y2"]) // 2
                pipe.update({"x1": center_x-50, "y1": center_y, "x2": center_x+50, "y2": center_y})
                save_pipes(st.session_state.pipes)
                st.rerun()
        with action_col2:
            if st.button("➡️ V", help="Make Vertical", use_container_width=True):
                center_x, center_y = (pipe["x1"] + pipe["x2"]) // 2, (pipe["y1"] + pipe["y2"]) // 2
                pipe.update({"x1": center_x, "y1": center_y-50, "x2": center_x, "y2": center_y+50})
                save_pipes(st.session_state.pipes)
                st.rerun()
        with action_col3:
            if st.button("🔄 C", help="Center Pipe", use_container_width=True):
                img_w, img_h = get_image_dimensions()
                pipe.update({"x1": img_w//2-50, "y1": img_h//2, "x2": img_w//2+50, "y2": img_h//2})
                save_pipes(st.session_state.pipes)
                st.rerun()
        
        # Movement controls
        st.subheader("📍 Move Pipe")
        move_col1, move_col2, move_col3, move_col4 = st.columns(4)
        with move_col1:
            if st.button("↑", use_container_width=True):
                pipe["y1"] -= 10; pipe["y2"] -= 10
                save_pipes(st.session_state.pipes); st.rerun()
        with move_col2:
            if st.button("↓", use_container_width=True):
                pipe["y1"] += 10; pipe["y2"] += 10
                save_pipes(st.session_state.pipes); st.rerun()
        with move_col3:
            if st.button("←", use_container_width=True):
                pipe["x1"] -= 10; pipe["x2"] -= 10
                save_pipes(st.session_state.pipes); st.rerun()
        with move_col4:
            if st.button("→", use_container_width=True):
                pipe["x1"] += 10; pipe["x2"] += 10
                save_pipes(st.session_state.pipes); st.rerun()
        
        # Manual coordinates
        st.subheader("🎯 Exact Coordinates")
        coord_col1, coord_col2 = st.columns(2)
        with coord_col1:
            new_x1 = st.number_input("X1", value=pipe["x1"], key="x1")
            new_y1 = st.number_input("Y1", value=pipe["y1"], key="y1")
        with coord_col2:
            new_x2 = st.number_input("X2", value=pipe["x2"], key="x2")
            new_y2 = st.number_input("Y2", value=pipe["y2"], key="y2")
        
        if st.button("💫 APPLY COORDINATES", use_container_width=True, type="primary"):
            pipe.update({"x1": new_x1, "y1": new_y1, "x2": new_x2, "y2": new_y2})
            save_pipes(st.session_state.pipes)
            st.rerun()

    # Pipe selection
    st.markdown("---")
    st.subheader("📋 Select Pipe")
    if st.session_state.pipes:
        pipe_cols = st.columns(4)
        for i, pipe in enumerate(st.session_state.pipes):
            with pipe_cols[i % 4]:
                is_selected = st.session_state.selected_pipe == i
                icon = "🟣" if is_selected else "🔵"
                if st.button(f"{icon}{i+1}", key=f"pipe_{i}", use_container_width=True):
                    st.session_state.selected_pipe = i
                    st.rerun()

    # Valve controls
    st.markdown("---")
    st.subheader("🎯 Valves")
    valve_cols = st.columns(3)
    for i, (tag, data) in enumerate(valves.items()):
        with valve_cols[i % 3]:
            current_state = st.session_state.valve_states[tag]
            icon = "🔴" if current_state else "🟢"
            label = f"{icon} {tag}"
            if st.button(label, key=f"valve_{tag}", use_container_width=True):
                st.session_state.valve_states[tag] = not current_state
                st.rerun()
