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
        # BUSCA DE DADOS (FORA DO FORMULÁRIO)
        res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        tab_lanc, tab_extrato, tab_cartao, tab_config = st.tabs(["➕ Lançar", "📊 Extrato", "💳 Visão Cartão", "⚙️ Config"])

        with tab_lanc:
            st.subheader("Novo Lançamento")
            # O segredo é garantir que as variáveis do formulário sejam únicas
            with st.form("form_financeiro_v3", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
                    desc = st.text_input("Descrição da Compra")
                    metodo = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"])
                with col2:
                    valor_total = st.number_input("Valor Total (R$)", min_value=0.01, step=0.01)
                    data_origem = st.date_input("Data da Operação", datetime.now())
                    
                    cartao_vontade = None
                    total_parc = 1
                    
                    if metodo == "Cartão de Crédito":
                        if lista_cartoes:
                            # Adicionamos uma KEY para garantir que o Streamlit não se perca
                            cartao_vontade = st.selectbox("Escolha o Cartão", lista_cartoes, key="sel_cartao_input")
                            total_parc = st.number_input("Quantidade de Parcelas", min_value=1, step=1)
                        else:
                            st.warning("Cadastre um cartão primeiro!")

                # BOTÃO DE SALVAR
                enviar = st.form_submit_button("Finalizar Lançamento")
                
                if enviar:
                    if valor_total <= 0:
                        st.error("O valor deve ser maior que zero.")
                    elif metodo == "Cartão de Crédito" and not cartao_vontade:
                        st.error("Selecione um cartão válido.")
                    else:
                        v_parcela = valor_total / int(total_parc)
                        
                        # Loop de inserção
                        for i in range(int(total_parc)):
                            data_venc = add_months(data_origem, i)
                            
                            dados_inserir = {
                                "user_email": st.session_state.user_email,
                                "type": tipo,
                                "category": desc,
                                "amount": round(v_parcela, 2),
                                "date": data_venc.strftime("%Y-%m-%d"),
                                "payment_method": metodo,
                                "card_name": cartao_vontade, # Aqui garante o cartão escolhido
                                "installment_total": int(total_parc),
                                "installment_number": i + 1
                            }
                            
                            # Inserção no Banco
                            supabase.table("profile_transactions").insert(dados_inserir).execute()
                        
                        st.success(f"Sucesso! Lançado em {cartao_vontade if cartao_vontade else 'Dinheiro'}")
                        st.rerun()

        # --- ABA VISÃO CARTÃO (COM CÁLCULO DE PARCELAS RESTANTES) ---
        with tab_cartao:
            if not df.empty:
                df_c = df[df['payment_method'] == "Cartão de Crédito"].copy()
                if not df_c.empty:
                    # Garantir que os tipos são inteiros para o cálculo
                    df_c['installment_total'] = df_c['installment_total'].fillna(1).astype(int)
                    df_c['installment_number'] = df_c['installment_number'].fillna(1).astype(int)
                    
                    df_c['Faltam'] = df_c['installment_total'] - df_c['installment_number']
                    df_c['Parcela Status'] = df_c.apply(lambda x: f"{x['installment_number']}/{x['installment_total']} (Faltam {x['Faltam']})", axis=1)
                    
                    st.dataframe(df_c[['date', 'card_name', 'category', 'Parcela Status', 'amount']].sort_values(by='date'))
                else:
                    st.info("Sem lançamentos de cartão.")

        # --- ABA CONFIG (PARA LIMPAR TESTES ERRADOS) ---
        with tab_config:
            st.subheader("Limpeza de Dados")
            if not df.empty:
                if st.button("🗑️ Apagar TODOS os Lançamentos (Limpar Testes)"):
                    supabase.table("profile_transactions").delete().eq("user_email", st.session_state.user_email).execute()
                    st.rerun()

if __name__ == "__main__":
    main()
