import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÃO SUPABASE ---
# No Streamlit Cloud, usaremos secrets. Localmente, pode substituir as strings.
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="Gestão Financeira", layout="wide")

# --- ESTADO DA SESSÃO ---
if 'user' not in st.session_state:
    st.session_state.user = None

# --- FUNÇÕES DE AUTH ---
def login_form():
    st.title("🔑 Acesso ao Sistema")
    aba1, aba2 = st.tabs(["Login", "Criar Conta"])
    
    with aba1:
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password", key="login_pass")
        if st.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error("Erro: Verifique os dados.")

    with aba2:
        novo_email = st.text_input("Novo E-mail")
        nova_senha = st.text_input("Nova Senha", type="password", key="reg_pass")
        if st.button("Registar"):
            try:
                supabase.auth.sign_up({"email": novo_email, "password": nova_senha})
                st.success("Conta criada! Tente fazer login.")
            except Exception as e:
                st.error(f"Erro: {e}")

# --- APP PRINCIPAL ---
if st.session_state.user is None:
    login_form()
else:
    u_id = st.session_state.user.id
    st.sidebar.title("💰 Finanças")
    menu = st.sidebar.radio("Navegação", ["Lançamentos", "Cartões de Crédito", "Relatórios"])
    
    if st.sidebar.button("Sair"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    if menu == "Lançamentos":
        st.header("Novo Lançamento")
        with st.form("form_novo"):
            tipo = st.selectbox("Tipo", ["Receita", "Despesa"])
            desc = st.text_input("Descrição")
            valor = st.number_input("Valor Total", min_value=0.0, format="%.2f")
            dt = st.date_input("Data Inicial", date.today())
            
            # Busca cartões para o selectbox
            res_c = supabase.table("cartoes").select("nome_cartao").eq("user_id", u_id).execute()
            lista_c = [c['nome_cartao'] for c in res_c.data]
            
            cartao = st.selectbox("Cartão de Crédito (Opcional)", ["Nenhum"] + lista_c)
            parcelas = st.number_input("Nº de Parcelas", min_value=1, value=1)
            
            if st.form_submit_button("Salvar Lançamento"):
                dados = []
                valor_parcela = valor / parcelas
                for i in range(parcelas):
                    dados.append({
                        "user_id": u_id,
                        "tipo": tipo,
                        "descricao": desc,
                        "valor": round(valor_parcela, 2),
                        "data": str(dt + relativedelta(months=i)),
                        "parcela_atual": i + 1,
                        "total_parcelas": parcelas,
                        "cartao_nome": cartao if cartao != "Nenhum" else None
                    })
                supabase.table("lancamentos").insert(dados).execute()
                st.success(f"Lançamento de {parcelas}x guardado!")

    elif menu == "Cartões de Crédito":
        st.header("💳 Gestão de Cartões")
        
        # Cadastro de cartão
        with st.expander("Cadastrar Novo Cartão"):
            nome_c = st.text_input("Nome do Cartão (ex: Visa)")
            if st.button("Guardar Cartão"):
                supabase.table("cartoes").insert({"user_id": u_id, "nome_cartao": nome_c}).execute()
                st.rerun()

        # Visualização de Parcelas
        st.subheader("Acompanhamento de Parcelas")
        res = supabase.table("lancamentos").select("*").eq("user_id", u_id).neq("cartao_nome", None).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            # Formatação solicitada: 1/10
            df['Parcelamento'] = df['parcela_atual'].astype(str) + "/" + df['total_parcelas'].astype(str)
            st.dataframe(df[['data', 'cartao_nome', 'descricao', 'Parcelamento', 'valor']])
        else:
            st.info("Nenhuma despesa parcelada encontrada.")

    elif menu == "Relatórios":
        st.header("📊 Resumo Mensal")
        res = supabase.table("lancamentos").select("*").eq("user_id", u_id).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['data'] = pd.to_datetime(df['data'])
            df['Mês/Ano'] = df['data'].dt.strftime('%m/%Y')
            
            mes_sel = st.selectbox("Selecione o Mês", df['Mês/Ano'].unique())
            df_mes = df[df['Mês/Ano'] == mes_sel]
            
            st.table(df_mes[['data', 'descricao', 'tipo', 'valor']])
            
            rec = df_mes[df_mes['tipo'] == 'Receita']['valor'].sum()
            des = df_mes[df_mes['tipo'] == 'Despesa']['valor'].sum()
            st.metric("Saldo", f"€ {rec - des:.2f}", delta=f"Ganhos: {rec} | Gastos: {des}")
