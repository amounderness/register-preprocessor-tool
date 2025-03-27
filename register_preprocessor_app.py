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
# Define Cleaning Logic
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

# -------------------------
# Process and Export
# -------------------------
if 'df_raw' in locals():
    expected_cols = ['Elector Number Prefix', 'Elector Number', 'Elector Number Suffix', 'Elector Markers', 'Name', 'Postcode', 'Address 1']
    available_cols = df_raw.columns.tolist()
    missing_cols = [col for col in expected_cols if col not in available_cols]

    if missing_cols:
        st.warning(f"Missing expected columns: {missing_cols}")
    else:
        df_raw['Elector Marker Type'] = df_raw['Elector Markers'].apply(translate_marker)
        df_raw['Street'] = df_raw['Address 1'].apply(extract_street)
        df_raw['Address'] = df_raw['Address 1']

        df_clean = df_raw.copy()
        df_clean = df_clean[expected_cols + ['Elector Marker Type', 'Street', 'Address']]

        st.markdown("### 🧾 Cleaned Electoral Register")
        st.dataframe(df_clean.head(20))

        st.download_button(
            label="📥 Download Clean CSV",
            data=df_clean.to_csv(index=False).encode('utf-8'),
            file_name="Clean_Electoral_Register.csv",
            mime="text/csv"
        )
