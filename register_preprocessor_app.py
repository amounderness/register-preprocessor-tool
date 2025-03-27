import streamlit as st
import pandas as pd
import re

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

✅ Upload a CSV or paste data below
✅ The app will identify and clean key fields
✅ Export the cleaned register for use in other tools
""")

# -------------------------
# Upload or Paste Input
# -------------------------
input_method = st.radio("Select Input Method:", ["Upload CSV", "Paste Table"], horizontal=True)

if input_method == "Upload CSV":
    uploaded_file = st.file_uploader("Upload raw electoral register CSV", type=["csv"]) 
    if uploaded_file:
        df_raw = pd.read_csv(uploaded_file)
        st.success("File uploaded successfully.")

elif input_method == "Paste Table":
    pasted = st.text_area("Paste your register table below:")
    if pasted:
        try:
            df_raw = pd.read_csv(pd.compat.StringIO(pasted))
            st.success("Table parsed successfully.")
        except:
            st.error("Could not parse pasted table. Make sure it's comma-separated.")

# -------------------------
# Define Helper Functions
# -------------------------
def extract_street(address):
    if pd.isna(address): return ""
    parts = address.split(',')
    return parts[-1].strip() if len(parts) > 1 else address.strip()

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

def detect_column(possible_names, columns):
    for name in possible_names:
        for col in columns:
            if name.lower() in col.lower():
                return col
    return None

# -------------------------
# Process and Export
# -------------------------
if 'df_raw' in locals():
    cols = df_raw.columns.tolist()

    prefix_col = detect_column(['prefix', 'ward'], cols)
    number_col = detect_column(['number'], cols)
    suffix_col = detect_column(['suffix'], cols)
    marker_col = detect_column(['marker', 'franchise'], cols)
    name_col = detect_column(['name'], cols)
    postcode_col = detect_column(['postcode'], cols)
    address1_col = detect_column(['address 1'], cols)
    address2_col = detect_column(['address 2'], cols)

    if not all([prefix_col, number_col, suffix_col, marker_col, name_col, postcode_col, address1_col]):
        st.warning("Missing one or more expected columns. Please check your input file.")
    else:
        df_raw['Elector Number'] = df_raw[prefix_col].astype(str).str.strip() + "." + \
                                    df_raw[number_col].astype(str).str.strip() + "." + \
                                    df_raw[suffix_col].astype(str).str.strip()

        df_raw['Elector Marker Type'] = df_raw[marker_col].apply(translate_marker)
        df_raw['Street'] = df_raw[address1_col].apply(extract_street)
        df_raw['Address'] = df_raw[address1_col]

        keep_cols = [
            'Elector Number', name_col, postcode_col, address1_col, address2_col,
            'Elector Marker Type', 'Street', 'Address'
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
