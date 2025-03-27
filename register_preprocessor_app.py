import streamlit as st
import pandas as pd
import re
import pdfplumber
import pytesseract
from PIL import Image
import io

# -------------------------
# Title and Instructions
# -------------------------
st.set_page_config(page_title="Register Pre-Processor", layout="wide")
st.title("🧹 Electoral Register Pre-Processor")

st.markdown("""
This tool helps campaigners convert a raw electoral register into a clean, machine-readable format for further use in:
- 🛣️ Route planning
- 📨 Postal vote tracking
- 📊 Voter contact recording

✅ Upload a CSV, PDF, or scanned image
✅ The app will identify and clean key fields
✅ Export the cleaned register for use in other tools
""")

# -------------------------
# Upload or Paste Input
# -------------------------
input_method = st.radio("Select Input Method:", ["Upload CSV", "Upload PDF", "Upload Image (PNG/JPG)", "Paste Table"], horizontal=True)

if input_method == "Upload CSV":
    uploaded_file = st.file_uploader("Upload raw electoral register CSV", type=["csv"])
    if uploaded_file:
        df_raw = pd.read_csv(uploaded_file)
        st.success("CSV file uploaded successfully.")

elif input_method == "Upload PDF":
    pdf_file = st.file_uploader("Upload scanned or digital electoral register PDF", type=["pdf"])
    if pdf_file:
        with pdfplumber.open(pdf_file) as pdf:
            text = "\n".join([page.extract_text() for page in pdf if page.extract_text()])
        rows = [line.split("\t") for line in text.split("\n") if line.strip()]
        df_raw = pd.DataFrame(rows)
        st.success("PDF content extracted. Please review below.")

elif input_method == "Upload Image (PNG/JPG)":
    image_file = st.file_uploader("Upload a scanned electoral register image (PNG or JPG)", type=["png", "jpg", "jpeg"])
    if image_file:
        image = Image.open(image_file)
        ocr_text = pytesseract.image_to_string(image)
        rows = [line.split("\t") for line in ocr_text.split("\n") if line.strip()]
        df_raw = pd.DataFrame(rows)
        st.success("Image scanned and text extracted. Please review below.")

elif input_method == "Paste Table":
    pasted = st.text_area("Paste your register table below:")
    if pasted:
        try:
            df_raw = pd.read_csv(io.StringIO(pasted))
            st.success("Table parsed successfully.")
        except:
            st.error("Could not parse pasted table. Make sure it's comma-separated.")

# -------------------------
# Define Helper Functions
# -------------------------
def translate_marker(marker):
    if pd.isna(marker): return "Eligible for all local elections"
    marker = marker.strip().upper()
    mapping = {
        'F': 'Overseas voter – Parliamentary only',
        'G': 'EU citizen – local elections only',
        'B': 'EU citizen (retained rights/qualifying)',
        'L': 'Peer – local elections only',
        'M': 'Qualifying foreign citizen – local elections only',
        'N': 'Attainer (not yet voting age)',
    }
    output = []
    for char in marker:
        output.append(mapping.get(char, f"Unknown ({char})"))
    return ", ".join(output)

def detect_column(possible_names, columns, exact_match=False):
    for col in columns:
        for name in possible_names:
            if exact_match:
                if name.lower() == col.lower():
                    return col
            else:
                if name.lower() in col.lower():
                    return col
    return None

# -------------------------
# Process and Export
# -------------------------
if 'df_raw' in locals():
    cols = df_raw.columns.tolist()

    full_elector_col = detect_column(['full elector number'], cols, exact_match=True)
    prefix_col = detect_column(['elector number prefix'], cols, exact_match=True)
    number_col = detect_column(['elector number'], [col for col in cols if col != prefix_col], exact_match=True)
    suffix_col = detect_column(['elector number suffix'], cols, exact_match=True)
    marker_col = detect_column(['marker', 'franchise'], cols)
    name_col = detect_column(['name'], cols)
    postcode_col = detect_column(['postcode'], cols)
    address1_col = detect_column(['address 1'], cols)
    address2_col = detect_column(['address 2'], cols)

    if not all([marker_col, name_col, postcode_col, address1_col]):
        st.warning("Missing one or more expected columns. Please check your input file.")
    else:
        if full_elector_col:
            df_raw['Elector Number'] = df_raw[full_elector_col].astype(str).str.strip()
            df_raw['Polling District'] = df_raw['Elector Number'].str.extract(r'^(\w+)')[0]
        elif prefix_col and number_col and suffix_col:
            prefix_vals = df_raw[prefix_col].astype(str).str.strip()
            number_vals = df_raw[number_col].astype(str).str.strip()
            suffix_vals = df_raw[suffix_col].astype(str).str.strip()

            df_raw['Elector Number'] = [
                f"{p}.{n}.{s}" if all([p, n, s]) else ""
                for p, n, s in zip(prefix_vals, number_vals, suffix_vals)
            ]
            df_raw['Polling District'] = prefix_vals
        else:
            st.warning("Cannot determine Elector Number from the input file. Please check the column headers.")

        df_raw['Elector Marker Type'] = df_raw[marker_col].apply(translate_marker)

        keep_cols = [
            'Elector Number', 'Polling District', name_col, postcode_col,
            address1_col, address2_col, 'Elector Marker Type'
        ]

        keep_cols = [col for col in keep_cols if col in df_raw.columns]  # Ensure all exist
        df_clean = df_raw[keep_cols].copy()

        st.markdown("### 🧾 Cleaned Electoral Register")
        st.dataframe(df_clean.head(20))

        st.download_button(
            label="📥 Download Clean CSV",
            data=df_clean.to_csv(index=False).encode('utf-8'),
            file_name="Clean_Electoral_Register.csv",
            mime="text/csv"
        )
