# app.py
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import io
import math

st.set_page_config(page_title="P&ID Valve Simulator", layout="wide")
st.title("🔧 P&ID Valve Simulator — Visual (Level 1)")

# ---------- helpers ----------
def draw_image_with_markers(img: Image.Image, valves):
    img2 = img.convert("RGBA").copy()
    draw = ImageDraw.Draw(img2)
    w, h = img2.size
    for v in valves:
        x = int(v["x_pct"] / 100.0 * w)
        y = int(v["y_pct"] / 100.0 * h)
        r = max(6, int(min(w, h) * 0.02))
        color = (0, 200, 0, 200) if v["open"] else (200, 0, 0, 200)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color, outline=(0,0,0,255))
        # label
        draw.text((x + r + 2, y - r), f'{v["name"]}', fill=(255,255,255,230))
    return img2

def get_demo_timeseries(valves, steps=60):
    # Simple demo: each valve toggles state sinusoidally (demo only)
    times = list(range(steps))
    rows = []
    for t in times:
        row = {"time": t}
        for v in valves:
            # demo open fraction between 0 and 1
            phase = (hash(v["name"]) % 7) / 7.0
            frac = 0.5 * (1 + math.sin(2 * math.pi * (t / steps) + phase))
            # map frac -> open (if > 0.5 it's considered open)
            open_now = frac > 0.5
            flow = v["flow_slpm"] if open_now and v["open"] else (v["flow_slpm"] * frac if v["open"] else 0.0)
            pressure = v["pressure_bar"] if open_now and v["open"] else (v["pressure_bar"] * (0.5 + 0.5*frac) if v["open"] else 0.0)
            row[f"{v['name']}_flow_slpm"] = flow
            row[f"{v['name']}_pressure_bar"] = pressure
        rows.append(row)
    return pd.DataFrame(rows)

# ---------- session state ----------
if "valves" not in st.session_state:
    st.session_state.valves = []  # list of dicts: name, x_pct, y_pct, flow_slpm, pressure_bar, open

# ---------- layout ----------
col_l, col_r = st.columns([1, 1])

with col_l:
    st.header("1) Upload P&ID or use blank canvas")
    pid_file = st.file_uploader("Upload P&ID image (PNG/JPG) — optional", type=["png","jpg","jpeg"])
    if pid_file:
        img = Image.open(pid_file).convert("RGB")
        st.session_state._uploaded_img = img
    else:
        # if no uploaded image, try to load from repo default (optional)
        try:
            img = Image.open("P&ID.png").convert("RGB")
            st.session_state._uploaded_img = img
        except Exception:
            img = Image.new("RGB", (1000,600), color=(30,30,30))
            st.session_state._uploaded_img = img
            st.info("No image uploaded — using blank canvas. You can still add valves by percentage X/Y positions.")

    st.image(img, caption="P&ID preview (markers shown below)", use_column_width=True)

    st.markdown("---")
    st.header("2) Add a Valve (by % position)")

    with st.form("add_valve_form", clear_on_submit=True):
        vname = st.text_input("Valve name (unique)", value=f"V{len(st.session_state.valves)+1}")
        col1, col2 = st.columns(2)
        with col1:
            x_pct = st.number_input("X position (%)", min_value=0.0, max_value=100.0, value=10.0)
            y_pct = st.number_input("Y position (%)", min_value=0.0, max_value=100.0, value=10.0)
        with col2:
            flow_slpm = st.number_input("Nominal flow (SLPM)", value=1.0, step=0.1, format="%.3f")
            pressure_bar = st.number_input("Nominal pressure (bar)", value=1.0, step=0.1, format="%.3f")
        open_default = st.checkbox("Start valve open?", value=True)
        submitted = st.form_submit_button("➕ Add Valve")
        if submitted:
            # ensure unique name
            names = [v["name"] for v in st.session_state.valves]
            if vname in names:
                st.error("Valve name must be unique.")
            else:
                st.session_state.valves.append({
                    "name": vname,
                    "x_pct": float(x_pct),
                    "y_pct": float(y_pct),
                    "flow_slpm": float(flow_slpm),
                    "pressure_bar": float(pressure_bar),
                    "open": bool(open_default)
                })
                st.success(f"Added valve {vname}")

    st.markdown("---")
    st.header("3) Valve List & Controls")
    if not st.session_state.valves:
        st.info("No valves added yet.")
    else:
        # show editable table of valves
        df_valves = pd.DataFrame(st.session_state.valves)
        st.dataframe(df_valves[["name","x_pct","y_pct","flow_slpm","pressure_bar","open"]], use_container_width=True)

        # controls per valve
        for idx, v in enumerate(st.session_state.valves):
            cols = st.columns([1,1,1,1,1,1])
            cols[0].markdown(f"**{v['name']}**")
            if cols[1].button("Toggle Open/Close", key=f"toggle_{idx}"):
                st.session_state.valves[idx]["open"] = not st.session_state.valves[idx]["open"]
            if cols[2].button("Remove", key=f"remove_{idx}"):
                st.session_state.valves.pop(idx)
                st.experimental_rerun()
            # small edit inline: flow and pressure
            new_flow = cols[3].number_input("Flow SLPM", value=float(v["flow_slpm"]), key=f"flow_in_{idx}")
            new_pres = cols[4].number_input("Pressure bar", value=float(v["pressure_bar"]), key=f"pres_in_{idx}")
            # apply changes
            st.session_state.valves[idx]["flow_slpm"] = float(new_flow)
            st.session_state.valves[idx]["pressure_bar"] = float(new_pres)

with col_r:
    st.header("Visualization & Simulation")

    # draw image with markers
    img_with = draw_image_with_markers(st.session_state._uploaded_img, st.session_state.valves)
    buf = io.BytesIO()
    img_with.save(buf, format="PNG")
    st.image(buf.getvalue(), caption="P&ID with valves (green=open, red=closed)", use_column_width=True)

    st.markdown("---")
    st.subheader("Snapshot Simulation (current statuses)")
    if not st.session_state.valves:
        st.info("Add valves to simulate.")
    else:
        rows = []
        total_flow = 0.0
        for v in st.session_state.valves:
            flow = v["flow_slpm"] if v["open"] else 0.0
            pressure = v["pressure_bar"] if v["open"] else 0.0
            rows.append({"Valve": v["name"], "Open": v["open"], "Flow_SLPM": flow, "Pressure_bar": pressure})
            total_flow += flow
        snap_df = pd.DataFrame(rows)
        st.table(snap_df)
        st.markdown(f"**Total flow (SLPM)**: {total_flow:.3f}")

    st.markdown("---")
    st.subheader("Demo Time-series Trends (auto demo)")
    steps = st.slider("Time steps (demo)", min_value=10, max_value=300, value=60, step=10)
    if st.button("▶️ Generate Demo Trends"):
        ts = get_demo_timeseries(st.session_state.valves, steps=steps)
        st.dataframe(ts.head(50))
        # show a couple of example charts (flows & pressures)
        flow_cols = [c for c in ts.columns if c.endswith("_flow_slpm")]
        pres_cols = [c for c in ts.columns if c.endswith("_pressure_bar")]
        if flow_cols:
            st.line_chart(ts.set_index("time")[flow_cols])
        if pres_cols:
            st.line_chart(ts.set_index("time")[pres_cols])
        # download
        csv = ts.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Demo Time-series CSV", csv, "demo_trends.csv", "text/csv")

st.markdown("---")
st.caption("Notes: This is a lightweight Level-1 visual simulator. Flows/pressures shown are demo/nominal values for visualization and training — not an engineering hydraulic model.")
