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
            pipes_data = json.load(f)
            # Check if pipes need to be scaled (if coordinates are very small)
            if pipes_data and pipes_data[0]["x1"] < 100:  # If first pipe has small coordinates
                return scale_pipe_coordinates(pipes_data)
            return pipes_data
    return []

def scale_pipe_coordinates(pipes_data, scale_factor=10):
    """Scale up pipe coordinates that are too small to be visible"""
    st.warning("🔍 Scaling pipe coordinates for better visibility...")
    scaled_pipes = []
    for pipe in pipes_data:
        scaled_pipe = {
            "x1": pipe["x1"] * scale_factor,
            "y1": pipe["y1"] * scale_factor,
            "x2": pipe["x2"] * scale_factor,
            "y2": pipe["y2"] * scale_factor
        }
        scaled_pipes.append(scaled_pipe)
    
    # Save the scaled coordinates
    save_pipes(scaled_pipes)
    return scaled_pipes

def normalize_pipe_coordinates(pipes_data):
    """Normalize pipe coordinates to spread them across the image"""
    st.warning("🔄 Normalizing pipe coordinates...")
    
    # Find min and max coordinates
    all_x = [pipe["x1"] for pipe in pipes_data] + [pipe["x2"] for pipe in pipes_data]
    all_y = [pipe["y1"] for pipe in pipes_data] + [pipe["y2"] for pipe in pipes_data]
    
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    
    img_width, img_height = get_image_dimensions()
    
    normalized_pipes = []
    for pipe in pipes_data:
        # Normalize coordinates to image dimensions
        norm_pipe = {
            "x1": int((pipe["x1"] - min_x) / (max_x - min_x) * img_width * 0.8 + img_width * 0.1),
            "y1": int((pipe["y1"] - min_y) / (max_y - min_y) * img_height * 0.8 + img_height * 0.1),
            "x2": int((pipe["x2"] - min_x) / (max_x - min_x) * img_width * 0.8 + img_width * 0.1),
            "y2": int((pipe["y2"] - min_y) / (max_y - min_y) * img_height * 0.8 + img_height * 0.1)
        }
        normalized_pipes.append(norm_pipe)
    
    # Save the normalized coordinates
    save_pipes(normalized_pipes)
    return normalized_pipes

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

# Pipe coordinate tools
st.warning("🔍 Your pipes have very small coordinates. Use the tools below to make them visible:")

col_tools1, col_tools2, col_tools3 = st.columns(3)
with col_tools1:
    if st.button("📏 SCALE COORDINATES (10x)", use_container_width=True):
        st.session_state.pipes = scale_pipe_coordinates(st.session_state.pipes, 10)
        st.success("✅ Coordinates scaled 10x!")
        st.rerun()
with col_tools2:
    if st.button("🔄 NORMALIZE COORDINATES", use_container_width=True):
        st.session_state.pipes = normalize_pipe_coordinates(st.session_state.pipes)
        st.success("✅ Coordinates normalized!")
        st.rerun()
with col_tools3:
    if st.button("🗑️ RESET TO ORIGINAL", use_container_width=True, type="secondary"):
        original_pipes = [
            {"x1": 3, "y1": 254, "x2": 16, "y2": 254},
            {"x1": 3, "y1": 655, "x2": 11, "y2": 655},
            {"x1": 0, "y1": 768, "x2": 14, "y2": 768},
            {"x1": 11, "y1": 791, "x2": 597, "y2": 789},
            {"x1": 722, "y1": 789, "x2": 994, "y2": 789},
            {"x1": 773, "y1": 655, "x2": 784, "y2": 655},
            {"x1": 410, "y1": 485, "x2": 423, "y2": 485},
            {"x1": 994, "y1": 637, "x2": 1001, "y2": 637},
            {"x1": 776, "y1": 0, "x2": 778, "y2": 0},
            {"x1": 502, "y1": 363, "x2": 510, "y2": 363},
            {"x1": 505, "y1": 393, "x2": 773, "y2": 393},
            {"x1": 413, "y1": 313, "x2": 420, "y2": 313},
            {"x1": 241, "y1": 476, "x2": 249, "y2": 476},
            {"x1": 241, "y1": 254, "x2": 249, "y2": 254},
            {"x1": 994, "y1": 121, "x2": 998, "y2": 121},
            {"x1": 502, "y1": 0, "x2": 510, "y2": 0},
            {"x1": 241, "y1": 0, "x2": 249, "y2": 0},
            {"x1": 994, "y1": 520, "x2": 998, "y2": 520},
            {"x1": 995, "y1": 38, "x2": 1001, "y2": 38},
            {"x1": 1001, "y1": 38, "x2": 1200, "y2": 38},
            {"x1": 0, "y1": 154, "x2": 5, "y2": 154},
            {"x1": 0, "y1": 0, "x2": 5, "y2": 0}
        ]
        st.session_state.pipes = original_pipes
        save_pipes(original_pipes)
        st.success("✅ Reset to original coordinates!")
        st.rerun()

# Rest of your compact controls code continues here...
# [Include the compact controls code from previous response]
