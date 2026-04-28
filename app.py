import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import calendar
import base64
import os
import json

# --- CONFIGURAÇÕES DE ARQUIVOS ---
# Certifique-se de que o arquivo no GitHub se chama exatamente logo.png
ARQUIVO_LOGO = "logo.png"

# --- FUNÇÃO PARA CONVERTER LOGO E MANIFESTO ---
def get_base64_img(img_path):
    try:
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            return f"data:image/png;base64,{data}"
    except:
        return None
    return None

def get_manifest_data_uri(logo_base64):
    manifest_dict = {
        "name": "ContabilApp Pro",
        "short_name": "ContabilApp",
        "start_url": ".",
        "display": "standalone",
        "background_color": "#F0F2F5",
        "theme_color": "#007BFF",
        "icons": [
            {"src": logo_base64, "sizes": "192x192", "type": "image/png"},
            {"src": logo_base64, "sizes": "512x512", "type": "image/png"}
        ]
    }
    manifest_json = json.dumps(manifest_dict)
    manifest_base64 = base64.b64encode(manifest_json.encode()).decode()
    return f"data:application/json;base64,{manifest_base64}"

# --- CONEXÃO SEGURA ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Erro nas credenciais.")
    st.stop()

# --- INICIALIZAÇÃO DO STATE ---
if "logado" not in st.session_state: st.session_state.logado = False
if "user_email" not in st.session_state: st.session_state.user_email = ""

def main():
    logo_data = get_base64_img(ARQUIVO_LOGO)
    
    # 1. SET_PAGE_CONFIG
    st.set_page_config(
        page_title="ContabilApp Pro",
        layout="wide",
        page_icon=ARQUIVO_LOGO if os.path.exists(ARQUIVO_LOGO) else "💰"
    )

    # 2. INJEÇÃO BLINDADA DE MANIFESTO (Força o ícone e nome no celular)
    if logo_data:
        manifest_uri = get_manifest_data_uri(logo_data)
        st.markdown(f"""
            <head>
                <link rel="manifest" href="{manifest_uri}">
                <link rel="apple-touch-icon" href="{logo_data}">
                <meta name="apple-mobile-web-app-title" content="ContabilApp Pro">
                <meta name="application-name" content="ContabilApp Pro">
                <meta name="apple-mobile-web-app-capable" content="yes">
            </head>
        """, unsafe_allow_html=True)

    # --- CSS E INTERFACE ---
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
            html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
            .stApp { background-color: #F0F2F5; }
            .stButton>button { width: 100%; border-radius: 10px; height: 3.2em; font-weight: 600; background-color: #007BFF; color: white; }
        </style>
    """, unsafe_allow_html=True)

    if not st.session_state.logado:
        if os.path.exists(ARQUIVO_LOGO):
            _, col_logo, _ = st.columns([1, 1, 1])
            col_logo.image(ARQUIVO_LOGO, width=150)
        
        st.markdown("<h1 style='text-align: center;'>💰 ContabilApp Pro</h1>", unsafe_allow_html=True)
        # ... Lógica de Login (Entrar/Criar Conta) ...
        # (Coloque aqui o seu código de login anterior)
        st.write("---")
        st.info("Para instalar, aguarde a logo carregar no topo e use o menu do navegador.")

if __name__ == "__main__":
    main()
