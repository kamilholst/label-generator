import re
import io
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128

# Ustawienia strony w przeglądarce
st.set_page_config(page_title="Label generator by Kamil H.", page_icon="🏷️", layout="centered")


def parsuj_kod(kod):
    """Rozbija kod formatu RR-MMM-PP na liczby."""
    czesci = kod.split('-')
    if len(czesci) != 3:
        raise ValueError(f"Wrong format: {kod}. Use instead: 21-005-08")
    return int(czesci[0]), int(czesci[1]), int(czesci[2])


def generuj_liste_kodow(start, koniec):
    """Generuje pełną listę kodów pomiędzy zakresem start a koniec."""
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


def generuj_pdf_w_pamieci(kody):
    """Generuje plik PDF bezpośrednio w strumieniu bajtów (w pamięci RAM)."""
    buffer = io.BytesIO()
    width, height = A4
    c = canvas.Canvas(buffer, pagesize=A4)

    etykieta_height = height / 4.0
    x_center = width / 2.0
    max_dostepna_szerokosc = width - (10 * mm)
    bar_height = 35 * mm

    for i, tekst_miejsca in enumerate(kody):
        pozycja_na_stronie = i % 4

        y_top = height - (pozycja_na_stronie * etykieta_height)
        y_start = y_top - etykieta_height
        y_barcode = y_start + (etykieta_height - bar_height) / 2.0 + 8 * mm

        probny_barcode = code128.Code128(tekst_miejsca, barWidth=1, barHeight=bar_height, quiet=0)
        idealny_bar_width = min(max_dostepna_szerokosc / probny_barcode.width, 1.45 * mm)

        barcode = code128.Code128(tekst_miejsca, barWidth=idealny_bar_width, barHeight=bar_height, quiet=0)

        c.saveState()
        barcode.drawOn(c, x_center - (barcode.width / 2.0), y_barcode)
        c.restoreState()

        c.setFont("Helvetica-Bold", 38)
        y_text = y_barcode - 15 * mm
        c.drawCentredString(x_center, y_text, tekst_miejsca)

        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.setLineWidth(0.5)
        c.line(0, y_start, width, y_start)

        if pozycja_na_stronie == 3 or i == len(kody) - 1:
            c.showPage()

    c.save()
    buffer.seek(0)
    return buffer


# --- INTERFEJS WEBOWY (STREAMLIT) ---
st.title("🏭 Label Generator by Kamil")
st.markdown("Type range:")

st.info("Form: **RR-MMM-PP** (for example `24-001-01`)")

# Formularz dla użytkownika
start_kod = st.text_input("Starting place:", placeholder="np. 24-001-01").strip()
koniec_kod = st.text_input("Ending place (leave empty for one label):", placeholder="example 24-002-06").strip()

if start_kod:
    try:
        # Generowanie listy kodów
        kody = generuj_liste_kodow(start_kod, koniec_kod)

        # Przygotowanie nazwy pliku
        if not koniec_kod:
            bezpieczna_nazwa = re.sub(r'[\\/*?:"<>|]', "", start_kod).strip()
            nazwa_pliku = f"{bezpieczna_nazwa}.pdf"
        else:
            nazwa_pliku = f"Range_{start_kod}_do_{koniec_kod}.pdf"

        # Generowanie PDF
        pdf_data = generuj_pdf_w_pamieci(kody)

        st.success(f"File ready! Labels: **{len(kody)}**")

        # Profesjonalny przycisk pobierania w przeglądarce
        st.download_button(
            label="📥 Download file",
            data=pdf_data,
            file_name=nazwa_pliku,
            mime="application/pdf",
            use_container_width=True
        )

    except ValueError as e:
        st.error(f"❌ {str(e)}")
