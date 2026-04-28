import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import calendar

# --- 1. CONFIGURAÇÃO DA LOGO E PÁGINA ---
USUARIO_GITHUB = "JardsonPereira" 
REPO_GITHUB = "orcamentodomestico"
URL_LOGO = f"https://raw.githubusercontent.com/{USUARIO_GITHUB}/{REPO_GITHUB}/main/logo.png"

st.set_page_config(
    page_title="ContabilApp Pro",
    layout="wide",
    page_icon=URL_LOGO
)

# --- 2. CONEXÃO SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("Erro nas credenciais do Supabase. Verifique o secrets.toml.")
        st.stop()

supabase = init_connection()

# --- 3. ESTILO CSS ---
st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        html, body, [class*="st-"] {{ font-family: 'Inter', sans-serif; }}
        .stMetric {{ background: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
        .stButton>button {{ width: 100%; border-radius: 10px; font-weight: 600; background-color: #007BFF; color: white; }}
    </style>
""", unsafe_allow_html=True)

# --- 4. LÓGICA DE SESSÃO ---
if "logado" not in st.session_state:
    st.session_state.logado = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

# --- 5. FUNÇÕES DE DADOS ---
def salvar_transacao(dados):
    try:
        supabase.table("transacoes").insert(dados).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def buscar_dados():
    try:
        res = supabase.table("transacoes").select("*").eq("email", st.session_state.user_email).execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.sidebar.error("Erro ao carregar dados do banco.")
        return pd.DataFrame()

# --- 6. INTERFACE PRINCIPAL ---
def main():
    if not st.session_state.logado:
        # --- TELA DE ACESSO ---
        _, col_logo, _ = st.columns([1, 1, 1])
        with col_logo: st.image(URL_LOGO, width=150)
        
        st.markdown("<h1 style='text-align: center;'>💰 ContabilApp Pro</h1>", unsafe_allow_html=True)
        
        _, col_central, _ = st.columns([1, 1.5, 1])
        with col_central:
            escolha = st.radio("Acesso", ["Login", "Cadastro"], horizontal=True, label_visibility="collapsed")
            
            if escolha == "Login":
                email = st.text_input("E-mail")
                senha = st.text_input("Senha", type='password')
                if st.button("ENTRAR"):
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        if res.user:
                            st.session_state.logado = True
                            st.session_state.user_email = email
                            st.rerun()
                    except: st.error("Login inválido.")
            
            else:
                novo_email = st.text_input("Novo E-mail")
                nova_senha = st.text_input("Senha", type='password')
                if st.button("CRIAR CONTA"):
                    try:
                        supabase.auth.sign_up({"email": novo_email, "password": nova_senha})
                        st.success("Conta criada! Verifique seu e-mail.")
                    except Exception as e: st.error(f"Erro: {e}")

    else:
        # --- ÁREA DO SISTEMA ---
        st.sidebar.image(URL_LOGO, width=100)
        st.sidebar.title("Menu")
        st.sidebar.write(f"👤 {st.session_state.user_email}")
        
        if st.sidebar.button("Sair"):
            st.session_state.logado = False
            st.rerun()

        tabs = st.tabs(["📊 Dashboard", "➕ Lançamentos"])

        # --- ABA 1: DASHBOARD ---
        with tabs[0]:
            col_t1, col_t2 = st.columns([2, 1])
            with col_t1: st.subheader("Resumo de Gastos")
            
            # Filtros de Período
            hoje = datetime.now()
            col_f1, col_f2 = st.columns(2)
            ano_sel = col_f1.selectbox("Ano", range(2024, 2030), index=hoje.year - 2024)
            mes_sel = col_f2.selectbox("Mês", list(calendar.month_name)[1:], index=hoje.month-1)
            mes_num = list(calendar.month_name).index(mes_sel)

            df = buscar_dados()

            if not df.empty:
                # Processamento de Datas
                df['data'] = pd.to_datetime(df['data'])
                df_mes = df[(df['data'].dt.month == mes_num) & (df['data'].dt.year == ano_sel)]

                # Métricas Principais
                rec = df_mes[df_mes['tipo'] == 'Receita']['valor'].sum()
                desp = df_mes[df_mes['tipo'] == 'Despesa']['valor'].sum()
                saldo = rec - desp

                m1, m2, m3 = st.columns(3)
                m1.metric("Receitas", f"R$ {rec:,.2f}")
                m2.metric("Despesas", f"R$ {desp:,.2f}", delta=f"-{desp:,.2f}", delta_color="inverse")
                m3.metric("Saldo", f"R$ {saldo:,.2f}")

                st.divider()
                st.write("### Histórico Detalhado")
                st.dataframe(df_mes[['data', 'descricao', 'categoria', 'tipo', 'valor']].sort_values('data', ascending=False), use_container_width=True)
            else:
                st.info("Nenhum dado registrado ainda. Vá na aba de Lançamentos!")

        # --- ABA 2: LANÇAMENTOS ---
        with tabs[1]:
            st.subheader("Novo Lançamento")
            with st.form("form_transacao", clear_on_submit=True):
                col_a, col_b = st.columns(2)
                descricao = col_a.text_input("Descrição", placeholder="Ex: Mercado, Salário...")
                valor = col_b.number_input("Valor (R$)", min_value=0.0, step=0.01)
                
                col_c, col_d, col_e = st.columns(3)
                tipo = col_c.selectbox("Tipo", ["Receita", "Despesa"])
                categoria = col_d.selectbox("Categoria", ["Alimentação", "Lazer", "Transporte", "Saúde", "Moradia", "Salário", "Outros"])
                data = col_e.date_input("Data", datetime.now())

                if st.form_submit_button("SALVAR REGISTRO"):
                    if descricao and valor > 0:
                        sucesso = salvar_transacao({
                            "email": st.session_state.user_email,
                            "descricao": descricao,
                            "valor": valor,
                            "tipo": tipo,
                            "categoria": categoria,
                            "data": str(data)
                        })
                        if sucesso:
                            st.success("Salvo com sucesso!")
                            st.rerun()
                    else:
                        st.warning("Preencha a descrição e o valor.")

if __name__ == "__main__":
    main()
