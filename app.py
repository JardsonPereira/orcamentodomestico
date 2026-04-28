import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import calendar

# --- CONFIGURAÇÃO DA LOGO ---
USUARIO_GITHUB = "JardsonPereira" 
REPO_GITHUB = "orcamentodomestico"
URL_LOGO = f"https://raw.githubusercontent.com/{USUARIO_GITHUB}/{REPO_GITHUB}/main/logo.png"

# --- CONEXÃO SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Erro nas credenciais do Supabase nos Secrets.")
    st.stop()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="ContabilApp Pro", layout="wide", page_icon=URL_LOGO)

# --- CSS CUSTOMIZADO ---
st.markdown(f"""
    <style>
        .stMetric {{ background: white; padding: 20px; border-radius: 10px; border: 1px solid #eee; }}
        .stButton>button {{ width: 100%; border-radius: 10px; font-weight: 600; }}
    </style>
""", unsafe_allow_html=True)

# --- ESTADOS DE SESSÃO ---
if "logado" not in st.session_state: st.session_state.logado = False
if "user_email" not in st.session_state: st.session_state.user_email = ""

def main():
    if not st.session_state.logado:
        # --- TELA DE LOGIN (Simplificada para o exemplo, mantenha a sua lógica anterior) ---
        _, col_logo, _ = st.columns([1, 1, 1])
        with col_logo: st.image(URL_LOGO, width=150)
        
        st.markdown("<h1 style='text-align: center;'>💰 ContabilApp Pro</h1>", unsafe_allow_html=True)
        col_login, _ = st.columns([1, 1]) # Centralize conforme seu layout
        
        with st.container():
            email_login = st.text_input("E-mail")
            senha_login = st.text_input("Senha", type='password')
            if st.button("ACESSAR SISTEMA"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email_login, "password": senha_login})
                    if res.user:
                        st.session_state.logado = True
                        st.session_state.user_email = email_login
                        st.rerun()
                except: st.error("Erro no login.")
    else:
        # --- AREA LOGADA ---
        st.sidebar.image(URL_LOGO, width=100)
        st.sidebar.title(f"Olá, {st.session_state.user_email.split('@')[0]}")
        
        if st.sidebar.button("Encerrar Sessão"):
            st.session_state.logado = False
            st.rerun()

        tabs = st.tabs(["📊 Dashboards", "➕ Novos Lançamentos"])

        # --- TAB 1: DASHBOARD ---
        with tabs[0]:
            st.subheader("Resumo Financeiro")
            
            # Filtros
            col_f1, col_f2 = st.columns(2)
            ano_sel = col_f1.selectbox("Ano", [2024, 2025, 2026], index=1)
            mes_sel = col_f2.selectbox("Mês", list(calendar.month_name)[1:], index=datetime.now().month-1)
            mes_num = list(calendar.month_name).index(mes_sel)

            # Buscar Dados
            res = supabase.table("transacoes").select("*").eq("email", st.session_state.user_email).execute()
            df = pd.DataFrame(res.data)

            if not df.empty:
                df['data'] = pd.to_datetime(df['data'])
                df_filtrado = df[(df['data'].dt.month == mes_num) & (df['data'].dt.year == ano_sel)]

                # Métricas
                receitas = df_filtrado[df_filtrado['tipo'] == 'Receita']['valor'].sum()
                despesas = df_filtrado[df_filtrado['tipo'] == 'Despesa']['valor'].sum()
                saldo = receitas - despesas

                m1, m2, m3 = st.columns(3)
                m1.metric("Receitas", f"R$ {receitas:,.2f}", delta_color="normal")
                m2.metric("Despesas", f"R$ {despesas:,.2f}", delta_color="inverse")
                m3.metric("Saldo Mensal", f"R$ {saldo:,.2f}")

                st.divider()
                st.subheader("Lista de Lançamentos")
                st.dataframe(df_filtrado[['data', 'descricao', 'categoria', 'tipo', 'valor']], use_container_width=True)
            else:
                st.info("Nenhum dado encontrado para este período.")

        # --- TAB 2: LANÇAMENTOS ---
        with tabs[1]:
            st.subheader("Cadastrar Nova Movimentação")
            with st.form("form_registro", clear_on_submit=True):
                col1, col2 = st.columns(2)
                desc = col1.text_input("Descrição (Ex: Salário, Aluguel)")
                valor = col2.number_input("Valor (R$)", min_value=0.0, step=0.01)
                
                col3, col4, col5 = st.columns(3)
                tipo = col3.selectbox("Tipo", ["Receita", "Despesa"])
                cat = col4.selectbox("Categoria", ["Lazer", "Alimentação", "Trabalho", "Saúde", "Outros"])
                data_lanc = col5.date_input("Data", datetime.now())

                if st.form_submit_button("SALVAR LANÇAMENTO"):
                    if desc and valor > 0:
                        dados = {
                            "email": st.session_state.user_email,
                            "descricao": desc,
                            "valor": valor,
                            "tipo": tipo,
                            "categoria": cat,
                            "data": str(data_lanc)
                        }
                        try:
                            supabase.table("transacoes").insert(dados).execute()
                            st.success("Lançamento salvo com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                    else:
                        st.warning("Preencha todos os campos corretamente.")

if __name__ == "__main__":
    main()
