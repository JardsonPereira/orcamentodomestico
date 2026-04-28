import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import calendar
import base64
import os

# --- CONFIGURAÇÃO EXATA DO NOME ---
# O nome deve ser idêntico ao que aparece no seu GitHub
NOME_ARQUIVO_LOGO = "orçamento doméstico.png"

def get_base64_img(img_path):
    """Converte a imagem local para Base64 para garantir o ícone no telemóvel"""
    try:
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            return f"data:image/png;base64,{data}"
    except Exception as e:
        return None
    return None

# --- CONEXÃO SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Erro nas credenciais do Supabase.")
    st.stop()

# --- ESTADO DA SESSÃO ---
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
    # 1. Tenta obter os dados da logo
    logo_base64 = get_base64_img(NOME_ARQUIVO_LOGO)
    
    # 2. Configuração inicial (Obrigatório ser o primeiro comando Streamlit)
    st.set_page_config(
        page_title="ContabilApp Pro",
        layout="wide",
        page_icon=NOME_ARQUIVO_LOGO if os.path.exists(NOME_ARQUIVO_LOGO) else "💰"
    )

    # 3. Metadados para ícone de Telemóvel e CSS Personalizado
    if logo_base64:
        st.markdown(f"""
            <head>
                <link rel="apple-touch-icon" href="{logo_base64}">
                <link rel="icon" sizes="192x192" href="{logo_base64}">
            </head>
        """, unsafe_allow_html=True)

    st.markdown(f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
            html, body, [class*="st-"] {{ font-family: 'Inter', sans-serif; }}
            .stApp {{ background-color: #F0F2F5; }}
            .stButton>button {{ width: 100%; border-radius: 10px; height: 3.2em; font-weight: 600; background-color: #007BFF; color: white; }}
            [data-testid="stExpander"], div[data-testid="stForm"], .stContainer {{ 
                background: white; border-radius: 12px; border: 1px solid #eee; padding: 15px; margin-bottom: 10px;
            }}
        </style>
    """, unsafe_allow_html=True)

    if not st.session_state.logado:
        # Mostra a logo no topo da tela de login para validar
        if os.path.exists(NOME_ARQUIVO_LOGO):
            st.image(NOME_ARQUIVO_LOGO, width=120)
        
        st.markdown("<h1 style='text-align: center;'>💰 ContabilApp Pro</h1>", unsafe_allow_html=True)
        
        _, col_central, _ = st.columns([1, 2, 1])
        with col_central:
            escolha = st.radio("Acesso", ["Entrar", "Criar Conta"], horizontal=True)
            
            if escolha == "Entrar":
                email = st.text_input("E-mail").strip()
                senha = st.text_input("Senha", type="password")
                if st.button("ACESSAR"):
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        if res.user:
                            st.session_state.logado = True
                            st.session_state.user_email = email
                            st.rerun()
                    except:
                        st.error("Falha no login.")
            else:
                nome = st.text_input("Nome")
                email_n = st.text_input("E-mail ")
                senha_n = st.text_input("Senha ", type="password")
                if st.button("CADASTRAR"):
                    try:
                        supabase.auth.sign_up({"email": email_n, "password": senha_n})
                        st.success("Conta criada! Verifique o e-mail.")
                    except Exception as e:
                        st.error(f"Erro: {e}")

    else:
        st.title(f"Olá, {st.session_state.user_name}")
        if st.button("Sair"):
            st.session_state.logado = False
            st.rerun()

if __name__ == "__main__":
    main()
