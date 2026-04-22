import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import calendar

# --- CONEXÃO ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Erro nas credenciais do Supabase.")
    st.stop()

if "logado" not in st.session_state:
    st.session_state.logado = False

def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)

def main():
    st.set_page_config(page_title="Gestão Financeira", layout="wide")
    
    if not st.session_state.logado:
        # Lógica de Login (Simplificada para o exemplo)
        st.sidebar.title("🔐 Login")
        email = st.sidebar.text_input("E-mail")
        senha = st.sidebar.text_input("Senha", type='password')
        if st.sidebar.button("Entrar"):
            try:
                supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.logado = True
                st.session_state.user_email = email
                st.rerun()
            except: st.error("Erro de login")
    else:
        st.title(f"💰 Controle de {st.session_state.user_email}")
        
        # Carregar cartões para o selectbox
        res_c = supabase.table("my_cards").select("card_name").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]

        tab_lanc, tab_extrato, tab_cartao = st.tabs(["➕ Lançar", "📊 Extrato Geral", "💳 Visão Cartão"])

        # --- ABA LANÇAMENTO ---
        with tab_lanc:
            with st.form("form_f", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    desc = st.text_input("Descrição da Compra")
                    valor_total = st.number_input("Valor Total (R$)", min_value=0.0)
                    metodo = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"])
                with col2:
                    data_compra = st.date_input("Data da Compra", datetime.now())
                    if metodo == "Cartão de Crédito":
                        cartao = st.selectbox("Selecione o Cartão", lista_cartoes)
                        num_parcelas = st.number_input("Total de Parcelas", min_value=1, value=1)
                    else:
                        cartao, num_parcelas = None, 1

                if st.form_submit_button("Registrar"):
                    v_parc = valor_total / num_parcelas
                    for i in range(num_parcelas):
                        # Calcula a data da parcela (mês a mês)
                        vencimento = add_months(data_compra, i)
                        supabase.table("profile_transactions").insert({
                            "user_email": st.session_state.user_email,
                            "type": "Despesa",
                            "category": desc,
                            "amount": v_parc,
                            "date": vencimento.strftime("%Y-%m-%d"),
                            "payment_method": metodo,
                            "card_name": cartao,
                            "installment_total": num_parcelas,
                            "installment_number": i + 1
                        }).execute()
                    st.success(f"Lançamento realizado: {num_parcelas}x de R$ {v_parc:.2f}")

        # --- ABA EXTRATO GERAL ---
        with tab_extrato:
            res = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês'] = df['date'].dt.strftime('%m/%Y')
                mes_sel = st.selectbox("Selecione o Mês", sorted(df['Mês'].unique(), reverse=True), key="sb1")
                
                filtro = df[df['Mês'] == mes_sel].copy()
                st.dataframe(filtro[['date', 'category', 'amount', 'payment_method', 'installment_number', 'installment_total']], use_container_width=True)

        # --- ABA EXCLUSIVA DE CARTÃO ---
        with tab_cartao:
            st.subheader("Visualização por Cartão e Parcelas")
            if not df.empty:
                # Filtrar apenas o que é cartão
                df_card = df[df['payment_method'] == "Cartão de Crédito"].copy()
                
                if not df_card.empty:
                    card_sel = st.selectbox("Filtrar por Cartão", ["Todos"] + lista_cartoes)
                    if card_sel != "Todos":
                        df_card = df_card[df_card['card_name'] == card_sel]
                    
                    # Criar coluna formatada "1/10"
                    df_card['Parcela'] = df_card['installment_number'].astype(str) + "/" + df_card['installment_total'].astype(str)
                    
                    # Exibição organizada
                    resumo_card = df_card[['date', 'card_name', 'category', 'Parcela', 'amount']].rename(
                        columns={'date': 'Data Vencimento', 'card_name': 'Cartão', 'category': 'Item', 'amount': 'Valor da Parcela'}
                    )
                    
                    st.dataframe(resumo_card.sort_values(by='Data Vencimento'), use_container_width=True)
                    st.metric("Total Comprometido em Cartão", f"R$ {df_card['amount'].sum():,.2f}")
                else:
                    st.info("Nenhuma despesa em cartão identificada.")

if __name__ == "__main__":
    main()
