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
    st.set_page_config(page_title="Gestão Financeira Mensal", layout="wide")
    st.title("💰 Controle de Gastos Mensais")
    
    menu = ["Login", "Criar Conta"]
    choice = st.sidebar.selectbox("Acesso ao Sistema", menu)

    if choice == "Criar Conta":
        st.subheader("Cadastro Rápido")
        email_novo = st.text_input("E-mail")
        senha_nova = st.text_input("Senha", type='password')
        
        if st.button("Cadastrar"):
            try:
                supabase.auth.sign_up({"email": email_novo, "password": senha_nova})
                st.success("Conta criada! Agora você pode fazer o login.")
            except Exception as e:
                st.error(f"Erro ao cadastrar: {e}")

    elif choice == "Login":
        st.sidebar.subheader("Entrar")
        email_login = st.sidebar.text_input("E-mail")
        senha_login = st.sidebar.text_input("Senha", type='password')
        
        if st.sidebar.checkbox("Aceder"):
            try:
                sessao = supabase.auth.sign_in_with_password({"email": email_login, "password": senha_login})
                st.sidebar.success(f"Usuário: {email_login}")
                
                tab_lancamento, tab_relatorio = st.tabs(["➕ Novo Lançamento", "📊 Relatório Mensal"])

                with tab_lancamento:
                    with st.form("form_financeiro", clear_on_submit=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            tipo = st.selectbox("Tipo", ["Receita", "Despesa"])
                            categoria = st.text_input("Descrição")
                        with col2:
                            valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
                            data = st.date_input("Data da Operação", datetime.now())
                        
                        if st.form_submit_button("Salvar Registro"):
                            dados = {
                                "user_email": email_login,
                                "type": tipo,
                                "category": categoria,
                                "amount": valor,
                                "date": data.strftime("%Y-%m-%d")
                            }
                            supabase.table("profile_transactions").insert(dados).execute()
                            st.success(f"Registrado com sucesso em {data.strftime('%d/%m/%Y')}!")

                with tab_relatorio:
                    resposta = supabase.table("profile_transactions").select("*").eq("user_email", email_login).execute()
                    df = pd.DataFrame(resposta.data)

                    if not df.empty:
                        # Tratamento de datas
                        df['date'] = pd.to_datetime(df['date'])
                        df['Mes_Ano'] = df['date'].dt.strftime('%m/%Y')
                        
                        # Seletor de Mês/Ano
                        meses_disponiveis = df['Mes_Ano'].unique()
                        mes_selecionado = st.selectbox("Selecione o Mês de Referência", meses_disponiveis)

                        # Filtrar DF pelo mês selecionado
                        df_mes = df[df['Mes_Ano'] == mes_selecionado].copy()
                        
                        # Formatação da data para exibição brasileira
                        df_mes['Data Formatada'] = df_mes['date'].dt.strftime('%d/%m/%Y')

                        # Totais do mês
                        receitas = df_mes[df_mes['type'] == 'Receita']['amount'].sum()
                        despesas = df_mes[df_mes['type'] == 'Despesa']['amount'].sum()
                        saldo = receitas - despesas

                        c1, c2, c3 = st.columns(3)
                        c1.metric("Receitas do Mês", f"R$ {receitas:,.2f}")
                        c2.metric("Despesas do Mês", f"R$ {despesas:,.2f}")
                        c3.metric("Saldo Mensal", f"R$ {saldo:,.2f}", delta=saldo)

                        st.markdown("---")
                        st.subheader(f"Detalhamento de {mes_selecionado}")
                        
                        # Mostrar tabela organizada
                        exibicao = df_mes[['Data Formatada', 'type', 'category', 'amount']].rename(
                            columns={'type': 'Tipo', 'category': 'Descrição', 'amount': 'Valor (R$)'}
                        )
                        st.dataframe(exibicao.sort_values(by='Data Formatada', ascending=False), use_container_width=True)
                    else:
                        st.info("Nenhum dado encontrado para gerar o relatório.")

            except Exception as e:
                st.sidebar.error("E-mail ou senha incorretos.")

if __name__ == "__main__":
    main()
