import base64
import io
import os
import re
import numpy as np
import pandas as pd
import pdfplumber
from PIL import Image
import easyocr
import streamlit as st
import streamlit.components.v1 as components

# Configuración de la página web
st.set_page_config(
    page_title="Matriz Comercial Claro Empresas",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Evitar que el traductor automático del navegador rompa el DOM de Streamlit
st.markdown(
    """
    <script>
        document.documentElement.setAttribute('translate', 'no');
    </script>
    <meta name="google" content="notranslate">
    """,
    unsafe_allow_html=True,
)

# Inicializar motor OCR en caché para no recargarlo en cada interacción
@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['es'], gpu=False)

# Inicializar variables de estado general
if "lines" not in st.session_state:
    st.session_state.lines = []
if "deleted_phones" not in st.session_state:
    st.session_state.deleted_phones = set()
if "fixed_services" not in st.session_state:
    st.session_state.fixed_services = []
if "equipment_proposals" not in st.session_state:
    st.session_state.equipment_proposals = []
if "ruc" not in st.session_state:
    st.session_state.ruc = ""
if "company" not in st.session_state:
    st.session_state.company = ""
if "clear_key" not in st.session_state:
    st.session_state.clear_key = 0

# --- LOGO OFICIAL VECTORIAL DE CLARO EMPRESAS ---
SVG_LOGO_CLARO = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 425 85" style="height: 100%; width: auto; display: block; overflow: visible;">
  <!-- Símbolo Claro con rayos solares -->
  <circle cx="116" cy="56" r="6" fill="#DA291C" />
  <rect x="113.5" y="22" width="5" height="15" rx="2.5" fill="#DA291C" />
  <rect x="126" y="32" width="5" height="15" rx="2.5" transform="rotate(45 128.5 39.5)" fill="#DA291C" />
  <rect x="133" y="53.5" width="15" height="5" rx="2.5" fill="#DA291C" />
  <!-- Texto Claro -->
  <text x="10" y="65" font-family="'Segoe UI', Arial, sans-serif" font-size="48" font-weight="900" fill="#DA291C" letter-spacing="-1">Claro</text>
  <!-- Texto empresas con suficiente espacio de margen -->
  <text x="156" y="65" font-family="'Segoe UI', Arial, sans-serif" font-size="44" font-weight="900" fill="#111111" letter-spacing="-0.5">empresas</text>
