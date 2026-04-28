import streamlit as st
from supabase import create_client, Client
from datetime import date
from dateutil.relativedelta import relativedelta
import pandas as pd

# Configurações do Supabase (Substitua pelos seus dados no dashboard do Supabase)
SUPABASE_URL = "SUA_URL_AQUI"
SUPABASE_KEY = "SUA_KEY_ANON_AQUI"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Finanças Pro", layout="wide")

# --- SISTEMA DE AUTENTICAÇÃO ---
if 'user' not in st.session_state:
    st.session_state.user = None

def login_usuario():
    st.subheader("Acesse sua Conta")
    email = st.text_input("E-mail")
    senha = st.text_input("Senha", type="password")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error(f"Erro no login: {e}")
    
    with col2:
        if st.button("Cadastrar"):
            try:
                # No Supabase, se você desativar 'confirm email', o user loga direto
                res = supabase.auth.sign_up({"email": email, "password": senha})
                st.success("Cadastro realizado! Clique em Entrar.")
            except Exception as e:
                st.error(f"Erro no cadastro: {e}")

# --- APP PRINCIPAL ---
if st.session_state.user:
    u_id = st.session_state.user.id
    st.sidebar.write(f"Logado como: {st.session_state.user.email}")
    menu = st.sidebar.radio("Menu", ["Lançamentos", "Gestão de Cartões", "Relatórios"])

    if menu == "Lançamentos":
        st.header("Novo Lançamento")
        
        with st.form("form_lancamento"):
            tipo = st.selectbox("Tipo", ["Receita", "Despesa"])
            desc = st.text_input("Descrição")
            valor = st.number_input("Valor", min_value=0.0)
            dt = st.date_input("Data", date.today())
            
            # Busca cartões do banco
            res_c = supabase.table("cartoes").select("nome_cartao").eq("user_id", u_id).execute()
            lista_cartoes = [item['nome_cartao'] for item in res_c.data]
            
            cartao = st.selectbox("Cartão (se aplicável)", ["Nenhum"] + lista_cartoes)
            parcelas = st.number_input("Parcelas (1 para à vista)", min_value=1, value=1)
            
            if st.form_submit_button("Salvar"):
                dados = []
                for i in range(parcelas):
                    nova_data = dt + relativedelta(months=i)
                    dados.append({
                        "user_id": u_id,
                        "tipo": tipo,
                        "descricao": desc,
                        "valor": valor / parcelas,
                        "data": str(nova_data),
                        "parcela_atual": i + 1,
                        "total_parcelas": parcelas,
                        "cartao_nome": cartao if cartao != "Nenhum" else None
                    })
                supabase.table("lancamentos").insert(dados).execute()
                st.success("Salvo com sucesso!")

    elif menu == "Gestão de Cartões":
        st.header("Meus Cartões")
        
        # Adicionar Novo
        novo_c = st.text_input("Nome do Cartão")
        if st.button("Cadastrar Novo Cartão"):
            supabase.table("cartoes").insert({"user_id": u_id, "nome_cartao": novo_c}).execute()
            st.rerun()

        # Visualizar Parcelas conforme solicitado (ex: 1/10)
        st.subheader("Resumo de Parcelas")
        res = supabase.table("lancamentos").select("*").eq("user_id", u_id).neq("cartao_nome", None).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['Parcela'] = df['parcela_atual'].astype(str) + "/" + df['total_parcelas'].astype(str)
            st.dataframe(df[['data', 'cartao_nome', 'descricao', 'Parcela', 'valor']])

    if st.sidebar.button("Sair"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
else:
    login_usuario()
