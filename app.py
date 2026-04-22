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
            except: st.error("Erro no login.")
    else:
        # --- BUSCA DE DADOS ---
        res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        tab_lanc, tab_extrato, tab_cartao, tab_gerenciar, tab_config = st.tabs(["➕ Lançar", "📊 Extrato", "💳 Visão Cartão", "⚙️ Editar/Excluir", "🛠️ Ajustes"])

        # --- ABA 1: LANÇAR ---
        with tab_lanc:
            st.subheader("Novo Lançamento")
            col_metodo, col_cartao = st.columns(2)
            with col_metodo:
                metodo_selecionado = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"], key="metodo_pag")
            
            cartao_vontade = None
            if metodo_selecionado == "Cartão de Crédito":
                with col_cartao:
                    if lista_cartoes:
                        cartao_vontade = st.selectbox("Qual Cartão?", lista_cartoes, key="card_ativo")
                    else:
                        st.warning("Cadastre um cartão na aba Ajustes.")

            with st.form("meu_formulario_lancamento", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
                    desc = st.text_input("Descrição")
                with c2:
                    valor_total_input = st.number_input("Valor Total (R$)", min_value=0.01, step=0.01)
                    data_origem = st.date_input("Data", datetime.now())
                    total_parc = st.number_input("Parcelas", min_value=1, step=1) if metodo_selecionado == "Cartão de Crédito" else 1

                if st.form_submit_button("Confirmar e Salvar"):
                    u_email = st.session_state.get('user_email')
                    v_parcela = valor_total_input / int(total_parc)
                    for i in range(int(total_parc)):
                        data_venc = add_months(data_origem, i)
                        supabase.table("profile_transactions").insert({
                            "user_email": u_email, "type": tipo, "category": desc,
                            "amount": round(v_parcela, 2), "date": data_venc.strftime("%Y-%m-%d"),
                            "payment_method": metodo_selecionado, "card_name": cartao_vontade,
                            "installment_total": int(total_parc), "installment_number": i + 1
                        }).execute()
                    st.success("Registrado!")
                    st.rerun()

        # --- ABA 2: EXTRATO ---
        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês'] = df['date'].dt.strftime('%m/%Y')
                mes_sel = st.selectbox("Filtrar Mês", sorted(df['Mês'].unique(), reverse=True))
                f = df[df['Mês'] == mes_sel].copy()
                f['Receita'] = f.apply(lambda x: float(x['amount']) if x['type'] == 'Receita' else 0.0, axis=1)
                f['Despesa'] = f.apply(lambda x: float(x['amount']) if x['type'] == 'Despesa' else 0.0, axis=1)
                st.dataframe(f[['date', 'category', 'card_name', 'Receita', 'Despesa']].sort_values(by='date'), use_container_width=True)

        # --- ABA 3: VISÃO CARTÃO (CONSOLIDADA COM FORMATO 1/10 FALTAM X) ---
        with tab_cartao:
            if not df.empty:
                df_c = df[df['payment_method'] == "Cartão de Crédito"].copy()
                if not df_c.empty:
                    df_c['date'] = pd.to_datetime(df_c['date'])
                    hoje = datetime.now()
                    
                    # Agrupar para tratar a compra como um todo
                    # Usamos a descrição e o total de parcelas para identificar a compra única
                    resumo = []
                    for (desc, card, total), grupo in df_c.groupby(['category', 'card_name', 'installment_total']):
                        # Encontrar a parcela do mês atual ou a próxima a vencer
                        grupo = grupo.sort_values('date')
                        proximas = grupo[grupo['date'] >= hoje.replace(day=1)]
                        
                        if not proximas.empty:
                            parcela_atual = proximas.iloc[0]['installment_number']
                            vencimento = proximas.iloc[0]['date']
                        else:
                            parcela_atual = total # Já finalizou
                            vencimento = grupo.iloc[-1]['date']
                        
                        faltam = int(total) - int(parcela_atual)
                        status_str = f"{int(parcela_atual)}/{int(total)} (Faltam {faltam})"
                        
                        resumo.append({
                            'Próximo Venc.': vencimento,
                            'Cartão': card,
                            'Descrição': desc,
                            'Parcelas': status_str,
                            'Valor Total': grupo['amount'].sum()
                        })
                    
                    st.dataframe(pd.DataFrame(resumo).sort_values('Próximo Venc.'), use_container_width=True)
                else: st.info("Sem despesas no cartão.")

        # --- ABA 4: GERENCIAR ---
        with tab_gerenciar:
            if not df.empty:
                opcoes = {f"{r['id']} | {r['category']}": r['id'] for _, r in df.iterrows()}
                item_sel = st.selectbox("Excluir item:", list(opcoes.keys()))
                if st.button("🗑️ Confirmar Exclusão"):
                    supabase.table("profile_transactions").delete().eq("id", opcoes[item_sel]).execute()
                    st.rerun()

        # --- ABA 5: AJUSTES ---
        with tab_config:
            n_c = st.text_input("Novo Cartão")
            if st.button("Adicionar"):
                supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": n_c}).execute()
                st.rerun()

if __name__ == "__main__":
    main()
