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
    st.error("Erro nas credenciais do Supabase. Verifique os Secrets.")
    st.stop()

# --- ESTADO DA SESSÃO ---
if "logado" not in st.session_state:
    st.session_state.logado = False

# --- FUNÇÃO PARA CALCULAR O MÊS DAS PARCELAS ---
def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)

def main():
    st.set_page_config(page_title="Gestão Financeira Jardson", layout="wide", page_icon="💳")
    
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
        st.sidebar.success(f"Conectado: {st.session_state.user_email}")
        if st.sidebar.button("Sair"):
            st.session_state.logado = False
            st.rerun()

        # BUSCA DE DADOS
        res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        tab_lanc, tab_extrato, tab_visao_cartao, tab_config = st.tabs(["➕ Novo Lançamento", "📊 Extrato Mensal", "💳 Detalhamento por Cartão", "⚙️ Ajustes"])

        # --- ABA 1: LANÇAR ---
        with tab_lanc:
            with st.form("form_f", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
                    desc = st.text_input("Descrição da Compra")
                    metodo = st.selectbox("Forma", ["Dinheiro/PIX", "Cartão de Crédito"])
                with c2:
                    valor_total = st.number_input("Valor Total (R$)", min_value=0.0)
                    data_compra = st.date_input("Data da Compra", datetime.now())
                    if metodo == "Cartão de Crédito":
                        cartao_sel = st.selectbox("Escolha o Cartão", lista_cartoes)
                        parcelas = st.number_input("Qtd de Parcelas", min_value=1, value=1)
                    else:
                        cartao_sel, parcelas = None, 1
                
                if st.form_submit_button("Registrar"):
                    v_parc = valor_total / int(parcelas)
                    for i in range(int(parcelas)):
                        vencimento = add_months(data_compra, i)
                        supabase.table("profile_transactions").insert({
                            "user_email": st.session_state.user_email,
                            "type": tipo, "category": desc, "amount": v_parc,
                            "date": vencimento.strftime("%Y-%m-%d"),
                            "payment_method": metodo, "card_name": cartao_sel,
                            "installment_total": int(parcelas), "installment_number": i + 1
                        }).execute()
                    st.success(f"Registrado: {parcelas} parcela(s) de R$ {v_parc:.2f}")
                    st.rerun()

        # --- ABA 2: EXTRATO MENSAL ---
        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês'] = df['date'].dt.strftime('%m/%Y')
                mes_sel = st.selectbox("Selecionar Mês", sorted(df['Mês'].unique(), reverse=True))
                
                f = df[df['Mês'] == mes_sel].copy()
                f['Status'] = f.apply(lambda x: f"Parcela {int(x['installment_number'])} de {int(x['installment_total'])}" 
                                     if x['payment_method'] == "Cartão de Crédito" else "À vista", axis=1)
                
                # Cálculo de Totais
                rec = f[f['type'] == 'Receita']['amount'].sum()
                desp = f[f['type'] == 'Despesa']['amount'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Receitas", f"R$ {rec:,.2f}")
                c2.metric("Despesas", f"R$ {desp:,.2f}")
                c3.metric("Saldo", f"R$ {rec-desp:,.2f}")
                
                st.dataframe(f[['date', 'category', 'Status', 'card_name', 'amount']].rename(
                    columns={'date':'Vencimento', 'category':'Item', 'amount':'Valor (R$)', 'card_name':'Cartão'}
                ), use_container_width=True)
            else: st.info("Sem dados.")

        # --- ABA 3: DETALHAMENTO POR CARTÃO (NOVA) ---
        with tab_visao_cartao:
            st.subheader("📊 Raio-X dos Cartões")
            if not df.empty:
                df_card = df[df['payment_method'] == "Cartão de Crédito"].copy()
                if not df_card.empty:
                    # Filtro por cartão específico
                    cartao_filtro = st.selectbox("Filtrar Cartão", ["Todos"] + lista_cartoes)
                    if cartao_filtro != "Todos":
                        df_card = df_card[df_card['card_name'] == cartao_filtro]
                    
                    # Cálculo de parcelas restantes
                    df_card['Faltam'] = df_card['installment_total'] - df_card['installment_number']
                    df_card['Progresso'] = df_card.apply(lambda x: f"{int(x['installment_number'])}/{int(x['installment_total'])} (Faltam {int(x['Faltam'])})", axis=1)
                    
                    # Ordenar por data
                    df_card = df_card.sort_values(by='date')
                    
                    resumo = df_card[['date', 'card_name', 'category', 'Progresso', 'amount']].rename(
                        columns={'date':'Data Vencimento', 'card_name':'Cartão', 'category':'Descrição', 'amount':'Valor da Parcela'}
                    )
                    st.dataframe(resumo, use_container_width=True)
                    
                    total_pendente = df_card['amount'].sum()
                    st.info(f"💰 **Total a pagar neste filtro:** R$ {total_pendente:,.2f}")
                else:
                    st.info("Nenhuma despesa em cartão encontrada.")

        # --- ABA 4: AJUSTES (CONFIGURAÇÕES E EXCLUSÕES) ---
        with tab_config:
            col_1, col_2 = st.columns(2)
            with col_1:
                st.subheader("➕ Novo Cartão")
                novo_c = st.text_input("Nome do Cartão")
                if st.button("Salvar Cartão"):
                    if novo_c:
                        supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": novo_c}).execute()
                        st.rerun()
            
            with col_2:
                st.subheader("🗑️ Excluir Dados")
                # Excluir Cartão
                if lista_cartoes:
                    del_c = st.selectbox("Remover Cartão", lista_cartoes)
                    if st.button("Confirmar Exclusão do Cartão"):
                        # Deleta transações e depois o cartão
                        supabase.table("profile_transactions").delete().eq("card_name", del_c).eq("user_email", st.session_state.user_email).execute()
                        supabase.table("my_cards").delete().eq("card_name", del_c).eq("user_email", st.session_state.user_email).execute()
                        st.rerun()
                
                st.markdown("---")
                # Excluir Lançamento Individual
                if not df.empty:
                    st.write("Excluir Lançamento Único")
                    opcoes_del = {f"{r['id']} | {r['category']} (R$ {r['amount']:.2f})": r['id'] for _, r in df.iterrows()}
                    id_del = st.selectbox("Escolha o item para apagar", list(opcoes_del.keys()))
                    if st.button("🗑️ Apagar este item"):
                        supabase.table("profile_transactions").delete().eq("id", opcoes_del[id_del]).execute()
                        st.rerun()

if __name__ == "__main__":
    main()
