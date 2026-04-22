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
    st.error("Erro ao carregar credenciais. Verifique os Secrets no Streamlit Cloud.")
    st.stop()

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
if "logado" not in st.session_state:
    st.session_state.logado = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

def main():
    st.set_page_config(page_title="Controle Financeiro", layout="wide", page_icon="💰")
    
    # Barra Lateral
    st.sidebar.title("💳 Menu de Acesso")
    
    if not st.session_state.logado:
        menu = ["Login", "Criar Conta"]
        choice = st.sidebar.selectbox("Selecione", menu)

        if choice == "Criar Conta":
            st.subheader("📝 Cadastro de Novo Usuário")
            email_novo = st.text_input("E-mail")
            senha_nova = st.text_input("Senha", type='password')
            if st.button("Cadastrar"):
                try:
                    # Nota: Lembre-se de desativar "Confirm Email" no painel do Supabase
                    supabase.auth.sign_up({"email": email_novo, "password": senha_nova})
                    st.success("Conta criada com sucesso! Mude para 'Login' para entrar.")
                except Exception as e:
                    st.error(f"Erro ao cadastrar: {e}")

        elif choice == "Login":
            st.sidebar.subheader("Entrar no Sistema")
            email_login = st.sidebar.text_input("E-mail")
            senha_login = st.sidebar.text_input("Senha", type='password')
            
            if st.sidebar.button("Entrar"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email_login, "password": senha_login})
                    st.session_state.logado = True
                    st.session_state.user_email = email_login
                    st.rerun()
                except Exception as e:
                    st.sidebar.error("E-mail ou senha inválidos.")
    else:
        # MENU LOGADO
        st.sidebar.info(f"Conectado como: \n{st.session_state.user_email}")
        if st.sidebar.button("Encerrar Sessão (Sair)"):
            st.session_state.logado = False
            st.session_state.user_email = ""
            st.rerun()

        st.title(f"📊 Gestão Financeira Doméstica")
        
        tab_lancamento, tab_relatorio = st.tabs(["➕ Novo Lançamento", "📅 Relatório Mensal"])

        with tab_lancamento:
            st.markdown("### Registrar Movimentação")
            with st.form("form_financeiro", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    tipo = st.selectbox("Tipo de Lançamento", ["Receita", "Despesa"])
                    categoria = st.text_input("Descrição / Categoria")
                with col2:
                    valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f", step=0.01)
                    data = st.date_input("Data", datetime.now())
                
                if st.form_submit_button("Salvar no Banco de Dados"):
                    dados = {
                        "user_email": st.session_state.user_email,
                        "type": tipo,
                        "category": categoria,
                        "amount": valor,
                        "date": data.strftime("%Y-%m-%d")
                    }
                    try:
                        # IMPORTANTE: A tabela no Supabase deve se chamar 'profile_transactions'
                        supabase.table("profile_transactions").insert(dados).execute()
                        st.success(f"Sucesso! {tipo} de R$ {valor:.2f} registrada em {data.strftime('%d/%m/%Y')}.")
                    except Exception as e:
                        st.error(f"Erro de permissão (RLS): {e}")

        with tab_relatorio:
            # Busca dados do usuário logado
            resposta = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
            df = pd.DataFrame(resposta.data)

            if not df.empty:
                # Tratamento de datas e filtros
                df['date'] = pd.to_datetime(df['date'])
                df['Mes_Ano'] = df['date'].dt.strftime('%m/%Y')
                
                meses = sorted(df['Mes_Ano'].unique(), reverse=True)
                mes_sel = st.selectbox("Selecione o mês para análise", meses)
                
                # Filtragem do mês e criação de colunas separadas
                df_mes = df[df['Mes_Ano'] == mes_sel].copy()
                df_mes['Receita (R$)'] = df_mes.apply(lambda x: x['amount'] if x['type'] == 'Receita' else 0.0, axis=1)
                df_mes['Despesa (R$)'] = df_mes.apply(lambda x: x['amount'] if x['type'] == 'Despesa' else 0.0, axis=1)
                df_mes['Data'] = df_mes['date'].dt.strftime('%d/%m/%Y')

                # Cálculos de Totais
                total_rec = df_mes['Receita (R$)'].sum()
                total_des = df_mes['Despesa (R$)'].sum()
                saldo_final = total_rec - total_des

                # Exibição dos indicadores
                m1, m2, m3 = st.columns(3)
                m1.metric("Receitas", f"R$ {total_rec:,.2f}")
                m2.metric("Despesas", f"R$ {total_des:,.2f}", delta_color="inverse")
                m3.metric("Saldo do Mês", f"R$ {saldo_final:,.2f}", delta=saldo_final)

                st.markdown("---")
                st.subheader(f"Extrato Detalhado: {mes_sel}")
                
                # Organização da Tabela
                tabela_final = df_mes[['Data', 'category', 'Receita (R$)', 'Despesa (R$)']].rename(
                    columns={'category': 'Descrição'}
                )
                st.dataframe(tabela_final.sort_values(by='Data', ascending=False), use_container_width=True)
                
                st.info(f"**Resumo:** Você fechou o mês de {mes_sel} com um saldo de **R$ {saldo_final:,.2f}**.")
            else:
                st.warning("Ainda não existem registros em sua conta. Comece fazendo um lançamento!")

if __name__ == "__main__":
    main()
