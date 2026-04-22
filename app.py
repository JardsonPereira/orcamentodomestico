import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
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

# --- FUNÇÃO PARA PULAR MESES CORRETAMENTE ---
def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)

def main():
    st.set_page_config(page_title="Gestão Financeira Jardson", layout="wide", page_icon="💳")
    
    if not st.session_state.logado:
        # Área de Login
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
        st.sidebar.success(f"Usuário: {st.session_state.user_email}")
        if st.sidebar.button("Sair"):
            st.session_state.logado = False
            st.rerun()

        # BUSCA DE DADOS ATUALIZADA
        res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        tab_lanc, tab_extrato, tab_visao_cartao, tab_config = st.tabs(["➕ Novo Lançamento", "📊 Extrato Mensal", "💳 Detalhe por Cartão", "⚙️ Configurações"])

        # --- ABA 1: LANÇAMENTOS ---
        with tab_lanc:
            with st.form("form_novo", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
                    desc = st.text_input("Descrição")
                    metodo = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"])
                with col2:
                    valor_total = st.number_input("Valor Total (R$)", min_value=0.0)
                    data_compra = st.date_input("Data da Compra", datetime.now())
                    if metodo == "Cartão de Crédito":
                        # CRÍTICO: Garante que o cartão selecionado seja o usado
                        cartao_escolhido = st.selectbox("Selecione o Cartão", lista_cartoes)
                        num_parcelas = st.number_input("Número de Parcelas", min_value=1, step=1, value=1)
                    else:
                        cartao_escolhido, num_parcelas = None, 1
                
                if st.form_submit_button("Registrar"):
                    v_parc = valor_total / int(num_parcelas)
                    for i in range(int(num_parcelas)):
                        vencimento = add_months(data_compra, i)
                        supabase.table("profile_transactions").insert({
                            "user_email": st.session_state.user_email,
                            "type": tipo, 
                            "category": desc, 
                            "amount": v_parc,
                            "date": vencimento.strftime("%Y-%m-%d"),
                            "payment_method": metodo, 
                            "card_name": cartao_escolhido, # Registra o cartão correto
                            "installment_total": int(num_parcelas), 
                            "installment_number": i + 1
                        }).execute()
                    st.success("Lançamento concluído com sucesso!")
                    st.rerun()

        # --- ABA 2: EXTRATO MENSAL ---
        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['MesAno'] = df['date'].dt.strftime('%m/%Y')
                mes_sel = st.selectbox("Mês de Referência", sorted(df['MesAno'].unique(), reverse=True))
                
                f = df[df['MesAno'] == mes_sel].copy()
                f['Info'] = f.apply(lambda x: f"Parcela {int(x['installment_number'])} de {int(x['installment_total'])}" 
                                     if x['payment_method'] == "Cartão de Crédito" else "À vista", axis=1)
                
                st.dataframe(f[['date', 'category', 'Info', 'card_name', 'amount']].rename(
                    columns={'date':'Vencimento', 'card_name':'Cartão', 'amount':'Valor (R$)'}
                ), use_container_width=True)
            else: st.info("Sem dados.")

        # --- ABA 3: DETALHAMENTO POR CARTÃO (STATUS DAS PARCELAS) ---
        with tab_visao_cartao:
            st.subheader("💳 Situação das Parcelas por Cartão")
            if not df.empty:
                df_c = df[df['payment_method'] == "Cartão de Crédito"].copy()
                if not df_c.empty:
                    # Filtro de Cartão
                    sel_c = st.selectbox("Filtrar por Cartão", ["Todos"] + lista_cartoes)
                    if sel_c != "Todos":
                        df_c = df_c[df_c['card_name'] == sel_c]
                    
                    # Cálculo de quanto falta
                    df_c['Faltam'] = df_c['installment_total'].astype(int) - df_c['installment_number'].astype(int)
                    df_c['Status'] = df_c.apply(lambda x: f"Paga {int(x['installment_number'])}/{int(x['installment_total'])} (Faltam {int(x['Faltam'])})", axis=1)
                    
                    exibicao = df_c[['date', 'card_name', 'category', 'Status', 'amount']].sort_values(by='date')
                    st.dataframe(exibicao.rename(columns={'date':'Próximo Vencimento', 'amount':'Valor Parcela'}), use_container_width=True)
                else: st.info("Nenhuma despesa em cartão.")

        # --- ABA 4: CONFIGURAÇÕES ---
        with tab_config:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Gerenciar Cartões")
                novo_c = st.text_input("Novo Cartão")
                if st.button("Adicionar"):
                    supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": novo_c}).execute()
                    st.rerun()
                
                if lista_cartoes:
                    exc_c = st.selectbox("Excluir Cartão", lista_cartoes)
                    if st.button("🗑️ Remover Cartão e Lançamentos"):
                        supabase.table("profile_transactions").delete().eq("card_name", exc_c).execute()
                        supabase.table("my_cards").delete().eq("card_name", exc_c).execute()
                        st.rerun()
            with c2:
                st.subheader("Remover Lançamento Único")
                if not df.empty:
                    opcoes = {f"{r['id']} | {r['category']} (R$ {r['amount']:.2f})": r['id'] for _, r in df.iterrows()}
                    id_del = st.selectbox("Escolha o item", list(opcoes.keys()))
                    if st.button("Apagar Registro"):
                        supabase.table("profile_transactions").delete().eq("id", opcoes[id_del]).execute()
                        st.rerun()

if __name__ == "__main__":
    main()
