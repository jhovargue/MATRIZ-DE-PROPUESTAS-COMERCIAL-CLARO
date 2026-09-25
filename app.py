import base64
import io
import os
import re
import pandas as pd
import pdfplumber
import streamlit as st
import streamlit.components.v1 as components

# Configuración de la página web
st.set_page_config(
    page_title="Matriz Comercial Claro Empresas",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Inicializar variables de estado general
if "lines" not in st.session_state:
    st.session_state.lines = []
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
    {"n": "800 Mbps - 2 Play Telefonía 5000", "p": 105.0, "reg": 105.0, "tipo": "2 Play", "categoria": "2 Play", "desc": "Internet Empresas Digital 800 Mbps + Telefonía 5000 min", "speed": 800, "promo_months": 0, "bonus_text": "Bono de velocidad a 1000 Mbps por 12 meses", "has_tv": False},
    {"n": "800 Mbps - 2 Play TV Estándar Pro", "p": 185.0, "reg": 185.0, "tipo": "2 Play TV", "categoria": "2 Play", "desc": "Internet Empresas Digital 800 Mbps + TV Estándar Pro", "speed": 800, "promo_months": 0, "bonus_text": "Bono de velocidad a 1000 Mbps por 12 meses", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "800 Mbps - 2 Play TV Superior Pro", "p": 155.0, "reg": 225.0, "tipo": "2 Play TV", "categoria": "2 Play", "desc": "Internet Empresas Digital 800 Mbps + TV Superior Pro", "speed": 800, "promo_months": 6, "bonus_text": "Bono de velocidad a 1000 Mbps por 12 meses", "has_tv": True, "tv_type": "Superior Pro"},
    {"n": "1000 Mbps (Full Claro) - 2 Play Telefonía 5000", "p": 150.0, "reg": 150.0, "tipo": "2 Play", "categoria": "2 Play", "desc": "Internet Empresas Digital 1000 Mbps + Telefonía 5000 min", "speed": 1000, "promo_months": 0, "bonus_text": "Bono de velocidad por 12 meses", "has_tv": False},
    {"n": "1000 Mbps (Full Claro) - 2 Play TV Estándar Pro", "p": 159.0, "reg": 230.0, "tipo": "2 Play TV", "categoria": "2 Play", "desc": "Internet Empresas Digital 1000 Mbps + TV Estándar Pro", "speed": 1000, "promo_months": 6, "bonus_text": "Bono de velocidad por 12 meses", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "1000 Mbps (Full Claro) - 2 Play TV Superior Pro", "p": 189.0, "reg": 270.0, "tipo": "2 Play TV", "categoria": "2 Play", "desc": "Internet Empresas Digital 1000 Mbps + TV Superior Pro", "speed": 1000, "promo_months": 6, "bonus_text": "Bono de velocidad por 12 meses", "has_tv": True, "tv_type": "Superior Pro"},
    {"n": "1500 Mbps (Solo FTTH) - 2 Play Telefonía 5000", "p": 205.0, "reg": 205.0, "tipo": "2 Play", "categoria": "2 Play", "desc": "Internet Empresas Digital 1500 Mbps + Telefonía 5000 min", "speed": 1500, "promo_months": 0, "bonus_text": "Con Full Claro + GB en tu móvil", "has_tv": False},
    {"n": "1500 Mbps (Solo FTTH) - 2 Play TV Estándar Pro", "p": 285.0, "reg": 285.0, "tipo": "2 Play TV", "categoria": "2 Play", "desc": "Internet Empresas Digital 1500 Mbps + TV Estándar Pro", "speed": 1500, "promo_months": 0, "bonus_text": "Con Full Claro + GB en tu móvil", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "1500 Mbps (Solo FTTH) - 2 Play TV Superior Pro", "p": 255.0, "reg": 325.0, "tipo": "2 Play TV", "categoria": "2 Play", "desc": "Internet Empresas Digital 1500 Mbps + TV Superior Pro", "speed": 1500, "promo_months": 6, "bonus_text": "Con Full Claro + GB en tu móvil", "has_tv": True, "tv_type": "Superior Pro"},
    # 3 PLAY
    {"n": "200 Mbps - 3 Play Estándar Pro", "p": 94.0, "reg": 155.0, "tipo": "3 Play", "categoria": "3 Play", "desc": "Internet Empresas Digital 200 Mbps + TV Estándar Pro + Telefonía 5000", "speed": 200, "promo_months": 6, "bonus_text": "Bono de velocidad a 400 Mbps por 6 meses", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "200 Mbps - 3 Play Superior Pro", "p": 124.0, "reg": 195.0, "tipo": "3 Play", "categoria": "3 Play", "desc": "Internet Empresas Digital 200 Mbps + TV Superior Pro + Telefonía 5000", "speed": 200, "promo_months": 6, "bonus_text": "Bono de velocidad a 400 Mbps por 6 meses", "has_tv": True, "tv_type": "Superior Pro"},
    {"n": "300 Mbps (600 Mbps) - 3 Play Estándar Pro", "p": 104.0, "reg": 165.0, "tipo": "3 Play", "categoria": "3 Play", "desc": "Internet Empresas Digital 300 Mbps + TV Estándar Pro + Telefonía 5000", "speed": 300, "promo_months": 6, "bonus_text": "Bono de velocidad a 600 Mbps por 6 meses", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "300 Mbps (600 Mbps) - 3 Play Superior Pro", "p": 205.0, "reg": 205.0, "tipo": "3 Play", "categoria": "3 Play", "desc": "Internet Empresas Digital 300 Mbps + TV Superior Pro + Telefonía 5000", "speed": 300, "promo_months": 0, "bonus_text": "Bono de velocidad a 600 Mbps por 6 meses", "has_tv": True, "tv_type": "Superior Pro"},
    {"n": "400 Mbps - 3 Play Estándar Pro", "p": 114.0, "reg": 175.0, "tipo": "3 Play", "categoria": "3 Play", "desc": "Internet Empresas Digital 400 Mbps + TV Estándar Pro + Telefonía 5000", "speed": 400, "promo_months": 6, "bonus_text": "Bono de velocidad a 1000 Mbps por 12 meses", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "400 Mbps - 3 Play Superior Pro", "p": 144.0, "reg": 215.0, "tipo": "3 Play", "categoria": "3 Play", "desc": "Internet Empresas Digital 400 Mbps + TV Superior Pro + Telefonía 5000", "speed": 400, "promo_months": 6, "bonus_text": "Bono de velocidad a 1000 Mbps por 12 meses", "has_tv": True, "tv_type": "Superior Pro"},
    {"n": "800 Mbps - 3 Play Estándar Pro", "p": 190.0, "reg": 190.0, "tipo": "3 Play", "categoria": "3 Play", "desc": "Internet Empresas Digital 800 Mbps + TV Estándar Pro + Telefonía 5000", "speed": 800, "promo_months": 0, "bonus_text": "Bono de velocidad a 1000 Mbps por 12 meses", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "800 Mbps - 3 Play Superior Pro", "p": 160.0, "reg": 230.0, "tipo": "3 Play", "categoria": "3 Play", "desc": "Internet Empresas Digital 800 Mbps + TV Superior Pro + Telefonía 5000", "speed": 800, "promo_months": 6, "bonus_text": "Bono de velocidad a 1000 Mbps por 12 meses", "has_tv": True, "tv_type": "Superior Pro"},
    {"n": "1000 Mbps (Full Claro) - 3 Play Estándar Pro", "p": 164.0, "reg": 235.0, "tipo": "3 Play", "categoria": "3 Play", "desc": "Internet Empresas Digital 1000 Mbps + TV Estándar Pro + Telefonía 5000", "speed": 1000, "promo_months": 6, "bonus_text": "Bono de velocidad por 12 meses", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "1000 Mbps (Full Claro) - 3 Play Superior Pro", "p": 194.0, "reg": 275.0, "tipo": "3 Play", "categoria": "3 Play", "desc": "Internet Empresas Digital 1000 Mbps + TV Superior Pro + Telefonía 5000", "speed": 1000, "promo_months": 6, "bonus_text": "Bono de velocidad por 12 meses", "has_tv": True, "tv_type": "Superior Pro"},
    {"n": "1500 Mbps (Solo FTTH) - 3 Play Estándar Pro", "p": 290.0, "reg": 290.0, "tipo": "3 Play", "categoria": "3 Play", "desc": "Internet Empresas Digital 1500 Mbps + TV Estándar Pro + Telefonía 5000", "speed": 1500, "promo_months": 0, "bonus_text": "Con Full Claro + GB en tu móvil", "has_tv": True, "tv_type": "Estándar Pro"},
    {"n": "1500 Mbps (Solo FTTH) - 3 Play Superior Pro", "p": 260.0, "reg": 330.0, "tipo": "3 Play", "categoria": "3 Play", "desc": "Internet Empresas Digital 1500 Mbps + TV Superior Pro + Telefonía 5000", "speed": 1500, "promo_months": 6, "bonus_text": "Con Full Claro + GB en tu móvil", "has_tv": True, "tv_type": "Superior Pro"},
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

def recommend_plan_movil(cf, mode="Plan equivalente"):
    eligible = [p for p in DEFAULT_PLANS_MOVIL if p["d"]]
    if mode == "Mayor ahorro":
        return eligible[0] if eligible else DEFAULT_PLANS_MOVIL[3]
    for p in eligible:
        if p["p"] >= cf: return p
    return eligible[-1] if eligible else DEFAULT_PLANS_MOVIL[3]

# --- EXTRACCIÓN DINÁMICA DE RECIBOS ---
def extract_pdf_data(file_bytes, filename, recommend_mode):
    extracted_lines = []
    full_text = ""
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text: full_text += text + "\n"
    except Exception as e:
        st.error(f"Error al leer el PDF {filename}: {e}")
        return []

    # 1. Extracción de RUC de la empresa
    ruc_encontrado = None
    file_ruc = re.search(r"\b([12]\d{10})\b", filename)
    if file_ruc:
        ruc_encontrado = file_ruc.group(1)

    if not ruc_encontrado:
        operator_rucs = ["20100017491", "20414955020", "20504771424", "20263322496"]
        all_rucs = re.findall(r"(?:RUC|N[º°]\s*Doc|R\.U\.C\.?)[\s:]*([12]\d{10})", full_text, re.IGNORECASE)
        for r in all_rucs:
            if r not in operator_rucs:
                ruc_encontrado = r
                break
        if not ruc_encontrado:
            direct_rucs = re.findall(r"\b([12]\d{10})\b", full_text)
            for r in direct_rucs:
                if r not in operator_rucs:
                    ruc_encontrado = r
                    break

    if ruc_encontrado:
        st.session_state.ruc = ruc_encontrado

    # 2. Extracción de Razón Social
    company_found = ""
    suffixes = ["S.A.C.", "S.A.C", "E.I.R.L.", "E.I.R.L", "S.A.", "S.A", "S.R.L.", "S.R.L", "SRL", "SAC", "EIRL", "SOCIEDAD ANONIMA"]
    for line in full_text.split("\n"):
        line_clean = line.strip()
        if any(re.search(rf"\b{re.escape(s)}\b", line_clean, re.IGNORECASE) for s in suffixes):
            if not any(w in line_clean.upper() for w in ["ENTEL PERU", "ENTEL PERÚ", "TELEFONICA DEL PERU", "TELEFÓNICA", "AMERICA MOVIL", "AMÉRICA MÓVIL", "CLARO", "INTEGRATEL"]):
                line_clean = re.sub(r"^(?:Señor\(es\)|Cliente|Razón Social|Titular|Abonado)[\s:]*", "", line_clean, flags=re.IGNORECASE).strip()
                line_clean = re.sub(r"(?:RUC|N[º°]).*", "", line_clean, flags=re.IGNORECASE).strip()
                if len(line_clean) > 4 and not line_clean.replace(" ", "").isdigit():
                    company_found = line_clean
                    break

    if not company_found:
        comp_matches = re.findall(r"(?:Señor\(es\)|Razón Social|Nombre o Razón Social)[\s:]+([^\n\r]+)", full_text, re.IGNORECASE)
        for cand in comp_matches:
            cand = cand.strip()
            cand = re.sub(r"(?:RUC|N[º°]|Doc).*", "", cand, flags=re.IGNORECASE).strip()
            if len(cand) > 4 and not cand.replace(" ", "").replace("-", "").isdigit():
                company_found = cand
                break

    if company_found:
        st.session_state.company = company_found

    is_entel = "entel" in full_text.lower() or "empresa pro" in full_text.lower()

    if is_entel:
        pattern = re.compile(
            r"^(9\d{8})\s+(.+?)\s+(-?\d+\.\d{2})\s+(-?\d+\.\d{2})\s+(-?\d+\.\d{2})\s+(-?\d+\.\d{2})\s+(-?\d+\.\d{2})\s+(-?\d+\.\d{2})\s+(-?\d+\.\d{2})$",
            re.MULTILINE,
        )
        matches = pattern.findall(full_text)

        if matches:
            for m in matches:
                ph = m[0]
                plan_name = m[1].strip()
                cf = float(m[2])
                disc_val = abs(float(m[5]))
                pay = float(m[8])
                discount_pct = (disc_val / cf * 100) if cf > 0 else 0.0

                rec = recommend_plan_movil(cf, recommend_mode)
                extracted_lines.append(
                    {
                        "id": str(pd.Timestamp.now().timestamp()) + "_" + ph,
                        "phone": ph,
                        "operator": "Entel",
                        "plan": plan_name,
                        "cf": cf,
                        "discount": round(discount_pct, 1),
                        "pay": pay,
                        "claro_plan_idx": DEFAULT_PLANS_MOVIL.index(rec),
                        "source": filename,
                    }
                )
        else:
            phones = re.findall(r"\b(9\d{8})\b", full_text)
            unique_phones = list(dict.fromkeys(phones))[:30]
            for ph in unique_phones:
                cf = 55.90
                pay = 27.95
                rec = recommend_plan_movil(cf, recommend_mode)
                extracted_lines.append(
                    {
                        "id": str(pd.Timestamp.now().timestamp()) + "_" + ph,
                        "phone": ph,
                        "operator": "Entel",
                        "plan": "Empresa PRO",
                        "cf": cf,
                        "discount": 50.0,
                        "pay": pay,
                        "claro_plan_idx": DEFAULT_PLANS_MOVIL.index(rec),
                        "source": filename,
                    }
                )
    else:
        movistar_plan_name = "Movistar Empresas"
        cf_detectado = None
        discount_pct = 0.0

        for line in full_text.split("\n"):
            line_str = line.strip()
            if any(w in line_str.upper() for w in ["MOVISTAR EMPRESAS", "ELIGE TODO", "B2B", "PLAN"]) and "S/" in line_str:
                m_cf = re.search(r"S/\.?\s*(\d+(?:\.\d{1,2})?)", line_str)
                if m_cf:
                    val = float(m_cf.group(1))
                    if 15.0 <= val <= 350.0:
                        cf_detectado = val
                        m_name = re.search(r"((?:Plan|B2B|Movistar)[^\(]+)", line_str, re.IGNORECASE)
                        if m_name:
                            plan_raw = m_name.group(1).strip()
                            plan_clean = re.sub(r"^(?:Cargos\s+Mensuales:?|Importe\s*S/?)\s*", "", plan_raw, flags=re.IGNORECASE)
                            plan_clean = re.sub(r"\s+\d+\s*$", "", plan_clean.strip())
                        else:
                            plan_clean = re.sub(r"\(.*?\)", "", line_str)
                            plan_clean = re.sub(r"^(?:Cargos\s+Mensuales:?|Importe\s*S/?)\s*", "", plan_clean, flags=re.IGNORECASE)
                        
                        plan_clean = plan_clean.strip(" :-\t")
                        if len(plan_clean) > 3:
                            movistar_plan_name = plan_clean

            if "DESCUENTO" in line_str.upper() and "%" in line_str:
                m_dscto = re.search(r"(\d+(?:\.\d+)?)%", line_str)
                if m_dscto:
                    discount_pct = float(m_dscto.group(1))

        if cf_detectado is None:
            unit_match = re.search(r"\b\d+\s+S/\.?\s*(\d+\.\d{2})\s+S/\.?\s*(\d+\.\d{2})", full_text)
            if unit_match:
                precio_unit_sin_igv = float(unit_match.group(1))
                cf_calc = round(precio_unit_sin_igv * 1.18, 2)
                if 15.0 <= cf_calc <= 350.0:
                    cf_detectado = cf_calc

        cf = cf_detectado if cf_detectado else 26.90
        pay = round(cf * (1 - (discount_pct / 100.0)), 2)

        phones = re.findall(r"\b(9\d{8})\b", full_text)
        operator_hotlines = ["966000000"]
        unique_phones = [p for p in dict.fromkeys(phones) if p not in operator_hotlines]

        if not unique_phones:
            unique_phones = ["900000000"]

        for ph in unique_phones:
            rec = recommend_plan_movil(cf, recommend_mode)
            extracted_lines.append(
                {
                    "id": str(pd.Timestamp.now().timestamp()) + "_" + ph,
                    "phone": ph,
                    "operator": "Movistar",
                    "plan": movistar_plan_name,
                    "cf": cf,
                    "discount": discount_pct,
                    "pay": pay,
                    "claro_plan_idx": DEFAULT_PLANS_MOVIL.index(rec),
                    "source": filename,
                }
            )

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
                "📁 Arrastra o selecciona recibos PDF",
                type=["pdf"],
                accept_multiple_files=True,
                key=f"pdf_uploader_{st.session_state.clear_key}",
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
            if l.get("source") == "Manual" or l.get("source") in current_filenames
        ]

        if uploaded_files:
            nuevas_totales = False
            for uf in uploaded_files:
                file_bytes = uf.read()
                if not any(l.get("source") == uf.name for l in st.session_state.lines):
                    nuevas = extract_pdf_data(file_bytes, uf.name, recommend_mode)
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
                rec = recommend_plan_movil(l["cf"], recommend_mode)
                l["claro_plan_idx"] = DEFAULT_PLANS_MOVIL.index(rec)

        col_r1, col_r2, col_r3, col_r4 = st.columns([2, 3, 1, 1])
        with col_r1:
            ruc_ingresado = st.text_input(
                "RUC de la empresa",
                value=st.session_state.ruc,
                placeholder="Ej. 20123456789",
            )
            st.session_state.ruc = ruc_ingresado

        with col_r2:
            company_ingresada = st.text_input(
                "Razón Social",
                value=st.session_state.company,
                placeholder="Nombre de la empresa",
            )
            st.session_state.company = company_ingresada

        with col_r3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("+ Línea manual", use_container_width=True):
                rec = recommend_plan_movil(55.9, recommend_mode)
                st.session_state.lines.append(
                    {
                        "id": str(pd.Timestamp.now().timestamp()),
                        "phone": "900000000",
                        "operator": "Movistar",
                        "plan": "Manual",
                        "cf": 55.9,
                        "discount": 0.0,
                        "pay": 55.9,
                        "claro_plan_idx": DEFAULT_PLANS_MOVIL.index(rec),
                        "source": "Manual",
                    }
                )
                st.rerun()
        with col_r4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ Limpiar todo", use_container_width=True):
                st.session_state.lines = []
                st.session_state.ruc = ""
                st.session_state.company = ""
                st.session_state.clear_key += 1
                st.rerun()

    st.markdown("---")

    lines = st.session_state.lines
    total_lines = len(lines)
    total_current = sum(l["pay"] for l in lines)

    def get_claro_offer(l):
        p = DEFAULT_PLANS_MOVIL[l["claro_plan_idx"]]
        if p["d"]:
            if modality == "Centralizado":
                return round(p["p"] * (1 - (manual_discount_pct / 100.0)), 2)
            else:
                return p["offer_price"]
        return p["p"]

    total_claro = sum(get_claro_offer(l) for l in lines)
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
        st.info("👆 Arrastra o carga tus recibos PDF en la parte superior o agrega una línea manualmente para comenzar.")
    else:
        plan_names = [p["n"] for p in DEFAULT_PLANS_MOVIL]

        table_data = []
        for i, l in enumerate(lines):
            current_plan = DEFAULT_PLANS_MOVIL[l["claro_plan_idx"]]
            offer = get_claro_offer(l)
            table_data.append(
                {
                    "N°": i + 1,
                    "Línea": l["phone"],
                    "Operador": l["operator"],
                    "Plan Actual": l["plan"],
                    "CF Actual": l["cf"],
                    "Dscto %": l["discount"],
                    "Pago Actual": l["pay"],
                    "Plan Claro": current_plan["n"],
                    "CF Claro": current_plan["p"],
                    "Pago Oferta": offer,
                    "Internet / Beneficios": current_plan["gb"],
                    "Ahorro Línea": l["pay"] - offer,
                }
            )

        df_editable = pd.DataFrame(table_data)

        edited_df = st.data_editor(
            df_editable,
            column_config={
                "Plan Claro": st.column_config.SelectboxColumn(
                    "Plan Claro",
                    options=plan_names,
                    required=True,
                )
            },
            disabled=[
                "N°", "Línea", "Operador", "Plan Actual", "CF Actual", "Dscto %",
                "Pago Actual", "CF Claro", "Pago Oferta", "Internet / Beneficios", "Ahorro Línea",
            ],
            hide_index=True,
            use_container_width=True,
            key="plan_editor_movil",
        )

        updated = False
        for index, row in edited_df.iterrows():
            selected_plan_name = row["Plan Claro"]
            new_plan_idx = next(i for i, p in enumerate(DEFAULT_PLANS_MOVIL) if p["n"] == selected_plan_name)
            if st.session_state.lines[index]["claro_plan_idx"] != new_plan_idx:
                st.session_state.lines[index]["claro_plan_idx"] = new_plan_idx
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

        rows_html = ""
        for idx, r in edited_df.iterrows():
            bg = "#f9f9f9" if idx % 2 == 0 else "#ffffff"
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
                <td style="padding:4px; border:1px solid #ddd; color:#e30613; font-weight:bold;">S/{r['Pago Oferta']:.2f}</td>
                <td style="padding:4px; border:1px solid #ddd; font-size:10px;">{r['Internet / Beneficios']}</td>
            </tr>
            """

        badge_text = (
            f"HASTA<br>{int(manual_discount_pct)}%<span style='font-size:9px; display:block;'>DTO. CENTRALIZADO</span>"
            if modality == "Centralizado"
            else "HASTA<br>50%<span style='font-size:9px; display:block;'>POR 12 MESES</span>"
        )

        empresa_titulo = f"{st.session_state.ruc} · {st.session_state.company}" if (st.session_state.ruc and st.session_state.company) else (st.session_state.ruc or st.session_state.company or "RUC · RAZÓN SOCIAL")

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
            .proposal-title {{ font-size: 16px; font-weight: 900; letter-spacing: 1px; text-align: center; flex-grow: 1; color: #ffffff; }}
            .badge-dto {{ background-color: #fff1bd !important; color: #e30613; padding: 6px 12px; border-radius: 6px; font-weight: 900; font-size: 11px; text-align: right; }}
            .proposal-footer {{ display: flex; justify-content: space-between; padding: 6px 12px; background: #e9ecef; font-size: 9px; color: #555; border-top: 1px solid #ccc; }}
        </style>
        </head>
        <body>
        <div class="proposal-container" id="print-section-movil">
            <div class="proposal-header">
                {LOGO_PROPOSAL_HTML}
                <div class="proposal-title">PROPUESTA DE PORTABILIDAD MÓVIL ({modality.upper()})<br><span style="font-size:12px; font-weight:bold; color:#ffd700;">{empresa_titulo}</span></div>
                <div class="badge-dto">{badge_text}</div>
            </div>
            <table style="width:100%; border-collapse:collapse; font-size:10px;">
                <thead>
                    <tr style="background-color:#1763a5 !important; color:white; text-align:center;">
                        <th colspan="7" style="padding:5px; border:1px solid #ddd; background:#151515 !important; color:white;">SERVICIO ACTUAL</th>
                        <th colspan="4" style="padding:5px; border:1px solid #ddd; background:#e30613 !important; color:white;">PLAN CON CLARO</th>
                    </tr>
                    <tr style="background-color:#f4b400 !important; color:#111; font-weight:bold; text-align:center;">
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
                        <li>Cobertura internacional integrada según el plan contratado.</li>
                    </ul>
                    {image_html_content}
                </div>
                <div style="width:38%; display:flex; flex-direction:column; gap:4px;">
                    <div style="display:flex; justify-content:space-between; background:#0d0d0e !important; color:white; padding:6px 10px; border-radius:4px; font-size:11px; font-weight:bold;">
                        <span>FACTURACIÓN ACTUAL</span><span>S/{total_current:.2f}</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; background:#1763a5 !important; color:white; padding:6px 10px; border-radius:4px; font-size:11px; font-weight:bold;">
                        <span>PAGO MENSUAL CLARO</span><span>S/{total_claro:.2f}</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; background:#e30613 !important; color:white; padding:6px 10px; border-radius:4px; font-size:11px; font-weight:bold;">
                        <span>AHORRO MENSUAL</span><span>S/{total_saving:.2f}</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; background:#e30613 !important; color:white; padding:8px 10px; border-radius:4px; font-size:12px; font-weight:900;">
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
        st.rerun()

    st.markdown("### 2. Resumen de Servicios Fijos (Servicio Nuevo)")
    fixed_list = st.session_state.fixed_services

    if not fixed_list:
        st.info("👆 Selecciona la categoría, plan fijo, puntos mesh y decodificadores para armar la propuesta de servicio nuevo.")
    else:
        fixed_data = []
        total_claro_fija = 0.0
        total_claro_regular = 0.0

        for idx, item in enumerate(fixed_list):
            current_mesh = mesh_count if item["tech"] == "FTTH" else 0
            current_deco = deco_count if item["has_tv"] else 0
            
            wifi_p, wifi_reg = calculate_wifi_360_cost(item["speed"], current_mesh)
            deco_p = calculate_deco_cost(item["tv_type"], current_deco)

            item_promo = item["base_promo"] + wifi_p + deco_p
            item_reg = item["base_reg"] + wifi_reg + deco_p
            total_claro_fija += item_promo
            total_claro_regular += item_reg

            addons_text = ""
            if current_mesh > 0: addons_text += f" + {current_mesh} Puntos Wi-Fi 360"
            if current_deco > 0: addons_text += f" + {current_deco} Decos Adicionales"

            item["calculated_promo"] = item_promo
            item["calculated_reg"] = item_reg
            item["calculated_desc"] = item["base_desc"] + addons_text
            item["calculated_mesh_count"] = current_mesh
            item["calculated_deco_count"] = current_deco

            has_discount = item_promo < item_reg

            fixed_data.append(
                {
                    "N°": idx + 1,
                    "Servicio / Pack": item["base_name"] + f" ({item['tech']})",
                    "Tipo": item["tipo"],
                    "Detalle / Beneficios": item["calculated_desc"],
                    "Oferta Promocional": f"S/{item_promo:.2f}" if has_discount else "-",
                    "Precio Regular": f"S/{item_reg:.2f}",
                }
            )

        df_fija = pd.DataFrame(fixed_data)
        
        for idx, row in df_fija.iterrows():
            col_r1, col_r2, col_r3, col_r4, col_r5, col_r6, col_r7 = st.columns([0.5, 3, 1, 3.5, 1.2, 1.2, 0.5])
            col_r1.write(str(row["N°"]))
            col_r2.write(row["Servicio / Pack"])
            col_r3.write(row["Tipo"])
            col_r4.write(row["Detalle / Beneficios"])
            col_r5.write(row["Oferta Promocional"])
            col_r6.write(row["Precio Regular"])
            if col_r7.button("🗑️", key=f"del_fijo_{fixed_list[idx]['id']}"):
                st.session_state.fixed_services.pop(idx)
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        fk1, fk2 = st.columns(2)
        has_overall_discount = total_claro_fija < total_claro_regular
        fk1.metric("Total Oferta Promocional Mensual", f"S/{total_claro_fija:.2f}" if has_overall_discount else "-")
        fk2.metric("Total Precio Regular Mensual", f"S/{total_claro_regular:.2f}")

        st.markdown("---")
        st.subheader("3. Vista Ejecutiva Fija para el Cliente (Servicio Nuevo)")

        rows_fija_html = ""
        benefits_html = ""
        has_any_tv_plan = any(item.get("has_tv", False) for item in fixed_list)

        for idx, r in df_fija.iterrows():
            bg = "#f9f9f9" if idx % 2 == 0 else "#ffffff"
            promo_display = r['Oferta Promocional']
            reg_display = r['Precio Regular']
            rows_fija_html += f"""
            <tr style="background-color:{bg}; text-align:center; border-bottom:1px solid #eee;">
                <td style="padding:6px; border:1px solid #ddd; font-weight:bold;">{r['N°']}</td>
                <td style="padding:6px; border:1px solid #ddd; text-align:left; padding-left:8px; font-weight:bold;">{r['Servicio / Pack']}</td>
                <td style="padding:6px; border:1px solid #ddd; font-size:10px;">{r['Detalle / Beneficios']}</td>
                <td style="padding:6px; border:1px solid #ddd; color:#e30613; font-weight:bold;">{promo_display}</td>
                <td style="padding:6px; border:1px solid #ddd;">{reg_display}</td>
            </tr>
            """
            item_orig = fixed_list[idx]
            p_months = item_orig.get("promo_months", 0)
            b_text = item_orig.get("bonus_text", "")
            curr_m = item_orig.get("calculated_mesh_count", 0)
            curr_d = item_orig.get("calculated_deco_count", 0)
            
            if p_months > 0: benefits_html += f"<li>Descuento promocional en el cargo fijo por {p_months} meses.</li>"
            if b_text: benefits_html += f"<li>{b_text}.</li>"
            if curr_m > 0: benefits_html += f"<li>{curr_m} Puntos Wi-Fi 360 con descuento promocional por {p_months if p_months > 0 else 6} meses (luego aplica costo regular).</li>"
            if curr_d > 0: benefits_html += f"<li>{curr_d} Decodificadores adicionales (1er punto adicional sin costo, del 2do al 4to a S/ 10 c/u).</li>"

        tv_banner_html = ""
        if has_any_tv_plan:
            tv_banner_html = """
            <div style="width: 100%; margin-top: 12px; text-align: center; background: #111; padding: 6px; border-radius: 6px;">
                <div style="color: #ffd700; font-weight: 900; font-size: 13px; margin-bottom: 4px;">¡INCLUYE LIGA 1 MAX! ⚽</div>
                <div style="color: white; font-size: 10px;">Disfruta de todo el fútbol peruano y los mejores canales en alta definición.</div>
            </div>
            """

        overall_promo_display = f"S/{total_claro_fija:.2f}" if has_overall_discount else "-"

        fija_html = f"""
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
            .proposal-title {{ font-size: 16px; font-weight: 900; letter-spacing: 1px; text-align: center; flex-grow: 1; color: #ffffff; }}
            .badge-dto {{ background-color: #fff1bd !important; color: #e30613; padding: 6px 12px; border-radius: 6px; font-weight: 900; font-size: 11px; text-align: right; }}
            .proposal-footer {{ display: flex; justify-content: space-between; padding: 6px 12px; background: #e9ecef; font-size: 9px; color: #555; border-top: 1px solid #ccc; }}
        </style>
        </head>
        <body>
        <div class="proposal-container" id="print-section-fija">
            <div class="proposal-header">
                {LOGO_PROPOSAL_HTML}
                <div class="proposal-title">PROPUESTA DE NUEVO SERVICIO - INTERNET EMPRESAS DIGITAL Y FIJOS<br><span style="font-size:11px; font-weight:bold; color:#ffffff;">{st.session_state.ruc or 'RUC'} · {st.session_state.company or 'RAZÓN SOCIAL'}</span></div>
                <div class="badge-dto">INTERNET EMPRESAS<br>DIGITAL</div>
            </div>
            <table style="width:100%; border-collapse:collapse; font-size:11px;">
                <thead>
                    <tr style="background-color:#1763a5 !important; color:white; text-align:center;">
                        <th colspan="3" style="padding:6px; border:1px solid #ddd; background:#151515 !important; color:white;">DETALLE DE SOLUCIÓN NUEVA / INTERNET</th>
                        <th style="padding:6px; border:1px solid #ddd; background:#e30613 !important; color:white;">OFERTA PROMOCIONAL</th>
                        <th style="padding:6px; border:1px solid #ddd; background:#1763a5 !important; color:white;">PRECIO REGULAR</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_fija_html}
                </tbody>
            </table>
            <div style="display:flex; justify-content:space-between; padding:12px; background:#f4f5f7 !important; align-items:flex-start; border-top:1px solid #ddd;">
                <div style="width:58%; background:white; padding:10px; border-radius:6px; border:1px solid #ddd;">
                    <strong style="font-size:11px; color:#111;">BENEFICIOS INCLUIDOS CON CLARO EMPRESAS</strong>
                    <ul style="margin:4px 0 0 15px; padding:0; font-size:10px; color:#444; line-height:1.4;">
                        <li>Internet Empresas Digital estable y de alta velocidad con herramientas digitales incluidas según el plan.</li>
                        {benefits_html}
                        <li>Soporte técnico especializado corporativo 24/7.</li>
                    </ul>
                    {tv_banner_html}
                </div>
                <div style="width:38%; display:flex; flex-direction:column; gap:4px;">
                    <div style="display:flex; justify-content:space-between; background:#e30613 !important; color:white; padding:8px 10px; border-radius:4px; font-size:12px; font-weight:900;">
                        <span>TOTAL OFERTA PROMOCIONAL</span><span>{overall_promo_display}</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; background:#1763a5 !important; color:white; padding:8px 10px; border-radius:4px; font-size:11px; font-weight:bold;">
                        <span>TOTAL PRECIO REGULAR</span><span>S/{total_claro_regular:.2f}</span>
                    </div>
                </div>
            </div>
            <div class="proposal-footer">
                <span>Soluciones Fijas y Fibra Óptica Claro Empresas</span>
                <span>Desarrollado por: <strong>JHONNIER VARELA</strong></span>
            </div>
        </div>
        <div class="no-print" style="text-align: center; margin-top: 15px; display: flex; justify-content: center; gap: 15px;">
            <button onclick="downloadImageFija()" style="background-color:#1763a5; color:white; border:none; padding:10px 20px; border-radius:8px; font-weight:bold; font-size:14px; cursor:pointer;">🖼️ Descargar como Imagen (PNG)</button>
            <button onclick="window.print()" style="background-color:#e30613; color:white; border:none; padding:10px 20px; border-radius:8px; font-weight:bold; font-size:14px; cursor:pointer;">🖨️ Guardar como PDF</button>
        </div>
        <script>
            function downloadImageFija() {{
                const element = document.getElementById("print-section-fija");
                html2canvas(element, {{ scale: 2, useCORS: true }}).then(canvas => {{
                    const link = document.createElement('a');
                    link.download = 'Propuesta_Fija_Nueva_Claro.png';
                    link.href = canvas.toDataURL('image/png');
                    link.click();
                }});
            }}
        </script>
        </body>
        </html>
        """

        components.html(fija_html, height=390 + (len(fixed_list) * 35), scrolling=False)


# ==========================================
# PESTAÑA 3: MATRIZ DE EQUIPOS MÓVILES (HOJAS "CONSOLIDADO TOTAL PORTA" Y "CONSOLIDADO TOTAL ALTA")
# ==========================================
with tab_equipos:
    st.markdown("### 📦 Matriz de Propuesta y Consulta de Stock de Equipos Móviles")

    # Detección de archivos consolidados en la carpeta
    consolidated_files = [
        f for f in os.listdir(".")
        if f.endswith((".xlsx", ".xlsm")) and not f.startswith("~$")
    ]
    consolidated_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    detected_file = consolidated_files[0] if consolidated_files else None

    with st.expander("⚙️ Cargar / Actualizar Archivo Consolidado de Equipos (.xlsx / .xlsm)", expanded=False):
        uploaded_excel = st.file_uploader(
            "Cargar Archivo Consolidado (hojas 'CONSOLIDADO TOTAL PORTA' / 'CONSOLIDADO TOTAL ALTA')",
            type=["xlsx", "xlsm"],
            key="up_consolidado_tab3",
        )

    active_excel_source = uploaded_excel if uploaded_excel is not None else detected_file

    if active_excel_source is not None:
        try:
            modalidad_equipo = st.radio(
                "Modalidad de Cotización de Equipos",
                ["Portabilidad / Renovación", "Línea Nueva"],
                horizontal=True,
                key="mod_eq_tab3_consolidado",
            )

            xl_obj = pd.ExcelFile(active_excel_source, engine="openpyxl")
            target_keyword = "PORTA" if modalidad_equipo == "Portabilidad / Renovación" else "ALTA"

            # Identificar la hoja exacta: "CONSOLIDADO TOTAL PORTA" o "CONSOLIDADO TOTAL ALTA"
            actual_sheet = next(
                (s for s in xl_obj.sheet_names if "CONSOLIDADO" in s.upper() and target_keyword in s.upper()),
                next((s for s in xl_obj.sheet_names if target_keyword in s.upper()), xl_obj.sheet_names[0])
            )

            # 1. Leer sin cabecera fija para evitar conflictos con celdas combinadas y duplicados
            raw_full = pd.read_excel(active_excel_source, sheet_name=actual_sheet, header=None, engine="openpyxl")
            if hasattr(active_excel_source, "seek"):
                active_excel_source.seek(0)

            # Buscar la fila donde se ubican las etiquetas "EQUIPO" y "PRECIO PREPAGO"
            header_row_idx = None
            for r_idx in range(min(15, len(raw_full))):
                row_str = " ".join([str(val).upper() for val in raw_full.iloc[r_idx].values if pd.notna(val)])
                if "EQUIPO" in row_str and ("PREPAGO" in row_str or "SISTEMA" in row_str or "STOCK" in row_str):
                    header_row_idx = r_idx
                    break

            if header_row_idx is None:
                header_row_idx = 3

            # Asignar datos por posición física de columna (evitando duplicate labels)
            df_data = raw_full.iloc[header_row_idx + 1:].copy().reset_index(drop=True)
            # Asegurar al menos 28 columnas (Col A=0 hasta Col AB=27)
            while df_data.shape[1] < 28:
                df_data[df_data.shape[1]] = None

            # MAPEO POR COLUMNA EXACTA:
            # Col A = 0: GAMA (inicial)
            # Col B = 1: Marca
            # Col C = 2: Equipo
            # Col D = 3: Precio Prepago
            # Col E = 4: Sistema Operativo
            # Col F a O = 5 a 14: CONTADO (10 planes)
            # Col P a Y = 15 a 24: CUOTA (10 planes)
            # Col Z = 25: STOCK
            # Col AA = 26: GAMA (nueva columna agregada)
            idx_marca = 1
            idx_equipo = 2
            idx_prepago = 3
            idx_stock = 25
            idx_gama = 26

            # Diccionario de offset de los 10 planes tarifarios (de 29.90 a 289.90)
            def get_plan_offset(plan_name):
                p_u = plan_name.upper()
                if "29.90" in p_u: return 0
                elif "39.90" in p_u: return 1
                elif "49.90" in p_u: return 2
                elif "55.90" in p_u or "69.90" in p_u: return 3
                elif "79.90" in p_u: return 4
                elif "95.90" in p_u: return 5
                elif "109.90" in p_u: return 6
                elif "125" in p_u: return 7
                elif "159.90" in p_u: return 8
                elif "189.90" in p_u or "289.90" in p_u: return 9
                return 0

            # Filtrar filas válidas que tengan nombre de equipo
            df_data = df_data[df_data[idx_equipo].notna()]
            df_data = df_data[~df_data[idx_equipo].astype(str).str.upper().isin(["NAN", "NONE", "EQUIPO", "TOTAL", "", "LLENAR"])]

            # Saneamiento de Marca
            df_data["MARCA_CLEAN"] = df_data[idx_marca].fillna("").astype(str).str.strip().str.upper()
            df_data["MARCA_CLEAN"] = df_data.apply(
                lambda r: r["MARCA_CLEAN"] if len(r["MARCA_CLEAN"]) > 1 else str(r[idx_equipo]).split()[0].upper(),
                axis=1
            )

            # Saneamiento de Gama (Columna AA)
            df_data["GAMA_CLEAN"] = df_data[idx_gama].fillna("").astype(str).str.strip().str.upper()
            df_data["GAMA_CLEAN"] = df_data["GAMA_CLEAN"].replace({"NAN": "SIN GAMA", "NONE": "SIN GAMA", "": "SIN GAMA"})

            # ==========================================
            # SECCIÓN A: CONSULTA DIRECTA DE STOCK Y FILTRO DE GAMA (CORREGIDO)
            # ==========================================
            st.markdown(f"#### 🔍 Consulta de Stock y Disponibilidad ({actual_sheet})")

            col_filtro1, col_filtro2, col_filtro3 = st.columns(3)

            # 1. Filtro por Gama (Columna AA / Índice 26) idéntico al segmentador de Excel
            gamas_detectadas = [
                g for g in df_data["GAMA_CLEAN"].unique() 
                if g not in ["", "SIN GAMA", "NAN", "NONE"]
            ]
            orden_preferido = ["HIGH", "MEDIUM", "LOW", "MODEM"]
            gamas_ordenadas = [g for g in orden_preferido if g in gamas_detectadas] + [g for g in gamas_detectadas if g not in orden_preferido]
            opciones_gama = ["-- Todas las Gamas --"] + gamas_ordenadas + ["(en blanco)"]

            with col_filtro1:
                filtro_gama = st.selectbox(
                    "Filtrar por Gama (Col AA)", 
                    opciones_gama, 
                    index=0, 
                    key="sel_gama_sheet_tab3"
                )

            # Aplicar filtro de gama si el usuario no eligió "Todas"
            if filtro_gama == "-- Todas las Gamas --":
                df_filtrado_gama = df_data
            elif filtro_gama == "(en blanco)":
                df_filtrado_gama = df_data[df_data["GAMA_CLEAN"].isin(["", "SIN GAMA"])]
            else:
                df_filtrado_gama = df_data[df_data["GAMA_CLEAN"] == filtro_gama]

            # 2. Filtro por Marca (Columna B / Índice 1) - Muestra todas las marcas
            marcas_list = sorted([
                str(m).strip().upper() 
                for m in df_filtrado_gama["MARCA_CLEAN"].unique() 
                if len(str(m).strip()) > 1 and not str(m).strip().isdigit() and str(m).strip().upper() not in ["NAN", "NONE", "MARCA"]
            ])

            with col_filtro2:
                filtro_marca = st.selectbox(
                    "Filtrar por Marca", 
                    ["-- Todas las Marcas --"] + marcas_list, 
                    index=0, 
                    key="sel_marca_sheet_tab3"
                )

            if filtro_marca != "-- Todas las Marcas --":
                df_filtrado_marca = df_filtrado_gama[df_filtrado_gama["MARCA_CLEAN"] == filtro_marca]
            else:
                df_filtrado_marca = df_filtrado_gama

            # 3. Selección de Terminal (Columna C / Índice 2)
            modelos_list = sorted([
                str(eq).strip() 
                for eq in df_filtrado_marca[idx_equipo].unique() 
                if len(str(eq).strip()) > 1 and str(eq).strip().upper() not in ["NAN", "NONE", "EQUIPO"]
            ])

            with col_filtro3:
                equipo_seleccionado = st.selectbox(
                    "Seleccionar Equipo / Terminal", 
                    ["-- Selecciona un Equipo --"] + modelos_list, 
                    index=0, 
                    key="sel_eq_sheet_tab3"
                )

            stock_encontrado = 0
            gama_del_equipo = "SIN GAMA"
            if equipo_seleccionado and equipo_seleccionado != "-- Selecciona un Equipo --":
                df_eq_rows = df_data[df_data[idx_equipo].astype(str).str.strip() == equipo_seleccionado.strip()]
                if not df_eq_rows.empty:
                    try:
                        raw_stk = df_eq_rows.iloc[0][idx_stock]
                        stock_encontrado = int(float(str(raw_stk).replace(",", "").strip()))
                    except Exception:
                        stock_encontrado = 0
                    
                    gama_del_equipo = str(df_eq_rows.iloc[0]["GAMA_CLEAN"])

                badge_color = "#28a745" if stock_encontrado > 0 else "#dc3545"
                st.markdown(
                    f"""
                    <div style="background-color: {badge_color}; color: white; padding: 12px 18px; border-radius: 8px; font-weight: bold; font-size: 15px; text-align: center; margin-top: 10px;">
                        📦 Stock Disponible ({actual_sheet}): {stock_encontrado} unidades | Gama: {gama_del_equipo} para {equipo_seleccionado}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("---")

            # ==========================================
            # SECCIÓN B: COTIZACIÓN EXACTA
            # ==========================================
            st.markdown("#### Configurar Asignación a Propuesta Ejecutiva")

            col_eq_cfg1, col_eq_cfg2, col_eq_cfg3, col_eq_cfg4 = st.columns(4)

            with col_eq_cfg1:
                linea_tel = st.text_input("N° de Línea / Teléfono", placeholder="999999999", key="eq_lin_sheet_tab3")

            with col_eq_cfg2:
                plan_equipo = st.selectbox("Plan Tarifario Claro", [p["n"] for p in DEFAULT_PLANS_MOVIL], key="eq_plan_sheet_tab3")

            with col_eq_cfg3:
                modalidad_pago = st.selectbox("Modalidad de Pago", ["Cuotas 18 Meses", "Cuotas 12 Meses", "Contado", "Precio Prepago"], key="eq_pago_sheet_tab3")

            with col_eq_cfg4:
                st.markdown("<br>", unsafe_allow_html=True)
                btn_agregar_equipo = st.button("+ Agregar a la Propuesta", type="primary", use_container_width=True, key="btn_add_eq_sheet_tab3")

            plan_obj = next((p for p in DEFAULT_PLANS_MOVIL if p["n"] == plan_equipo), DEFAULT_PLANS_MOVIL[0])
            plan_precio_val = float(plan_obj["p"])

            eq_precio_total = 0.0
            eq_cuota_mes = 0.0
            total_mensual_linea = plan_precio_val

            if equipo_seleccionado and equipo_seleccionado != "-- Selecciona un Equipo --":
                df_target = df_data[df_data[idx_equipo].astype(str).str.strip() == equipo_seleccionado.strip()]

                if not df_target.empty:
                    row_data = df_target.iloc[0]
                    p_offset = get_plan_offset(plan_equipo)

                    # 1. Si es Prepago (Columna D = índice 3)
                    if "PREPAGO" in modalidad_pago.upper():
                        try:
                            eq_precio_total = float(str(row_data[idx_prepago]).replace("S/", "").replace(",", "").strip())
                        except Exception:
                            eq_precio_total = 0.0
                        eq_cuota_mes = eq_precio_total
                        total_mensual_linea = eq_precio_total + plan_precio_val

                    # 2. Si es Contado (Columnas F a O = índices 5 a 14)
                    elif "CONTADO" in modalidad_pago.upper():
                        col_contado_idx = 5 + p_offset
                        try:
                            eq_precio_total = float(str(row_data[col_contado_idx]).replace("S/", "").replace(",", "").strip())
                        except Exception:
                            eq_precio_total = 0.0
                        eq_cuota_mes = eq_precio_total
                        total_mensual_linea = eq_precio_total + plan_precio_val

                    # 3. Si es Cuotas (Columnas P a Y = índices 15 a 24)
                    else:
                        col_cuota_idx = 15 + p_offset
                        try:
                            eq_precio_total = float(str(row_data[col_cuota_idx]).replace("S/", "").replace(",", "").strip())
                        except Exception:
                            eq_precio_total = 0.0

                        plazo_num = 18.0 if "18" in modalidad_pago else 12.0
                        eq_cuota_mes = eq_precio_total / plazo_num if eq_precio_total > 0 else 0.0
                        total_mensual_linea = eq_cuota_mes + plan_precio_val

            str_cuota_desc = f"S/ {eq_cuota_mes:.2f} ({'18 cuotas' if '18' in modalidad_pago else '12 cuotas'})" if "CUOTA" in modalidad_pago.upper() else f"S/ {eq_cuota_mes:.2f}"

            st.info(f"💡 **Terminal:** {equipo_seleccionado} ({gama_del_equipo}) | **Plan:** {plan_equipo} (S/ {plan_precio_val:.2f}) | **Modalidad:** {modalidad_pago} | **Precio Total:** S/ {eq_precio_total:.2f} | **Cuota Mes:** {str_cuota_desc} | **Total Mensual (Equipo + Plan):** S/ {total_mensual_linea:.2f} | **Stock:** {stock_encontrado} unds")

            if btn_agregar_equipo:
                if not equipo_seleccionado or equipo_seleccionado == "-- Selecciona un Equipo --":
                    st.warning("Selecciona primero un equipo de la lista.")
                else:
                    st.session_state.equipment_proposals.append({
                        "id": str(pd.Timestamp.now().timestamp()),
                        "linea": linea_tel if linea_tel else "900000000",
                        "equipo": equipo_seleccionado,
                        "gama": gama_del_equipo,
                        "plan": plan_equipo,
                        "modalidad": modalidad_pago,
                        "precio_total": f"S/ {eq_precio_total:.2f}",
                        "precio_cuota": str_cuota_desc,
                        "suma_val": total_mensual_linea,
                    })
                    st.success(f"¡{equipo_seleccionado} agregado exitosamente a la propuesta!")
                    st.rerun()

            # ==========================================
            # SECCIÓN C: TABLA Y VISTA EJECUTIVA
            # ==========================================
            if st.session_state.equipment_proposals:
                st.markdown("#### Resumen de Equipos Cotizados")

                for idx, eq in enumerate(st.session_state.equipment_proposals):
                    col_item1, col_item2, col_item3, col_item4, col_item5, col_item6 = st.columns([1, 2.5, 3, 2.5, 2.5, 0.8])
                    col_item1.write(f"**#{idx + 1}**")
                    col_item2.write(eq['linea'])
                    col_item3.write(f"{eq['equipo']} ({eq.get('gama', 'SIN GAMA')})")
                    col_item4.write(eq['plan'])
                    col_item5.write(eq['precio_cuota'])
                    if col_item6.button("🗑️", key=f"del_eq_{eq['id']}"):
                        st.session_state.equipment_proposals.pop(idx)
                        st.rerun()

                if st.button("🗑️ Limpiar cotización completa de equipos", key="btn_clear_eq_sheet_tab3"):
                    st.session_state.equipment_proposals = []
                    st.rerun()

                st.markdown("---")
                st.subheader("Vista Ejecutiva - Propuesta de Equipos Móviles")

                rows_eq_html = ""
                total_suma_mensual = 0.0
                for idx, eq in enumerate(st.session_state.equipment_proposals):
                    bg = "#f9f9f9" if idx % 2 == 0 else "#ffffff"
                    s_val = float(eq.get("suma_val", 0.0))
                    total_suma_mensual += s_val
                    gama_str = f" <span style='font-size:9px; background:#e9ecef; padding:2px 4px; border-radius:3px;'>{eq.get('gama', '')}</span>" if eq.get('gama') and eq.get('gama') != 'SIN GAMA' else ""
                    rows_eq_html += f"""
                    <tr style="background-color:{bg}; text-align:center; border-bottom:1px solid #eee;">
                        <td style="padding:6px; border:1px solid #ddd; font-weight:bold;">{idx + 1}</td>
                        <td style="padding:6px; border:1px solid #ddd;">{eq['linea']}</td>
                        <td style="padding:6px; border:1px solid #ddd; text-align:left; padding-left:8px; font-weight:bold;">{eq['equipo']}{gama_str}</td>
                        <td style="padding:6px; border:1px solid #ddd;">{eq['plan']}</td>
                        <td style="padding:6px; border:1px solid #ddd;">{eq['modalidad']}</td>
                        <td style="padding:6px; border:1px solid #ddd; font-weight:bold; color:#1763a5;">{eq['precio_total']}</td>
                        <td style="padding:6px; border:1px solid #ddd; color:#e30613; font-weight:bold;">{eq['precio_cuota']}</td>
                        <td style="padding:6px; border:1px solid #ddd; font-weight:bold;">S/ {s_val:.2f}</td>
                    </tr>
                    """

                empresa_titulo = f"{st.session_state.ruc} · {st.session_state.company}" if (st.session_state.ruc and st.session_state.company) else (st.session_state.ruc or st.session_state.company or "RUC · RAZÓN SOCIAL")

                equipos_html = f"""
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
                    .proposal-title {{ font-size: 16px; font-weight: 900; letter-spacing: 1px; text-align: center; flex-grow: 1; color: #ffffff; }}
                    .badge-dto {{ background-color: #fff1bd !important; color: #e30613; padding: 6px 12px; border-radius: 6px; font-weight: 900; font-size: 11px; text-align: right; }}
                    .proposal-footer {{ display: flex; justify-content: space-between; padding: 6px 12px; background: #e9ecef; font-size: 9px; color: #555; border-top: 1px solid #ccc; }}
                </style>
                </head>
                <body>
                <div class="proposal-container" id="print-section-equipos">
                    <div class="proposal-header">
                        {LOGO_PROPOSAL_HTML}
                        <div class="proposal-title">PROPUESTA EJECUTIVA - EQUIPOS MÓVILES<br><span style="font-size:11px; font-weight:bold; color:#ffffff;">{empresa_titulo}</span></div>
                        <div class="badge-dto">OFERTA DE<br>EQUIPOS</div>
                    </div>
                    <table style="width:100%; border-collapse:collapse; font-size:11px;">
                        <thead>
                            <tr style="background-color:#1763a5 !important; color:white; text-align:center;">
                                <th colspan="5" style="padding:6px; border:1px solid #ddd; background:#151515 !important; color:white;">DETALLE DE ASIGNACIÓN DE EQUIPOS Y PLANES</th>
                                <th style="padding:6px; border:1px solid #ddd; background:#1763a5 !important; color:white;">PRECIO TOTAL</th>
                                <th style="padding:6px; border:1px solid #ddd; background:#e30613 !important; color:white;">EQUIPO / CUOTA</th>
                                <th style="padding:6px; border:1px solid #ddd; background:#1763a5 !important; color:white;">TOTAL MENSUAL</th>
                            </tr>
                            <tr style="background-color:#f4b400 !important; color:#111; font-weight:bold; text-align:center;">
                                <th style="padding:5px; border:1px solid #ddd;">N°</th>
                                <th style="padding:5px; border:1px solid #ddd;">Línea</th>
                                <th style="padding:5px; border:1px solid #ddd;">Modelo / Equipo</th>
                                <th style="padding:5px; border:1px solid #ddd;">Plan Asociado</th>
                                <th style="padding:5px; border:1px solid #ddd;">Modalidad</th>
                                <th style="padding:5px; border:1px solid #ddd; background:#1763a5 !important; color:white;">Precio Total Equipo</th>
                                <th style="padding:5px; border:1px solid #ddd; background:#e30613 !important; color:white;">Precio / Cuota Mes</th>
                                <th style="padding:5px; border:1px solid #ddd; background:#1763a5 !important; color:white;">Cuota + Plan</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_eq_html}
                        </tbody>
                    </table>
                    <div style="display:flex; justify-content:space-between; padding:12px; background:#f4f5f7 !important; align-items:flex-start; border-top:1px solid #ddd;">
                        <div style="width:58%; background:white; padding:10px; border-radius:6px; border:1px solid #ddd;">
                            <strong style="font-size:11px; color:#111;">CONDICIONES COMERCIALES DE EQUIPOS</strong>
                            <ul style="margin:4px 0 0 15px; padding:0; font-size:10px; color:#444; line-height:1.4;">
                                <li>Precios sujetos a evaluación crediticia y stock disponible al momento de la aprobación.</li>
                                <li>Garantía oficial de fábrica aplicable a todos los terminales móviles corporativos.</li>
                                <li>Soporte técnico y atención preferencial para empresas 24/7.</li>
                            </ul>
                        </div>
                        <div style="width:38%; display:flex; flex-direction:column; gap:4px;">
                            <div style="display:flex; justify-content:space-between; background:#e30613 !important; color:white; padding:8px 10px; border-radius:4px; font-size:12px; font-weight:900;">
                                <span>TOTAL MENSUAL (EQUIPO + PLAN)</span><span>S/ {total_suma_mensual:.2f}</span>
                            </div>
                        </div>
                    </div>
                    <div class="proposal-footer">
                        <span>Catálogo Oficial de Terminales Móviles Claro Empresas</span>
                        <span>Desarrollado por: <strong>JHONNIER VARELA</strong></span>
                    </div>
                </div>
                <div class="no-print" style="text-align: center; margin-top: 15px; display: flex; justify-content: center; gap: 15px;">
                    <button onclick="downloadImageEquipos()" style="background-color:#1763a5; color:white; border:none; padding:10px 20px; border-radius:8px; font-weight:bold; font-size:14px; cursor:pointer;">🖼️ Descargar como Imagen (PNG)</button>
                    <button onclick="window.print()" style="background-color:#e30613; color:white; border:none; padding:10px 20px; border-radius:8px; font-weight:bold; font-size:14px; cursor:pointer;">🖨️ Guardar como PDF</button>
                </div>
                <script>
                    function downloadImageEquipos() {{
                        const element = document.getElementById("print-section-equipos");
                        html2canvas(element, {{ scale: 2, useCORS: true }}).then(canvas => {{
                            const link = document.createElement('a');
                            link.download = 'Propuesta_Equipos_Claro.png';
                            link.href = canvas.toDataURL('image/png');
                            link.click();
                        }});
                    }}
                </script>
                </body>
                </html>
                """

                components.html(equipos_html, height=360 + (len(st.session_state.equipment_proposals) * 35), scrolling=False)

        except Exception as e:
            st.error(f"Error al procesar el archivo consolidado: {e}")
    else:
        st.info("👆 Carga tu archivo consolidado (`Cotizacion_Equipo_Movil_Junio V1.1.xlsm` o `.xlsx`) mediante el botón superior para consultar stock y cotizar.")

# --- FOOTER ---
st.markdown(
    """
    <div class="footer-bar">
        Matriz Comercial y Propuesta Ejecutiva Claro Empresas &copy; 2026 | Desarrollado por: <strong>JHONNIER VARELA</strong>
    </div>
    """,
    unsafe_allow_html=True,
)