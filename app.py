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
    st.error("Erro nas credenciais. Verifique os Secrets.")
    st.stop()

if "logado" not in st.session_state:
    st.session_state.logado = False

# --- FUNÇÃO PARA PROJETAR MESES ---
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
            except: st.sidebar.error("Falha no login.")
    else:
        st.sidebar.success(f"Conectado: {st.session_state.user_email}")
        if st.sidebar.button("Sair"):
            st.session_state.logado = False
            st.rerun()

        # --- BUSCA DE DADOS ---
        # 1. Busca cartões
        res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        
        # 2. Busca transações
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        tab_lanc, tab_extrato, tab_visao_cartao, tab_config = st.tabs(["➕ Lançar", "📊 Extrato Mensal", "💳 Detalhe por Cartão", "⚙️ Ajustes"])

        # --- ABA 1: LANÇAMENTOS (CORREÇÃO DE SELEÇÃO DE CARTÃO) ---
        with tab_lanc:
            with st.form("form_registro", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
                    desc = st.text_input("Descrição")
                    metodo = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"])
                with c2:
                    valor_total = st.number_input("Valor Total (R$)", min_value=0.0)
                    data_compra = st.date_input("Data", datetime.now())
                    
                    # Variáveis de controle
                    c_escolhido = None
                    n_parcelas = 1
                    
                    if metodo == "Cartão de Crédito":
                        if lista_cartoes:
                            c_escolhido = st.selectbox("Qual Cartão?", lista_cartoes)
                            n_parcelas = st.number_input("Parcelas", min_value=1, step=1)
                        else:
                            st.warning("⚠️ Cadastre um cartão primeiro na aba Ajustes!")

                if st.form_submit_button("Salvar"):
                    if metodo == "Cartão de Crédito" and not c_escolhido:
                        st.error("Selecione um cartão para prosseguir.")
                    else:
                        v_parcela = valor_total / int(n_parcelas)
                        for i in range(int(n_parcelas)):
                            venc = add_months(data_compra, i)
                            supabase.table("profile_transactions").insert({
                                "user_email": st.session_state.user_email,
                                "type": tipo,
                                "category": desc,
                                "amount": v_parcela,
                                "date": venc.strftime("%Y-%m-%d"),
                                "payment_method": metodo,
                                "card_name": c_escolhido,
                                "installment_total": int(n_parcelas),
                                "installment_number": i + 1
                            }).execute()
                        st.success("Lançamento concluído!")
                        st.rerun()

        # --- ABA 2: EXTRATO MENSAL ---
        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês'] = df['date'].dt.strftime('%m/%Y')
                mes_sel = st.selectbox("Mês", sorted(df['Mês'].unique(), reverse=True))
                
                f = df[df['Mês'] == mes_sel].copy()
                
                # Formatação da informação da parcela
                def format_info(row):
                    if row['payment_method'] == "Cartão de Crédito":
                        total = int(row['installment_total']) if pd.notnull(row['installment_total']) else 1
                        atual = int(row['installment_number']) if pd.notnull(row['installment_number']) else 1
                        return f"Parcela {atual} de {total}"
                    return "À vista"

                f['Parcela Info'] = f.apply(format_info, axis=1)
                
                st.dataframe(f[['date', 'category', 'Parcela Info', 'card_name', 'amount']].rename(
                    columns={'date':'Vencimento', 'card_name':'Cartão', 'amount':'Valor (R$)'}
                ), use_container_width=True)
            else: st.info("Sem dados.")

        # --- ABA 3: DETALHAMENTO POR CARTÃO ---
        with tab_visao_cartao:
            if not df.empty:
                df_c = df[df['payment_method'] == "Cartão de Crédito"].copy()
                if not df_c.empty:
                    sel_c = st.selectbox("Filtrar Cartão", ["Todos"] + lista_cartoes)
                    if sel_c != "Todos":
                        df_c = df_c[df_c['card_name'] == sel_c]
                    
                    # Cálculo de parcelas restantes
                    df_c['Total'] = df_c['installment_total'].fillna(1).astype(int)
                    df_c['Atual'] = df_c['installment_number'].fillna(1).astype(int)
                    df_c['Faltam'] = df_c['Total'] - df_c['Atual']
                    
                    df_c['Status'] = df_c.apply(lambda x: f"{x['Atual']}/{x['Total']} (Faltam {x['Faltam']})", axis=1)
                    
                    view = df_c[['date', 'card_name', 'category', 'Status', 'amount']].sort_values(by='date')
                    st.dataframe(view.rename(columns={'date':'Vencimento', 'amount':'Valor Parcela'}), use_container_width=True)
                else: st.info("Nenhuma despesa no cartão.")

        # --- ABA 4: AJUSTES ---
        with tab_config:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("💳 Cartões")
                n_c = st.text_input("Novo Cartão")
                if st.button("Adicionar"):
                    supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": n_c}).execute()
                    st.rerun()
                
                if lista_cartoes:
                    exc_c = st.selectbox("Remover Cartão", lista_cartoes)
                    if st.button("🗑️ Excluir Cartão e Dados"):
                        supabase.table("profile_transactions").delete().eq("card_name", exc_c).eq("user_email", st.session_state.user_email).execute()
                        supabase.table("my_cards").delete().eq("card_name", exc_c).eq("user_email", st.session_state.user_email).execute()
                        st.rerun()
            
            with col2:
                st.subheader("⚙️ Manutenção")
                if not df.empty:
                    opcoes = {f"{r['id']} | {r['category']} (R$ {r['amount']:.2f})": r['id'] for _, r in df.iterrows()}
                    id_del = st.selectbox("Excluir Lançamento Único", list(opcoes.keys()))
                    if st.button("Apagar Registro"):
                        supabase.table("profile_transactions").delete().eq("id", opcoes[id_del]).execute()
                        st.rerun()

if __name__ == "__main__":
    main()
