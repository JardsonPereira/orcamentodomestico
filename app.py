import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import calendar

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="ContabilApp Pro", layout="wide")

# --- CONEXÃO SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("Erro nas credenciais do Supabase. Verifique o secrets do Streamlit.")
        return None

supabase = init_connection()

# --- ESTADOS DE SESSÃO ---
if "logado" not in st.session_state:
    st.session_state.logado = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

# --- FUNÇÕES DE DADOS ---
def buscar_dados():
    try:
        # Busca apenas os dados do usuário logado
        res = supabase.table("transacoes").select("*").eq("email", st.session_state.user_email).execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        # Retorna dataframe vazio em caso de erro para não quebrar o app
        st.sidebar.warning("Aguardando dados ou erro de conexão...")
        return pd.DataFrame()

# --- INTERFACE ---
def main():
    if not st.session_state.logado:
        st.title("💰 ContabilApp Pro")
        col1, _ = st.columns([1, 1.5])
        with col1:
            aba_login, aba_cad = st.tabs(["Login", "Cadastrar"])
            
            with aba_login:
                email = st.text_input("Email", key="login_email")
                senha = st.text_input("Senha", type="password", key="login_pw")
                if st.button("Entrar"):
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        if res.user:
                            st.session_state.logado = True
                            st.session_state.user_email = email
                            st.rerun()
                    except: st.error("Email ou senha inválidos.")

            with aba_cad:
                n_email = st.text_input("Email", key="cad_email")
                n_senha = st.text_input("Senha", type="password", key="cad_pw")
                if st.button("Criar Conta"):
                    try:
                        supabase.auth.sign_up({"email": n_email, "password": n_senha})
                        st.success("Verifique seu email para confirmar o cadastro!")
                    except Exception as e: st.error(f"Erro: {e}")

    else:
        # --- ÁREA LOGADA ---
        st.sidebar.title(f"Olá, {st.session_state.user_email.split('@')[0]}")
        if st.sidebar.button("Sair"):
            st.session_state.logado = False
            st.rerun()

        tab1, tab2 = st.tabs(["📊 Dashboard", "➕ Novo Lançamento"])

        # ABA DASHBOARD
        with tab1:
            df = buscar_dados()
            
            # Filtros de Mês/Ano
            hoje = datetime.now()
            c1, c2 = st.columns(2)
            ano = c1.selectbox("Ano", [2024, 2025, 2026], index=1)
            mes_nome = c2.selectbox("Mês", list(calendar.month_name)[1:], index=hoje.month-1)
            mes_num = list(calendar.month_name).index(mes_nome)

            if not df.empty:
                df['data'] = pd.to_datetime(df['data'])
                df_filtro = df[(df['data'].dt.month == mes_num) & (df['data'].dt.year == ano)]
                
                # Métricas
                rec = df_filtro[df_filtro['tipo'] == 'Receita']['valor'].sum()
                des = df_filtro[df_filtro['tipo'] == 'Despesa']['valor'].sum()
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Receitas", f"R$ {rec:,.2f}")
                m2.metric("Despesas", f"R$ {des:,.2f}", delta_color="inverse")
                m3.metric("Saldo", f"R$ {rec - des:,.2f}")

                st.subheader("Lista de Transações")
                st.dataframe(df_filtro[['data', 'descricao', 'categoria', 'tipo', 'valor']], use_container_width=True)
            else:
                st.info("Nenhum dado encontrado para o período selecionado.")

        # ABA LANÇAMENTOS
        with tab2:
            with st.form("add_transacao", clear_on_submit=True):
                st.subheader("Cadastrar Movimentação")
                col_d, col_v = st.columns([2, 1])
                desc = col_d.text_input("Descrição")
                val = col_v.number_input("Valor", min_value=0.0, step=0.01)
                
                c_t, c_c, c_dt = st.columns(3)
                tipo = c_t.selectbox("Tipo", ["Receita", "Despesa"])
                cat = c_c.selectbox("Categoria", ["Alimentação", "Salário", "Lazer", "Saúde", "Outros"])
                dt = c_dt.date_input("Data", datetime.now())

                if st.form_submit_button("Salvar"):
                    if desc and val > 0:
                        nova_trans = {
                            "email": st.session_state.user_email,
                            "descricao": desc,
                            "valor": val,
                            "tipo": tipo,
                            "categoria": cat,
                            "data": str(dt)
                        }
                        supabase.table("transacoes").insert(nova_trans).execute()
                        st.success("Lançamento salvo!")
                        st.rerun()

if __name__ == "__main__":
    main()
