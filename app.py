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
    st.error("Erro ao carregar credenciais. Verifique os Secrets.")
    st.stop()

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
if "logado" not in st.session_state:
    st.session_state.logado = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

def main():
    st.set_page_config(page_title="Gestão Financeira", layout="wide")
    
    # Barra Lateral
    st.sidebar.title("Configurações")
    
    if not st.session_state.logado:
        menu = ["Login", "Criar Conta"]
        choice = st.sidebar.selectbox("Acesso", menu)

        if choice == "Criar Conta":
            st.subheader("Cadastro de Usuário")
            email_novo = st.text_input("E-mail")
            senha_nova = st.text_input("Senha", type='password')
            if st.button("Cadastrar"):
                try:
                    supabase.auth.sign_up({"email": email_novo, "password": senha_nova})
                    st.success("Conta criada! Agora faça o login.")
                except Exception as e:
                    st.error(f"Erro: {e}")

        elif choice == "Login":
            st.sidebar.subheader("Entrar")
            email_login = st.sidebar.text_input("E-mail")
            senha_login = st.sidebar.text_input("Senha", type='password')
            
            if st.sidebar.button("Entrar"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email_login, "password": senha_login})
                    st.session_state.logado = True
                    st.session_state.user_email = email_login
                    st.rerun() # Recarrega para entrar no modo logado
                except Exception as e:
                    st.sidebar.error("E-mail ou senha incorretos.")
    else:
        # BOTÃO DE LOGOUT
        if st.sidebar.button("Sair / Logoff"):
            st.session_state.logado = False
            st.session_state.user_email = ""
            st.rerun()

        st.title(f"💰 Painel de {st.session_state.user_email}")
        
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
                        "user_email": st.session_state.user_email,
                        "type": tipo,
                        "category": categoria,
                        "amount": valor,
                        "date": data.strftime("%Y-%m-%d")
                    }
                    try:
                        supabase.table("profile_transactions").insert(dados).execute()
                        st.success(f"Registrado: {data.strftime('%d/%m/%Y')}")
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

        with tab_relatorio:
            resposta = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
            df = pd.DataFrame(resposta.data)

            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mes_Ano'] = df['date'].dt.strftime('%m/%Y')
                
                meses = df['Mes_Ano'].unique()
                mes_sel = st.selectbox("Selecione o Mês", meses)
                
                df_mes = df[df['Mes_Ano'] == mes_sel].copy()
                df_mes['Data'] = df_mes['date'].dt.strftime('%d/%m/%Y')

                rec = df_mes[df_mes['type'] == 'Receita']['amount'].sum()
                des = df_mes[df_mes['type'] == 'Despesa']['amount'].sum()

                c1, c2, c3 = st.columns(3)
                c1.metric("Receitas", f"R$ {rec:,.2f}")
                c2.metric("Despesas", f"R$ {des:,.2f}")
                c3.metric("Saldo", f"R$ {rec - des:,.2f}")

                st.dataframe(df_mes[['Data', 'type', 'category', 'amount']].sort_values(by='Data', ascending=False), use_container_width=True)
            else:
                st.info("Nenhum dado encontrado.")

if __name__ == "__main__":
    main()
