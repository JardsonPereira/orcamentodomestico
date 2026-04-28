import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import calendar

# --- CONFIGURAÇÃO DA LOGO ---
# Substitua pelo link direto da sua imagem (PNG ou JPG)
# Dica: Use uma imagem quadrada para não cortar no celular.
LOGO_URL = "https://gemini.google.com/app/6ee3948b9b1aae33?hl=pt-BR" 

# --- CONEXÃO SEGURA ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Erro nas credenciais. Verifique os Secrets.")
    st.stop()

# --- INICIALIZAÇÃO DO STATE ---
if "logado" not in st.session_state:
    st.session_state.logado = False
if "user_name" not in st.session_state:
    st.session_state.user_name = "Usuário"
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)

def main():
    # ALTERAÇÃO 1: Definindo o page_icon com a sua logo
    st.set_page_config(
        page_title="ContabilApp Pro", 
        layout="wide", 
        page_icon=LOGO_URL  # Aqui entra a sua logo
    )
    
    # ALTERAÇÃO 2: Injetando HTML para reconhecimento de ícone no celular (iOS e Android)
    st.markdown(f"""
        <head>
            <link rel="apple-touch-icon" href="{LOGO_URL}">
            <link rel="icon" sizes="192x192" href="{LOGO_URL}">
        </head>
    """, unsafe_allow_html=True)

    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
        .stApp { background-color: #F0F2F5; }
        .stButton>button { width: 100%; border-radius: 10px; height: 3.2em; font-weight: 600; }
        [data-testid="stExpander"], div[data-testid="stForm"], .stContainer { 
            background: white; border-radius: 12px; border: 1px solid #eee; padding: 15px; margin-bottom: 10px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # ... (Restante do seu código permanece igual)
    if not st.session_state.logado:
        st.markdown("<h1 style='text-align: center;'>💰 ContabilApp Pro</h1>", unsafe_allow_html=True)
        # ... continuação do código
