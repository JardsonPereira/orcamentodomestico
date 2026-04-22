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
    st.error("Erro nas credenciais. Verifique os Secrets.")
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
    st.set_page_config(page_title="Gestão Financeira Jardson", layout="wide")
    
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
            except: st.error("Erro no login.")
    else:
        # BUSCA DE DADOS
        res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        tab_lanc, tab_extrato, tab_cartao, tab_config = st.tabs(["➕ Lançar", "📊 Extrato", "💳 Visão Cartão", "⚙️ Config"])

        with tab_lanc:
            st.subheader("Novo Lançamento")
            
            # --- PARTE 1: SELEÇÃO REATIVA (FORA DO FORMULÁRIO) ---
            col_metodo, col_cartao = st.columns(2)
            
            with col_metodo:
                metodo_selecionado = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"], key="metodo_pag")
            
            cartao_vontade = None
            total_parc = 1
            
            if metodo_selecionado == "Cartão de Crédito":
                with col_cartao:
                    if lista_cartoes:
                        # O cartão aparece imediatamente aqui
                        cartao_vontade = st.selectbox("Qual Cartão?", lista_cartoes, key="card_ativo")
                    else:
                        st.warning("Cadastre um cartão na aba Config.")

            # --- PARTE 2: DADOS DA COMPRA (DENTRO DO FORMULÁRIO) ---
            with st.form("meu_formulario_lancamento", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
                    desc = st.text_input("Descrição da Compra")
                with c2:
                    valor_total = st.number_input("Valor Total (R$)", min_value=0.01, step=0.01)
                    data_origem = st.date_input("Data da Operação", datetime.now())
                    if metodo_selecionado == "Cartão de Crédito":
                        total_parc = st.number_input("Quantidade de Parcelas", min_value=1, step=1)

                enviar = st.form_submit_button("Confirmar e Salvar")
                
                if enviar:
                    if metodo_selecionado == "Cartão de Crédito" and not cartao_vontade:
                        st.error("Erro: Nenhum cartão selecionado!")
                    else:
                        v_parcela = valor_total / int(total_parc)
                        
                        for i in range(int(total_parc)):
                            data_venc = add_months(data_origem, i)
                            supabase.table("profile_transactions").insert({
                                "user_email": st.session_state.user_email,
                                "type": tipo,
                                "category": desc,
                                "amount": round(v_parcela, 2),
                                "date": data_venc.strftime("%Y-%m-%d"),
                                "payment_method": metodo_selecionado,
                                "card_name": cartao_vontade,
                                "installment_total": int(total_parc),
                                "installment_number": i + 1
                            }).execute()
                        
                        st.success(f"Registrado com sucesso!")
                        st.rerun()

        # --- EXTRATO MENSAL COM STATUS DE PARCELAS ---
        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês'] = df['date'].dt.strftime('%m/%Y')
                mes_sel = st.selectbox("Mês", sorted(df['Mês'].unique(), reverse=True))
                
                f = df[df['Mês'] == mes_sel].copy()
                # Mostra "Parcela X de Y"
                f['Status'] = f.apply(lambda x: f"{int(x['installment_number'])}/{int(x['installment_total'])}" if x['payment_method'] == "Cartão de Crédito" else "À vista", axis=1)
                
                st.dataframe(f[['date', 'category', 'Status', 'card_name', 'amount']].rename(columns={'date':'Vencimento', 'amount':'Valor'}))
            else:
                st.info("Sem dados.")

        with tab_config:
            st.subheader("Configurações")
            c1, c2 = st.columns(2)
            with c1:
                n_c = st.text_input("Novo Cartão")
                if st.button("Adicionar Cartão"):
                    supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": n_c}).execute()
                    st.rerun()
            with c2:
                if st.button("🗑️ Limpar Todos os Lançamentos"):
                    supabase.table("profile_transactions").delete().eq("user_email", st.session_state.user_email).execute()
                    st.rerun()

if __name__ == "__main__":
    main()
