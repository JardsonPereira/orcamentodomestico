import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import calendar
import base64
import os
import json

# --- CONFIGURAÇÃO DA LOGO ---
# Certifique-se de que o arquivo se chama logo.png no seu GitHub
ARQUIVO_LOGO = "logo.png"

def get_base64_img(img_path):
    try:
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            return f"data:image/png;base64,{data}"
    except:
        return None
    return None

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
if "user_name" not in st.session_state: st.session_state.user_name = "Usuário"
if "user_email" not in st.session_state: st.session_state.user_email = ""

def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)

def main():
    logo_data = get_base64_img(ARQUIVO_LOGO)
    
    # 1. SET_PAGE_CONFIG (Obrigatório ser o primeiro)
    st.set_page_config(
        page_title="ContabilApp Pro",
        layout="wide",
        page_icon=ARQUIVO_LOGO if os.path.exists(ARQUIVO_LOGO) else "💰"
    )

    # 2. INJEÇÃO DE CABEÇALHO "AGRESSIVA"
    # Aqui forçamos o navegador a ler o ícone antes do manifesto do Streamlit
    if logo_data:
        st.markdown(f"""
            <head>
                <link rel="icon" type="image/png" href="{logo_data}">
                <link rel="apple-touch-icon" sizes="180x180" href="{logo_data}">
                <link rel="shortcut icon" href="{logo_data}">
                <meta name="mobile-web-app-capable" content="yes">
                <meta name="apple-mobile-web-app-capable" content="yes">
                <meta name="apple-mobile-web-app-title" content="ContabilApp Pro">
                <meta name="application-name" content="ContabilApp Pro">
                <meta name="msapplication-TileImage" content="{logo_data}">
            </head>
        """, unsafe_allow_html=True)

    # --- CSS ---
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
            html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
            .stApp { background-color: #F0F2F5; }
            .stButton>button { width: 100%; border-radius: 10px; height: 3.2em; font-weight: 600; background-color: #007BFF; color: white; }
            [data-testid="stExpander"], div[data-testid="stForm"], .stContainer { 
                background: white; border-radius: 12px; border: 1px solid #eee; padding: 15px; margin-bottom: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

    if not st.session_state.logado:
        if os.path.exists(ARQUIVO_LOGO):
            _, col_logo, _ = st.columns([1, 1, 1])
            col_logo.image(ARQUIVO_LOGO, width=150)
        
        st.markdown("<h1 style='text-align: center;'>💰 ContabilApp Pro</h1>", unsafe_allow_html=True)
        
        _, col_central, _ = st.columns([1, 2, 1])
        with col_central:
            escolha = st.radio("Acesso", ["Entrar na Conta", "Criar Nova Conta"], horizontal=True, label_visibility="collapsed")
            
            with st.container():
                if escolha == "Entrar na Conta":
                    st.subheader("Login")
                    email_login = st.text_input("E-mail", key="login_email").strip()
                    senha_login = st.text_input("Senha", type='password', key="login_pass")
                    
                    if st.button("ACESSAR SISTEMA"):
                        try:
                            response = supabase.auth.sign_in_with_password({"email": email_login, "password": senha_login})
                            if response.user:
                                st.session_state.logado = True
                                st.session_state.user_email = email_login
                                st.rerun()
                        except:
                            st.error("E-mail ou senha incorretos.")
                            
                elif escolha == "Criar Nova Conta":
                    st.subheader("Cadastro")
                    novo_nome = st.text_input("Seu Nome")
                    novo_email = st.text_input("E-mail").strip()
                    nova_senha = st.text_input("Crie uma senha", type='password')
                    
                    if st.button("CRIAR MINHA CONTA"):
                        try:
                            res = supabase.auth.sign_up({"email": novo_email, "password": nova_senha})
                            if res.user:
                                st.session_state.user_name = novo_nome
                                st.success("Conta criada! Por favor, faça o login.")
                        except Exception as e:
                            st.error(f"Erro ao cadastrar: {str(e)}")
    else:
        # ÁREA LOGADA
        col_title, col_user = st.columns([3, 1])
        with col_title:
            st.title(f"Olá, {st.session_state.get('user_name', 'Usuário')}")
        if st.button("Sair"):
            st.session_state.logado = False
            st.rerun()

        # DADOS
        try:
            res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
            df = pd.DataFrame(res_f.data)
            tab1, tab2 = st.tabs(["Lançamentos", "Extrato"])
            with tab1:
                st.info("Pronto para lançar.")
            with tab2:
                if not df.empty:
                    st.dataframe(df, use_container_width=True)
        except:
            st.error("Erro ao carregar dados.")

if __name__ == "__main__":
    main()
