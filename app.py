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
        st.error("Erro nas credenciais do Supabase.")
        return None

supabase = init_connection()

if "logado" not in st.session_state: st.session_state.logado = False
if "user_email" not in st.session_state: st.session_state.user_email = ""

def buscar_dados():
    try:
        res = supabase.table("transacoes").select("*").eq("email", st.session_state.user_email).execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

def main():
    if not st.session_state.logado:
        # --- TELA DE LOGIN SIMPLIFICADA ---
        st.title("💰 ContabilApp Pro")
        email = st.text_input("Email")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                if res.user:
                    st.session_state.logado = True
                    st.session_state.user_email = email
                    st.rerun()
            except: st.error("Erro no login.")
    else:
        # --- MENU LATERAL ---
        st.sidebar.write(f"👤 {st.session_state.user_email}")
        if st.sidebar.button("Sair"):
            st.session_state.logado = False
            st.rerun()

        tab1, tab2 = st.tabs(["📊 Dashboard", "➕ Novo Lançamento"])

        # --- ABA DASHBOARD ---
        with tab1:
            df = buscar_dados()
            if not df.empty:
                st.subheader("Histórico Financeiro")
                # Exibindo a nova coluna se ela existir no DF
                colunas_exibir = ['data', 'descricao', 'categoria', 'tipo', 'metodo_pagamento', 'valor']
                # Filtra apenas colunas que realmente existem no DF para evitar erro
                cols_finais = [c for c in colunas_exibir if c in df.columns]
                st.dataframe(df[cols_finais], use_container_width=True)
            else:
                st.info("Sem dados para exibir.")

        # --- ABA LANÇAMENTOS (ONDE A MUDANÇA OCORRE) ---
        with tab2:
            st.subheader("Cadastrar Movimentação")
            with st.form("form_novo_lancamento", clear_on_submit=True):
                col_desc, col_val = st.columns([2, 1])
                desc = col_desc.text_input("Descrição")
                valor = col_val.number_input("Valor (R$)", min_value=0.0, step=0.01)
                
                col_tipo, col_cat, col_data = st.columns(3)
                tipo = col_tipo.selectbox("Tipo", ["Receita", "Despesa"])
                cat = col_cat.selectbox("Categoria", ["Alimentação", "Salário", "Lazer", "Transporte", "Saúde", "Outros"])
                dt = col_data.date_input("Data", datetime.now())

                # --- NOVO CAMPO CONDICIONAL ---
                metodo = "N/A"
                if tipo == "Despesa":
                    metodo = st.selectbox("Forma de Pagamento", ["Dinheiro", "Cartão de Crédito", "Pix"])
                
                if st.form_submit_button("Salvar Registro"):
                    if desc and valor > 0:
                        dados = {
                            "email": st.session_state.user_email,
                            "descricao": desc,
                            "valor": valor,
                            "tipo": tipo,
                            "categoria": cat,
                            "data": str(dt),
                            "metodo_pagamento": metodo # Enviando para o banco
                        }
                        try:
                            supabase.table("transacoes").insert(dados).execute()
                            st.success("Lançamento salvo com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar no banco: {e}")
                    else:
                        st.warning("Preencha a descrição e o valor.")

if __name__ == "__main__":
    main()
