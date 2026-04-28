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
    st.error("Erro: Credenciais do Supabase não configuradas nos Secrets.")
    st.stop()

# --- CONFIGURAÇÃO VISUAL MODERNA ---
st.set_page_config(page_title="Finanças Pro", layout="wide", page_icon="💎")

# CSS para customização de UI
st.markdown("""
    <style>
    /* Estilização do Fundo e Cards */
    .stApp {
        background-color: #0e1117;
    }
    div[data-testid="metric-container"] {
        background-color: #1e2130;
        border: 1px solid #313348;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    div[data-testid="stExpander"] {
        border-radius: 10px;
        border: 1px solid #313348;
        background-color: #1e2130;
    }
    .stButton>button {
        border-radius: 8px;
        border: none;
        background-color: #4f46e5;
        color: white;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #6366f1;
        transform: translateY(-2px);
    }
    /* Estilo para tabelas e inputs */
    .stDataFrame, .stTable {
        border-radius: 10px;
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
    st.markdown("<h1 style='text-align: center; color: #4f46e5;'>💎 Finanças Pro</h1>", unsafe_allow_html=True)
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.image("https://img.icons8.com/clouds/500/checked-user-male.png", width=250)
    with col_r:
        aba_in, aba_up = st.tabs(["🔒 Entrar", "📝 Cadastrar"])
        with aba_in:
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            if st.button("Aceder ao Painel"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                    st.session_state.user = res.user
                    st.rerun()
                except: st.error("Login inválido.")
        with aba_up:
            n_email = st.text_input("Novo E-mail")
            n_senha = st.text_input("Nova Senha", type="password")
            if st.button("Criar Minha Conta"):
                try:
                    supabase.auth.sign_up({"email": n_email, "password": n_senha})
                    st.success("Conta criada! Tente logar.")
                except Exception as e: st.error(f"Erro: {e}")

if st.session_state.user is None:
    tela_login()
else:
    u_id = st.session_state.user.id
    st.sidebar.markdown("<h2 style='color: #4f46e5;'>💎 Finanças Pro</h2>", unsafe_allow_html=True)
    menu = st.sidebar.radio("Navegação", ["📊 Dashboard Mensal", "➕ Novo Lançamento", "💳 Cartões de Crédito", "⚙️ Gerenciar Outros"])
    
    st.sidebar.divider()
    if st.sidebar.button("🚪 Sair"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    # --- ABA: NOVO LANÇAMENTO ---
    if menu == "➕ Novo Lançamento":
        st.markdown("## 📝 Novo Lançamento")
        with st.form("form_lan", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Receita", "Despesa"])
            desc = st.text_input("Descrição do Gasto/Ganho")
            valor_total = st.number_input("Valor Total (R$)", min_value=0.0, format="%.2f")
            data_base = st.date_input("Data de Referência", date.today())
            res_c = supabase.table("cartoes").select("nome_cartao").eq("user_id", u_id).execute()
            lista_c = [c['nome_cartao'] for c in res_c.data]
            cartao_sel = st.selectbox("Método de Pagamento", ["Dinheiro/Pix/Débito"] + lista_c)
            parcelas = st.number_input("Número de Parcelas", min_value=1, value=1)
            
            if st.form_submit_button("Confirmar Lançamento"):
                v_parc = valor_total / parcelas
                dados = []
                for i in range(parcelas):
                    dados.append({
                        "user_id": u_id, "tipo": tipo, "descricao": desc,
                        "valor": round(float(v_parc), 2),
                        "data": str(data_base + relativedelta(months=i)),
                        "parcela_atual": i + 1, "total_parcelas": parcelas,
                        "cartao_nome": cartao_sel if cartao_sel != "Dinheiro/Pix/Débito" else None
                    })
                supabase.table("lancamentos").insert(dados).execute()
                st.success("Lançamento efetuado com sucesso!")

    # --- ABA: DASHBOARD MENSAL ---
    elif menu == "📊 Dashboard Mensal":
        st.markdown("## 📊 Resumo do Mês")
        res = supabase.table("lancamentos").select("*").eq("user_id", u_id).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            df['data'] = pd.to_datetime(df['data'])
            df['MesAno'] = df['data'].dt.strftime('%m/%Y')
            
            meses = sorted(df['MesAno'].unique(), reverse=True)
            mes_sel = st.selectbox("Selecione o período", meses)
            df_mes = df[df['MesAno'] == mes_sel].copy()
            
            c1, c2, c3 = st.columns(3)
            receitas = df_mes[df_mes['tipo'] == 'Receita']['valor'].sum()
            despesas = df_mes[df_mes['tipo'] == 'Despesa']['valor'].sum()
            c1.metric("Receitas", format_real(receitas))
            c2.metric("Despesas", format_real(despesas))
            c3.metric("Saldo Líquido", format_real(receitas - despesas))
            
            st.markdown("### 📋 Detalhes dos Lançamentos")
            df_mes['Data'] = df_mes['data'].dt.strftime('%d/%m/%Y')
            df_mes['Valor R$'] = df_mes['valor'].apply(format_real)
            df_mes['Origem'] = df_mes['cartao_nome'].fillna("Dinheiro/Pix")
            
            st.dataframe(df_mes[['Data', 'descricao', 'Origem', 'tipo', 'Valor R$']], use_container_width=True)
        else:
            st.info("Nenhum dado encontrado para gerar o dashboard.")

    # --- ABA: CARTÕES DE CRÉDITO ---
    elif menu == "💳 Cartões de Crédito":
        st.markdown("## 💳 Central de Cartões")
        tab1, tab2, tab3 = st.tabs(["📅 Fatura do Mês", "📋 Resumo de Compras", "🛠️ Configurar Cartões"])
        
        res_l = supabase.table("lancamentos").select("*").eq("user_id", u_id).neq("cartao_nome", None).execute()
        df_all = pd.DataFrame(res_l.data) if res_l.data else pd.DataFrame()
        hoje = pd.to_datetime(date.today())

        with tab1:
            if not df_all.empty:
                df_all['data'] = pd.to_datetime(df_all['data'])
                df_f = df_all[df_all['data'].dt.strftime('%m/%Y') == hoje.strftime('%m/%Y')].copy()
                
                for cartao in df_f['cartao_nome'].unique():
                    with st.expander(f"💳 Cartão {cartao}", expanded=True):
                        df_c = df_f[df_f['cartao_nome'] == cartao].copy()
                        df_c['Parc.'] = df_c['parcela_atual'].astype(str) + "/" + df_c['total_parcelas'].astype(str)
                        df_c['Valor'] = df_c['valor'].apply(format_real)
                        st.table(df_c[['descricao', 'Parc.', 'Valor']])
                        st.markdown(f"**Total da Fatura:** <span style='color: #10b981; font-size: 20px;'>{format_real(df_c['valor'].sum())}</span>", unsafe_allow_html=True)
            else: st.info("Sem faturas para o mês atual.")

        with tab2:
            if not df_all.empty:
                df_all['data'] = pd.to_datetime(df_all['data'])
                grupos = df_all.groupby(['descricao', 'cartao_nome'])
                
                for (desc, cartao), df_compra in grupos:
                    with st.container():
                        c1, c2, c3, c4, c5 = st.columns([1.5, 1, 1, 1, 0.5])
                        valor_total_orig = df_compra['valor'].sum()
                        data_ultima = df_compra['data'].max().strftime('%d/%m/%Y')
                        saldo_restante = df_compra[df_compra['data'].dt.date >= date.today()]['valor'].sum()

                        c1.markdown(f"**{desc}**<br><small>{cartao}</small>", unsafe_allow_html=True)
                        c2.write(f"Total: **{format_real(valor_total_orig)}**")
                        c3.write(f"Saldo: **{format_real(saldo_restante)}**")
                        c4.write(f"Fim: {data_ultima}")
                        if c5.button("❌", key=f"del_c_{desc}_{cartao}"):
                            supabase.table("lancamentos").delete().eq("user_id", u_id).eq("descricao", desc).eq("cartao_nome", cartao).execute()
                            st.rerun()
                        st.divider()

        with tab3:
            col_nc, col_lc = st.columns([1, 1])
            with col_nc:
                st.markdown("### ➕ Novo Cartão")
                n_c = st.text_input("Nome do Cartão")
                if st.button("Adicionar Cartão"):
                    if n_c:
                        supabase.table("cartoes").insert({"user_id": u_id, "nome_cartao": n_c}).execute()
                        st.rerun()
            with col_lc:
                st.markdown("### 🗑️ Excluir Cartão")
                res_c = supabase.table("cartoes").select("*").eq("user_id", u_id).execute()
                for c in res_c.data:
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"💳 {c['nome_cartao']}")
                    if c2.button("Apagar", key=f"del_card_{c['id']}"):
                        supabase.table("lancamentos").delete().eq("user_id", u_id).eq("cartao_nome", c['nome_cartao']).execute()
                        supabase.table("cartoes").delete().eq("id", c['id']).execute()
                        st.rerun()

    # --- ABA: GERENCIAR OUTROS ---
    elif menu == "⚙️ Gerenciar Outros":
        st.markdown("## ⚙️ Gerenciar Lançamentos Avulsos")
        res_o = supabase.table("lancamentos").select("*").eq("user_id", u_id).is_("cartao_nome", "null").execute()
        if res_o.data:
            for item in res_o.data:
                c1, c2, c3 = st.columns([2,1,1])
                c1.write(f"📅 {item['data']} - **{item['descricao']}**")
                c2.write(format_real(item['valor']))
                if c3.button("Excluir", key=f"del_o_{item['id']}"):
                    supabase.table("lancamentos").delete().eq("id", item['id']).execute()
                    st.rerun()
                st.divider()
        else:
            st.info("Nenhum lançamento avulso encontrado.")
