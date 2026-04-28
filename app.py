import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
import re

# --- CONFIGURAÇÃO SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("Erro: Credenciais do Supabase não configuradas nos Secrets do Streamlit.")
    st.stop()

st.set_page_config(page_title="Gestão Financeira", layout="wide", page_icon="💰")

# --- ESTADO DA SESSÃO ---
if 'user' not in st.session_state:
    st.session_state.user = None

# --- FUNÇÕES DE UTILIDADE ---
def format_real(valor):
    """Formata número para padrão R$ 1.234,56"""
    return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

# --- AUTENTICAÇÃO ---
def tela_login():
    st.title("💰 Orçamento Doméstico")
    col_l, _ = st.columns([1, 1])
    with col_l:
        aba_in, aba_up = st.tabs(["Entrar", "Cadastrar"])
        with aba_in:
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password", key="login_pass")
            if st.button("Aceder"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                    st.session_state.user = res.user
                    st.rerun()
                except:
                    st.error("Utilizador ou senha inválidos.")
        with aba_up:
            novo_email = st.text_input("Novo E-mail")
            nova_senha = st.text_input("Nova Senha", type="password", key="reg_pass")
            if st.button("Criar Conta"):
                try:
                    res = supabase.auth.sign_up({"email": novo_email, "password": nova_senha})
                    if res.user:
                        st.success("Conta criada! Pode fazer login.")
                except Exception as e:
                    st.error(f"Erro: {e}")

# --- APP PRINCIPAL ---
if st.session_state.user is None:
    tela_login()
else:
    u_id = st.session_state.user.id
    st.sidebar.title("💰 Menu Financeiro")
    menu = st.sidebar.radio("Navegação", ["Dashboard Mensal", "Novo Lançamento", "Cartões de Crédito"])
    
    if st.sidebar.button("Sair"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    # --- ABA: LANÇAMENTOS ---
    if menu == "Novo Lançamento":
        st.header("📝 Registar Movimentação")
        with st.form("form_lan", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Receita", "Despesa"])
            desc = st.text_input("Descrição (Ex: Notebook, Supermercado)")
            valor_total = st.number_input("Valor Total (R$)", min_value=0.0, format="%.2f", step=0.01)
            data_base = st.date_input("Data de Início/Compra", date.today())
            
            res_c = supabase.table("cartoes").select("nome_cartao").eq("user_id", u_id).execute()
            lista_cartoes = [c['nome_cartao'] for c in res_c.data]
            
            cartao_sel = st.selectbox("Forma de Pagamento", ["Dinheiro/Pix/Débito"] + lista_cartoes)
            parcelas = st.number_input("Número de Parcelas", min_value=1, value=1)
            
            if st.form_submit_button("Guardar Lançamento"):
                if not desc or valor_total <= 0:
                    st.warning("Preencha a descrição e o valor.")
                else:
                    dados = []
                    valor_parc = valor_total / parcelas
                    for i in range(parcelas):
                        dados.append({
                            "user_id": u_id, "tipo": tipo,
                            "descricao": desc, # Salvamos a descrição limpa
                            "valor": round(float(valor_parc), 2),
                            "data": str(data_base + relativedelta(months=i)),
                            "parcela_atual": i + 1, "total_parcelas": parcelas,
                            "cartao_nome": cartao_sel if cartao_sel != "Dinheiro/Pix/Débito" else None
                        })
                    supabase.table("lancamentos").insert(dados).execute()
                    st.success(f"Lançamento de {parcelas}x guardado!")

    # --- ABA: DASHBOARD MENSAL ---
    elif menu == "Dashboard Mensal":
        st.header("📊 Resumo Mensal")
        res = supabase.table("lancamentos").select("*").eq("user_id", u_id).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['data'] = pd.to_datetime(df['data'])
            df['MesAno'] = df['data'].dt.strftime('%m/%Y')
            mes_sel = st.selectbox("Selecione o Mês", sorted(df['MesAno'].unique(), reverse=True))
            
            # Filtro e Remoção de Duplicados
            df_mes = df[df['MesAno'] == mes_sel].copy()
            df_mes = df_mes.drop_duplicates(subset=['data', 'descricao', 'valor', 'parcela_atual'])
            
            c1, c2, c3 = st.columns(3)
            rec = df_mes[df_mes['tipo'] == 'Receita']['valor'].sum()
            des = df_mes[df_mes['tipo'] == 'Despesa']['valor'].sum()
            c1.metric("Receitas", format_real(rec))
            c2.metric("Despesas", format_real(des))
            c3.metric("Saldo", format_real(rec - des))
            
            st.divider()
            df_mes['Exibição'] = df_mes.apply(lambda x: f"{x['descricao']} ({x['parcela_atual']}/{x['total_parcelas']})" if x['total_parcelas'] > 1 else x['descricao'], axis=1)
            df_mes['Valor R$'] = df_mes['valor'].apply(format_real)
            df_mes['Data'] = df_mes['data'].dt.strftime('%d/%m/%Y')
            
            st.dataframe(df_mes[['Data', 'Exibição', 'tipo', 'Valor R$']], use_container_width=True)
        else:
            st.info("Nenhum lançamento encontrado.")

    # --- ABA: CARTÕES DE CRÉDITO ---
    elif menu == "Cartões de Crédito":
        st.header("💳 Gestão de Cartões")
        tab1, tab2, tab3 = st.tabs(["Fatura do Mês", "Resumo Total de Compras", "Gerenciar Cartões"])

        res_l = supabase.table("lancamentos").select("*").eq("user_id", u_id).neq("cartao_nome", None).execute()
        df_all = pd.DataFrame(res_l.data) if res_l.data else pd.DataFrame()
        hoje = pd.to_datetime(date.today())

        with tab1:
            st.subheader(f"📅 Fatura de {hoje.strftime('%m/%Y')}")
            if not df_all.empty:
                df_all['data'] = pd.to_datetime(df_all['data'])
                df_fatura = df_all[df_all['data'].dt.strftime('%m/%Y') == hoje.strftime('%m/%Y')].copy()
                df_fatura = df_fatura.drop_duplicates(subset=['data', 'descricao', 'valor', 'parcela_atual'])
                
                if not df_fatura.empty:
                    for cartao in df_fatura['cartao_nome'].unique():
                        with st.expander(f"Cartão: {cartao}", expanded=True):
                            df_c = df_fatura[df_fatura['cartao_nome'] == cartao].copy()
                            df_c['Parcela'] = df_c['parcela_atual'].astype(str) + "/" + df_c['total_parcelas'].astype(str)
                            df_c['Valor R$'] = df_c['valor'].apply(format_real)
                            st.table(df_c[['data', 'descricao', 'Parcela', 'Valor R$']])
                            total_c = df_c['valor'].sum()
                            st.write(f"**Total da Fatura {cartao}:** :green[{format_real(total_c)}]")
                else:
                    st.info("Sem parcelas para este mês.")

        with tab2:
            st.subheader("📋 Histórico Total Agrupado")
            if not df_all.empty:
                # Agrupamento para mostrar apenas 1 linha por compra total
                df_all['desc_limpa'] = df_all['descricao'].apply(lambda x: re.sub(r'\s\(\d+/\d+\)$', '', str(x)))
                resumo = df_all.groupby(['desc_limpa', 'cartao_nome', 'total_parcelas']).agg({'valor': 'sum'}).reset_index()
                
                def calc_pagas(row):
                    vencidas = df_all[(df_all['desc_limpa'] == row['desc_limpa']) & (df_all['cartao_nome'] == row['cartao_nome']) & (df_all['data'] <= hoje)]
                    return len(vencidas.drop_duplicates(subset=['data', 'parcela_atual']))
                
                resumo['pagas'] = resumo.apply(calc_pagas, axis=1)
                resumo['Status (Total/Pagas)'] = resumo['total_parcelas'].astype(str) + "/" + resumo['pagas'].astype(str)
                resumo['Valor Total Compra'] = resumo['valor'].apply(format_real)
                st.table(resumo[['cartao_nome', 'desc_limpa', 'Status (Total/Pagas)', 'Valor Total Compra']])

        with tab3:
            c_a, c_b = st.columns(2)
            with c_a:
                st.subheader("Novo Cartão")
                n_c = st.text_input("Nome (ex: Nubank)")
                if st.button("Cadastrar"):
                    supabase.table("cartoes").insert({"user_id": u_id, "nome_cartao": n_c}).execute()
                    st.rerun()
            with c_b:
                st.subheader("Excluir Cartão")
                res_c = supabase.table("cartoes").select("*").eq("user_id", u_id).execute()
                for c in res_c.data:
                    col_x, col_y = st.columns([3, 1])
                    col_x.write(f"💳 {c['nome_cartao']}")
                    if col_y.button("❌", key=c['id']):
                        supabase.table("cartoes").delete().eq("id", c['id']).execute()
                        st.rerun()
