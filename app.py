import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO DE ACESSO (SECRETS) ---
try:
    # O Streamlit busca automaticamente nos "Secrets" que você configurou
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Erro ao carregar credenciais. Verifique as chaves nos Secrets do Streamlit.")
    st.stop()

def main():
    st.set_page_config(page_title="Gestão Financeira Pessoal", layout="wide")
    
    st.title("💰 Sistema de Controle de Gastos")
    
    # Menu lateral para navegação
    menu = ["Login", "Criar Conta"]
    choice = st.sidebar.selectbox("Acesso ao Sistema", menu)

    # --- LÓGICA DE CADASTRO ---
    if choice == "Criar Conta":
        st.subheader("Cadastro de Novo Usuário")
        email_novo = st.text_input("E-mail para cadastro")
        senha_nova = st.text_input("Defina uma senha", type='password')
        
        if st.button("Finalizar Cadastro"):
            try:
                # O Supabase gerencia a segurança da senha automaticamente
                supabase.auth.sign_up({"email": email_novo, "password": senha_nova})
                st.success("Cadastro realizado! Por favor, verifique se recebeu um e-mail de confirmação.")
            except Exception as e:
                st.error(f"Erro ao cadastrar: {e}")

    # --- LÓGICA DE LOGIN E OPERAÇÃO ---
    elif choice == "Login":
        st.sidebar.subheader("Área de Login")
        email_login = st.sidebar.text_input("E-mail")
        senha_login = st.sidebar.text_input("Senha", type='password')
        
        if st.sidebar.checkbox("Aceder"):
            try:
                # Autenticação via Supabase
                sessao = supabase.auth.sign_in_with_password({"email": email_login, "password": senha_login})
                st.sidebar.success(f"Logado como: {email_login}")
                
                # Interface principal após login
                tab_lancamento, tab_relatorio = st.tabs(["➕ Novo Lançamento", "📊 Histórico e Gráficos"])

                with tab_lancamento:
                    st.markdown("### Registrar Receita ou Despesa")
                    with st.form("form_financeiro", clear_on_submit=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            tipo = st.selectbox("Categoria de Fluxo", ["Receita", "Despesa"])
                            categoria = st.text_input("Descrição (Ex: Supermercado, Aluguel, Freelance)")
                        with col2:
                            valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
                            data = st.date_input("Data da Operação", datetime.now())
                        
                        botao_salvar = st.form_submit_button("Guardar Registro")

                        if botao_salvar:
                            dados = {
                                "user_email": email_login,
                                "type": tipo,
                                "category": categoria,
                                "amount": valor,
                                "date": data.strftime("%Y-%m-%d")
                            }
                            # Insere na tabela que criamos no SQL do Supabase
                            supabase.table("profile_transactions").insert(dados).execute()
                            st.balloons()
                            st.success("Lançamento registado com sucesso!")

                with tab_relatorio:
                    st.markdown("### Resumo das Finanças")
                    # Busca apenas os dados do usuário logado
                    resposta = supabase.table("profile_transactions").select("*").eq("user_email", email_login).execute()
                    df = pd.DataFrame(resposta.data)

                    if not df.empty:
                        # Cálculos de Totais
                        receitas = df[df['type'] == 'Receita']['amount'].sum()
                        despesas = df[df['type'] == 'Despesa']['amount'].sum()
                        saldo = receitas - despesas

                        c1, c2, c3 = st.columns(3)
                        c1.metric("Total Receitas", f"R$ {receitas:,.2f}")
                        c2.metric("Total Despesas", f"R$ {despesas:,.2f}", delta_color="inverse")
                        c3.metric("Saldo Líquido", f"R$ {saldo:,.2f}", delta=saldo)

                        st.markdown("---")
                        st.subheader("Lista Detalhada")
                        st.dataframe(df.sort_values(by='date', ascending=False), use_container_width=True)
                    else:
                        st.info("Ainda não existem lançamentos registados para este utilizador.")

            except Exception as e:
                st.sidebar.error("E-mail ou senha incorretos.")

if __name__ == "__main__":
    main()
