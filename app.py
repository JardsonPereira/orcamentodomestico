import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import calendar
import os

# --- CONFIGURAÇÃO DA LOGO ---
# Substitua SEU_USUARIO_GITHUB pelo seu nome de usuário real
GITHUB_USER = "JardsonPereira" 
NOME_REPO = "orcamentodomestico"
LINK_LOGO = f"https://raw.githubusercontent.com/{GITHUB_USER}/{NOME_REPO}/main/logo.png"

# --- CONEXÃO SEGURA ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Erro nas credenciais do Supabase.")
    st.stop()

# --- INICIALIZAÇÃO DO STATE ---
if "logado" not in st.session_state: st.session_state.logado = False
if "user_email" not in st.session_state: st.session_state.user_email = ""

def main():
    # 1. SET_PAGE_CONFIG
    st.set_page_config(
        page_title="ContabilApp V2",
        layout="wide",
        page_icon=LINK_LOGO # Usando o link direto aqui também
    )

    # 2. INJEÇÃO DE CABEÇALHO PARA FORÇAR A LOGO
    # Usamos o link direto do GitHub porque o celular confia mais em URLs HTTPS
    st.markdown(f"""
        <head>
            <link rel="icon" type="image/png" href="{LINK_LOGO}">
            <link rel="apple-touch-icon" href="{LINK_LOGO}">
            <link rel="shortcut icon" href="{LINK_LOGO}">
            <meta name="apple-mobile-web-app-title" content="ContabilApp Pro">
            <meta name="application-name" content="ContabilApp Pro">
        </head>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
            html, body, [class*="st-"] {{ font-family: 'Inter', sans-serif; }}
            .stApp {{ background-color: #F0F2F5; }}
            .stButton>button {{ width: 100%; border-radius: 10px; height: 3.2em; font-weight: 600; background-color: #007BFF; color: white; }}
        </style>
    """, unsafe_allow_html=True)

    if not st.session_state.logado:
        # Mostra a logo para confirmar que o link está funcionando
        st.image(LINK_LOGO, width=120)
        
        st.markdown("<h1 style='text-align: center;'>💰 ContabilApp Pro</h1>", unsafe_allow_html=True)
        
        _, col_central, _ = st.columns([1, 2, 1])
        with col_central:
            escolha = st.radio("Acesso", ["Entrar na Conta", "Criar Nova Conta"], horizontal=True, label_visibility="collapsed")
            
            if escolha == "Entrar na Conta":
                email_login = st.text_input("E-mail", key="email_log").strip()
                senha_login = st.text_input("Senha", type='password', key="pass_log")
                if st.button("ACESSAR SISTEMA"):
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email_login, "password": senha_login})
                        if res.user:
                            st.session_state.logado = True
                            st.session_state.user_email = email_login
                            st.rerun()
                    except:
                        st.error("E-mail ou senha incorretos.")
            else:
                novo_email = st.text_input("E-mail para cadastro").strip()
                nova_senha = st.text_input("Senha para cadastro", type='password')
                if st.button("CADASTRAR"):
                    try:
                        supabase.auth.sign_up({"email": novo_email, "password": nova_senha})
                        st.success("Conta criada! Verifique o e-mail.")
                    except Exception as e:
                        st.error(f"Erro: {e}")
    else:
        st.title(f"Olá, {st.session_state.user_email}")
        if st.button("Sair"):
            st.session_state.logado = False
            st.rerun()

if __name__ == "__main__":
    main()
