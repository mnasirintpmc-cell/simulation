import streamlit as st
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw
import os

st.set_page_config(layout="wide")

# Configuration
PID_FILE = "P&ID.png"
DATA_FILE = "valves.json"

def load_valves():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def analyze_pid_structure():
    """Analyze P&ID image to detect pipes, valves, and connections"""
    try:
        # Load the image
        image = cv2.imread(PID_FILE)
        if image is None:
            st.error("Could not load P&ID image")
            return None
            
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply edge detection to find pipes and lines
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Detect lines using HoughLinesP (for pipes)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, 
                               minLineLength=30, maxLineGap=10)
        
        # Detect circles (for valves, tanks, etc.)
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1, minDist=20,
                                  param1=50, param2=30, minRadius=5, maxRadius=50)
        
        analysis_results = {
            "detected_lines": lines.shape[0] if lines is not None else 0,
            "detected_circles": circles.shape[1] if circles is not None else 0,
            "image_dimensions": f"{image.shape[1]} x {image.shape[0]}",
            "estimated_pipes": [],
            "potential_valves": []
        }
        
        return analysis_results
        
    except Exception as e:
        st.error(f"Error analyzing P&ID: {e}")
        return None

def create_mechanical_analysis_display():
    """Create a display that helps analyze mechanical characteristics"""
    try:
        pid_img = Image.open(PID_FILE).convert("RGBA")
        draw = ImageDraw.Draw(pid_img)
        
        # Add grid for coordinate reference
        width, height = pid_img.size
        grid_spacing = 50
        
        # Draw grid (light gray)
        for x in range(0, width, grid_spacing):
            draw.line([(x, 0), (x, height)], fill=(200, 200, 200, 100), width=1)
        for y in range(0, height, grid_spacing):
            draw.line([(0, y), (width, y)], fill=(200, 200, 200, 100), width=1)
        
        # Add coordinate labels
        for x in range(0, width, 100):
            draw.text((x, 10), str(x), fill=(100, 100, 100, 200))
        for y in range(0, height, 100):
            draw.text((10, y), str(y), fill=(100, 100, 100, 200))
        
        return pid_img.convert("RGB")
    
    except Exception as e:
        st.error(f"Error creating analysis display: {e}")
        return Image.new("RGB", (800, 600), (255, 255, 255))

# Load valve data
valves = load_valves()

# Initialize session state
if "valve_states" not in st.session_state:
    st.session_state.valve_states = {tag: data["state"] for tag, data in valves.items()}

# Main app
st.title("🔧 P&ID Mechanical Analysis Tool")

# Analysis Section
st.header("1. P&ID Structural Analysis")

# Perform automatic analysis
with st.spinner("Analyzing P&ID structure..."):
    analysis = analyze_pid_structure()

if analysis:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Detected Lines", analysis["detected_lines"])
    with col2:
        st.metric("Detected Circles", analysis["detected_circles"])
    with col3:
        st.metric("Image Size", analysis["image_dimensions"])

# Display P&ID with coordinate grid
st.header("2. Coordinate Reference Grid")
st.markdown("**Use this grid to identify pipe coordinates and valve positions**")

analysis_img = create_mechanical_analysis_display()
st.image(analysis_img, use_container_width=True, caption="P&ID with Coordinate Grid - Note down pipe coordinates")

# Manual Pipe Configuration Section
st.header("3. Manual Pipe Path Configuration")

st.markdown("### 🎯 How to Map Your P&ID:")

st.markdown("**Step 1: Trace Pipe Paths**")
st.markdown("- Follow each pipe from start to end")
st.markdown("- Note the (x,y) coordinates where pipes change direction")
st.markdown("- Pipes are typically straight lines between fittings")

st.markdown("**Step 2: Identify Valve Locations**")
st.markdown("- Valves are usually shown as circles or specific symbols")
st.markdown("- Note the exact (x,y) coordinates of each valve")
st.markdown("- Valves break pipe continuity")

st.markdown("**Step 3: Define Flow Logic**")
st.markdown("- Flow requires continuous open path from source to destination")
st.markdown("- Each closed valve blocks flow in its section")
st.markdown("- Multiple valves may control complex paths")

# Current valve positions display
st.header("4. Current Valve Configuration")
if valves:
    st.success(f"✅ Found {len(valves)} valves in configuration")
    
    cols = st.columns(3)
    for i, (tag, data) in enumerate(valves.items()):
        col_idx = i % 3
        with cols[col_idx]:
            st.write(f"**{tag}**")
            st.write(f"Position: ({data['x']}, {data['y']})")
            st.write(f"Initial: {'OPEN' if data['state'] else 'CLOSED'}")
else:
    st.error("❌ No valves configured")

# Pipe Mapping Interface
st.header("5. Map Your Pipe Sections")

