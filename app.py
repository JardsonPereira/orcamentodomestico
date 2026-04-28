import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import calendar
import base64
import os

# --- CONFIGURAÇÕES DE ARQUIVOS ---
ARQUIVO_LOGO = "logo.png"

# --- CONEXÃO SEGURA ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Erro nas credenciais. Verifique os Secrets.")
    st.stop()

# --- FUNÇÕES DE SUPORTE ---
def get_base64_img(img_path):
    try:
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            return f"data:image/png;base64,{data}"
    except:
        return None
    return None

def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)

# --- INICIALIZAÇÃO DO STATE ---
if "logado" not in st.session_state:
    st.session_state.logado = False
if "user_name" not in st.session_state:
    st.session_state.user_name = "Usuário"
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

def main():
    logo_data = get_base64_img(ARQUIVO_LOGO)

    # 1. SET_PAGE_CONFIG (Sempre o primeiro comando)
    st.set_page_config(
        page_title="ContabilApp Pro",
        layout="wide",
        page_icon=ARQUIVO_LOGO if os.path.exists(ARQUIVO_LOGO) else "💰"
    )

    # 2. INJEÇÃO DE MANIFESTO E METADADOS (Resolve o ícone na instalação)
    st.markdown(f"""
        <head>
            <link rel="manifest" href="./manifest.json">
            <link rel="apple-touch-icon" href="{logo_data}">
            <meta name="mobile-web-app-capable" content="yes">
            <meta name="apple-mobile-web-app-title" content="ContabilApp">
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

    if not st.session_state.logado:
        # Exibe a logo no topo da tela de login
        if os.path.exists(ARQUIVO_LOGO):
            _, col_logo, _ = st.columns([1, 1, 1])
            with col_logo:
                st.image(ARQUIVO_LOGO, width=150)
        
        st.markdown("<h1 style='text-align: center;'>💰 ContabilApp Pro</h1>", unsafe_allow_html=True)
        
        _, col_central, _ = st.columns([1, 2, 1])
        with col_central:
            escolha = st.radio("Acesso", ["Entrar na Conta", "Criar Nova Conta"], horizontal=True, label_visibility="collapsed")
            
            with st.container():
                if escolha == "Entrar na Conta":
                    st.subheader("Login")
                    email_login = st.text_input("E-mail", placeholder="seu@email.com").strip()
                    senha_login = st.text_input("Senha", type='password')
                    
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
                                st.success("Conta criada! Agora faça o login.")
                        except Exception as e:
                            st.error(f"Erro ao cadastrar: {str(e)}")

    else:
        # --- SISTEMA LOGADO ---
        col_title, col_user = st.columns([3, 1])
        with col_title:
            st.title(f"💰 Olá, {st.session_state.get('user_name', 'Usuário')}")
        with col_user:
            if st.button("Encerrar Sessão"):
                st.session_state.logado = False
                st.rerun()

        # TABELAS E DADOS (Resumo)
        try:
            res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
            df = pd.DataFrame(res_f.data)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Bem-vindo! Comece lançando seus dados.")
        except:
            st.error("Erro ao conectar aos dados.")

if __name__ == "__main__":
    main()
