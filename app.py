import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import calendar
import os

# --- 1. CONFIGURAÇÃO DA LOGO (Link Direto do GitHub) ---
# Substitui pelo teu utilizador e repositório reais
USUARIO_GITHUB = "JardsonPereira" 
REPO_GITHUB = "orcamentodomestico"
URL_LOGO = f"https://raw.githubusercontent.com/{USUARIO_GITHUB}/{REPO_GITHUB}/main/logo.png"

# --- 2. CONEXÃO SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Erro nas credenciais do Supabase nos Secrets.")
    st.stop()

# --- 3. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="ContabilApp Pro",
    layout="wide",
    page_icon=URL_LOGO
)

# --- 4. INJEÇÃO DE CABEÇALHO PARA O ÍCONE ---
st.markdown(f"""
    <head>
        <link rel="icon" type="image/png" href="{URL_LOGO}">
        <link rel="apple-touch-icon" sizes="180x180" href="{URL_LOGO}">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-title" content="ContabilApp Pro">
    </head>
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

# --- 5. LÓGICA DE LOGIN / CADASTRO ---
if "logado" not in st.session_state:
    st.session_state.logado = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

def main():
    if not st.session_state.logado:
        # Exibição da Logo
        _, col_logo, _ = st.columns([1, 1, 1])
        with col_logo:
            st.image(URL_LOGO, width=150)
        
        st.markdown("<h1 style='text-align: center;'>💰 ContabilApp Pro</h1>", unsafe_allow_html=True)
        
        _, col_central, _ = st.columns([1, 2, 1])
        with col_central:
            # Menu de Opções
            escolha = st.radio(
                "Acesso", 
                ["Entrar na Conta", "Criar Nova Conta", "Recuperar Senha"], 
                horizontal=True, 
                label_visibility="collapsed"
            )
            
            with st.container():
                if escolha == "Entrar na Conta":
                    st.subheader("Login")
                    email_login = st.text_input("E-mail", key="l_email").strip()
                    senha_login = st.text_input("Senha", type='password', key="l_pass")
                    if st.button("ACESSAR SISTEMA"):
                        try:
                            res = supabase.auth.sign_in_with_password({"email": email_login, "password": senha_login})
                            if res.user:
                                st.session_state.logado = True
                                st.session_state.user_email = email_login
                                st.rerun()
                        except:
                            st.error("E-mail ou senha incorretos.")
                            
                elif escolha == "Criar Nova Conta":
                    st.subheader("Cadastro")
                    novo_nome = st.text_input("Nome Completo")
                    novo_email = st.text_input("E-mail para cadastro").strip()
                    nova_senha = st.text_input("Defina uma senha", type='password')
                    if st.button("FINALIZAR CADASTRO"):
                        try:
                            res = supabase.auth.sign_up({"email": novo_email, "password": nova_senha})
                            if res.user:
                                st.success("Conta criada! Confirme o seu e-mail e faça login.")
                        except Exception as e:
                            st.error(f"Erro ao cadastrar: {e}")
                
                elif escolha == "Recuperar Senha":
                    st.subheader("Recuperação")
                    email_rec = st.text_input("E-mail registado").strip()
                    if st.button("ENVIAR LINK DE REDEFINIÇÃO"):
                        try:
                            supabase.auth.reset_password_for_email(email_rec)
                            st.info("Se o e-mail existir, receberá um link em breve.")
                        except:
                            st.error("Erro ao processar pedido.")

    else:
        # --- ÁREA DO SISTEMA (LOGADO) ---
        st.title(f"Bem-vindo, {st.session_state.user_email}")
        
        if st.sidebar.button("Encerrar Sessão"):
            st.session_state.logado = False
            st.rerun()
            
        t1, t2 = st.tabs(["📊 Dashboards", "➕ Novos Lançamentos"])
        with t1:
            st.write("Dados do sistema...")

if __name__ == "__main__":
    main()
