import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO DE ACESSO (SECRETS) ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Erro ao carregar credenciais. Verifique as chaves nos Secrets.")
    st.stop()

def main():
    st.set_page_config(page_title="Gestão Financeira", layout="wide")
    st.title("💰 Controle de Gastos Domésticos")
    
    menu = ["Login", "Criar Conta"]
    choice = st.sidebar.selectbox("Acesso", menu)

    # --- CADASTRO SEM CONFIRMAÇÃO DE E-MAIL ---
    if choice == "Criar Conta":
        st.subheader("Cadastro Rápido")
        email_novo = st.text_input("E-mail")
        senha_nova = st.text_input("Senha", type='password')
        
        if st.button("Cadastrar"):
            try:
                # Ao desativar 'Confirm Email' no Supabase, o usuário é criado e fica ativo na hora
                supabase.auth.sign_up({"email": email_novo, "password": senha_nova})
                st.success("Conta criada com sucesso! Você já pode mudar para a aba de Login.")
            except Exception as e:
                st.error(f"Erro ao cadastrar: {e}")

    # --- LOGIN E DASHBOARD ---
    elif choice == "Login":
        st.sidebar.subheader("Entrar")
        email_login = st.sidebar.text_input("E-mail")
        senha_login = st.sidebar.text_input("Senha", type='password')
        
        if st.sidebar.checkbox("Aceder"):
            try:
                sessao = supabase.auth.sign_in_with_password({"email": email_login, "password": senha_login})
                st.sidebar.success(f"Logado: {email_login}")
                
                tab_lancamento, tab_relatorio = st.tabs(["➕ Lançamento", "📊 Relatórios"])

                with tab_lancamento:
                    with st.form("form_financeiro", clear_on_submit=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            tipo = st.selectbox("Tipo", ["Receita", "Despesa"])
                            categoria = st.text_input("Descrição")
                        with col2:
                            valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
                            data = st.date_input("Data", datetime.now())
                        
                        if st.form_submit_button("Salvar"):
                            dados = {
                                "user_email": email_login,
                                "type": tipo,
                                "category": categoria,
                                "amount": valor,
                                "date": data.strftime("%Y-%m-%d")
                            }
                            supabase.table("profile_transactions").insert(dados).execute()
                            st.success("Registrado!")

                with tab_relatorio:
                    resposta = supabase.table("profile_transactions").select("*").eq("user_email", email_login).execute()
                    df = pd.DataFrame(resposta.data)

                    if not df.empty:
                        receitas = df[df['type'] == 'Receita']['amount'].sum()
                        despesas = df[df['type'] == 'Despesa']['amount'].sum()
                        saldo = receitas - despesas

                        c1, c2, c3 = st.columns(3)
                        c1.metric("Receitas", f"R$ {receitas:,.2f}")
                        c2.metric("Despesas", f"R$ {despesas:,.2f}")
                        c3.metric("Saldo", f"R$ {saldo:,.2f}", delta=saldo)

                        st.dataframe(df.sort_values(by='date', ascending=False), use_container_width=True)
                    else:
                        st.info("Nenhum dado encontrado.")

            except Exception as e:
                st.sidebar.error("E-mail ou senha incorretos.")

if __name__ == "__main__":
    main()
