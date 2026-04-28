import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import calendar

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="ContabilApp Pro", layout="wide")

@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

if "logado" not in st.session_state: st.session_state.logado = False
if "user_email" not in st.session_state: st.session_state.user_email = ""

# --- INTERFACE ---
if not st.session_state.logado:
    st.title("💰 Login - ContabilApp")
    e = st.text_input("Email")
    p = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        res = supabase.auth.sign_in_with_password({"email": e, "password": p})
        if res.user:
            st.session_state.logado = True
            st.session_state.user_email = e
            st.rerun()
else:
    tab1, tab2 = st.tabs(["📊 Dashboard", "➕ Novo Lançamento"])

    with tab1:
        # Busca dados atualizados
        res = supabase.table("transacoes").select("*").eq("email", st.session_state.user_email).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhum dado encontrado.")

    with tab2:
        st.subheader("Cadastrar Movimentação")
        
        col1, col2 = st.columns(2)
        desc = col1.text_input("Descrição")
        valor = col2.number_input("Valor (R$)", min_value=0.0, step=0.01)
        
        c_tipo, c_cat, c_data = st.columns(3)
        tipo = c_tipo.selectbox("Tipo", ["Receita", "Despesa"])
        cat = c_cat.selectbox("Categoria", ["Alimentação", "Salário", "Lazer", "Saúde", "Outros"])
        dt = c_data.date_input("Data", datetime.now())

        # Lógica de atualização em tempo real
        metodo = "N/A"
        if tipo == "Despesa":
            metodo = st.selectbox("Forma de Pagamento", ["Dinheiro", "Cartão de Crédito", "Pix"])
        
        if st.button("SALVAR LANÇAMENTO"):
            if desc and valor > 0:
                dados = {
                    "email": st.session_state.user_email,
                    "descricao": desc,
                    "valor": valor,
                    "tipo": tipo,
                    "categoria": cat,
                    "data": str(dt),
                    "metodo_pagamento": metodo
                }
                supabase.table("transacoes").insert(dados).execute()
                st.success(f"Registrado: {tipo} via {metodo}")
                st.rerun()
            else:
                st.error("Preencha todos os campos.")
