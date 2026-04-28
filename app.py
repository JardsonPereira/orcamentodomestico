import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import os

# --- 1. CONFIGURAÇÃO DO LINK DA LOGO (Link Direto do seu GitHub) ---
# Substitua pelo seu usuário real do GitHub
USUARIO_GITHUB = "JardsonPereira" 
REPO_GITHUB = "orcamentodomestico"
URL_LOGO = f"https://raw.githubusercontent.com/{USUARIO_GITHUB}/{REPO_GITHUB}/main/logo.png"

# --- 2. CONEXÃO SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Erro nas credenciais.")
    st.stop()

# --- 3. CONFIGURAÇÃO DA PÁGINA ---
def main():
    # O set_page_config precisa ser o primeiro
    st.set_page_config(
        page_title="ContabilApp Pro",
        layout="wide",
        page_icon=URL_LOGO
    )

    # 4. INJEÇÃO DE CÓDIGO PARA "FORÇAR" O NAVEGADOR
    # Este bloco tenta sobrescrever o comportamento do Streamlit Cloud
    st.markdown(f"""
        <script>
            // Tenta mudar o título da aba e o ícone via JavaScript após o carregamento
            window.onload = function() {{
                var link = document.querySelector("link[rel*='icon']") || document.createElement('link');
                link.type = 'image/png';
                link.rel = 'shortcut icon';
                link.href = '{URL_LOGO}';
                document.getElementsByTagName('head')[0].appendChild(link);
                
                // Força o título para o PWA
                document.title = "ContabilApp Pro";
            }}
        </script>
        
        <head>
            <link rel="icon" type="image/png" href="{URL_LOGO}">
            <link rel="apple-touch-icon" sizes="180x180" href="{URL_LOGO}">
            <meta name="mobile-web-app-capable" content="yes">
            <meta name="apple-mobile-web-app-capable" content="yes">
            <meta name="apple-mobile-web-app-title" content="ContabilApp Pro">
            <meta name="application-name" content="ContabilApp Pro">
            <meta name="theme-color" content="#007BFF">
        </head>
        
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
            html, body, [class*="st-"] {{ font-family: 'Inter', sans-serif; }}
            .stApp {{ background-color: #F0F2F5; }}
            .stButton>button {{ width: 100%; border-radius: 10px; height: 3.2em; font-weight: 600; background-color: #007BFF; color: white; }}
        </style>
    """, unsafe_allow_html=True)

    # --- INTERFACE DE LOGIN ---
    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        st.image(URL_LOGO, width=120)
        st.markdown("<h1 style='text-align: center;'>💰 ContabilApp Pro</h1>", unsafe_allow_html=True)
        
        email = st.text_input("E-mail").strip()
        senha = st.text_input("Senha", type="password")
        
        if st.button("ACESSAR"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                if res.user:
                    st.session_state.logado = True
                    st.rerun()
            except:
                st.error("Credenciais inválidas.")
    else:
        st.success("Logado com sucesso!")
        if st.button("Sair"):
            st.session_state.logado = False
            st.rerun()

if __name__ == "__main__":
    main()
