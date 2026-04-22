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
    st.error("Erro nas credenciais do Supabase nos Secrets.")
    st.stop()

# --- ESTADO DA SESSÃO ---
if "logado" not in st.session_state:
    st.session_state.logado = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

# --- FUNÇÃO PARA CALCULAR MESES (PARCELAS) ---
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
        col_l, col_c = st.sidebar.columns(2)
        
        if col_l.button("Entrar"):
            try:
                supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.logado = True
                st.session_state.user_email = email
                st.rerun()
            except: st.error("Login inválido")
            
        if col_c.button("Cadastrar"):
            try:
                supabase.auth.sign_up({"email": email, "password": senha})
                st.info("Cadastro realizado! Tente logar.")
            except: st.error("Erro ao cadastrar")
    else:
        # MENU LATERAL
        st.sidebar.success(f"Usuário: {st.session_state.user_email}")
        if st.sidebar.button("Sair"):
            st.session_state.logado = False
            st.rerun()

        st.title("💰 Controle Financeiro Jardson")

        # BUSCAR CARTÕES ATUALIZADOS
        res_c = supabase.table("my_cards").select("card_name").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]

        tab_lanc, tab_extrato, tab_visao_cartao = st.tabs(["➕ Lançamentos", "📊 Extrato Mensal", "💳 Detalhe de Cartões"])

        with tab_lanc:
            # --- NOVA OPÇÃO: CADASTRAR CARTÃO DENTRO DA ABA ---
            with st.expander("🆕 Cadastrar Novo Cartão de Crédito"):
                nome_novo_cartao = st.text_input("Nome do Cartão (ex: Nubank, Inter)")
                if st.button("Salvar Novo Cartão"):
                    if nome_novo_cartao:
                        supabase.table("my_cards").insert({
                            "user_email": st.session_state.user_email, 
                            "card_name": nome_novo_cartao
                        }).execute()
                        st.success(f"Cartão {nome_novo_cartao} cadastrado!")
                        st.rerun() # Atualiza a lista de opções imediatamente

            st.markdown("---")
            st.subheader("Registrar Nova Movimentação")
            
            with st.form("form_financeiro", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
                    desc = st.text_input("Descrição (O que você comprou/recebeu?)")
                    metodo = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"])
                
                with c2:
                    valor_total = st.number_input("Valor Total (R$)", min_value=0.0, format="%.2f")
                    data_base = st.date_input("Data do Lançamento", datetime.now())
                    
                    cartao_sel = None
                    parcelas = 1
                    
                    if metodo == "Cartão de Crédito":
                        if lista_cartoes:
                            cartao_sel = st.selectbox("Selecione o Cartão", lista_cartoes)
                            parcelas = st.number_input("Quantidade de Parcelas", min_value=1, max_value=48, value=1)
                        else:
                            st.warning("⚠️ Cadastre um cartão acima primeiro!")
                
                if st.form_submit_button("Finalizar Lançamento"):
                    if metodo == "Cartão de Crédito" and not cartao_sel:
                        st.error("Erro: Selecione um cartão.")
                    else:
                        valor_parc = valor_total / parcelas
                        for i in range(parcelas):
                            data_vencimento = add_months(data_base, i)
                            supabase.table("profile_transactions").insert({
                                "user_email": st.session_state.user_email,
                                "type": tipo,
                                "category": f"{desc} ({i+1}/{parcelas})" if parcelas > 1 else desc,
                                "amount": valor_parc,
                                "date": data_vencimento.strftime("%Y-%m-%d"),
                                "payment_method": metodo,
                                "card_name": cartao_sel,
                                "installment_total": parcelas,
                                "installment_number": i + 1
                            }).execute()
                        st.success("Lançamento(s) realizado(s) com sucesso!")

        with tab_extrato:
            res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
            df = pd.DataFrame(res_f.data)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês'] = df['date'].dt.strftime('%m/%Y')
                mes_sel = st.selectbox("Mês de Referência", sorted(df['Mês'].unique(), reverse=True))
                
                f = df[df['Mês'] == mes_sel].copy()
                f['Rec'] = f.apply(lambda x: x['amount'] if x['type'] == 'Receita' else 0, axis=1)
                f['Desp'] = f.apply(lambda x: x['amount'] if x['type'] == 'Despesa' else 0, axis=1)
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Receitas", f"R$ {f['Rec'].sum():,.2f}")
                c2.metric("Despesas", f"R$ {f['Desp'].sum():,.2f}")
                c3.metric("Saldo", f"R$ {f['Rec'].sum() - f['Desp'].sum():,.2f}")
                
                st.dataframe(f[['date', 'category', 'payment_method', 'card_name', 'Rec', 'Desp']], use_container_width=True)

        with tab_visao_cartao:
            st.subheader("💳 Detalhamento de Compras no Cartão")
            if not df.empty:
                df_c = df[df['payment_method'] == "Cartão de Crédito"].copy()
                if not df_c.empty:
                    df_c['Parcela'] = df_c['installment_number'].astype(str) + "/" + df_c['installment_total'].astype(str)
                    view = df_c[['date', 'card_name', 'category', 'Parcela', 'amount']].sort_values(by='date')
                    st.dataframe(view.rename(columns={'date':'Vencimento', 'card_name':'Cartão', 'category':'Item', 'amount':'Valor'}), use_container_width=True)
                else:
                    st.info("Nenhuma despesa no cartão encontrada.")

if __name__ == "__main__":
    main()
