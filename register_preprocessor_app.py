import streamlit as st
import pandas as pd
import re
import pdfplumber
import pytesseract
from PIL import Image
import io
import platform
import subprocess
from datetime import datetime

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
        try:
            with pdfplumber.open(pdf_file) as pdf:
                pages_text = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        pages_text.append(page_text)
                text = "\n".join(pages_text)

            if not text.strip():
                raise ValueError("No extractable text found in PDF. Attempting OCR fallback.")

            lines = [line.strip() for line in text.split("\n") if line.strip()]
            st.markdown("### 📄 Extracted Lines from PDF")
            st.text("\n".join(lines[:30]))

            extracted = []
            for line in lines:
                parts = [part.strip() for part in re.split(r'\s{2,}', line)]
                if len(parts) >= 3:
                    try:
                        elector_number = parts[0]
                        marker_candidate = parts[1]
                        if re.match(r"\d{2}/\d{2}/\d{4}", marker_candidate):
                            marker = marker_candidate
                            name = parts[2]
                            address = parts[3] if len(parts) > 3 else ""
                        elif re.fullmatch(r'[A-Z]{1,3}', marker_candidate):
                            marker = marker_candidate
                            name = parts[2]
                            address = parts[3] if len(parts) > 3 else ""
                        else:
                            marker = ""
                            name = marker_candidate
                            address = parts[2] if len(parts) > 2 else ""

                        extracted.append([elector_number, marker, name, address])
                    except:
                        continue

            if extracted:
                df_raw = pd.DataFrame(extracted, columns=["Elector Number", "Marker", "Name", "Address"])
                df_raw["Elector Marker Type"] = df_raw["Marker"].apply(lambda x: translate_marker(x))
                st.success("Structured data extracted from PDF.")
            else:
                st.warning("Could not parse PDF lines into structured register format.")

        except Exception as e:
            try:
                with pdfplumber.open(pdf_file) as pdf:
                    ocr_text_combined = []
                    for page in pdf.pages:
                        image = page.to_image(resolution=300).original
                        pil_image = Image.frombytes("RGB", image.size, image.tobytes())
                        text = pytesseract.image_to_string(pil_image)
                        ocr_text_combined.append(text)
                ocr_text = "\n".join(ocr_text_combined)
                rows = [line.split("\t") for line in ocr_text.split("\n") if line.strip()]
                df_raw = pd.DataFrame(rows)
                st.success("OCR fallback used. Please review extracted content.")
            except Exception as fallback_error:
                st.error(f"Failed to extract PDF content with OCR: {fallback_error}")

elif input_method == "Upload Image (PNG/JPG)":
    image_file = st.file_uploader("Upload a scanned electoral register image (PNG or JPG)", type=["png", "jpg", "jpeg"])
    if image_file:
        try:
            if platform.system() == "Linux" and not subprocess.getoutput("which tesseract"):
                raise FileNotFoundError("Tesseract is not available on this platform.")
            image = Image.open(image_file)
            ocr_text = pytesseract.image_to_string(image)
            rows = [line.split("\t") for line in ocr_text.split("\n") if line.strip()]
            df_raw = pd.DataFrame(rows)
            st.success("Image scanned and text extracted. Please review below.")
        except FileNotFoundError:
            st.error("OCR is not available in this environment. Please run locally with Tesseract installed or use CSV/PDF.")

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
    if pd.isna(marker): return ""
    marker = marker.strip().upper()
    date_match = re.match(r"(\d{2}/\d{2}/\d{4})", marker)
    if date_match:
        return f"Will become eligible to vote on {date_match.group(1)}"
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
    try:
        if "Elector Number" in df_raw.columns:
            df_raw['Polling District'] = df_raw['Elector Number'].str.extract(r'^(\w+)')[0]

        st.markdown("### 🧾 Cleaned Electoral Register")
        st.dataframe(df_raw.head(20))

        st.download_button(
            label="📥 Download Clean CSV",
            data=df_raw.to_csv(index=False).encode('utf-8'),
            file_name="Clean_Electoral_Register.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.warning("Missing one or more expected columns. Please check your input file.")
