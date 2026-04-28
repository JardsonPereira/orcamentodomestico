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
    st.error("Erro: Credenciais do Supabase não encontradas.")
    st.stop()

st.set_page_config(page_title="Gestão Financeira", layout="wide", page_icon="💰")

if 'user' not in st.session_state:
    st.session_state.user = None

def format_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

# --- AUTENTICAÇÃO ---
if st.session_state.user is None:
    st.title("💰 Orçamento Doméstico")
    aba_in, aba_up = st.tabs(["Entrar", "Cadastrar"])
    with aba_in:
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.button("Aceder"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state.user = res.user
                st.rerun()
            except: st.error("Erro no login.")
    with aba_up:
        n_email = st.text_input("Novo E-mail")
        n_senha = st.text_input("Nova Senha", type="password")
        if st.button("Criar Conta"):
            try:
                supabase.auth.sign_up({"email": n_email, "password": n_senha})
                st.success("Conta criada!")
            except Exception as e: st.error(f"Erro: {e}")
else:
    u_id = st.session_state.user.id
    st.sidebar.title("Menu")
    menu = st.sidebar.radio("Navegação", ["Dashboard Mensal", "Novo Lançamento", "Cartões de Crédito"])
    if st.sidebar.button("Sair"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    # --- LANÇAMENTOS ---
    if menu == "Novo Lançamento":
        st.header("📝 Novo Lançamento")
        with st.form("form_lan"):
            tipo = st.selectbox("Tipo", ["Receita", "Despesa"])
            desc = st.text_input("Descrição")
            valor_total = st.number_input("Valor Total (R$)", min_value=0.0, format="%.2f")
            dt_base = st.date_input("Data", date.today())
            res_c = supabase.table("cartoes").select("nome_cartao").eq("user_id", u_id).execute()
            lista_c = [c['nome_cartao'] for c in res_c.data]
            cartao_sel = st.selectbox("Cartão", ["Dinheiro/Pix"] + lista_c)
            parcelas = st.number_input("Parcelas", min_value=1, value=1)
            
            if st.form_submit_button("Salvar"):
                v_parc = valor_total / parcelas
                dados = []
                for i in range(parcelas):
                    # Guardamos a descrição limpa e adicionamos o sufixo apenas para o dashboard mensal
                    dados.append({
                        "user_id": u_id, "tipo": tipo, 
                        "descricao": desc, # Descrição limpa para agrupar fácil depois
                        "valor": round(float(v_parc), 2),
                        "data": str(dt_base + relativedelta(months=i)),
                        "parcela_atual": i + 1, "total_parcelas": parcelas,
                        "cartao_nome": cartao_sel if cartao_sel != "Dinheiro/Pix" else None
                    })
                supabase.table("lancamentos").insert(dados).execute()
                st.success("Salvo com sucesso!")

    # --- DASHBOARD MENSAL ---
    elif menu == "Dashboard Mensal":
        st.header("📊 Dashboard")
        res = supabase.table("lancamentos").select("*").eq("user_id", u_id).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['data'] = pd.to_datetime(df['data'])
            df['Mes'] = df['data'].dt.strftime('%m/%Y')
            mes_sel = st.selectbox("Mês", sorted(df['Mes'].unique(), reverse=True))
            df_mes = df[df['Mes'] == mes_sel].copy()
            # No dashboard mensal, mostramos qual parcela é (ex: Compra 1/10)
            df_mes['descricao_full'] = df_mes.apply(lambda x: f"{x['descricao']} ({x['parcela_atual']}/{x['total_parcelas']})" if x['total_parcelas'] > 1 else x['descricao'], axis=1)
            st.dataframe(df_mes[['data', 'descricao_full', 'valor']], use_container_width=True)

    # --- CARTÕES DE CRÉDITO (CORRIGIDO) ---
    elif menu == "Cartões de Crédito":
        st.header("💳 Cartões de Crédito")
        tab1, tab2, tab3 = st.tabs(["Resumo de Compras", "Gerenciar Cartões", "Novo Cartão"])

        with tab3:
            n_c = st.text_input("Nome do Cartão")
            if st.button("Salvar Cartão"):
                supabase.table("cartoes").insert({"user_id": u_id, "nome_cartao": n_c}).execute()
                st.rerun()

        with tab2:
            res_c = supabase.table("cartoes").select("*").eq("user_id", u_id).execute()
            for c in res_c.data:
                col_n, col_b = st.columns([3, 1])
                col_n.write(f"💳 {c['nome_cartao']}")
                if col_b.button("Excluir", key=c['id']):
                    supabase.table("cartoes").delete().eq("id", c['id']).execute()
                    st.rerun()

        with tab1:
            res_l = supabase.table("lancamentos").select("*").eq("user_id", u_id).neq("cartao_nome", None).execute()
            if res_l.data:
                df_all = pd.DataFrame(res_l.data)
                df_all['data'] = pd.to_datetime(df_all['data'])
                hoje = pd.to_datetime(date.today())

                # Agrupamento para mostrar apenas 1 linha por compra
                # Somamos os valores e pegamos o máximo de parcelas
                resumo = df_all.groupby(['descricao', 'cartao_nome', 'total_parcelas']).agg({
                    'valor': 'sum',
                    'data': 'min'
                }).reset_index()

                # Lógica para contar parcelas pagas (data da parcela <= hoje)
                def contar_pagas(row):
                    temp = df_all[(df_all['descricao'] == row['descricao']) & 
                                  (df_all['cartao_nome'] == row['cartao_nome']) & 
                                  (df_all['data'] <= hoje)]
                    return len(temp)

                resumo['pagas'] = resumo.apply(contar_pagas, axis=1)
                
                # Formato solicitado: Total/Pagas (Ex: 10/1)
                resumo['Parcelas'] = resumo['total_parcelas'].astype(str) + "/" + resumo['pagas'].astype(str)
                resumo['Valor Total'] = resumo['valor'].apply(format_real)
                
                # Tabela final limpa
                st.table(resumo[['cartao_nome', 'descricao', 'Parcelas', 'Valor Total']])
            else:
                st.info("Nenhuma compra parcelada encontrada.")
