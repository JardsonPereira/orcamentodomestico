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
    .stButton>button { border-radius: 12px; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); color: white; font-weight: 600; }
    .stDataFrame, .stTable { background: white; border-radius: 15px; overflow: hidden; }
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

    # --- NOVO LANÇAMENTO ---
    if menu == "Novo Lançamento":
        st.header("📝 Novo Registro")
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

    # --- DASHBOARD MENSAL ---
    elif menu == "Dashboard Mensal":
        st.header("📊 Dashboard")
        res = supabase.table("lancamentos").select("*").eq("user_id", u_id).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['data'] = pd.to_datetime(df['data'])
            df['MesAno'] = df['data'].dt.strftime('%m/%Y')
            
            aba_mensal, aba_periodo = st.tabs(["Mês Individual", "Resultado por Período"])
            
            with aba_mensal:
                meses_disponiveis = sorted(df['MesAno'].unique(), reverse=True)
                hoje_str = date.today().strftime('%m/%Y')
                idx_padrao = meses_disponiveis.index(hoje_str) if hoje_str in meses_disponiveis else 0
                mes_sel = st.selectbox("Selecione o Mês", meses_disponiveis, index=idx_padrao, key="dash_sel")
                
                df_mes = df[df['MesAno'] == mes_sel].copy()
                c1, c2, c3 = st.columns(3)
                rec = df_mes[df_mes['tipo'] == 'Receita']['valor'].sum()
                des = df_mes[df_mes['tipo'] == 'Despesa']['valor'].sum()
                c1.metric("Entradas", format_real(rec))
                c2.metric("Saídas", format_real(des))
                c3.metric("Saldo", format_real(rec - des))
                
                st.markdown("### 📋 Extrato Detalhado")
                df_view = df_mes.copy()
                df_view['Data'] = df_view['data'].dt.strftime('%d/%m/%Y')
                df_view['Valor'] = df_view['valor'].apply(format_real)
                df_view['Origem'] = df_view['cartao_nome'].fillna("💰 Avulso")
                df_view['Tipo'] = df_view['tipo'].apply(lambda x: "🟢 Receita" if x == "Receita" else "🔴 Despesa")
                df_view = df_view.sort_values(by='data', ascending=True)
                st.dataframe(df_view[['Data', 'descricao', 'Tipo', 'Origem', 'Valor']], use_container_width=True, hide_index=True)

            with aba_periodo:
                df_periodo = df.groupby(['MesAno', 'tipo'])['valor'].sum().unstack(fill_value=0)
                for col in ['Receita', 'Despesa']:
                    if col not in df_periodo.columns: df_periodo[col] = 0
                df_periodo['Resultado'] = df_periodo['Receita'] - df_periodo['Despesa']
                st.dataframe(df_periodo.style.format(format_real), use_container_width=True)

    # --- CARTÕES DE CRÉDITO (COM CONSULTA DE FATURAS FUTURAS) ---
    elif menu == "Cartões de Crédito":
        st.header("💳 Gestão de Cartões")
        tab1, tab2, tab3 = st.tabs(["Faturas (Mês a Mês)", "Resumo de Compras", "Configurações"])
        res_l = supabase.table("lancamentos").select("*").eq("user_id", u_id).neq("cartao_nome", None).execute()
        df_all = pd.DataFrame(res_l.data) if res_l.data else pd.DataFrame()

        with tab1:
            if not df_all.empty:
                df_all['data'] = pd.to_datetime(df_all['data'])
                df_all['MesAno'] = df_all['data'].dt.strftime('%m/%Y')
                
                # Gera lista de meses para consulta de faturas futuras
                meses_fatura = sorted(df_all['MesAno'].unique(), key=lambda x: pd.to_datetime(x, format='%m/%Y'), reverse=False)
                hoje_str = date.today().strftime('%m/%Y')
                idx_h = meses_fatura.index(hoje_str) if hoje_str in meses_fatura else 0
                
                col_f1, col_f2 = st.columns([1, 2])
                mes_f_sel = col_f1.selectbox("Consultar Fatura de:", meses_fatura, index=idx_h)
                
                df_f = df_all[df_all['MesAno'] == mes_f_sel].copy()
                
                if not df_f.empty:
                    total_geral_faturas = 0
                    for cartao in df_f['cartao_nome'].unique():
                        with st.expander(f"Fatura {cartao} - {mes_f_sel}", expanded=True):
                            df_c = df_f[df_f['cartao_nome'] == cartao].copy()
                            subtotal = df_c['valor'].sum()
                            total_geral_faturas += subtotal
                            
                            df_c['Parc.'] = df_c['parcela_atual'].astype(str) + "/" + df_c['total_parcelas'].astype(str)
                            df_c['Valor'] = df_c['valor'].apply(format_real)
                            st.dataframe(df_c[['descricao', 'Parc.', 'Valor']], use_container_width=True, hide_index=True)
                            st.markdown(f"**Subtotal {cartao}: {format_real(subtotal)}**")
                    
                    st.divider()
                    st.markdown(f"### 🧾 Soma Total das Faturas em {mes_f_sel}: {format_real(total_geral_faturas)}")
                else: st.info(f"Sem faturas para {mes_f_sel}.")
            else: st.info("Sem dados de cartões.")

        with tab2:
            if not df_all.empty:
                df_all['data'] = pd.to_datetime(df_all['data'])
                grupos = df_all.groupby(['descricao', 'cartao_nome', 'total_parcelas'])
                for i, ((desc, cartao, total_parc), df_compra) in enumerate(grupos):
                    unique_id = f"card_{i}_{desc}_{cartao}".replace(" ", "_")
                    v_total = df_compra['valor'].sum()
                    d_inicio = df_compra['data'].min()
                    with st.container():
                        c1, c2, c3, c4, c5, c6 = st.columns([1.5, 1, 1, 1, 0.5, 0.5])
                        c1.markdown(f"**{desc}**<br><small>{cartao} ({total_parc}x)</small>", unsafe_allow_html=True)
                        c2.write(f"Total: {format_real(v_total)}")
                        c4.write(f"Início: {d_inicio.strftime('%d/%m/%Y')}")
                        
                        with c5.popover("📝"):
                            n_desc = st.text_input("Descrição", value=desc, key=f"ed_c_d_{unique_id}")
                            n_val = st.number_input("Novo Total", value=float(v_total), key=f"ed_c_v_{unique_id}")
                            if st.button("Salvar Alterações", key=f"btn_c_{unique_id}"):
                                supabase.table("lancamentos").delete().eq("user_id", u_id).eq("descricao", desc).eq("cartao_nome", cartao).execute()
                                v_parc = n_val / total_parc
                                for j in range(int(total_parc)):
                                    supabase.table("lancamentos").insert({
                                        "user_id": u_id, "tipo": "Despesa", "descricao": n_desc,
                                        "valor": round(float(v_parc), 2),
                                        "data": str(d_inicio + relativedelta(months=j)),
                                        "parcela_atual": j + 1, "total_parcelas": total_parc, "cartao_nome": cartao
                                    }).execute()
                                st.rerun()
                        if c6.button("❌", key=f"del_c_m_{unique_id}"):
                            supabase.table("lancamentos").delete().eq("user_id", u_id).eq("descricao", desc).eq("cartao_nome", cartao).execute()
                            st.rerun()
                        st.divider()

        with tab3:
            col_nc, col_lc = st.columns(2)
            with col_nc:
                n_c = st.text_input("Novo Cartão")
                if st.button("Adicionar"):
                    supabase.table("cartoes").insert({"user_id": u_id, "nome_cartao": n_c}).execute(); st.rerun()
            with col_lc:
                res_c = supabase.table("cartoes").select("*").eq("user_id", u_id).execute()
                for c in res_c.data:
                    c1, c2 = st.columns([3, 1]); c1.write(f"💳 {c['nome_cartao']}")
                    if c2.button("Apagar", key=f"del_c_x_{c['id']}"):
                        supabase.table("lancamentos").delete().eq("user_id", u_id).eq("cartao_nome", c['nome_cartao']).execute()
                        supabase.table("cartoes").delete().eq("id", c['id']).execute(); st.rerun()

    # --- GERENCIAR OUTROS ---
    elif menu == "Gerenciar Outros":
        st.header("⚙️ Gerenciar Lançamentos Avulsos")
        res_o = supabase.table("lancamentos").select("*").eq("user_id", u_id).is_("cartao_nome", "null").execute()
        if res_o.data:
            df_o = pd.DataFrame(res_o.data)
            df_o['data'] = pd.to_datetime(df_o['data'])
            df_o['MesAno'] = df_o['data'].dt.strftime('%m/%Y')
            meses_o = sorted(df_o['MesAno'].unique(), key=lambda x: pd.to_datetime(x, format='%m/%Y'), reverse=True)
            mes_sel_o = st.selectbox("Mês para gerenciar", meses_o, key="mes_o_sel")
            
            df_f_o = df_o[df_o['MesAno'] == mes_sel_o].sort_values(by='data', ascending=False)
            st.divider()
            for item in df_f_o.to_dict(orient='records'):
                item_id = item['id']
                icon = "🟢" if item['tipo'] == "Receita" else "🔴"
                c1, c2, c3, c4 = st.columns([2, 1, 0.5, 0.5])
                c1.write(f"{icon} {item['data'].strftime('%d/%m/%Y')} - **{item['descricao']}**")
                c2.write(format_real(item['valor']))
                with c3.popover("📝"):
                    n_t_o = st.selectbox("Tipo", ["Receita", "Despesa"], index=0 if item['tipo'] == "Receita" else 1, key=f"t_o_{item_id}")
                    n_d_o = st.text_input("Descrição", value=item['descricao'], key=f"d_o_{item_id}")
                    n_v_o = st.number_input("Valor", value=float(item['valor']), key=f"v_o_{item_id}")
                    if st.button("Atualizar", key=f"btn_o_{item_id}"):
                        supabase.table("lancamentos").update({"tipo": n_t_o, "descricao": n_d_o, "valor": n_v_o}).eq("id", item_id).execute()
                        st.rerun()
                if c4.button("❌", key=f"del_o_{item_id}"):
                    supabase.table("lancamentos").delete().eq("id", item_id).execute(); st.rerun()
        else: st.info("Nenhum lançamento avulso.")