</svg>
"""

LOGO_TOP_HTML = f'<div style="background: white; padding: 4px 14px; border-radius: 8px; display: inline-flex; align-items: center; height: 38px;">{SVG_LOGO_CLARO}</div>'
LOGO_PROPOSAL_HTML = f'<div style="background: white; padding: 3px 10px; border-radius: 6px; display: inline-flex; align-items: center; height: 30px;">{SVG_LOGO_CLARO}</div>'

# Estilos CSS generales
st.markdown(
    """
    <style>
    .top-bar { 
        background-color: #0d0d0e; 
        padding: 14px 22px; 
        color: white; 
        border-radius: 12px; 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        margin-bottom: 20px;
    }
    .dev-badge {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        color: #ddd;
        letter-spacing: 0.5px;
    }
    .dev-badge strong {
        color: #ffd700;
    }
    .footer-bar {
        margin-top: 50px;
        padding: 18px;
        border-top: 1px solid #ddd;
        text-align: center;
        font-size: 12px;
        color: #666;
        background-color: #fafafa;
        border-radius: 8px;
    }
    .footer-bar strong {
        color: #e30613;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Planes tarifarios móviles por defecto
DEFAULT_PLANS_MOVIL = [
    {"p": 29.9, "n": "Max Negocios + 29.90", "gb": "25 GB · bono 50 GB x 6 meses", "d": False, "offer_price": 29.9},
    {"p": 39.9, "n": "Max Negocios + 39.90", "gb": "30 GB · bono 60 GB x 6 meses", "d": False, "offer_price": 39.9},
    {"p": 49.9, "n": "Max Negocios + 49.90", "gb": "45 GB · bono 90 GB x 6 meses", "d": False, "offer_price": 49.9},
    {"p": 55.9, "n": "Max Negocios + 55.90", "gb": "75 GB · bono 150 GB x 6 meses", "d": True, "offer_price": 27.95},
    {"p": 69.9, "n": "Max Negocios Ilimitado + 69.90", "gb": "Internet ilimitado · 110 GB alta velocidad", "d": True, "offer_price": 34.95},
    {"p": 79.9, "n": "Max Negocios Ilimitado + 79.90", "gb": "Internet ilimitado · 125 GB alta velocidad", "d": True, "offer_price": 39.95},
    {"p": 95.9, "n": "Max Negocios Ilimitado + 95.90", "gb": "Internet ilimitado · 155 GB alta velocidad", "d": True, "offer_price": 47.95},
    {"p": 109.9, "n": "Max Negocios Ilimitado + 109.90", "gb": "Internet ilimitado · 160 GB alta velocidad", "d": True, "offer_price": 54.95},
    {"p": 125.0, "n": "Max Negocios Ilimitado + 125.00", "gb": "Internet ilimitado · 165 GB alta velocidad", "d": True, "offer_price": 62.50},
    {"p": 159.9, "n": "Max Negocios Ilimitado + 159.90", "gb": "Internet ilimitado · 175 GB alta velocidad", "d": True, "offer_price": 79.95},
    {"p": 189.9, "n": "Max Negocios Ilimitado + 189.90", "gb": "Internet ilimitado · 185 GB alta velocidad", "d": True, "offer_price": 94.95},
    {"p": 289.9, "n": "Max Negocios Ilimitado + 289.90", "gb": "Internet ilimitado · 200 GB alta velocidad", "d": True, "offer_price": 144.95},
]

# Catálogo oficial exacto de Servicios Fijos
DEFAULT_PLANS_FIJA = [
    # 1 PLAY
    {"n": "200 Mbps - 1 Play Internet Empresas Digital", "p": 69.0, "reg": 69.0, "tipo": "1 Play", "categoria": "1 Play", "desc": "Internet Empresas Digital 200 Mbps", "speed": 200, "promo_months": 0, "bonus_text": "Bono de velocidad a 400 Mbps por 6 meses", "has_tv": False},
    {"n": "300 Mbps (600 Mbps) - 1 Play Internet Empresas Digital", "p": 79.0, "reg": 79.0, "tipo": "1 Play", "categoria": "1 Play", "desc": "Internet Empresas Digital 300 Mbps", "speed": 300, "promo_months": 0, "bonus_text": "Bono de velocidad a 600 Mbps por 6 meses", "has_tv": False},
    {"n": "400 Mbps - 1 Play Internet Empresas Digital", "p": 69.0, "reg": 89.0, "tipo": "1 Play", "categoria": "1 Play", "desc": "Internet Empresas Digital 400 Mbps", "speed": 400, "promo_months": 6, "bonus_text": "Bono de velocidad a 1000 Mbps por 12 meses", "has_tv": False},
    {"n": "800 Mbps - 1 Play Internet Empresas Digital", "p": 100.0, "reg": 100.0, "tipo": "1 Play", "categoria": "1 Play", "desc": "Internet Empresas Digital 800 Mbps", "speed": 800, "promo_months": 0, "bonus_text": "Bono de velocidad a 1000 Mbps por 12 meses", "has_tv": False},
    {"n": "1000 Mbps (Full Claro) - 1 Play Internet Empresas Digital", "p": 119.0, "reg": 145.0, "tipo": "1 Play", "categoria": "1 Play", "desc": "Internet Empresas Digital 1000 Mbps Full Claro", "speed": 1000, "promo_months": 6, "bonus_text": "Bono de velocidad por 12 meses", "has_tv": False},
    {"n": "1500 Mbps (Solo FTTH) - 1 Play Internet Empresas Digital", "p": 200.0, "reg": 200.0, "tipo": "1 Play", "categoria": "1 Play", "desc": "Internet Empresas Digital 1500 Mbps FTTH", "speed": 1500, "promo_months": 0, "bonus_text": "Con Full Claro + GB en tu móvil", "has_tv": False},
    # 2 PLAY
    {"n": "200 Mbps - 2 Play Telefonía 5000", "p": 74.0, "reg": 74.0, "tipo": "2 Play", "categoria": "2 Play", "desc": "Internet Empresas Digital 200 Mbps + Telefonía 5000 min", "speed": 200, "promo_months": 0, "bonus_text": "Bono de velocidad a 400 Mbps por 6 meses", "has_tv": False},
    {"n": "200 Mbps - 2 Play TV Estándar Pro", "p": 89.0, "reg": 150.0, "tipo": "2 Play TV", "categoria": "2 Play", "desc": "Internet Empresas Digital 200 Mbps + TV Estándar Pro", "speed": 200, "promo_months": 6, "bonus_text": "Bono de velocidad a 400 Mbps por 6 meses", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "200 Mbps - 2 Play TV Superior Pro", "p": 119.0, "reg": 190.0, "tipo": "2 Play TV", "categoria": "2 Play", "desc": "Internet Empresas Digital 200 Mbps + TV Superior Pro", "speed": 200, "promo_months": 6, "bonus_text": "Bono de velocidad a 400 Mbps por 6 meses", "has_tv": True, "tv_type": "Superior Pro"},
    {"n": "300 Mbps (600 Mbps) - 2 Play Telefonía 5000", "p": 84.0, "reg": 84.0, "tipo": "2 Play", "categoria": "2 Play", "desc": "Internet Empresas Digital 300 Mbps + Telefonía 5000 min", "speed": 300, "promo_months": 6, "bonus_text": "Bono de velocidad a 600 Mbps por 6 meses", "has_tv": False},
    {"n": "300 Mbps (600 Mbps) - 2 Play TV Estándar Pro", "p": 99.0, "reg": 160.0, "tipo": "2 Play TV", "categoria": "2 Play", "desc": "Internet Empresas Digital 300 Mbps + TV Estándar Pro", "speed": 300, "promo_months": 6, "bonus_text": "Bono de velocidad a 600 Mbps por 6 meses", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "300 Mbps (600 Mbps) - 2 Play TV Superior Pro", "p": 200.0, "reg": 200.0, "tipo": "2 Play TV", "categoria": "2 Play", "desc": "Internet Empresas Digital 300 Mbps + TV Superior Pro", "speed": 300, "promo_months": 0, "bonus_text": "Bono de velocidad a 600 Mbps por 6 meses", "has_tv": True, "tv_type": "Superior Pro"},
    {"n": "400 Mbps - 2 Play Telefonía 5000", "p": 74.0, "reg": 94.0, "tipo": "2 Play", "categoria": "2 Play", "desc": "Internet Empresas Digital 400 Mbps + Telefonía 5000 min", "speed": 400, "promo_months": 6, "bonus_text": "Bono de velocidad a 1000 Mbps por 12 meses", "has_tv": False},
    {"n": "400 Mbps - 2 Play TV Estándar Pro", "p": 109.0, "reg": 170.0, "tipo": "2 Play TV", "categoria": "2 Play", "desc": "Internet Empresas Digital 400 Mbps + TV Estándar Pro", "speed": 400, "promo_months": 6, "bonus_text": "Bono de velocidad a 1000 Mbps por 12 meses", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "400 Mbps - 2 Play TV Superior Pro", "p": 139.0, "reg": 210.0, "tipo": "2 Play TV", "categoria": "2 Play", "desc": "Internet Empresas Digital 400 Mbps + TV Superior Pro", "speed": 400, "promo_months": 6, "bonus_text": "Bono de velocidad a 1000 Mbps por 12 meses", "has_tv": True, "tv_type": "Superior Pro"},
    {"n": "800 Mbps - 2 Play Telefonía 5000", "p": 105.0, "reg": 105.0, "tipo": "2 Play", "desc": "Internet Empresas Digital 800 Mbps + Telefonía 5000 min", "speed": 800, "promo_months": 0, "bonus_text": "Bono de velocidad a 1000 Mbps por 12 meses", "has_tv": False},
    {"n": "800 Mbps - 2 Play TV Estándar Pro", "p": 185.0, "reg": 185.0, "tipo": "2 Play TV", "desc": "Internet Empresas Digital 800 Mbps + TV Estándar Pro", "speed": 800, "promo_months": 0, "bonus_text": "Bono de velocidad a 1000 Mbps por 12 meses", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "800 Mbps - 2 Play TV Superior Pro", "p": 155.0, "reg": 225.0, "tipo": "2 Play TV", "desc": "Internet Empresas Digital 800 Mbps + TV Superior Pro", "speed": 800, "promo_months": 6, "bonus_text": "Bono de velocidad a 1000 Mbps por 12 meses", "has_tv": True, "tv_type": "Superior Pro"},
    {"n": "1000 Mbps (Full Claro) - 2 Play Telefonía 5000", "p": 150.0, "reg": 150.0, "tipo": "2 Play", "desc": "Internet Empresas Digital 1000 Mbps + Telefonía 5000 min", "speed": 1000, "promo_months": 0, "bonus_text": "Bono de velocidad por 12 meses", "has_tv": False},
    {"n": "1000 Mbps (Full Claro) - 2 Play TV Estándar Pro", "p": 159.0, "reg": 230.0, "tipo": "2 Play TV", "desc": "Internet Empresas Digital 1000 Mbps + TV Estándar Pro", "speed": 1000, "promo_months": 6, "bonus_text": "Bono de velocidad por 12 meses", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "1000 Mbps (Full Claro) - 2 Play TV Superior Pro", "p": 189.0, "reg": 270.0, "tipo": "2 Play TV", "desc": "Internet Empresas Digital 1000 Mbps + TV Superior Pro", "speed": 1000, "promo_months": 6, "bonus_text": "Bono de velocidad por 12 meses", "has_tv": True, "tv_type": "Superior Pro"},
    {"n": "1500 Mbps (Solo FTTH) - 2 Play Telefonía 5000", "p": 205.0, "reg": 205.0, "tipo": "2 Play", "desc": "Internet Empresas Digital 1500 Mbps + Telefonía 5000 min", "speed": 1500, "promo_months": 0, "bonus_text": "Con Full Claro + GB en tu móvil", "has_tv": False},
    {"n": "1500 Mbps (Solo FTTH) - 2 Play TV Estándar Pro", "p": 285.0, "reg": 285.0, "tipo": "2 Play TV", "desc": "Internet Empresas Digital 1500 Mbps + TV Estándar Pro", "speed": 1500, "promo_months": 0, "bonus_text": "Con Full Claro + GB en tu móvil", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "1500 Mbps (Solo FTTH) - 2 Play TV Superior Pro", "p": 255.0, "reg": 325.0, "tipo": "2 Play TV", "desc": "Internet Empresas Digital 1500 Mbps + TV Superior Pro", "speed": 1500, "promo_months": 6, "bonus_text": "Con Full Claro + GB en tu móvil", "has_tv": True, "tv_type": "Superior Pro"},
    # 3 PLAY
    {"n": "200 Mbps - 3 Play Estándar Pro", "p": 94.0, "reg": 155.0, "tipo": "3 Play", "categoria": "3 Play", "desc": "Internet Empresas Digital 200 Mbps + TV Estándar Pro + Telefonía 5000", "speed": 200, "promo_months": 6, "bonus_text": "Bono de velocidad a 400 Mbps por 6 meses", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "200 Mbps - 3 Play Superior Pro", "p": 124.0, "reg": 195.0, "tipo": "3 Play", "desc": "Internet Empresas Digital 200 Mbps + TV Superior Pro + Telefonía 5000", "speed": 200, "promo_months": 6, "bonus_text": "Bono de velocidad a 400 Mbps por 6 meses", "has_tv": True, "tv_type": "Superior Pro"},
    {"n": "300 Mbps (600 Mbps) - 3 Play Estándar Pro", "p": 104.0, "reg": 165.0, "tipo": "3 Play", "desc": "Internet Empresas Digital 300 Mbps + TV Estándar Pro + Telefonía 5000", "speed": 300, "promo_months": 6, "bonus_text": "Bono de velocidad a 600 Mbps por 6 meses", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "300 Mbps (600 Mbps) - 3 Play Superior Pro", "p": 205.0, "reg": 205.0, "tipo": "3 Play", "desc": "Internet Empresas Digital 300 Mbps + TV Superior Pro + Telefonía 5000", "speed": 300, "promo_months": 0, "bonus_text": "Bono de velocidad a 600 Mbps por 6 meses", "has_tv": True, "tv_type": "Superior Pro"},
    {"n": "400 Mbps - 3 Play Estándar Pro", "p": 114.0, "reg": 175.0, "tipo": "3 Play", "desc": "Internet Empresas Digital 400 Mbps + TV Estándar Pro + Telefonía 5000", "speed": 400, "promo_months": 6, "bonus_text": "Bono de velocidad a 1000 Mbps por 12 meses", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "400 Mbps - 3 Play Superior Pro", "p": 144.0, "reg": 215.0, "tipo": "3 Play", "desc": "Internet Empresas Digital 400 Mbps + TV Superior Pro + Telefonía 5000", "speed": 400, "promo_months": 6, "bonus_text": "Bono de velocidad a 1000 Mbps por 12 meses", "has_tv": True, "tv_type": "Superior Pro"},
    {"n": "800 Mbps - 3 Play Estándar Pro", "p": 190.0, "reg": 190.0, "tipo": "3 Play", "desc": "Internet Empresas Digital 800 Mbps + TV Estándar Pro + Telefonía 5000", "speed": 800, "promo_months": 0, "bonus_text": "Bono de velocidad a 1000 Mbps por 12 meses", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "800 Mbps - 3 Play Superior Pro", "p": 160.0, "reg": 230.0, "tipo": "3 Play", "desc": "Internet Empresas Digital 800 Mbps + TV Superior Pro + Telefonía 5000", "speed": 800, "promo_months": 6, "bonus_text": "Bono de velocidad a 1000 Mbps por 12 meses", "has_tv": True, "tv_type": "Superior Pro"},
    {"n": "1000 Mbps (Full Claro) - 3 Play Estándar Pro", "p": 164.0, "reg": 235.0, "tipo": "3 Play", "desc": "Internet Empresas Digital 1000 Mbps + TV Estándar Pro + Telefonía 5000", "speed": 1000, "promo_months": 6, "bonus_text": "Bono de velocidad por 12 meses", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "1000 Mbps (Full Claro) - 3 Play Superior Pro", "p": 194.0, "reg": 275.0, "tipo": "3 Play", "desc": "Internet Empresas Digital 1000 Mbps + TV Superior Pro + Telefonía 5000", "speed": 1000, "promo_months": 6, "bonus_text": "Bono de velocidad por 12 meses", "has_tv": True, "tv_type": "Superior Pro"},
    {"n": "1500 Mbps (Solo FTTH) - 3 Play Estándar Pro", "p": 290.0, "reg": 290.0, "tipo": "3 Play", "desc": "Internet Empresas Digital 1500 Mbps + TV Estándar Pro + Telefonía 5000", "speed": 1500, "promo_months": 0, "bonus_text": "Con Full Claro + GB en tu móvil", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "1500 Mbps (Solo FTTH) - 3 Play Superior Pro", "p": 260.0, "reg": 330.0, "tipo": "3 Play", "desc": "Internet Empresas Digital 1500 Mbps + TV Superior Pro + Telefonía 5000", "speed": 1500, "promo_months": 6, "bonus_text": "Con Full Claro + GB en tu móvil", "has_tv": True, "tv_type": "Superior Pro"},
]

def calculate_wifi_360_cost(speed, total_mesh_count):
    if total_mesh_count <= 0:
        return 0.0, 0.0
    promo_total = 0.0
    regular_total = 0.0
    for i in range(1, total_mesh_count + 1):
        p_cost = 0.0
        r_cost = 0.0
        if speed == 200: p_cost, r_cost = 10.5, 15.0
        elif speed == 300: p_cost, r_cost = 7.0, 10.0
        elif 400 <= speed < 800:
            if i > 1: p_cost, r_cost = 7.0, 10.0
        elif speed >= 800:
            if i > 2: p_cost, r_cost = 7.0, 10.0
        promo_total += p_cost
        regular_total += r_cost
    return promo_total, regular_total

def calculate_deco_cost(tv_type, deco_count):
    if deco_count <= 0:
        return 0.0
    cost = 0.0
    for i in range(1, deco_count + 1):
        if i > 1: cost += 10.0
    return cost

def get_cloud_tools_text(speed):
    if speed == 200:
        return "2 Herramientas Digitales totalmente gratuitas: Claro Drive Negocios (100 GB) y Seguridad Empresas (1 Licencia de Antivirus)."
    elif speed == 300:
        return "4 Herramientas Digitales totalmente gratuitas: Claro Drive Negocios (100 GB), Claro Backup (15 GB / 1 Equipo), Seguridad Empresas (1 Licencia de Antivirus) y Email Empresas* (2 Cuentas)."
    elif speed == 400:
        return "5 Herramientas Digitales totalmente gratuitas: Claro Drive Negocios (100 GB), Claro Backup (15 GB / 1 Equipo), Seguridad Empresas (1 Licencia de Antivirus), Email Empresas* (2 Cuentas) y Tienda Virtual (Plan Comienza)."
    else:
        lic_m365 = "1 Licencia" if speed == 800 else "2 Licencias"
        return f"6 Herramientas Digitales totalmente gratuitas: Claro Drive Negocios (100 GB), Claro Backup (15 GB / 1 Equipo), Seguridad Empresas (2 Licencias de Antivirus), Email Empresas* (2 Cuentas), Microsoft 365* ({lic_m365}) y Tienda Virtual (Plan Comienza)."

def recommend_plan_movil(cf, mode="Plan equivalente", modality="PDV"):
    if modality == "Centralizado":
        eligible = DEFAULT_PLANS_MOVIL
    else:
        eligible = [p for p in DEFAULT_PLANS_MOVIL if p["d"]]

    if mode == "Mayor ahorro":
        return eligible[0] if eligible else DEFAULT_PLANS_MOVIL[0]
    for p in eligible:
        if p["p"] >= cf:
            return p
    return eligible[-1] if eligible else DEFAULT_PLANS_MOVIL[-1]

# --- EXTRACCIÓN DINÁMICA DE RECIBOS ---
def extract_receipt_data(file_bytes, filename, recommend_mode, modality_choice="PDV"):
    extracted_lines = []
    full_text = ""
    is_image = filename.lower().endswith(('.png', '.jpg', '.jpeg'))

    ocr_raw_boxes = []
    if is_image:
        try:
            reader = load_ocr_reader()
            img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            w, h = img.size
            img_resized = img.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
            img_np = np.array(img_resized)
            
            ocr_raw_boxes = reader.readtext(img_np, detail=1)
            full_text = "\n".join([item[1] for item in ocr_raw_boxes])
        except Exception as e:
            st.error(f"Error procesando imagen {filename} con OCR: {e}")
            return []
    else:
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    txt = page.extract_text()
                    if txt:
                        full_text += txt + "\n"
        except Exception as e:
            st.error(f"Error al leer el PDF {filename}: {e}")
            return []

    operator_rucs = [
        "20100017491", # Telefónica / Movistar
        "20414955020", # Telefónica Móviles
        "20504771424", # Bitel
        "20263322496", # Claro
        "20106897914", # Entel Perú
    ]

    ruc_encontrado = None
    file_ruc = re.search(r"\b([12]\d{10})\b", filename)
    if file_ruc and file_ruc.group(1) not in operator_rucs:
        ruc_encontrado = file_ruc.group(1)

    if not ruc_encontrado:
        m_doc = re.search(r"(?:N[º°]?\s*Doc(?:\s*\(RUC\))?|R\.?U\.?C\.?)[\s:]*([12]\d{10})\b", full_text, re.IGNORECASE)
        if m_doc and m_doc.group(1) not in operator_rucs:
            ruc_encontrado = m_doc.group(1)

    if not ruc_encontrado:
        all_rucs = re.findall(r"\b([12]\d{10})\b", full_text)
        for r in all_rucs:
            if r not in operator_rucs:
                ruc_encontrado = r
                break

    if ruc_encontrado:
        st.session_state.ruc = ruc_encontrado
        st.session_state["ruc_input_movil_val"] = ruc_encontrado
        st.session_state["ruc_input_fija"] = ruc_encontrado
        st.session_state["ruc_input_equipos"] = ruc_encontrado

    company_found = ""
    suffixes = [
        r"S\.?A\.?C\.?", r"E\.?I\.?R\.?L\.?", r"S\.?A\.?", r"S\.?R\.?L\.?",
        r"SOCIEDAD ANONIMA CERRADA", r"SOCIEDAD ANONIMA", r"SOCIEDAD COMERCIAL"
    ]
    ignored_keywords = [
        "ENTEL", "TELEFONICA", "TELEFÓNICA", "MOVISTAR", "AMERICA MOVIL",
        "AMÉRICA MÓVIL", "CLARO", "INTEGRATEL", "MINISTERIO", "OSIPTEL", "RECIBO"
    ]

    for line in full_text.split("\n"):
        line_clean = line.strip()
        if any(re.search(rf"\b{s}\b", line_clean, re.IGNORECASE) for s in suffixes):
            if not any(k in line_clean.upper() for k in ignored_keywords):
                clean_name = re.sub(r"^(?:Señor\(es\)|Cliente|Razón Social|Titular|Abonado|Nombre)[\s:]*", "", line_clean, flags=re.IGNORECASE).strip()
                clean_name = re.sub(r"(?:RUC|N[º°]|Doc|Fecha|Recibo|Dirección).*", "", clean_name, flags=re.IGNORECASE).strip()
                if len(clean_name) >= 4 and not clean_name.replace(" ", "").isdigit():
                    company_found = clean_name
                    break

    if not company_found:
        m_comp = re.search(r"(?:Señor\(es\)|Razón Social|Nombre o Razón Social)[\s:]+([^\n\r]+)", full_text, re.IGNORECASE)
        if m_comp:
            cand = m_comp.group(1).strip()
            cand = re.sub(r"(?:RUC|N[º°]|Doc).*", "", cand, flags=re.IGNORECASE).strip()
            if len(cand) >= 4 and not any(k in cand.upper() for k in ignored_keywords):
                company_found = cand

    if company_found:
        st.session_state.company = company_found
        st.session_state["company_input_movil_val"] = company_found
        st.session_state["company_input_fija"] = company_found
        st.session_state["company_input_equipos"] = company_found

    is_entel = "entel" in full_text.lower() or "empresa pro" in full_text.lower() or "empresa power" in full_text.lower() or "empresa plus" in full_text.lower()

    if is_entel:
        operator_hotlines = ["966000000", "900000000"]

        if not is_image:
            lines_raw = full_text.split("\n")
            processed_phones = set()

            for line in lines_raw:
                line_str = line.strip()
                match_phone = re.search(r"^(9\d{8})\b", line_str)
                if match_phone:
                    ph = match_phone.group(1)
                    if ph in processed_phones or ph in operator_hotlines or ph in st.session_state.deleted_phones:
                        continue

                    amounts = re.findall(r"[-+]?\b\d+\.\d{2}\b", line_str)
                    
                    if len(amounts) >= 3:
                        cf = float(amounts[0])
                        negatives = [abs(float(a)) for a in amounts if float(a) < 0]
                        disc_val = negatives[0] if negatives else 0.0
                        pay = float(amounts[-1])
                    else:
                        cf = 59.90
                        disc_val = 0.0
                        pay = 59.90

                    discount_pct = round((disc_val / cf * 100), 1) if (cf > 0 and disc_val > 0) else 0.0

                    plan_match = re.search(rf"^{ph}\s+(.+?)\s+{amounts[0]}", line_str) if amounts else None
                    plan_name = plan_match.group(1).strip() if plan_match else f"Empresa PRO 2.0 {cf:.1f}"

                    rec = recommend_plan_movil(cf, recommend_mode, modality_choice)
                    extracted_lines.append({
                        "id": str(pd.Timestamp.now().timestamp()) + "_" + ph,
                        "phone": ph,
                        "operator": "Entel",
                        "plan": plan_name,
                        "cf": cf,
                        "discount": discount_pct,
                        "pay": pay,
                        "claro_plan_idx": DEFAULT_PLANS_MOVIL.index(rec),
                        "source": filename,
                    })
                    processed_phones.add(ph)

        else:
            raw_candidates = re.findall(r"\b([89]\d{8})\b", full_text)
            phones_ordered = []
            for p in raw_candidates:
                fixed_phone = "9" + p[1:] if p.startswith("8") else p
                if fixed_phone not in operator_hotlines and fixed_phone not in phones_ordered and fixed_phone not in st.session_state.deleted_phones:
                    phones_ordered.append(fixed_phone)

            discounts_map = {}
            detail_blocks = re.findall(r"(9\d{8})\s*\([^\)]+\)[\s\S]*?(?:Descuentos|Dev Inter)[\s\S]*?(-?\d+\.\d{2})", full_text, re.IGNORECASE)
            for d_ph, d_val in detail_blocks:
                discounts_map[d_ph] = abs(float(d_val))

            for ph in phones_ordered:
                cf = 59.90
                pay = 59.90
                discount_pct = 0.0

                if ocr_raw_boxes:
                    y_center = None
                    for bbox, text, conf in ocr_raw_boxes:
                        clean_t = text.replace(" ", "")
                        if ph in clean_t or (ph[1:] in clean_t and len(clean_t) == 9):
                            y_center = (bbox[0][1] + bbox[2][1]) / 2.0
                            break

                    if y_center is not None:
                        row_elements = [item for item in ocr_raw_boxes if abs(((item[0][0][1] + item[0][2][1]) / 2.0) - y_center) < 30]
                        row_elements.sort(key=lambda item: item[0][0][0])
                        row_str = " ".join([item[1] for item in row_elements])

                        if "105.9" in row_str: cf = 105.90
                        elif "85.9" in row_str: cf = 85.90
                        elif "74.9" in row_str: cf = 74.90
                        elif "72.9" in row_str: cf = 72.90
                        elif "59.9" in row_str: cf = 59.90
                        elif "52.9" in row_str: cf = 52.90
                        elif "44.9" in row_str: cf = 44.90
                        elif "36.9" in row_str: cf = 36.90

                        money_matches = re.findall(r"[-+]?\b\d+(?:\.\d{2})\b", row_str)
                        money_floats = [float(m) for m in money_matches if abs(float(m)) < 500.0]

                        negatives = [abs(m) for m in money_floats if m < 0]
                        disc_val = discounts_map.get(ph, negatives[0] if negatives else 0.0)

                        if disc_val > 0:
                            discount_pct = round((disc_val / cf * 100), 1) if cf > 0 else 0.0
                            pay = round(cf - disc_val, 2)
                        else:
                            pay = cf

                plan_name = f"Empresa PRO 2.0 {cf:.1f}"
                rec = recommend_plan_movil(cf, recommend_mode, modality_choice)

                extracted_lines.append({
                    "id": str(pd.Timestamp.now().timestamp()) + "_" + ph,
                    "phone": ph,
                    "operator": "Entel",
                    "plan": plan_name,
                    "cf": cf,
                    "discount": discount_pct,
                    "pay": pay,
                    "claro_plan_idx": DEFAULT_PLANS_MOVIL.index(rec),
                    "source": filename,
                })

    elif not is_entel and not is_image:
        phones = re.findall(r"\b(9\d{8})\b", full_text)
        phones = [p for p in dict.fromkeys(phones) if p not in ["966000000", "900000000"] and p not in st.session_state.deleted_phones]
        for ph in phones:
            cf = 26.90
            rec = recommend_plan_movil(cf, recommend_mode, modality_choice)
            extracted_lines.append({
                "id": str(pd.Timestamp.now().timestamp()) + "_" + ph,
                "phone": ph,
                "operator": "Movistar",
                "plan": "Movistar Empresas",
                "cf": cf,
                "discount": 0.0,
                "pay": cf,
                "claro_plan_idx": DEFAULT_PLANS_MOVIL.index(rec),
                "source": filename,
            })

    return extracted_lines

# --- HEADER SUPERIOR ---
st.markdown(
    f"""
    <div class="top-bar">
        <div style="display: flex; align-items: center; gap: 14px;">
            {LOGO_TOP_HTML}
            <div>
                <h1 style="font-size: 18px; margin: 0; color: white;">Matriz Comercial y Propuesta Ejecutiva</h1>
                <p style="color: #bbb; font-size: 12px; margin: 0;">Soluciones Móviles, Fijas y Equipos Corporativos</p>
            </div>
        </div>
        <div class="dev-badge">
            💻 Desarrollado por: <strong>JHONNIER VARELA</strong>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

tab_movil, tab_fija, tab_equipos = st.tabs(
    ["📱 Propuestas Móviles", "🌐 Propuestas Fijas / Internet", "📦 Matriz de Equipos Móviles"]
)

# ==========================================
# PESTAÑA 1: MÓVIL (PORTABILIDAD)
# ==========================================
with tab_movil:
    with st.container():
        st.markdown("### 1. Panel de Configuración y Carga de Archivos (Móvil)")

        modality = st.radio(
            "Modalidad de Propuesta Móvil",
            ["PDV", "Centralizado"],
            horizontal=True,
            key="modality_movil",
        )

        col_c1, col_c2, col_c3 = st.columns(3)

        with col_c1:
            uploaded_files = st.file_uploader(
                "📁 Arrastra recibos (PDF o Imágenes JPG/PNG)",
                type=["pdf", "png", "jpg", "jpeg"],
                accept_multiple_files=True,
                key=f"receipt_uploader_{st.session_state.clear_key}",
            )

        with col_c2:
            uploaded_image = st.file_uploader(
                "🖼️ Arrastra o selecciona imagen publicitaria",
                type=["png", "jpg", "jpeg"],
                key=f"img_uploader_{st.session_state.clear_key}",
            )

        with col_c3:
            if modality == "Centralizado":
                manual_discount_pct = st.number_input(
                    "Ingresa el % de Descuento Manual",
                    min_value=0.0,
                    max_value=100.0,
                    value=40.0,
                    step=1.0,
                    key="manual_disc_movil",
                )
            else:
                manual_discount_pct = 50.0

            recommend_mode = st.radio(
                "Recomendación",
                ["Plan equivalente", "Mayor ahorro"],
                horizontal=True,
                key="rec_mode_movil",
            )

        current_filenames = [uf.name for uf in uploaded_files] if uploaded_files else []
        st.session_state.lines = [
            l for l in st.session_state.lines
            if (l.get("source") == "Manual" or l.get("source") in current_filenames)
            and l.get("phone") not in st.session_state.deleted_phones
        ]

        if uploaded_files:
            nuevas_totales = False
            for uf in uploaded_files:
                file_bytes = uf.read()
                if not any(l.get("source") == uf.name for l in st.session_state.lines):
                    nuevas = extract_receipt_data(file_bytes, uf.name, recommend_mode, modality)
                    if nuevas:
                        st.session_state.lines.extend(nuevas)
                        nuevas_totales = True
            if nuevas_totales:
                st.rerun()

        if "last_recommend_mode" not in st.session_state:
            st.session_state.last_recommend_mode = recommend_mode
        elif st.session_state.last_recommend_mode != recommend_mode:
            st.session_state.last_recommend_mode = recommend_mode
            for l in st.session_state.lines:
                rec = recommend_plan_movil(l["cf"], recommend_mode, modality)
                l["claro_plan_idx"] = DEFAULT_PLANS_MOVIL.index(rec)

        col_r1, col_r2, col_r3, col_r4 = st.columns([2, 3, 1, 1])
        with col_r1:
            st.session_state.ruc = st.text_input(
                "RUC de la empresa",
                value=st.session_state.get("ruc", ""),
                placeholder="Ej. 20123456789",
                key="ruc_input_movil_val",
            )

        with col_r2:
            st.session_state.company = st.text_input(
                "Razón Social",
                value=st.session_state.get("company", ""),
                placeholder="Nombre de la empresa",
                key="company_input_movil_val",
            )

        with col_r3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("+ Línea manual", use_container_width=True):
                rec = recommend_plan_movil(55.9, recommend_mode, modality)
                st.session_state.lines.append(
                    {
                        "id": str(pd.Timestamp.now().timestamp()),
                        "phone": "900000000",
                        "operator": "Movistar",
                        "plan": "Manual",
                        "cf": 55.90,
                        "discount": 0.0,
                        "pay": 55.90,
                        "claro_plan_idx": DEFAULT_PLANS_MOVIL.index(rec),
                        "source": "Manual",
                    }
                )
                st.rerun()
        with col_r4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑 Limpiar todo", use_container_width=True):
                st.session_state.lines = []
                st.session_state.deleted_phones = set()
                st.session_state.ruc = ""
                st.session_state.company = ""
                st.session_state["ruc_input_movil_val"] = ""
                st.session_state["company_input_movil_val"] = ""
                st.session_state["ruc_input_fija"] = ""
                st.session_state["company_input_fija"] = ""
                st.session_state["ruc_input_equipos"] = ""
                st.session_state["company_input_equipos"] = ""
                st.session_state.clear_key += 1
                st.rerun()

    st.markdown("---")

    lines = st.session_state.lines
    total_lines = len(lines)
    total_current = sum(l["pay"] for l in lines)

    def get_claro_offer(plan_dict):
        precio = plan_dict["p"]
        if modality == "Centralizado":
            return round(precio * (1 - (manual_discount_pct / 100.0)), 2)
        else:
            return plan_dict["offer_price"] if plan_dict.get("d", False) else precio

    total_claro = sum(get_claro_offer(DEFAULT_PLANS_MOVIL[l["claro_plan_idx"]]) for l in lines)
    total_saving = total_current - total_claro
    total_annual = total_saving * 12

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Líneas", total_lines)
    k2.metric("Pago actual", f"S/{total_current:.2f}")
    k3.metric(
        f"Claro ({modality})",
        f"S/{total_claro:.2f}",
        delta=f"{manual_discount_pct}% desc." if modality == "Centralizado" else "50% desc.",
        delta_color="off",
    )
    k4.metric("Ahorro mensual", f"S/{total_saving:.2f}")
    k5.metric("Ahorro anual", f"S/{total_annual:.2f}")

    st.markdown("### 2. Revisar y asignar planes (Móvil)")

    if not lines:
        st.info("👆 Arrastra o carga tus recibos (PDF o Imágenes) en la parte superior o agrega una línea manualmente para comenzar.")
    else:
        plan_names = [p["n"] for p in DEFAULT_PLANS_MOVIL]

        table_data = []
        for i, l in enumerate(lines):
            current_plan = DEFAULT_PLANS_MOVIL[l["claro_plan_idx"]]
            offer = get_claro_offer(current_plan)
            table_data.append(
                {
                    "N°": i + 1,
                    "Línea": l["phone"],
                    "Operador": l["operator"],
                    "Plan Actual": l["plan"],
                    "CF Actual": float(l["cf"]),
                    "Dscto %": float(l["discount"]),
                    "Pago Actual": float(l["pay"]),
                    "Plan Claro": current_plan["n"],
                    "CF Claro": current_plan["p"],
                    "Pago Oferta": offer,
                    "Internet / Beneficios": current_plan["gb"],
                    "Ahorro Línea": l["pay"] - offer,
                }
            )

        df_editable = pd.DataFrame(table_data)

        # TABLA CON DINAMISMO HABILITADO (num_rows="dynamic" para borrado directo)
        edited_df = st.data_editor(
            df_editable,
            column_config={
                "Línea": st.column_config.TextColumn(
                    "Línea",
                    help="Número de teléfono (9 dígitos)",
                    max_chars=9,
                    required=True,
                ),
                "Operador": st.column_config.SelectboxColumn(
                    "Operador",
                    options=["Movistar", "Entel", "Bitel", "Otro"],
                    required=True,
                ),
                "Plan Actual": st.column_config.TextColumn(
                    "Plan Actual",
                    required=False,
                ),
                "CF Actual": st.column_config.NumberColumn(
                    "CF Actual",
                    min_value=0.0,
                    step=0.01,
                    format="S/ %.2f",
                ),
                "Dscto %": st.column_config.NumberColumn(
                    "Dscto %",
                    min_value=0.0,
                    max_value=100.0,
                    step=1.0,
                    format="%.0f%%",
                ),
                "Plan Claro": st.column_config.SelectboxColumn(
                    "Plan Claro",
                    options=plan_names,
                    required=True,
                ),
            },
            disabled=[
                "N°", "Pago Actual", "CF Claro", "Pago Oferta", 
                "Internet / Beneficios", "Ahorro Línea",
            ],
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            key=f"plan_editor_movil_{modality}_{manual_discount_pct}",
        )

        # SECCIÓN DIRECTA PARA ELIMINAR LÍNEA ESPECÍFICA CON BOTÓN
        col_del_sel, col_del_btn, _ = st.columns([2, 1, 3])
        with col_del_sel:
            phone_options = [f"{idx + 1}. {l['phone']} ({l['plan']})" for idx, l in enumerate(st.session_state.lines)]
            selected_line_to_del = st.selectbox("Seleccionar línea para quitar:", phone_options, key="select_phone_delete")
        with col_del_btn:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            if st.button("🗑️ Quitar línea", use_container_width=True):
                idx_to_remove = int(selected_line_to_del.split(".")[0]) - 1
                deleted_ph = st.session_state.lines[idx_to_remove]["phone"]
                st.session_state.deleted_phones.add(deleted_ph)
                st.session_state.lines.pop(idx_to_remove)
                st.rerun()

        # Detección de filas borradas desde la casilla de la tabla
        if len(edited_df) < len(st.session_state.lines):
            remaining_phones = set(edited_df["Línea"].astype(str))
            for l in st.session_state.lines:
                if l["phone"] not in remaining_phones:
                    st.session_state.deleted_phones.add(l["phone"])
            st.session_state.lines = [l for l in st.session_state.lines if l["phone"] in remaining_phones]
            st.rerun()

        updated = False
        for index, row in edited_df.iterrows():
            if index >= len(st.session_state.lines):
                break
            line_item = st.session_state.lines[index]
            
            new_phone = str(row["Línea"]).strip()
            if line_item["phone"] != new_phone:
                line_item["phone"] = new_phone
                updated = True

            new_op = str(row["Operador"]).strip()
            if line_item["operator"] != new_op:
                line_item["operator"] = new_op
                updated = True

            new_plan_actual = str(row["Plan Actual"]).strip()
            if line_item["plan"] != new_plan_actual:
                line_item["plan"] = new_plan_actual
                updated = True

            new_cf = float(row["CF Actual"]) if pd.notna(row["CF Actual"]) else 0.0
            new_dscto = float(row["Dscto %"]) if pd.notna(row["Dscto %"]) else 0.0
            new_pay = round(new_cf * (1 - (new_dscto / 100.0)), 2)
            if line_item["cf"] != new_cf or line_item["discount"] != new_dscto:
                line_item["cf"] = new_cf
                line_item["discount"] = new_dscto
                line_item["pay"] = new_pay
                updated = True

            selected_plan_name = row["Plan Claro"]
            new_plan_idx = next(i for i, p in enumerate(DEFAULT_PLANS_MOVIL) if p["n"] == selected_plan_name)
            if line_item["claro_plan_idx"] != new_plan_idx:
                line_item["claro_plan_idx"] = new_plan_idx
                updated = True

        if updated:
            st.rerun()

        image_html_content = """
            <div style="border: 2px dashed #ccc; border-radius: 6px; padding: 35px; text-align: center; color: #777; background: #fafafa; margin-top: 10px;">
                <strong style="font-size: 12px; color: #555;">ESPACIO PARA TU IMAGEN HD</strong>
                <div style="font-size: 10px; color: #888; margin-top: 4px;">Arrastra una imagen arriba y se integrará aquí</div>
            </div>
        """
        if uploaded_image is not None:
            img_bytes = uploaded_image.read()
            uploaded_image.seek(0)
            img_encoded = base64.b64encode(img_bytes).decode("utf-8")
            img_format = uploaded_image.type.split("/")[-1]
            image_html_content = f"""
                <div style="width: 100%; margin-top: 10px; text-align: center;">
                    <img src="data:image/{img_format};base64,{img_encoded}" style="width: 100%; height: auto; display: block; border-radius: 4px;" />
                </div>
            """

        st.markdown("---")
        st.subheader(f"3. Vista Ejecutiva para el Cliente ({modality} Móvil)")

        has_plan_55_90 = any("55.90" in str(r['Plan Claro']) for _, r in edited_df.iterrows())
        redes_sociales_html = (
            "<li>Redes sociales ilimitadas (Instagram, Facebook, Messenger, Threads, WhatsApp, Waze) y en portabilidad Microsoft Teams.</li>"
            if has_plan_55_90 else ""
        )

        rows_html = ""
        for idx, r in edited_df.iterrows():
            bg = "#f9f9f9" if idx % 2 == 0 else "#ffffff"
            p_obj = next(p for p in DEFAULT_PLANS_MOVIL if p["n"] == r['Plan Claro'])
            oferta_real = get_claro_offer(p_obj)

            rows_html += f"""
            <tr style="background-color:{bg}; text-align:center; border-bottom:1px solid #eee;">
                <td style="padding:4px; border:1px solid #ddd; font-weight:bold;">{r['N°']}</td>
                <td style="padding:4px; border:1px solid #ddd;">{r['Línea']}</td>
                <td style="padding:4px; border:1px solid #ddd;">{r['Operador']}</td>
                <td style="padding:4px; border:1px solid #ddd; text-align:left; padding-left:6px;">{r['Plan Actual']}</td>
                <td style="padding:4px; border:1px solid #ddd;">S/{r['CF Actual']:.2f}</td>
                <td style="padding:4px; border:1px solid #ddd;">{r['Dscto %']:.0f}%</td>
                <td style="padding:4px; border:1px solid #ddd; font-weight:bold;">S/{r['Pago Actual']:.2f}</td>
                <td style="padding:4px; border:1px solid #ddd; text-align:left; padding-left:6px; font-weight:bold;">{r['Plan Claro']}</td>
                <td style="padding:4px; border:1px solid #ddd;">S/{r['CF Claro']:.2f}</td>
                <td style="padding:4px; border:1px solid #ddd; color:#e30613; font-weight:bold;">S/{oferta_real:.2f}</td>
                <td style="padding:4px; border:1px solid #ddd; font-size:10px;">{r['Internet / Beneficios']}</td>
            </tr>
            """

        badge_text = (
            f"HASTA<br>{int(manual_discount_pct)}%<span style='font-size:9px; display:block;'>DTO. CENTRALIZADO</span>"
            if modality == "Centralizado"
            else "HASTA<br>50%<span style='font-size:9px; display:block;'>POR 12 MESES</span>"
        )

        empresa_titulo_p1 = f"{st.session_state.ruc} · {st.session_state.company}" if (st.session_state.ruc and st.session_state.company) else (st.session_state.ruc or st.session_state.company or "")

        header_title_p1 = f"""
        <div class="proposal-title" style="font-size:16px; font-weight:900; color:#ffd700;">
            {empresa_titulo_p1}<br>
            <span style="font-size:12px; font-weight:bold; color:#ffffff; letter-spacing:1px;">PROPUESTA DE PORTABILIDAD MÓVIL ({modality.upper()})</span>
        </div>
        """ if empresa_titulo_p1 else f"""
        <div class="proposal-title" style="font-size:16px; font-weight:900; color:#ffffff; letter-spacing:1px;">
            PROPUESTA DE PORTABILIDAD MÓVIL ({modality.upper()})
        </div>
        """

        client_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <style>
            @page {{ size: landscape; margin: 5mm; }}
            @media print {{ .no-print {{ display: none !important; }} }}
            body {{ font-family: Arial, sans-serif; margin: 0; background: #fff; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            .proposal-container {{ background: #ffffff; border: 2px solid #0d0d0e; border-radius: 6px; width: 100%; }}
            .proposal-header {{ background-color: #0d0d0e !important; color: white; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; }}
            .proposal-title {{ letter-spacing: 0.5px; text-align: center; flex-grow: 1; }}
            .badge-dto {{ background-color: #fff1bd !important; color: #e30613; padding: 6px 12px; border-radius: 6px; font-weight: 900; font-size: 11px; text-align: right; }}
            .proposal-footer {{ display: flex; justify-content: space-between; padding: 6px 12px; background: #e9ecef; font-size: 9px; color: #555; border-top: 1px solid #ccc; }}
        </style>
        </head>
        <body>
        <div class="proposal-container" id="print-section-movil">
            <div class="proposal-header">
                {LOGO_PROPOSAL_HTML}
                {header_title_p1}
                <div class="badge-dto">{badge_text}</div>
            </div>
            <table style="width:100%; border-collapse:collapse; font-size:10px;">
                <thead>
                    <tr style="background-color:#1763a5 !important; color:white; text-align:center;">
                        <th colspan="7" style="padding:5px; border:1px solid #ddd; background:#151515 !important; color:white;">SERVICIO ACTUAL</th>
                        <th colspan="4" style="padding:5px; border:1px solid #ddd; background:#e30613 !important; color:white;">PLAN CON CLARO</th>
                    </tr>
                    <tr style="background-color:#1763a5 !important; color:white; font-weight:bold; text-align:center;">
                        <th style="padding:4px; border:1px solid #ddd;">N°</th>
                        <th style="padding:4px; border:1px solid #ddd;">Línea</th>
                        <th style="padding:4px; border:1px solid #ddd;">Operador</th>
                        <th style="padding:4px; border:1px solid #ddd;">Plan actual</th>
                        <th style="padding:4px; border:1px solid #ddd;">CF</th>
                        <th style="padding:4px; border:1px solid #ddd;">Dscto.</th>
                        <th style="padding:4px; border:1px solid #ddd;">Pago actual</th>
                        <th style="padding:4px; border:1px solid #ddd; background:#e30613 !important; color:white;">Plan Claro</th>
                        <th style="padding:4px; border:1px solid #ddd; background:#e30613 !important; color:white;">CF</th>
                        <th style="padding:4px; border:1px solid #ddd; background:#e30613 !important; color:white;">Oferta</th>
                        <th style="padding:4px; border:1px solid #ddd; background:#e30613 !important; color:white;">Internet</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
            <div style="display:flex; justify-content:space-between; padding:10px; background:#f4f5f7 !important; align-items:flex-start; border-top:1px solid #ddd;">
                <div style="width:58%; background:white; padding:10px; border-radius:6px; border:1px solid #ddd; box-sizing: border-box;">
                    <strong style="font-size:11px; color:#111;">BENEFICIOS INCLUIDOS CON CLARO</strong>
                    <ul style="margin:3px 0 8px 15px; padding:0; font-size:10px; color:#444; line-height:1.4;">
                        <li>Descuento corporativo aplicado: {manual_discount_pct}%.</li>
                        <li>Llamadas y SMS nacionales ilimitados. Desde S/55.90: llamadas ilimitadas a 7 destinos.</li>
                        {redes_sociales_html}
                        <li>Cobertura internacional integrada según el plan contratado.</li>
                    </ul>
                    {image_html_content}
                </div>
                <div style="width:38%; display:flex; flex-direction:column; gap:4px;">
                    <div style="display:flex; justify-content:space-between; background:#1763a5 !important; color:white; padding:6px 10px; border-radius:4px; font-size:11px; font-weight:bold;">
                        <span>FACTURACIÓN ACTUAL</span><span>S/{total_current:.2f}</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; background:#f4b400 !important; color:#111111; padding:6px 10px; border-radius:4px; font-size:11px; font-weight:bold;">
                        <span>PAGO MENSUAL CLARO</span><span>S/{total_claro:.2f}</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; background:#e30613 !important; color:white; padding:6px 10px; border-radius:4px; font-size:11px; font-weight:bold;">
                        <span>AHORRO MENSUAL</span><span>S/{total_saving:.2f}</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; background:#0d0d0e !important; color:white; padding:8px 10px; border-radius:4px; font-size:12px; font-weight:900;">
                        <span>AHORRO ANUAL</span><span>S/{total_annual:.2f}</span>
                    </div>
                </div>
            </div>
            <div class="proposal-footer">
                <span>Plataforma de Cotizaciones Corporativas Claro Empresas</span>
                <span>Desarrollado por: <strong>JHONNIER VARELA</strong></span>
            </div>
        </div>
        <div class="no-print" style="text-align: center; margin-top: 15px; display: flex; justify-content: center; gap: 15px;">
            <button onclick="downloadImageMovil()" style="background-color:#1763a5; color:white; border:none; padding:10px 20px; border-radius:8px; font-weight:bold; font-size:14px; cursor:pointer;">🖼️ Descargar como Imagen (PNG)</button>
            <button onclick="window.print()" style="background-color:#e30613; color:white; border:none; padding:10px 20px; border-radius:8px; font-weight:bold; font-size:14px; cursor:pointer;">🖨️ Guardar como PDF</button>
        </div>
        <script>
            function downloadImageMovil() {{
                const element = document.getElementById("print-section-movil");
                html2canvas(element, {{ scale: 2, useCORS: true }}).then(canvas => {{
                    const link = document.createElement('a');
                    link.download = 'Propuesta_Movil_Claro.png';
                    link.href = canvas.toDataURL('image/png');
                    link.click();
                }});
            }}
        </script>
        </body>
        </html>
        """

        img_extra = 300 if uploaded_image is not None else 80
        dynamic_height = 460 + img_extra + (len(lines) * 28)
        components.html(client_html, height=dynamic_height, scrolling=False)

        st.markdown("<br>", unsafe_allow_html=True)
        col_e1, _ = st.columns([1, 4])
        with col_e1:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                edited_df.to_excel(writer, index=False, sheet_name="Movil")
            excel_data = output.getvalue()
            st.download_button(
                label="📥 Descargar Excel Móvil",
                data=excel_data,
                file_name="Propuesta_Movil_Claro.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )


# ==========================================
# PESTAÑA 2: PROPUESTAS FIJAS / INTERNET
# ==========================================
with tab_fija:
    st.markdown("### 1. Configuración de Servicios Fijos Nuevos")

    col_rf1, col_rf2 = st.columns([2, 4])
    with col_rf1:
        st.session_state.ruc = st.text_input(
            "RUC de la empresa",
            value=st.session_state.get("ruc", ""),
            placeholder="Ej. 20123456789",
            key="ruc_input_fija",
        )
    with col_rf2:
        st.session_state.company = st.text_input(
            "Razón Social",
            value=st.session_state.get("company", ""),
            placeholder="Nombre de la empresa",
            key="company_input_fija",
        )

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        tech_type = st.radio("Seleccionar Tecnología", ["HFC", "FTTH"], horizontal=True, key="tech_type_radio")
    with col_t2:
        if tech_type == "FTTH":
            mesh_count = st.number_input(
                "Cantidad de Puntos Wi-Fi 360 (Mesh)",
                min_value=0, max_value=5,
                value=st.session_state.get("current_mesh_count", 0),
                step=1,
                help="Selecciona de 1 a 5 equipos Mesh según las reglas de la matriz.",
                key="current_mesh_count",
            )
        else:
            mesh_count = 0

    col_cat1, col_cat2 = st.columns(2)
    with col_cat1:
        categoria_seleccionada = st.selectbox("Segmentar por Tipo de Servicio Fijo", ["1 Play", "2 Play", "3 Play"], key="select_categoria_fija")

    planes_filtrados = [p for p in DEFAULT_PLANS_FIJA if p.get("categoria", "") == categoria_seleccionada]

    with col_cat2:
        fixed_plan_name = st.selectbox("Seleccionar Solución Fija / Fibra Oficial", [p["n"] for p in planes_filtrados], key="select_fijo_plan_nuevo")

    selected_temp_p = next(p for p in DEFAULT_PLANS_FIJA if p["n"] == fixed_plan_name)
    
    col_deco1, _ = st.columns(2)
    with col_deco1:
        deco_count = 0
        if selected_temp_p.get("has_tv", False):
            deco_count = st.number_input(
                f"Decodificadores Adicionales ({selected_temp_p.get('tv_type', '')})",
                min_value=0, max_value=4,
                value=st.session_state.get("current_deco_count", 0),
                step=1,
                help="1er punto adicional gratis, 2do al 4to punto valen S/ 10 c/u",
                key="current_deco_count",
            )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("+ Agregar servicio fijo nuevo", type="primary", use_container_width=True):
        st.session_state.fixed_services.append(
            {
                "id": str(pd.Timestamp.now().timestamp()),
                "base_name": selected_temp_p["n"],
                "speed": selected_temp_p["speed"],
                "base_promo": selected_temp_p["p"],
                "base_reg": selected_temp_p["reg"],
                "tipo": selected_temp_p["tipo"],
                "base_desc": selected_temp_p["desc"],
                "tech": tech_type,
                "initial_mesh": mesh_count if tech_type == "FTTH" else 0,
                "initial_deco": deco_count,
                "has_tv": selected_temp_p.get("has_tv", False),
                "tv_type": selected_temp_p.get("tv_type", ""),
                "promo_months": selected_temp_p["promo_months"],
                "bonus_text": selected_temp_p["bonus_text"],
            }
        )
        st.success("¡Servicio fijo agregado a la propuesta nueva!")
        st.rerun()

    if st.button("🗑️ Limpiar servicios fijos nuevos", use_container_width=False):
        st.session_state.fixed_services = []
        st.rerun