with st.form("pipe_mapping_form"):
    st.subheader("Add Pipe Section")
    
    section_name = st.text_input("Section Name (e.g., 'Supply_Line', 'Main_Header')")
    
    st.markdown("**Pipe Coordinates (follow the pipe path):**")
    col1, col2 = st.columns(2)
    with col1:
        x1 = st.number_input("Start X", value=0, key="x1")
        y1 = st.number_input("Start Y", value=0, key="y1")
        x2 = st.number_input("End X", value=100, key="x2")
        y2 = st.number_input("End Y", value=100, key="y2")
    
    with col2:
        # Add more coordinate pairs for complex paths
        st.markdown("**Additional points (for curved/bent pipes):**")
        x3 = st.number_input("Point 3 X", value=0, key="x3")
        y3 = st.number_input("Point 3 Y", value=0, key="y3")
        x4 = st.number_input("Point 4 X", value=0, key="x4")
        y4 = st.number_input("Point 4 Y", value=0, key="y4")
    
    st.markdown("**Valves Controlling This Section:**")
    if valves:
        controlling_valves = st.multiselect(
            "Select valves that control flow in this section",
            options=list(valves.keys()),
            help="Flow will only pass if ALL selected valves are OPEN"
        )
    else:
        st.warning("No valves configured yet")
        controlling_valves = []
    
    if st.form_submit_button("Add Pipe Section"):
        if section_name and controlling_valves:
            st.success(f"Added section '{section_name}' controlled by {controlling_valves}")
        else:
            st.error("Please provide section name and controlling valves")

# Template for providing your actual P&ID data
st.header("6. Provide Your P&ID Data")

st.markdown("### 📋 Copy this template and fill with your actual P&ID data:")

st.code("""# VALVE POSITIONS (from your valves.json - already done)
# V-101: (x, y)
# V-301: (x, y) 
# V-105: (x, y)
# [Add other valves...]

# PIPE SECTIONS - TRACE THESE ON YOUR P&ID:

pipe_segments = {
    "supply_line": {
        "coords": [
            (SOURCE_X, SOURCE_Y, V101_X, V101_Y)  # From source to V-101
        ],
        "flow_logic": ["V-101"]  # Only V-101 controls this section
    },
    "section_1": {
        "coords": [
            (V101_X, V101_Y, MIDPOINT_X, MIDPOINT_Y),  # V-101 to midpoint
            (MIDPOINT_X, MIDPOINT_Y, V301_X, V301_Y)   # Midpoint to V-301
        ],
        "flow_logic": ["V-101"]  # Flow exists if V-101 is open
    },
    "section_2": {
        "coords": [
            (V301_X, V301_Y, V105_X, V105_Y)  # V-301 to V-105
        ],
        "flow_logic": ["V-101", "V-301"]  # Needs both valves open
    },
    "section_3": {
        "coords": [
            (V105_X, V105_Y, DESTINATION_X, DESTINATION_Y)  # V-105 to destination
        ],
        "flow_logic": ["V-101", "V-301", "V-105"]  # Needs all three valves
    }
}""")

st.markdown("### 🎯 What I Need From You:")

st.markdown("1. **Trace each pipe** on your P&ID and provide the (x,y) coordinates")
st.markdown("2. **Tell me the flow logic** - which valves control which sections")
st.markdown("3. **Identify all components** - pumps, tanks, instruments")
st.markdown("4. **Describe the overall process flow** - source to destination")

# Quick Help Section
with st.expander("🔍 Mechanical Analysis Tips"):
    st.markdown("**P&ID Reading Fundamentals:**")
    st.markdown("- **Pipes**: Solid lines, follow the flow path")
    st.markdown("- **Valves**: Circles/diamonds that break pipe continuity")  
    st.markdown("- **Flow Direction**: Typically left-to-right or top-to-bottom")
    st.markdown("- **Fittings**: Elbows, tees, reducers where pipes change direction")
    
    st.markdown("**Coordinate Mapping:**")
    st.markdown("- Start at component center points")
    st.markdown("- Follow pipe centerlines")
    st.markdown("- Note coordinates at every direction change")
    st.markdown("- Include all valves in the flow path")
    
    st.markdown("**Flow Logic Rules:**")
    st.markdown("- Flow requires continuous open path")
    st.markdown("- Each closed valve blocks its section")
    st.markdown("- Multiple valves create complex logic")
    st.markdown("- Source valve (like V-101) controls entire system")

# Next Steps
st.header("🎯 Next Steps")
st.markdown("1. **Study your P&ID** and trace the main flow paths")
st.markdown("2. **Note down coordinates** using the grid above")  
st.markdown("3. **Identify all valves** and their positions")
st.markdown("4. **Describe the flow logic** for each pipe section")
st.markdown("5. **Provide this information** so I can build accurate flow simulation")

st.markdown("**Once you provide the pipe coordinates and flow logic, I'll create the exact simulation you need!**")
