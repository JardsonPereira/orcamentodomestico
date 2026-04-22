import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÕES SUPABASE ---
# No Streamlit Cloud, use st.secrets para segurança
url = st.sidebar.text_input("Supabase URL", type="password")
key = st.sidebar.text_input("Supabase Key", type="password")

if not url or not key:
    st.warning("Insira suas credenciais do Supabase na barra lateral para começar.")
    st.stop()

supabase: Client = create_client(url, key)

def main():
    st.set_page_config(page_title="Controle Financeiro Supabase", layout="centered")
    st.title("💰 Gestão Financeira com Cloud")

    menu = ["Login", "Cadastro"]
    choice = st.sidebar.selectbox("Acesso", menu)

    if choice == "Cadastro":
        st.subheader("Criar conta no Supabase")
        email = st.text_input("Email")
        password = st.text_input("Senha", type='password')
        if st.button("Registrar"):
            try:
                res = supabase.auth.sign_up({"email": email, "password": password})
                st.success("Cadastro realizado! Verifique seu email para confirmar.")
            except Exception as e:
                st.error(f"Erro: {e}")

    elif choice == "Login":
        st.subheader("Login")
        email = st.sidebar.text_input("Email")
        password = st.sidebar.text_input("Senha", type='password')

        if st.sidebar.checkbox("Entrar"):
            try:
                user = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.success(f"Bem-vindo, {email}")
                
                # --- DASHBOARD APÓS LOGIN ---
                tab1, tab2 = st.tabs(["Novo Lançamento", "Relatórios"])

                with tab1:
                    with st.form("form_financeiro"):
                        tipo = st.selectbox("Tipo", ["Receita", "Despesa"])
                        cat = st.text_input("Categoria")
                        valor = st.number_input("Valor", min_value=0.0)
                        data = st.date_input("Data")
                        enviar = st.form_submit_button("Salvar")

                        if enviar:
                            data_insert = {
                                "user_email": email,
                                "type": tipo,
                                "category": cat,
                                "amount": valor,
                                "date": data.strftime("%Y-%m-%d")
                            }
                            supabase.table("profile_transactions").insert(data_insert).execute()
                            st.success("Dados salvos no Supabase!")

                with tab2:
                    res = supabase.table("profile_transactions").select("*").eq("user_email", email).execute()
                    df = pd.DataFrame(res.data)
                    
                    if not df.empty:
                        st.dataframe(df)
                        receita = df[df['type'] == 'Receita']['amount'].sum()
                        despesa = df[df['type'] == 'Despesa']['amount'].sum()
                        st.metric("Saldo Atual", f"R$ {receita - despesa:,.2f}")
                    else:
                        st.info("Nenhum registro encontrado.")

            except Exception as e:
                st.sidebar.error("Falha no login. Verifique as credenciais.")

if __name__ == '__main__':
    main()
