import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import calendar

# --- CONEXÃO SEGURA ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Erro nas credenciais do Supabase. Verifique os Secrets no Streamlit.")
    st.stop()

# --- ESTADO DA SESSÃO ---
if "logado" not in st.session_state:
    st.session_state.logado = False

# --- FUNÇÃO PARA PULAR MESES CORRETAMENTE ---
def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)

def main():
    st.set_page_config(page_title="Gestão Financeira Pro", layout="wide", page_icon="💰")
    
    if not st.session_state.logado:
        st.sidebar.title("🔐 Acesso")
        email = st.sidebar.text_input("E-mail")
        senha = st.sidebar.text_input("Senha", type='password')
        if st.sidebar.button("Entrar"):
            try:
                supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.logado = True
                st.session_state.user_email = email
                st.rerun()
            except: st.error("Login inválido")
    else:
        st.sidebar.success(f"Logado: {st.session_state.user_email}")
        if st.sidebar.button("Sair"):
            st.session_state.logado = False
            st.rerun()

        # BUSCA DE DADOS
        res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        tab_lanc, tab_extrato, tab_cartao, tab_config = st.tabs(["➕ Lançar", "📊 Extrato Mensal", "💳 Visão Cartão", "⚙️ Configurações"])

        # --- ABA 1: LANÇAMENTOS ---
        with tab_lanc:
            st.subheader("Novo Registro")
            with st.form("novo_lanc", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
                    desc = st.text_input("Descrição")
                    metodo = st.selectbox("Forma", ["PIX/Dinheiro", "Cartão de Crédito"])
                with c2:
                    valor_total = st.number_input("Valor Total", min_value=0.0)
                    data_base = st.date_input("Data da Compra/Início", datetime.now())
                    if metodo == "Cartão de Crédito":
                        cartao_sel = st.selectbox("Cartão", lista_cartoes)
                        parcelas = st.number_input("Parcelas", min_value=1, value=1)
                    else:
                        cartao_sel, parcelas = None, 1
                
                if st.form_submit_button("Salvar"):
                    v_parc = valor_total / parcelas
                    for i in range(int(parcelas)):
                        vencimento = add_months(data_base, i)
                        supabase.table("profile_transactions").insert({
                            "user_email": st.session_state.user_email,
                            "type": tipo,
                            "category": desc,
                            "amount": v_parc,
                            "date": vencimento.strftime("%Y-%m-%d"),
                            "payment_method": metodo,
                            "card_name": cartao_sel,
                            "installment_total": int(parcelas),
                            "installment_number": i + 1
                        }).execute()
                    st.success("Lançado com sucesso!")
                    st.rerun()

        # --- ABA 2: EXTRATO MENSAL (CORRIGIDA) ---
        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês/Ano'] = df['date'].dt.strftime('%m/%Y')
                meses = sorted(df['Mês/Ano'].unique(), reverse=True)
                mes_sel = st.selectbox("Filtrar Mês", meses)

                f = df[df['Mês/Ano'] == mes_sel].copy()
                
                # Info da parcela
                f['Info'] = f.apply(lambda x: f"Parcela {int(x['installment_number'])} de {int(x['installment_total'])}" 
                                   if x['payment_method'] == "Cartão de Crédito" else x['payment_method'], axis=1)
                
                f['Receita'] = f.apply(lambda x: x['amount'] if x['type'] == 'Receita' else 0, axis=1)
                f['Despesa'] = f.apply(lambda x: x['amount'] if x['type'] == 'Despesa' else 0, axis=1)
                
                # CÁLCULO DO SALDO CORRIGIDO (Usando 'Despesa' em vez de 'Desp')
                total_rec = f['Receita'].sum()
                total_desp = f['Despesa'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Receitas", f"R$ {total_rec:,.2f}")
                c2.metric("Despesas", f"R$ {total_desp:,.2f}")
                c3.metric("Saldo do Mês", f"R$ {total_rec - total_desp:,.2f}")
                
                st.dataframe(f[['date', 'category', 'Info', 'card_name', 'Receita', 'Despesa']].rename(columns={'date':'Data', 'category':'Descrição', 'card_name':'Cartão'}), use_container_width=True)
            else: st.info("Nenhum dado encontrado.")

        # --- ABA 3: VISÃO CARTÃO ---
        with tab_cartao:
            st.subheader("Projeção de Faturas de Cartão")
            if not df.empty:
                df_c = df[df['payment_method'] == "Cartão de Crédito"].copy()
                if not df_c.empty:
                    df_c['Status'] = df_c.apply(lambda x: f"Parcela {int(x['installment_number'])}/{int(x['installment_total'])}", axis=1)
                    exibicao_c = df_c[['date', 'card_name', 'category', 'Status', 'amount']].sort_values(by='date')
                    st.dataframe(exibicao_c.rename(columns={'date':'Vencimento', 'card_name':'Cartão', 'category':'Item', 'amount':'Valor'}), use_container_width=True)
                else: st.info("Nenhuma despesa em cartão identificada.")

        # --- ABA 4: CONFIGURAÇÕES ---
        with tab_config:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("➕ Novo Cartão")
                n_c = st.text_input("Nome do Cartão")
                if st.button("Adicionar Cartão"):
                    if n_c:
                        supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": n_c}).execute()
                        st.rerun()
            with c2:
                st.subheader("🗑️ Excluir Cartão")
                if lista_cartoes:
                    del_c = st.selectbox("Selecione o cartão para remover", lista_cartoes)
                    if st.button("Remover Cartão e Dados"):
                        # Deleta transações e depois o cartão
                        supabase.table("profile_transactions").delete().eq("card_name", del_c).eq("user_email", st.session_state.user_email).execute()
                        supabase.table("my_cards").delete().eq("card_name", del_c).eq("user_email", st.session_state.user_email).execute()
                        st.success(f"Cartão {del_c} removido!")
                        st.rerun()

if __name__ == "__main__":
    main()
