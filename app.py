import re
import io
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
from PIL import Image

# Browser tab and page layout configuration
st.set_page_config(page_title="Warehouse Label Generator", page_icon="🏷️", layout="centered")

def parsuj_kod(kod):
    """Parses the RR-MMM-PP format string into integers."""
    czesci = kod.split('-')
    if len(czesci) != 3:
        raise ValueError(f"Invalid code format: {kod}. Correct format example: 21-005-08")
    return int(czesci[0]), int(czesci[1]), int(czesci[2])

def generuj_liste_kodow(start, koniec):
    """Generates a full list of sequential codes between start and end parameters."""
    if not koniec:
        return [start]
        
    rz_start, m_start, p_start = parsuj_kod(start)
    rz_koniec, m_koniec, p_koniec = parsuj_kod(koniec)
    
    lista_kodow = []
    MAX_MIEJSCE = 66
    MAX_POZIOM = 6
    
    for rz in range(rz_start, rz_koniec + 1):
        od_m = m_start if rz == rz_start else 1
        do_m = m_koniec if rz == rz_koniec else MAX_MIEJSCE
        
        for m in range(od_m, do_m + 1):
            od_p = p_start if (rz == rz_start and m == m_start) else 1
            do_p = p_koniec if (rz == rz_koniec and m == m_koniec) else MAX_POZIOM
            
            for p in range(od_p, do_p + 1):
                kod_sformatowany = f"{rz:02d}-{m:03d}-{p:02d}"
                lista_kodow.append(kod_sformatowany)
                
    return lista_kodow

def generuj_pdf_w_pamieci(kody, logo_bytes=None):
    """Generates the final PDF in RAM (BytesIO stream), applying an optional company logo."""
    buffer = io.BytesIO()
    width, height = A4
    c = canvas.Canvas(buffer, pagesize=A4)
    
    etykieta_height = height / 4.0
    x_center = width / 2.0
    
    # Logistical sizing parameters
    bar_height = 35 * mm
    logo_size = 35 * mm  # Matches the height of the barcode
    
    # If a logo is provided, dynamically scale the barcode width to fit alongside it
    if logo_bytes:
        max_dostepna_szerokosc = width - (logo_size + 20 * mm)  # Allocate space for logo and paddings
        x_shift_barcode = (logo_size / 2.0) + 5 * mm  # Shift barcode right
    else:
        max_dostepna_szerokosc = width - (10 * mm)
        x_shift_barcode = 0

    for i, tekst_miejsca in enumerate(kody):
        pozycja_na_stronie = i % 4
        
        y_top = height - (pozycja_na_stronie * etykieta_height)
        y_start = y_top - etykieta_height
        y_barcode = y_start + (etykieta_height - bar_height) / 2.0 + 8 * mm
        
        # Calculate barcode module sizes
        probny_barcode = code128.Code128(tekst_miejsca, barWidth=1, barHeight=bar_height, quiet=0)
        idealny_bar_width = min(max_dostepna_szerokosc / probny_barcode.width, 1.45 * mm)
        
        barcode = code128.Code128(tekst_miejsca, barWidth=idealny_bar_width, barHeight=bar_height, quiet=0)
        
        # Render the barcode
        c.saveState()
        barcode_x_pos = (x_center - (barcode.width / 2.0)) + x_shift_barcode
        barcode.drawOn(c, barcode_x_pos, y_barcode)
        c.restoreState()
        
        # Render the company logo on the left side (if uploaded)
        if logo_bytes:
            logo_x_pos = barcode_x_pos - logo_size - 5 * mm
            logo_img = Image.open(io.BytesIO(logo_bytes))
            c.drawImage(logo_img, logo_x_pos, y_barcode, width=logo_size, height=logo_size, mask='auto')
        
        # Render the large human-readable text label centered below the barcode
        c.setFont("Helvetica-Bold", 38)
        y_text = y_barcode - 15 * mm
        c.drawCentredString(x_center, y_text, tekst_miejsca)
        
        # Render the cutting guides
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.setLineWidth(0.5)
        c.line(0, y_start, width, y_start)
        
        if pozycja_na_stronie == 3 or i == len(kody) - 1:
            c.showPage()
            
    c.save()
    buffer.seek(0)
    return buffer

# --- WEB USER INTERFACE (STREAMLIT) ---
st.title("🏭 Warehouse Label Generator")
st.markdown("Enter your shelf location range and optionally add a company logo to download layout-ready A4 PDF sheets (**4 horizontal labels per page**).")

# Sidebar settings for logo uploading and branding signatures
with st.sidebar:
    st.header("⚙️ Additional Options")
    uploaded_logo = st.file_uploader("Upload Company Logo (PNG/JPG):", type=["png", "jpg", "jpeg"])
    if uploaded_logo:
        st.image(uploaded_logo, caption="Logo Preview", use_container_width=True)
    
    st.markdown("---")
    st.caption("Developed by **Kamil H.**")

st.info("Input format: **RR-MMM-PP** (e.g., `24-001-01`)")

# User form input fields
start_kod = st.text_input("Starting location code:", placeholder="e.g., 24-001-01").strip()
koniec_kod = st.text_input("Ending location code (leave empty for 1 single label):", placeholder="e.g., 24-002-06").strip()

if start_kod:
    try:
        # Generate the sequential code array
        kody = generuj_liste_kodow(start_kod, koniec_kod)
        
        # Define output file naming logic
        if not koniec_kod:
            bezpieczna_nazwa = re.sub(r'[\\/*?:"<>|]', "", start_kod).strip()
            nazwa_pliku = f"{bezpieczna_nazwa}.pdf"
        else:
            nazwa_pliku = f"Range_{start_kod}_to_{koniec_kod}.pdf"
            
        # Extract the uploaded logo binary stream if present
        logo_data = uploaded_logo.getvalue() if uploaded_logo else None
        
        # Generate PDF data array
        pdf_data = generuj_pdf_w_pamieci(kody, logo_data)
        
        st.success(f"File prepared successfully! Total labels to print: **{len(kody)}**")
        
        # Download trigger button
        st.download_button(
            label="📥 DOWNLOAD PDF PRINT FILE",
            data=pdf_data,
            file_name=nazwa_pliku,
            mime="application/pdf",
            use_container_width=True
        )
        
    except ValueError as e:
        st.error(f"❌ {str(e)}")

# Bottom footer signature
st.markdown(
    """
    <style>
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: transparent;
        color: gray;
        text-align: center;
        font-size: 12px;
        padding: 10px;
    }
    </style>
    <div class="footer">
        <p>Developed by Kamil H.</p>
    </div>
    """,
    unsafe_allow_html=True
)
