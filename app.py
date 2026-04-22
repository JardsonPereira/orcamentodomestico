import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DE ACESSO ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Erro ao carregar credenciais. Verifique os Secrets.")
    st.stop()

if "logado" not in st.session_state:
    st.session_state.logado = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

def main():
    st.set_page_config(page_title="Gestão Financeira & Cartões", layout="wide", page_icon="💳")
    
    if not st.session_state.logado:
        # --- LOGIN / CADASTRO ---
        st.sidebar.title("💳 Acesso")
        menu = ["Login", "Criar Conta"]
        choice = st.sidebar.selectbox("Opção", menu)
        
        email = st.text_input("E-mail")
        password = st.text_input("Senha", type='password')
        
        if st.button("Confirmar"):
            try:
                if choice == "Login":
                    supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.logado = True
                    st.session_state.user_email = email
                    st.rerun()
                else:
                    supabase.auth.sign_up({"email": email, "password": password})
                    st.success("Conta criada! Já pode logar.")
            except:
                st.error("Erro na autenticação.")
    else:
        # --- ÁREA LOGADA ---
        st.sidebar.write(f"Usuário: {st.session_state.user_email}")
        if st.sidebar.button("Sair"):
            st.session_state.logado = False
            st.rerun()

        st.title("💰 Controle Financeiro com Cartão")
        
        tab_lanc, tab_cards, tab_relat = st.tabs(["➕ Lançamento", "💳 Gerenciar Cartões", "📊 Relatório"])

        # --- ABA: GERENCIAR CARTÕES ---
        with tab_cards:
            st.subheader("Meus Cartões de Crédito")
            with st.form("form_card"):
                novo_cartao = st.text_input("Nome do Cartão (Ex: Nubank, Visa BB)")
                if st.form_submit_button("Adicionar Cartão"):
                    supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": novo_cartao}).execute()
                    st.success("Cartão salvo!")
            
            # Listar cartões existentes
            res_cards = supabase.table("my_cards").select("card_name").eq("user_email", st.session_state.user_email).execute()
            meus_cartoes = [c['card_name'] for c in res_cards.data]
            if meus_cartoes:
                st.write("**Cartões Ativos:** " + ", ".join(meus_cartoes))

        # --- ABA: LANÇAMENTO ---
        with tab_lanc:
            with st.form("form_financeiro", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
                    categoria = st.text_input("Descrição")
                    metodo = st.selectbox("Método de Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"])
                with col2:
                    valor_total = st.number_input("Valor Total (R$)", min_value=0.0, format="%.2f")
                    data_base = st.date_input("Data da Compra", datetime.now())
                    
                    # Opções extras se for cartão
                    if metodo == "Cartão de Crédito":
                        cartao_sel = st.selectbox("Qual Cartão?", meus_cartoes)
                        parcelas = st.number_input("Quantidade de Parcelas", min_value=1, max_value=48, value=1)
                    else:
                        cartao_sel = None
                        parcelas = 1

                if st.form_submit_button("Salvar Registro"):
                    # Lógica para criar as parcelas nos meses seguintes
                    valor_parcela = valor_total / parcelas
                    for i in range(parcelas):
                        data_parcela = data_base + timedelta(days=30 * i)
                        dados = {
                            "user_email": st.session_state.user_email,
                            "type": tipo,
                            "category": f"{categoria} ({i+1}/{parcelas})",
                            "amount": valor_parcela,
                            "date": data_parcela.strftime("%Y-%m-%d"),
                            "payment_method": metodo,
                            "card_name": cartao_sel,
                            "installment_total": parcelas,
                            "installment_number": i + 1
                        }
                        supabase.table("profile_transactions").insert(dados).execute()
                    st.success(f"Lançamento de {parcelas}x realizado!")

        # --- ABA: RELATÓRIO ---
        with tab_relat:
            res = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
            df = pd.DataFrame(res.data)

            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mes_Ano'] = df['date'].dt.strftime('%m/%Y')
                meses = sorted(df['Mes_Ano'].unique(), reverse=True)
                mes_sel = st.selectbox("Mês de Referência", meses)

                df_mes = df[df['Mes_Ano'] == mes_sel].copy()
                df_mes['Receita (R$)'] = df_mes.apply(lambda x: x['amount'] if x['type'] == 'Receita' else 0.0, axis=1)
                df_mes['Despesa (R$)'] = df_mes.apply(lambda x: x['amount'] if x['type'] == 'Despesa' else 0.0, axis=1)
                df_mes['Data'] = df_mes['date'].dt.strftime('%d/%m/%Y')

                # Totais
                r, d = df_mes['Receita (R$)'].sum(), df_mes['Despesa (R$)'].sum()
                c1, c2, c3 = st.columns(3)
                c1.metric("Receitas", f"R$ {r:,.2f}")
                c2.metric("Despesas", f"R$ {d:,.2f}")
                c3.metric("Saldo", f"R$ {r-d:,.2f}")

                st.dataframe(df_mes[['Data', 'category', 'payment_method', 'card_name', 'Receita (R$)', 'Despesa (R$)']], use_container_width=True)
            else:
                st.info("Sem dados.")

if __name__ == "__main__":
    main()
