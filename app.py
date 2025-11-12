def load_lines():
    if not os.path.exists(LINES_FILE):
        st.warning(f"Missing {LINES_FILE} – upload your Figma export")
        return []

    if LINES_FILE.endswith(".svg"):
        import xml.etree.ElementTree as ET
        try:
            tree = ET.parse(LINES_FILE)
            root = tree.getroot()
            ns = {'svg': 'http://www.w3.org/2000/svg'}
            lines = []
            for line in root.findall('.//svg:line', ns):
                try:
                    x1 = int(float(line.get('x1', 0)))
                    y1 = int(float(line.get('y1', 0)))
                    x2 = int(float(line.get('x2', 0)))
                    y2 = int(float(line.get('y2', 0)))
                    if (x1, y1) != (x2, y2):
                        lines.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2})
                except:
                    pass
            return lines
        except Exception as e:
            st.error(f"SVG parse error: {e}")
            return []
    else:
        try:
            with open(LINES_FILE) as f:
                data = json.load(f)
            return data.get("lines", data) if isinstance(data, dict) else data
        except Exception as e:
            st.error(f"JSON error: {e}")
            return []
