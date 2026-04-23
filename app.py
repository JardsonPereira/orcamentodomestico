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

# --- INICIALIZAÇÃO DO STATE ---
if "logado" not in st.session_state:
    st.session_state.logado = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""

def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)

def main():
    # --- CONFIGURAÇÃO MOBILE-FRIENDLY ---
    st.set_page_config(page_title="ContabilApp Pro", layout="wide", page_icon="💰")
    
    # CSS Customizado para Mobile (Foco em toque e legibilidade)
    st.markdown("""
        <style>
        @media (max-width: 640px) {
            .stMetric { padding: 10px !important; }
            .stMetric div { font-size: 0.8rem !important; }
            .stTabs [data-baseweb="tab-list"] { gap: 8px; }
            .stTabs [data-baseweb="tab"] { padding: 8px 4px; font-size: 12px; }
            h1 { font-size: 1.5rem !important; }
        }
        .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold; }
        .main { background-color: #f8f9fa; }
        div[data-testid="stExpander"], div[data-testid="stForm"], .stContainer { 
            background: white; border-radius: 12px; border: 1px solid #eee; padding: 10px; margin-bottom: 10px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if not st.session_state.logado:
        st.markdown("<h1 style='text-align: center;'>💰 ContabilApp</h1>", unsafe_allow_html=True)
        
        _, col_central, _ = st.columns([0.1, 0.8, 0.1])
        with col_central:
            escolha = st.radio("Acesso", ["Entrar", "Criar Conta"], horizontal=True, label_visibility="collapsed")
            
            with st.container():
                if escolha == "Entrar":
                    email = st.text_input("E-mail")
                    senha = st.text_input("Senha", type='password')
                    nome_exibicao = st.text_input("Seu Nome")
                    if st.button("ACESSAR"):
                        try:
                            supabase.auth.sign_in_with_password({"email": email, "password": senha})
                            st.session_state.logado = True
                            st.session_state.user_email = email
                            st.session_state.user_name = nome_exibicao
                            st.rerun()
                        except: st.error("Dados incorretos.")
                else:
                    n_email = st.text_input("E-mail (Novo)")
                    n_senha = st.text_input("Senha (Novo)", type='password')
                    n_nome = st.text_input("Nome (Novo)")
                    if st.button("CADASTRAR"):
                        try:
                            supabase.auth.sign_up({"email": n_email, "password": n_senha})
                            st.session_state.logado = True
                            st.session_state.user_email = n_email
                            st.session_state.user_name = n_nome
                            st.rerun()
                        except: st.error("Erro no cadastro.")
    else:
        # --- HEADER ---
        c_h1, c_h2 = st.columns([3, 1])
        c_h1.markdown(f"### Olá, {st.session_state.get('user_name', 'Usuário')}")
        if c_h2.button("Sair"):
            st.session_state.logado = False
            st.rerun()

        # --- BUSCA DE DADOS ---
        res_c = supabase.table("my_cards").select("*").eq("user_email", st.session_state.user_email).execute()
        lista_cartoes = [item['card_name'] for item in res_c.data]
        dict_cartoes = {item['card_name']: item['id'] for item in res_c.data}
        
        res_f = supabase.table("profile_transactions").select("*").eq("user_email", st.session_state.user_email).execute()
        df = pd.DataFrame(res_f.data)

        tab_lanc, tab_extrato, tab_cartao, tab_gerenciar, tab_config = st.tabs([
            "➕ Lançar", "📊 Extrato", "💳 Cartão", "⚙️ Editar", "🛠️ Ajustes"
        ])

        with tab_lanc:
            st.subheader("Nova Movimentação")
            metodo_sel = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Cartão de Crédito"])
            cart_v = None
            if metodo_sel == "Cartão de Crédito":
                if lista_cartoes: cart_v = st.selectbox("Qual Cartão?", lista_cartoes)
                else: st.warning("Cadastre um cartão primeiro.")

            with st.form("form_lanca", clear_on_submit=True):
                tipo = st.selectbox("Categoria", ["Despesa", "Receita"])
                desc = st.text_input("Descrição")
                valor_t = st.number_input("Valor (R$)", min_value=0.01, step=0.10)
                data_o = st.date_input("Data", datetime.now())
                total_p = 1
                if metodo_sel == "Cartão de Crédito":
                    total_p = st.number_input("Parcelas", min_value=1, step=1)

                if st.form_submit_button("💾 Salvar"):
                    v_parc = valor_t / int(total_p)
                    for i in range(int(total_p)):
                        d_venc = add_months(data_o, i)
                        supabase.table("profile_transactions").insert({
                            "user_email": st.session_state.user_email, "type": tipo, "category": desc,
                            "amount": round(v_parc, 2), "date": d_venc.strftime("%Y-%m-%d"),
                            "payment_method": metodo_sel, "card_name": cart_v,
                            "installment_total": int(total_p), "installment_number": i + 1
                        }).execute()
                    st.success("Salvo!")
                    st.rerun()

        with tab_extrato:
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['Mês'] = df['date'].dt.strftime('%m/%Y')
                meses = sorted(df['Mês'].unique(), key=lambda x: datetime.strptime(x, '%m/%Y'))
                mes_sel = st.radio("Meses", meses, index=len(meses)-1, horizontal=True)
                
                f = df[df['Mês'] == mes_sel].copy().sort_values(by='date', ascending=False)
                rec = f[f['type'] == 'Receita']['amount'].sum()
                des = f[f['type'] == 'Despesa']['amount'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Rec.", f"R${rec:,.2f}")
                c2.metric("Desp.", f"R${des:,.2f}")
                c3.metric("Saldo", f"R${rec-des:,.2f}")

                st.markdown("---")
                # Layout de Lista Compacta
                for _, row in f.iterrows():
                    with st.container():
                        col_i, col_v = st.columns([2, 1])
                        cor = "#2ECC71" if row['type'] == 'Receita' else "#E74C3C"
                        with col_i:
                            st.markdown(f"**{row['category']}**")
                            p_info = f"💳 {int(row['installment_number'])}/{int(row['installment_total'])}" if row['payment_method'] == "Cartão de Crédito" else "💵 À vista"
                            st.caption(f"{row['date'].strftime('%d/%m')} • {p_info}")
                        with col_v:
                            st.markdown(f"<p style='text-align:right; color:{cor}; font-weight:bold;'>R$ {row['amount']:,.2f}</p>", unsafe_allow_html=True)
            else: st.info("Sem dados.")

        with tab_cartao:
            if not df.empty and lista_cartoes:
                df_c = df[df['payment_method'] == "Cartão de Crédito"].copy()
                df_c['date'] = pd.to_datetime(df_c['date'])
                for c in lista_cartoes:
                    with st.container():
                        st.markdown(f"**💳 {c}**")
                        dados = df_c[df_c['card_name'] == c]
                        if not dados.empty:
                            fat = dados[dados['date'].dt.strftime('%m/%Y') == datetime.now().strftime('%m/%Y')]['amount'].sum()
                            st.metric("Fatura Atual", f"R$ {fat:,.2f}")
                            st.dataframe(dados[['date', 'category', 'amount']], use_container_width=True, hide_index=True)
            else: st.info("Sem cartões cadastrados.")

        with tab_gerenciar:
            if not df.empty:
                df_edit = df.copy()
                df_edit['date'] = pd.to_datetime(df_edit['date'])
                df_grouped = df_edit.sort_values(['category', 'card_name', 'installment_total', 'date'])
                df_grouped = df_grouped.groupby(['category', 'card_name', 'installment_total', 'payment_method', 'type'], as_index=False, dropna=False).first()
                
                opcoes = {f"{r['category']} | Total R${float(r['amount'])*int(r['installment_total']):.2f}": r['id'] for _, r in df_grouped.iterrows()}
                item_s = st.selectbox("Escolha para Editar/Excluir", list(opcoes.keys()))
                d_at = df[df['id'] == opcoes[item_s]].iloc[0]

                with st.form("edit_form"):
                    n_desc = st.text_input("Descrição", value=d_at['category'])
                    n_valor_t = st.number_input("Valor Total", value=float(d_at['amount']) * int(d_at['installment_total']))
                    
                    if st.form_submit_button("SALVAR ALTERAÇÕES EM TUDO"):
                        rel = df[(df['category'] == d_at['category']) & (df['installment_total'] == d_at['installment_total'])]
                        v_p = n_valor_t / int(d_at['installment_total'])
                        for _, r in rel.iterrows():
                            supabase.table("profile_transactions").update({"category": n_desc, "amount": round(v_p, 2)}).eq("id", r['id']).execute()
                        st.rerun()
                    if st.form_submit_button("🗑️ EXCLUIR TUDO"):
                        rel = df[(df['category'] == d_at['category']) & (df['installment_total'] == d_at['installment_total'])]
                        for _, r in rel.iterrows():
                            supabase.table("profile_transactions").delete().eq("id", r['id']).execute()
                        st.rerun()

        with tab_config:
            st.subheader("Ajustes")
            n_c = st.text_input("Nome do Cartão")
            if st.button("Adicionar"):
                supabase.table("my_cards").insert({"user_email": st.session_state.user_email, "card_name": n_c}).execute()
                st.rerun()
            if lista_cartoes:
                c_del = st.selectbox("Remover", lista_cartoes)
                if st.button("Excluir"):
                    supabase.table("my_cards").delete().eq("id", dict_cartoes[c_del]).execute()
                    st.rerun()

if __name__ == "__main__":
    main()
