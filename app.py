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

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Pocket Finance", layout="wide", page_icon="🍃")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); min-height: 100vh; }
    div[data-testid="metric-container"] { background: rgba(255, 255, 255, 0.6); backdrop-filter: blur(10px); border-radius: 20px; padding: 20px; border: 1px solid rgba(255, 255, 255, 0.4); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.05); }
    .stButton>button { border-radius: 12px; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); color: white; font-weight: 600; width: 100%; }
    .stDataFrame, .stTable { background: white; border-radius: 15px; overflow: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTES ---
CATEGORIAS_DESPESA = ["Alimentação", "Moradia", "Transporte", "Lazer", "Educação", "Saúde", "Assinaturas", "Outros"]
CATEGORIAS_RECEITA = ["Salário", "Investimentos", "Extra", "Outros"]

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
            if st.button("Aceder Painel"):
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
                    st.success("Conta criada! Verifique seu e-mail.")
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

    # --- NOVO LANÇAMENTO ---
    if menu == "Novo Lançamento":
        st.header("📝 Novo Registro")
        with st.form("form_lan", clear_on_submit=True):
            col1, col2 = st.columns(2)
            tipo = col1.selectbox("Tipo", ["Despesa", "Receita"])
            cats = CATEGORIAS_DESPESA if tipo == "Despesa" else CATEGORIAS_RECEITA
            categoria = col2.selectbox("Categoria", cats)
            
            desc = st.text_input("Descrição")
            col3, col4 = st.columns(2)
            valor_total = col3.number_input("Valor Total (R$)", min_value=0.0, format="%.2f")
            data_base = col4.date_input("Data", date.today())
            
            res_c = supabase.table("cartoes").select("nome_cartao").eq("user_id", u_id).execute()
            lista_c = [c['nome_cartao'] for c in res_c.data]
            col5, col6 = st.columns(2)
            cartao_sel = col5.selectbox("Pagamento", ["Dinheiro/Pix/Débito"] + lista_c)
            parcelas = col6.number_input("Parcelas", min_value=1, value=1)
            
            if st.form_submit_button("Confirmar Lançamento"):
                v_parc = valor_total / parcelas
                for i in range(parcelas):
                    supabase.table("lancamentos").insert({
                        "user_id": u_id, "tipo": tipo, "categoria": categoria, "descricao": desc,
                        "valor": round(float(v_parc), 2),
                        "data": str(data_base + relativedelta(months=i)),
                        "parcela_atual": i + 1, "total_parcelas": parcelas,
                        "cartao_nome": cartao_sel if cartao_sel != "Dinheiro/Pix/Débito" else None
                    }).execute()
                st.success("Lançamento realizado!")

    # --- DASHBOARD MENSAL ---
    elif menu == "Dashboard Mensal":
        st.header("📊 Dashboard")
        res = supabase.table("lancamentos").select("*").eq("user_id", u_id).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            if 'categoria' not in df.columns: df['categoria'] = 'Outros'
            df['data'] = pd.to_datetime(df['data'])
            df['MesAno'] = df['data'].dt.strftime('%m/%Y')
            
            aba_mensal, aba_periodo = st.tabs(["Mês Individual", "Resultado por Período"])
            
            with aba_mensal:
                meses_disponiveis = sorted(df['MesAno'].unique(), key=lambda x: pd.to_datetime(x, format='%m/%Y'), reverse=True)
                mes_sel = st.selectbox("Selecione o Mês", meses_disponiveis, key="dash_sel")
                
                df_mes = df[df['MesAno'] == mes_sel].copy()
                c1, c2, c3 = st.columns(3)
                rec = df_mes[df_mes['tipo'] == 'Receita']['valor'].sum()
                des = df_mes[df_mes['tipo'] == 'Despesa']['valor'].sum()
                c1.metric("Entradas", format_real(rec))
                c2.metric("Saídas", format_real(des))
                c3.metric("Saldo", format_real(rec - des))
                
                col_chart1, col_chart2 = st.columns([1.2, 1])
                with col_chart1:
                    st.markdown("### 📋 Extrato")
                    df_view = df_mes.copy()
                    df_view['Data'] = df_view['data'].dt.strftime('%d/%m')
                    df_view['Valor'] = df_view['valor'].apply(format_real)
                    df_view['Tipo'] = df_view['tipo'].apply(lambda x: "🟢" if x == "Receita" else "🔴")
                    df_view = df_view.sort_values(by='data', ascending=True)
                    st.dataframe(df_view[['Data', 'Tipo', 'categoria', 'descricao', 'Valor']], use_container_width=True, hide_index=True)
                
                with col_chart2:
                    st.markdown("### 🍕 Gastos por Categoria")
                    df_gastos = df_mes[df_mes['tipo'] == 'Despesa']
                    if not df_gastos.empty:
                        cat_chart = df_gastos.groupby('categoria')['valor'].sum()
                        st.bar_chart(cat_chart)
                    else: st.info("Sem despesas para o gráfico.")

    # --- CARTÕES DE CRÉDITO ---
    elif menu == "Cartões de Crédito":
        st.header("💳 Gestão de Cartões")
        tab1, tab2, tab3 = st.tabs(["Faturas", "Resumo de Compras", "Configurações"])
        res_l = supabase.table("lancamentos").select("*").eq("user_id", u_id).neq("cartao_nome", None).execute()
        df_all = pd.DataFrame(res_l.data) if res_l.data else pd.DataFrame()

        with tab1:
            if not df_all.empty:
                if 'categoria' not in df_all.columns: df_all['categoria'] = 'Outros'
                df_all['data'] = pd.to_datetime(df_all['data'])
                df_all['MesAno'] = df_all['data'].dt.strftime('%m/%Y')
                meses_fatura = sorted(df_all['MesAno'].unique(), key=lambda x: pd.to_datetime(x, format='%m/%Y'))
                mes_f_sel = st.selectbox("Consultar Fatura de:", meses_fatura)
                df_f = df_all[df_all['MesAno'] == mes_f_sel].copy()
                if not df_f.empty:
                    total_f = 0
                    for cartao in df_f['cartao_nome'].unique():
                        with st.expander(f"Fatura {cartao}", expanded=True):
                            df_c = df_f[df_f['cartao_nome'] == cartao].copy()
                            sub = df_c['valor'].sum()
                            total_f += sub
                            df_c['Parc.'] = df_c['parcela_atual'].astype(str) + "/" + df_c['total_parcelas'].astype(str)
                            df_c['Valor'] = df_c['valor'].apply(format_real)
                            st.dataframe(df_c[['descricao', 'categoria', 'Parc.', 'Valor']], use_container_width=True, hide_index=True)
                            st.write(f"**Subtotal: {format_real(sub)}**")
                    st.divider()
                    st.markdown(f"### 🧾 Total das Faturas: {format_real(total_f)}")

        with tab2:
            if not df_all.empty:
                grupos = df_all.groupby(['descricao', 'cartao_nome', 'total_parcelas'])
                for i, ((desc, cartao, total_parc), df_compra) in enumerate(grupos):
                    unique_id = f"card_{i}_{desc}_{cartao}".replace(" ", "_")
                    v_total = df_compra['valor'].sum()
                    d_inicio = df_compra['data'].min()
                    with st.container():
                        c1, c2, c3, c4, c5 = st.columns([1.5, 1, 1, 0.5, 0.5])
                        c1.markdown(f"**{desc}**<br><small>{cartao} ({total_parc}x)</small>", unsafe_allow_html=True)
                        c2.write(f"Total: {format_real(v_total)}")
                        c3.write(f"Início: {pd.to_datetime(d_inicio).strftime('%d/%m/%Y')}")
                        
                        # FUNÇÃO DE EDIÇÃO REATIVADA
                        with c4.popover("📝"):
                            n_desc = st.text_input("Descrição", value=desc, key=f"ed_c_d_{unique_id}")
                            n_val = st.number_input("Novo Total", value=float(v_total), key=f"ed_c_v_{unique_id}")
                            if st.button("Salvar Alterações", key=f"btn_c_{unique_id}"):
                                supabase.table("lancamentos").delete().eq("user_id", u_id).eq("descricao", desc).eq("cartao_nome", cartao).execute()
                                v_parc = n_val / total_parc
                                for j in range(int(total_parc)):
                                    supabase.table("lancamentos").insert({
                                        "user_id": u_id, "tipo": "Despesa", "categoria": "Outros", "descricao": n_desc,
                                        "valor": round(float(v_parc), 2),
                                        "data": str(pd.to_datetime(d_inicio) + relativedelta(months=j)),
                                        "parcela_atual": j + 1, "total_parcelas": total_parc, "cartao_nome": cartao
                                    }).execute()
                                st.rerun()
                        if c5.button("❌", key=f"del_c_{unique_id}"):
                            supabase.table("lancamentos").delete().eq("user_id", u_id).eq("descricao", desc).eq("cartao_nome", cartao).execute()
                            st.rerun()
                        st.divider()

    # --- GERENCIAR OUTROS ---
    elif menu == "Gerenciar Outros":
        st.header("⚙️ Lançamentos Avulsos")
        res_o = supabase.table("lancamentos").select("*").eq("user_id", u_id).is_("cartao_nome", "null").execute()
        if res_o.data:
            df_o = pd.DataFrame(res_o.data)
            if 'categoria' not in df_o.columns: df_o['categoria'] = 'Outros'
            df_o['data'] = pd.to_datetime(df_o['data'])
            df_o['MesAno'] = df_o['data'].dt.strftime('%m/%Y')
            mes_sel_o = st.selectbox("Mês", sorted(df_o['MesAno'].unique(), reverse=True))
            df_f_o = df_o[df_o['MesAno'] == mes_sel_o].sort_values(by='data', ascending=False)
            
            for item in df_f_o.to_dict(orient='records'):
                item_id = item['id']
                icon = "🟢" if item['tipo'] == "Receita" else "🔴"
                c1, c2, c3, c4 = st.columns([2, 1, 0.5, 0.5])
                c1.write(f"{icon} {item['data'].strftime('%d/%m')} - **{item['descricao']}** ({item['categoria']})")
                c2.write(format_real(item['valor']))
                
                # FUNÇÃO DE EDIÇÃO REATIVADA
                with c3.popover("📝"):
                    n_t_o = st.selectbox("Tipo", ["Receita", "Despesa"], index=0 if item['tipo'] == "Receita" else 1, key=f"t_o_{item_id}")
                    n_cat_o = st.selectbox("Categoria", CATEGORIAS_RECEITA if n_t_o == "Receita" else CATEGORIAS_DESPESA, key=f"cat_o_{item_id}")
                    n_d_o = st.text_input("Descrição", value=item['descricao'], key=f"d_o_{item_id}")
                    n_v_o = st.number_input("Valor", value=float(item['valor']), key=f"v_o_{item_id}")
                    if st.button("Atualizar", key=f"btn_o_{item_id}"):
                        supabase.table("lancamentos").update({"tipo": n_t_o, "categoria": n_cat_o, "descricao": n_d_o, "valor": n_v_o}).eq("id", item_id).execute()
                        st.rerun()
                if c4.button("❌", key=f"del_o_{item_id}"):
                    supabase.table("lancamentos").delete().eq("id", item_id).execute()
                    st.rerun()
        else: st.info("Nenhum lançamento avulso.")
