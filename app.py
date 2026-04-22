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

# --- FUNÇÃO PARA PROJETAR MESES ---
def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)

def main():
    st.set_page_config(page_title="Gestão Financeira Jardson", layout="wide", page_icon="💰")
    
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

        # BUSCA DE DADOS INICIAL
        res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        tab_lanc, tab_extrato, tab_gerenciar, tab_config = st.tabs(["➕ Lançar", "📊 Extrato Mensal", "⚙️ Gerenciar Dados", "💳 Cartões"])

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
                    data_base = st.date_input("Data", datetime.now())
                    if metodo == "Cartão de Crédito":
                        cartao_sel = st.selectbox("Cartão", lista_cartoes)
                        parcelas = st.number_input("Parcelas", min_value=1, value=1)
                    else:
                        cartao_sel, parcelas = None, 1
                
                if st.form_submit_button("Salvar"):
                    v_parc = valor_total / int(parcelas)
                    for i in range(int(parcelas)):
                        vencimento = add_months(data_base, i)
                        supabase.table("profile_transactions").insert({
                            "user_email": st.session_state.user_email,
                            "type": tipo, "category": desc, "amount": v_parc,
                            "date": vencimento.strftime("%Y-%m-%d"),
                            "payment_method": metodo, "card_name": cartao_sel,
                            "installment_total": int(parcelas), "installment_number": i + 1
                        }).execute()
                    st.success("Lançado com sucesso!")
                    st.rerun()

        # --- ABA 2: EXTRATO ---
        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês/Ano'] = df['date'].dt.strftime('%m/%Y')
                mes_sel = st.selectbox("Mês", sorted(df['Mês/Ano'].unique(), reverse=True))
                f = df[df['Mês/Ano'] == mes_sel].copy()
                
                f['Info'] = f.apply(lambda x: f"Parcela {int(x['installment_number'])} de {int(x['installment_total'])}" 
                                   if x['payment_method'] == "Cartão de Crédito" else x['payment_method'], axis=1)
                
                f['Receita'] = f.apply(lambda x: x['amount'] if x['type'] == 'Receita' else 0, axis=1)
                f['Despesa'] = f.apply(lambda x: x['amount'] if x['type'] == 'Despesa' else 0, axis=1)
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Receitas", f"R$ {f['Receita'].sum():,.2f}")
                c2.metric("Despesas", f"R$ {f['Despesa'].sum():,.2f}")
                c3.metric("Saldo", f"R$ {f['Receita'].sum() - f['Despesa'].sum():,.2f}")
                
                st.dataframe(f[['date', 'category', 'Info', 'card_name', 'Receita', 'Despesa']], use_container_width=True)
            else: st.info("Sem dados.")

        # --- ABA 3: GERENCIAR (EDITAR E EXCLUIR LANÇAMENTOS) ---
        with tab_gerenciar:
            st.subheader("Excluir ou Editar Lançamentos Individuais")
            if not df.empty:
                # Criar uma lista para seleção amigável
                df_view = df.sort_values(by='date', ascending=False)
                opcoes = {f"{row['id']} | {row['date'].strftime('%d/%m/%Y')} | {row['category']} (R$ {row['amount']:.2f})": row['id'] for _, row in df_view.iterrows()}
                
                escolha = st.selectbox("Selecione o lançamento que deseja apagar ou editar:", list(opcoes.keys()))
                id_alvo = opcoes[escolha]
                
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if st.button("🗑️ Excluir este Lançamento"):
                        supabase.table("profile_transactions").delete().eq("id", id_alvo).execute()
                        st.warning(f"Lançamento {id_alvo} removido!")
                        st.rerun()
                
                with col_btn2:
                    st.info("Para editar, basta excluir e lançar novamente com os dados corretos.")
            else:
                st.info("Nenhum lançamento disponível para excluir.")

        # --- ABA 4: CONFIGURAÇÕES DE CARTÃO ---
        with tab_config:
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("➕ Novo Cartão")
                n_c = st.text_input("Nome")
                if st.button("Adicionar"):
                    if n_c:
                        supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": n_c}).execute()
                        st.rerun()
            with col_b:
                st.subheader("🗑️ Excluir Cartão")
                if lista_cartoes:
                    del_c = st.selectbox("Cartão para remover", lista_cartoes)
                    if st.button("Remover Cartão e Tudo dele"):
                        # Remove transações do cartão primeiro e depois o cartão
                        supabase.table("profile_transactions").delete().eq("card_name", del_c).eq("user_email", st.session_state.user_email).execute()
                        supabase.table("my_cards").delete().eq("card_name", del_c).eq("user_email", st.session_state.user_email).execute()
                        st.success(f"Cartão {del_c} e seus dados foram excluídos.")
                        st.rerun()

if __name__ == "__main__":
    main()
