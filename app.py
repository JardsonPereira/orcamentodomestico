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
    
    # CSS Customizado para Mobile
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
        # --- HEADER COMPACTO ---
        st.title("💰 ContabilApp")
        with st.expander(f"👤 {st.session_state.user_email}"):
            if st.button("Encerrar Sessão"):
                st.session_state.logado = False
                st.rerun()

        # --- BUSCA DE DADOS ---
        res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        dict_cartoes = {item['card_name']: item['id'] for item in res_c.data}
        
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        # --- NAVEGAÇÃO POR ABAS ---
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
                
                # --- SELETOR DE MÊS EM COLUNA ---
                meses_disponiveis = sorted(df['Mês'].unique(), reverse=True)
                mes_atual_str = datetime.now().strftime('%m/%Y')
                
                # Se o mês atual não tiver dados, ele usa o primeiro da lista
                default_idx = meses_disponiveis.index(mes_atual_str) if mes_atual_str in meses_disponiveis else 0
                
                mes_sel = st.selectbox("Mês de Referência", meses_disponiveis, index=default_idx)
                
                f = df[df['Mês'] == mes_sel].copy().sort_values(by='date', ascending=False)
                
                # Métricas lado a lado
                m1, m2, m3 = st.columns(3)
                rec = f[f['type'] == 'Receita']['amount'].sum()
                des = f[f['type'] == 'Despesa']['amount'].sum()
                m1.metric("Receitas", f"R${rec:,.2f}")
                m2.metric("Despesas", f"R${des:,.2f}")
                m3.metric("Saldo", f"R${rec-des:,.2f}")

                st.markdown("---")
                
                for _, row in f.iterrows():
                    with st.container(border=True):
                        c_info, c_valor = st.columns([2, 1])
                        with c_info:
                            st.markdown(f"**{row['category']}**")
                            data_str = row['date'].strftime('%d/%m')
                            info_pag = f"💳 {int(row['installment_number'])}/{int(row['installment_total'])}" if row['payment_method'] == "Cartão de Crédito" else "💵 À vista"
                            st.caption(f"📅 {data_str} • {info_pag}")
                        
                        with c_valor:
                            cor = "#2ECC71" if row['type'] == 'Receita' else "#E74C3C"
                            simbolo = "+" if row['type'] == 'Receita' else "-"
                            st.markdown(f"<p style='text-align:right; color:{cor}; font-weight:bold; margin-top:5px;'> {simbolo} R$ {row['amount']:,.2f}</p>", unsafe_allow_html=True)
            else:
                st.info("Sem dados.")

        with tab_cartao:
            if not df.empty:
                df_c = df[df['payment_method'] == "Cartão de Crédito"].copy()
                if not df_c.empty:
                    df_c['date'] = pd.to_datetime(df_c['date'])
                    hoje = datetime.now()
                    resumo = []
                    for (desc, card, total), grupo in df_c.groupby(['category', 'card_name', 'installment_total']):
                        grupo = grupo.sort_values('date')
                        proximas = grupo[grupo['date'] >= hoje.replace(day=1)]
                        parc_at = proximas.iloc[0]['installment_number'] if not proximas.empty else total
                        venc = proximas.iloc[0]['date'] if not proximas.empty else grupo.iloc[-1]['date']
                        resumo.append({
                            'Venc.': venc.strftime('%d/%m'),
                            'Cartão': card, 'Item': desc,
                            'Parc.': f"{int(parc_at)}/{int(total)}",
                            'Total': f"R$ {grupo['amount'].sum():,.2f}"
                        })
                    st.dataframe(pd.DataFrame(resumo), use_container_width=True, hide_index=True)

        with tab_gerenciar:
            if not df.empty:
                df_view = df.sort_values(by='date', ascending=False)
                opcoes = {f"{r['date'].strftime('%d/%m')} | {r['category']}": r['id'] for _, r in df_view.iterrows()}
                item_sel = st.selectbox("Editar/Excluir", list(opcoes.keys()))
                id_alvo = opcoes[item_sel]
                d_at = df[df['id'] == id_alvo].iloc[0]

                with st.form("edit_mobile"):
                    n_desc = st.text_input("Descrição", value=d_at['category'])
                    n_valor = st.number_input("Valor", value=float(d_at['amount']))
                    n_data = st.date_input("Data", pd.to_datetime(d_at['date']))
                    
                    if st.form_submit_button("Salvar Alterações"):
                        supabase.table("profile_transactions").update({"category": n_desc, "amount": n_valor, "date": n_data.strftime("%Y-%m-%d")}).eq("id", id_alvo).execute()
                        st.rerun()
                    if st.form_submit_button("🗑️ Excluir Registro"):
                        supabase.table("profile_transactions").delete().eq("id", id_alvo).execute()
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
