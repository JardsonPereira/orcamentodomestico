import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÃO SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("Erro: Credenciais do Supabase não configuradas.")
    st.stop()

# --- CONFIGURAÇÃO VISUAL: CLEAN GLASSMORPHISM ---
st.set_page_config(page_title="Pocket Finance", layout="wide", page_icon="🍃")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        min-height: 100vh;
    }

    /* Container de Métricas (Glass Effect) */
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.6);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.4);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.05);
    }

    /* Botões */
    .stButton>button {
        border-radius: 12px;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
        transition: 0.3s;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 10px 20px rgba(118, 75, 162, 0.3);
    }

    /* Tabelas */
    .stDataFrame, .stTable {
        background: white;
        border-radius: 15px;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)

if 'user' not in st.session_state:
    st.session_state.user = None

def format_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

# --- AUTENTICAÇÃO ---
def tela_login():
    st.markdown("<h1 style='text-align: center;'>🍃 Pocket Finance</h1>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        aba_in, aba_up = st.tabs(["👋 Entrar", "✨ Criar Conta"])
        with aba_in:
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            if st.button("Acessar Painel"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                    st.session_state.user = res.user
                    st.rerun()
                except: st.error("Login inválido.")
        with aba_up:
            n_email = st.text_input("Novo e-mail")
            n_senha = st.text_input("Nova senha", type="password")
            if st.button("Cadastrar"):
                try:
                    supabase.auth.sign_up({"email": n_email, "password": n_senha})
                    st.success("Conta criada!")
                except Exception as e: st.error(f"Erro: {e}")

if st.session_state.user is None:
    tela_login()
else:
    u_id = st.session_state.user.id
    st.sidebar.markdown("<h2 style='text-align: center;'>🍃 Pocket</h2>", unsafe_allow_html=True)
    menu = st.sidebar.radio("Navegação", ["Dashboard Mensal", "Novo Lançamento", "Cartões de Crédito", "Gerenciar Outros"])
    
    st.sidebar.write("---")
    if st.sidebar.button("Sair da Conta"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    # --- ABA: NOVO LANÇAMENTO ---
    if menu == "Novo Lançamento":
        st.markdown("## 📝 Novo Registro")
        with st.form("form_lan", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Receita", "Despesa"])
            desc = st.text_input("Descrição")
            valor_total = st.number_input("Valor Total (R$)", min_value=0.0, format="%.2f")
            data_base = st.date_input("Data", date.today())
            res_c = supabase.table("cartoes").select("nome_cartao").eq("user_id", u_id).execute()
            lista_c = [c['nome_cartao'] for c in res_c.data]
            cartao_sel = st.selectbox("Pagamento", ["Dinheiro/Pix/Débito"] + lista_c)
            parcelas = st.number_input("Parcelas", min_value=1, value=1)
            
            if st.form_submit_button("Salvar Lançamento"):
                v_parc = valor_total / parcelas
                for i in range(parcelas):
                    supabase.table("lancamentos").insert({
                        "user_id": u_id, "tipo": tipo, "descricao": desc,
                        "valor": round(float(v_parc), 2),
                        "data": str(data_base + relativedelta(months=i)),
                        "parcela_atual": i + 1, "total_parcelas": parcelas,
                        "cartao_nome": cartao_sel if cartao_sel != "Dinheiro/Pix/Débito" else None
                    }).execute()
                st.success("Lançado!")

    # --- ABA: DASHBOARD MENSAL ---
    elif menu == "Dashboard Mensal":
        st.markdown("## 📊 Dashboard")
        res = supabase.table("lancamentos").select("*").eq("user_id", u_id).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['data'] = pd.to_datetime(df['data'])
            df['MesAno'] = df['data'].dt.strftime('%m/%Y')
            mes_sel = st.selectbox("Mês", sorted(df['MesAno'].unique(), reverse=True))
            df_mes = df[df['MesAno'] == mes_sel].copy()
            
            c1, c2, c3 = st.columns(3)
            rec = df_mes[df_mes['tipo'] == 'Receita']['valor'].sum()
            des = df_mes[df_mes['tipo'] == 'Despesa']['valor'].sum()
            c1.metric("Entradas", format_real(rec))
            c2.metric("Saídas", format_real(des))
            c3.metric("Saldo", format_real(rec - des))
            
            st.markdown("### Extrato Detalhado")
            df_mes['Data'] = df_mes['data'].dt.strftime('%d/%m/%Y')
            df_mes['Valor R$'] = df_mes['valor'].apply(format_real)
            df_mes['Origem'] = df_mes['cartao_nome'].fillna("Dinheiro/Pix")
            st.dataframe(df_mes[['Data', 'descricao', 'Origem', 'tipo', 'Valor R$']], use_container_width=True)

    # --- ABA: CARTÕES DE CRÉDITO ---
    elif menu == "Cartões de Crédito":
        st.markdown("## 💳 Gestão de Cartões")
        tab1, tab2, tab3 = st.tabs(["Fatura Atual", "Resumo de Compras", "Configurações"])
        
        res_l = supabase.table("lancamentos").select("*").eq("user_id", u_id).neq("cartao_nome", None).execute()
        df_all = pd.DataFrame(res_l.data) if res_l.data else pd.DataFrame()
        hoje = pd.to_datetime(date.today())

        with tab1:
            if not df_all.empty:
                df_all['data'] = pd.to_datetime(df_all['data'])
                df_f = df_all[df_all['data'].dt.strftime('%m/%Y') == hoje.strftime('%m/%Y')].copy()
                for cartao in df_f['cartao_nome'].unique():
                    with st.expander(f"Fatura {cartao}", expanded=True):
                        df_c = df_f[df_f['cartao_nome'] == cartao].copy()
                        df_c['Parc.'] = df_c['parcela_atual'].astype(str) + "/" + df_c['total_parcelas'].astype(str)
                        df_c['Valor'] = df_c['valor'].apply(format_real)
                        st.table(df_c[['descricao', 'Parc.', 'Valor']])
                        st.write(f"Total: **{format_real(df_c['valor'].sum())}**")

        with tab2:
            if not df_all.empty:
                df_all['data'] = pd.to_datetime(df_all['data'])
                grupos = df_all.groupby(['descricao', 'cartao_nome'])
                for (desc, cartao), df_compra in grupos:
                    with st.container():
                        c1, c2, c3, c4, c5 = st.columns([1.5, 1, 1, 1, 0.5])
                        valor_total_orig = df_compra['valor'].sum()
                        saldo_restante = df_compra[df_compra['data'].dt.date >= date.today()]['valor'].sum()
                        data_ultima = df_compra['data'].max().strftime('%d/%m/%Y')

                        c1.markdown(f"**{desc}**<br><small>{cartao}</small>", unsafe_allow_html=True)
                        c2.write(f"Total: **{format_real(valor_total_orig)}**")
                        c3.write(f"A pagar: **{format_real(saldo_restante)}**")
                        c4.write(f"Última: {data_ultima}")
                        if c5.button("❌", key=f"del_{desc}_{cartao}"):
                            supabase.table("lancamentos").delete().eq("user_id", u_id).eq("descricao", desc).eq("cartao_nome", cartao).execute()
                            st.rerun()
                        st.divider()

        with tab3:
            col_nc, col_lc = st.columns(2)
            with col_nc:
                n_c = st.text_input("Novo Cartão")
                if st.button("Adicionar"):
                    supabase.table("cartoes").insert({"user_id": u_id, "nome_cartao": n_c}).execute()
                    st.rerun()
            with col_lc:
                res_c = supabase.table("cartoes").select("*").eq("user_id", u_id).execute()
                for c in res_c.data:
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"💳 {c['nome_cartao']}")
                    if c2.button("Apagar", key=f"del_c_{c['id']}"):
                        supabase.table("lancamentos").delete().eq("user_id", u_id).eq("cartao_nome", c['nome_cartao']).execute()
                        supabase.table("cartoes").delete().eq("id", c['id']).execute()
                        st.rerun()

    # --- ABA: GERENCIAR OUTROS ---
    elif menu == "Gerenciar Outros":
        st.markdown("## ⚙️ Movimentações Avulsas")
        res_o = supabase.table("lancamentos").select("*").eq("user_id", u_id).is_("cartao_nome", "null").execute()
        if res_o.data:
            for item in res_o.data:
                c1, c2, c3 = st.columns([2,1,1])
                c1.write(f"{item['data']} - {item['descricao']}")
                c2.write(format_real(item['valor']))
                if c3.button("Excluir", key=f"del_o_{item['id']}"):
                    supabase.table("lancamentos").delete().eq("id", item['id']).execute()
                    st.rerun()
