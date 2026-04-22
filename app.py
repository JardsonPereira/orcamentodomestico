import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta

# --- CONEXÃO SEGURA ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Erro nos Secrets: Verifique SUPABASE_URL e SUPABASE_KEY.")
    st.stop()

# --- ESTADO DA SESSÃO ---
if "logado" not in st.session_state:
    st.session_state.logado = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

def main():
    st.set_page_config(page_title="Orçamento Doméstico", layout="wide", page_icon="💰")
    
    if not st.session_state.logado:
        st.sidebar.title("🔐 Acesso")
        opcao = st.sidebar.radio("Escolha", ["Login", "Cadastrar"])
        email = st.sidebar.text_input("E-mail")
        senha = st.sidebar.text_input("Senha", type='password')
        
        if st.sidebar.button("Entrar"):
            try:
                if opcao == "Login":
                    supabase.auth.sign_in_with_password({"email": email, "password": senha})
                else:
                    supabase.auth.sign_up({"email": email, "password": senha})
                    st.info("Cadastro realizado!")
                st.session_state.logado = True
                st.session_state.user_email = email
                st.rerun()
            except:
                st.error("Falha na autenticação.")
    else:
        st.sidebar.success(f"Logado: {st.session_state.user_email}")
        if st.sidebar.button("Sair"):
            st.session_state.logado = False
            st.rerun()

        st.title("🏡 Controle Financeiro Jardson")
        
        tab_lanc, tab_cards, tab_relat = st.tabs(["➕ Lançamento", "💳 Meus Cartões", "📊 Extrato"])

        # --- ABA CARTÕES ---
        with tab_cards:
            st.subheader("Gerenciar Cartões de Crédito")
            with st.form("add_card"):
                nome_c = st.text_input("Nome do Cartão (ex: Nubank, Inter)")
                if st.form_submit_button("Salvar Cartão"):
                    if nome_c:
                        supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": nome_c}).execute()
                        st.success("Cartão adicionado!")
                        st.rerun()
            
            res_c = supabase.table("my_cards").select("card_name").eq("user_email", st.session_state.user_email).execute()
            lista_cartoes = [item['card_name'] for item in res_c.data]
            st.write("**Seus cartões:**", ", ".join(lista_cartoes) if lista_cartoes else "Nenhum cartão cadastrado.")

        # --- ABA LANÇAMENTO ---
        with tab_lanc:
            with st.form("financeiro", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
                    desc = st.text_input("O que é? (Descrição)")
                    metodo = st.selectbox("Forma de Pagamento", ["PIX/Dinheiro", "Cartão de Crédito"])
                with c2:
                    valor = st.number_input("Valor Total (R$)", min_value=0.0, step=0.01)
                    data_compra = st.date_input("Data", datetime.now())
                    
                    cartao_escolhido = None
                    parcelas = 1
                    if metodo == "Cartão de Crédito":
                        cartao_escolhido = st.selectbox("Escolha o Cartão", lista_cartoes)
                        parcelas = st.number_input("Parcelas", min_value=1, max_value=48, value=1)

                if st.form_submit_button("Registrar"):
                    v_parc = valor / parcelas
                    for i in range(parcelas):
                        # Soma 30 dias para cada parcela posterior
                        vencimento = data_compra + timedelta(days=30 * i)
                        supabase.table("profile_transactions").insert({
                            "user_email": st.session_state.user_email,
                            "type": tipo,
                            "category": f"{desc} ({i+1}/{parcelas})" if parcelas > 1 else desc,
                            "amount": v_parc,
                            "date": vencimento.strftime("%Y-%m-%d"),
                            "payment_method": metodo,
                            "card_name": cartao_escolhido
                        }).execute()
                    st.success("Lançamento concluído!")

        # --- ABA RELATÓRIO ---
        with tab_relat:
            res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
            df = pd.DataFrame(res_f.data)
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês/Ano'] = df['date'].dt.strftime('%m/%Y')
                mes_sel = st.selectbox("Mês", sorted(df['Mês/Ano'].unique(), reverse=True))
                
                filtro = df[df['Mês/Ano'] == mes_sel].copy()
                filtro['Receita'] = filtro.apply(lambda x: x['amount'] if x['type'] == 'Receita' else 0, axis=1)
                filtro['Despesa'] = filtro.apply(lambda x: x['amount'] if x['type'] == 'Despesa' else 0, axis=1)
                
                col_r, col_d, col_s = st.columns(3)
                col_r.metric("Receitas", f"R$ {filtro['Receita'].sum():,.2f}")
                col_d.metric("Despesas", f"R$ {filtro['Despesa'].sum():,.2f}")
                col_s.metric("Saldo", f"R$ {filtro['Receita'].sum() - filtro['Despesa'].sum():,.2f}")
                
                st.dataframe(filtro[['date', 'category', 'payment_method', 'card_name', 'Receita', 'Despesa']], use_container_width=True)
            else:
                st.info("Nenhum dado lançado ainda.")

if __name__ == "__main__":
    main()
