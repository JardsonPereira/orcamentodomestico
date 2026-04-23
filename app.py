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
    # --- CONFIGURAÇÃO MOBILE-FRIENDLY ---
    st.set_page_config(page_title="ContabilApp Pro", layout="wide", page_icon="💰")
    
    st.markdown("""
        <style>
        @media (max-width: 640px) {
            .stMetric { padding: 5px !important; }
            .stMetric div { font-size: 0.75rem !important; }
            .stTabs [data-baseweb="tab-list"] { gap: 4px; }
            .stTabs [data-baseweb="tab"] { padding: 8px 2px; font-size: 11px; }
            h1 { font-size: 1.4rem !important; }
        }
        .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold; }
        .main { background-color: #f8f9fa; }
        div[data-testid="stExpander"] { background: white; border-radius: 12px; }
        </style>
    """, unsafe_allow_html=True)
    
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
            except: st.sidebar.error("Dados incorretos.")
    else:
        st.title("💰 ContabilApp")
        with st.expander(f"👤 {st.session_state.user_email}"):
            if st.button("Encerrar Sessão"):
                st.session_state.logado = False
                st.rerun()

        res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        dict_cartoes = {item['card_name']: item['id'] for item in res_c.data}
        
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        tab_lanc, tab_extrato, tab_cartao, tab_gerenciar, tab_config = st.tabs([
            "➕ Lançar", "📊 Extrato", "💳 Cartão", "⚙️ Editar", "🛠️ Config"
        ])

        with tab_lanc:
            st.subheader("Nova Movimentação")
            metodo_sel = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"], key="metodo_pag")
            cart_vontade = None
            if metodo_sel == "Cartão de Crédito":
                if lista_cartoes:
                    cart_vontade = st.selectbox("Qual Cartão?", lista_cartoes, key="card_ativo")
                else:
                    st.warning("Cadastre um cartão na aba Config.")

            with st.form("form_mobile", clear_on_submit=True):
                tipo = st.selectbox("Categoria", ["Despesa", "Receita"])
                desc = st.text_input("Descrição")
                valor_total = st.number_input("Valor (R$)", min_value=0.01, step=0.10)
                data_origem = st.date_input("Data", datetime.now())
                total_parc = 1
                if metodo_sel == "Cartão de Crédito":
                    total_parc = st.number_input("Parcelas", min_value=1, step=1)

                if st.form_submit_button("💾 Salvar Lançamento"):
                    u_email = st.session_state.get('user_email')
                    v_parc = valor_total / int(total_parc)
                    for i in range(int(total_parc)):
                        data_venc = add_months(data_origem, i)
                        supabase.table("profile_transactions").insert({
                            "user_email": u_email, "type": tipo, "category": desc,
                            "amount": round(v_parc, 2), "date": data_venc.strftime("%Y-%m-%d"),
                            "payment_method": metodo_sel, "card_name": cart_vontade,
                            "installment_total": int(total_parc), "installment_number": i + 1
                        }).execute()
                    st.success("Lançado!")
                    st.rerun()

        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês'] = df['date'].dt.strftime('%m/%Y')
                meses_disponiveis = sorted(df['Mês'].unique(), key=lambda x: datetime.strptime(x, '%m/%Y'))
                mes_atual_str = datetime.now().strftime('%m/%Y')
                try: default_idx = meses_disponiveis.index(mes_atual_str)
                except: default_idx = len(meses_disponiveis) - 1

                mes_sel = st.radio("Meses", meses_disponiveis, index=default_idx, horizontal=True, label_visibility="collapsed")
                
                f = df[df['Mês'] == mes_sel].copy().sort_values(by='date', ascending=False)
                
                # Cabeçalho de Saldo
                rec_total = f[f['type'] == 'Receita']['amount'].sum()
                des_total = f[f['type'] == 'Despesa']['amount'].sum()
                
                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("Receitas", f"R${rec_total:,.2f}")
                col_m2.metric("Despesas", f"R${des_total:,.2f}")
                col_m3.metric("Saldo", f"R${rec_total-des_total:,.2f}")

                st.markdown("---")

                # Layout de Tabela Lado a Lado
                col_rec, col_des = st.columns(2)

                with col_rec:
                    st.markdown("<h4 style='text-align: center; color: #2ECC71;'>Receitas</h4>", unsafe_allow_html=True)
                    df_rec = f[f['type'] == 'Receita'][['date', 'category', 'amount']].copy()
                    if not df_rec.empty:
                        df_rec['date'] = df_rec['date'].dt.strftime('%d/%m')
                        df_rec.columns = ['Data', 'Item', 'Valor']
                        st.dataframe(df_rec, use_container_width=True, hide_index=True)
                    else:
                        st.caption("Sem receitas.")

                with col_des:
                    st.markdown("<h4 style='text-align: center; color: #E74C3C;'>Despesas</h4>", unsafe_allow_html=True)
                    df_des = f[f['type'] == 'Despesa'][['date', 'category', 'amount']].copy()
                    if not df_des.empty:
                        df_des['date'] = df_des['date'].dt.strftime('%d/%m')
                        df_des.columns = ['Data', 'Item', 'Valor']
                        st.dataframe(df_des, use_container_width=True, hide_index=True)
                    else:
                        st.caption("Sem despesas.")
            else:
                st.info("Nenhuma movimentação neste período.")

        with tab_cartao:
            if not df.empty and lista_cartoes:
                df_c = df[df['payment_method'] == "Cartão de Crédito"].copy()
                df_c['date'] = pd.to_datetime(df_c['date'])
                hoje = datetime.now()
                for nome_cartao in lista_cartoes:
                    with st.container(border=True):
                        st.markdown(f"### 💳 {nome_cartao}")
                        dados_este_cartao = df_c[df_c['card_name'] == nome_cartao]
                        if not dados_este_cartao.empty:
                            total_fatura = dados_este_cartao[dados_este_cartao['date'].dt.strftime('%m/%Y') == hoje.strftime('%m/%Y')]['amount'].sum()
                            c1, c2 = st.columns([1, 2])
                            c1.metric("Fatura do Mês", f"R$ {total_fatura:,.2f}")
                            resumo_cartao = []
                            for (desc, total), grupo in dados_este_cartao.groupby(['category', 'installment_total']):
                                grupo = grupo.sort_values('date')
                                proximas = grupo[grupo['date'] >= hoje.replace(day=1)]
                                if not proximas.empty:
                                    parc_at = proximas.iloc[0]['installment_number']
                                    venc = proximas.iloc[0]['date']
                                    resumo_cartao.append({'Venc.': venc.strftime('%d/%m'), 'Item': desc, 'Parc.': f"{int(parc_at)}/{int(total)}", 'Valor': f"R$ {proximas.iloc[0]['amount']:,.2f}"})
                            if resumo_cartao:
                                with c2: st.dataframe(pd.DataFrame(resumo_cartao), use_container_width=True, hide_index=True)
                            else: c2.caption("Nenhuma parcela pendente.")
                        else: st.info(f"Sem lançamentos para {nome_cartao}.")
            else: st.info("Sem cartões ou dados.")

        with tab_gerenciar:
            if not df.empty:
                df_edit = df.copy()
                df_edit['date'] = pd.to_datetime(df_edit['date'])
                df_edit = df_edit.sort_values(['category', 'card_name', 'installment_total', 'date'])
                df_grouped = df_edit.groupby(['category', 'card_name', 'installment_total', 'payment_method'], as_index=False).first()
                df_grouped = df_grouped.sort_values(by='date', ascending=False)

                opcoes = {f"{r['date'].strftime('%d/%m')} | {r['category']} (Total)": r['id'] for _, r in df_grouped.iterrows()}
                item_sel = st.selectbox("Selecione para Editar/Excluir", list(opcoes.keys()))
                id_alvo = opcoes[item_sel]
                d_at = df[df['id'] == id_alvo].iloc[0]

                valor_exibido = float(d_at['amount'])
                if d_at['payment_method'] == "Cartão de Crédito":
                    valor_exibido = float(d_at['amount']) * int(d_at['installment_total'])

                with st.form("edit_mobile"):
                    n_desc = st.text_input("Descrição", value=d_at['category'])
                    n_valor = st.number_input("Valor Total do Lançamento", value=valor_exibido)
                    n_data = st.date_input("Data Original", pd.to_datetime(d_at['date']))
                    
                    st.info("⚠️ Alterações serão aplicadas a todas as parcelas.")
                    
                    if st.form_submit_button("Salvar Alterações em Tudo"):
                        relacionadas = df[(df['category'] == d_at['category']) & 
                                         (df['card_name'] == d_at['card_name']) & 
                                         (df['installment_total'] == d_at['installment_total'])]
                        v_parc_novo = n_valor / int(d_at['installment_total'])
                        for idx, row in relacionadas.iterrows():
                            nova_data_parc = add_months(n_data, int(row['installment_number']) - 1)
                            supabase.table("profile_transactions").update({
                                "category": n_desc, 
                                "amount": round(v_parc_novo, 2), 
                                "date": nova_data_parc.strftime("%Y-%m-%d")
                            }).eq("id", row['id']).execute()
                        st.success("Atualizado!")
                        st.rerun()
                        
                    if st.form_submit_button("🗑️ Excluir Lançamento Completo"):
                        relacionadas = df[(df['category'] == d_at['category']) & 
                                         (df['card_name'] == d_at['card_name']) & 
                                         (df['installment_total'] == d_at['installment_total'])]
                        for _, row in relacionadas.iterrows():
                            supabase.table("profile_transactions").delete().eq("id", row['id']).execute()
                        st.warning("Excluído.")
                        st.rerun()

        with tab_config:
            st.write("**Gerenciar Cartões**")
            n_c = st.text_input("Novo Cartão")
            if st.button("Adicionar Cartão"):
                if n_c:
                    supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": n_c}).execute()
                    st.rerun()
            if lista_cartoes:
                cart_del = st.selectbox("Remover Cartão", lista_cartoes)
                if st.button("Excluir"):
                    supabase.table("my_cards").delete().eq("id", dict_cartoes[cart_del]).execute()
                    st.rerun()

if __name__ == "__main__":
    main()
